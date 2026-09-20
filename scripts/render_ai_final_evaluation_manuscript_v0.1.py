#!/usr/bin/env python3
"""Render manuscript-facing R3 tables and SVGs from frozen registries only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

PRIMARY_BLOB = "40d590f742c85f7e853bd3766a41fc335510b4b9"
SECONDARY_BLOB = "3f99a7cca25e4ee7248d48e90d1db5aa45a08fe1"

PRIMARY_ORDER = (
    "service_level",
    "waste_share_of_terminal_outflow",
    "importer_procurement_bullwhip",
    "mean_total_inventory",
    "mean_abs_target_allocation_gap_exporter_average",
)
SECONDARY_ORDER = (
    "retail_order_bullwhip",
    "total_lost_sales",
    "total_waste",
    "mean_abs_stock_allocation_gap_exporter_average",
)
LABELS = {
    "service_level": "Service level",
    "waste_share_of_terminal_outflow": "Waste share of terminal outflow",
    "importer_procurement_bullwhip": "Importer procurement bullwhip",
    "mean_total_inventory": "Mean total inventory",
    "mean_abs_target_allocation_gap_exporter_average": "Target-allocation gap",
    "retail_order_bullwhip": "Retail-order bullwhip",
    "total_lost_sales": "Total lost sales",
    "total_waste": "Total waste",
    "mean_abs_stock_allocation_gap_exporter_average": "Stock-allocation gap",
}
SEEDS = (41001, 41002, 41003, 41004, 41005)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load_json(path: Path, expected_blob: str) -> dict:
    if git_blob_sha(path) != expected_blob:
        raise ValueError(f"frozen registry Git blob mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry must contain one JSON object")
    return value


def fmt(value: float) -> str:
    return f"{float(value):.6f}"


def rows_primary(registry: dict) -> list[dict]:
    results = registry.get("primary_results", {})
    if tuple(results) != PRIMARY_ORDER:
        raise ValueError("primary registry ordering/scope drift")
    rows = []
    for outcome in PRIMARY_ORDER:
        for estimand in ("Gamma_V", "Gamma_H"):
            item = results[outcome][estimand]
            rows.append(_row("PRIMARY", outcome, estimand, item))
    return rows


def rows_exploratory(registry: dict) -> list[dict]:
    results = registry.get("secondary_results", {})
    if tuple(results) != SECONDARY_ORDER:
        raise ValueError("secondary registry ordering/scope drift")
    rows = []
    for outcome in SECONDARY_ORDER:
        block = results[outcome]["frozen_exploratory_interactions"]
        for estimand in ("Gamma_V", "Gamma_H"):
            rows.append(_row("EXPLORATORY", outcome, estimand, block[estimand]))
    return rows


def _row(layer: str, outcome: str, estimand: str, item: dict) -> dict:
    seeds = item["seed_means"]
    if len(seeds) != 5:
        raise ValueError("expected five frozen seed means")
    return {
        "layer": layer,
        "outcome_key": outcome,
        "outcome_label": LABELS[outcome],
        "estimand": estimand,
        "mean": float(item["mean"]),
        "ci_low": float(item["ci95"][0]),
        "ci_high": float(item["ci95"][1]),
        "between_seed_sd": float(item["between_seed_sd"]),
        **{f"seed_{seed}": float(value) for seed, value in zip(SEEDS, seeds)},
    }


def csv_text(rows: list[dict]) -> str:
    fields = [
        "layer", "outcome_key", "outcome_label", "estimand",
        "mean", "ci_low", "ci_high", "between_seed_sd",
        *[f"seed_{seed}" for seed in SEEDS],
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            key: (fmt(row[key]) if key not in {"layer", "outcome_key", "outcome_label", "estimand"} else row[key])
            for key in fields
        })
    return output.getvalue()


def markdown_text(rows: list[dict], layer: str) -> str:
    lines = [
        f"# {layer} interaction results",
        "",
        f"**Layer:** {layer}",
        "",
        "| Outcome | Estimand | Mean | 95% interval | Between-seed SD |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['outcome_label']} | {row['estimand']} | {fmt(row['mean'])} | "
            f"[{fmt(row['ci_low'])}, {fmt(row['ci_high'])}] | {fmt(row['between_seed_sd'])} |"
        )
    lines += [
        "",
        "Numbers are display-formatted copies of frozen registry values; no scientific estimate is recomputed here.",
        "",
    ]
    return "\n".join(lines)


def svg_text(rows: list[dict], layer: str) -> str:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["outcome_key"], []).append(row)
    order = PRIMARY_ORDER if layer == "PRIMARY" else SECONDARY_ORDER
    panel_h = 150
    width = 1100
    height = 70 + panel_h * len(order)
    left, right = 320.0, 1040.0
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font-family:Arial,sans-serif;font-size:14px;fill:currentColor}.title{font-size:20px;font-weight:700}.label{font-weight:700}.axis{stroke:currentColor;stroke-width:1}.ci{stroke:currentColor;stroke-width:3}.zero{stroke:currentColor;stroke-width:1;stroke-dasharray:5 5}.point{fill:currentColor}</style>',
        f'<text x="20" y="32" class="title">{escape(layer)} interaction estimates — frozen 95% intervals</text>',
        f'<text x="20" y="54">{escape(layer)} — presentation only; each outcome has its own scale.</text>',
    ]
    for idx, outcome in enumerate(order):
        block = grouped[outcome]
        lo = min(0.0, *(r["ci_low"] for r in block))
        hi = max(0.0, *(r["ci_high"] for r in block))
        span = hi - lo
        pad = 0.08 * span if span > 0 else 1.0
        lo -= pad
        hi += pad
        def xpos(value: float) -> float:
            return left + (float(value) - lo) / (hi - lo) * (right - left)
        top = 70 + idx * panel_h
        y_v, y_h, y_axis = top + 55, top + 92, top + 122
        zero_x = xpos(0.0)
        out += [
            f'<text x="20" y="{top+26}" class="label">{escape(LABELS[outcome])}</text>',
            f'<line x1="{left:.2f}" y1="{y_axis}" x2="{right:.2f}" y2="{y_axis}" class="axis"/>',
            f'<line x1="{zero_x:.2f}" y1="{top+38}" x2="{zero_x:.2f}" y2="{y_axis}" class="zero"/>',
            f'<text x="250" y="{y_v+5}" text-anchor="end">Gamma_V</text>',
            f'<text x="250" y="{y_h+5}" text-anchor="end">Gamma_H</text>',
            f'<text x="{left:.2f}" y="{y_axis+20}" text-anchor="start">{escape(fmt(lo))}</text>',
            f'<text x="{right:.2f}" y="{y_axis+20}" text-anchor="end">{escape(fmt(hi))}</text>',
        ]
        for row, y in zip(block, (y_v, y_h)):
            x1, x2, xm = xpos(row["ci_low"]), xpos(row["ci_high"]), xpos(row["mean"])
            out += [
                f'<line x1="{x1:.2f}" y1="{y}" x2="{x2:.2f}" y2="{y}" class="ci"/>',
                f'<circle cx="{xm:.2f}" cy="{y}" r="5" class="point"/>',
            ]
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write_exact(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--primary-registry", type=Path, default=Path("experiments/ai_final_evaluation_result_registry_v0.1.json"))
    p.add_argument("--secondary-registry", type=Path, default=Path("experiments/ai_final_evaluation_secondary_result_registry_v0.1.json"))
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()

    primary = rows_primary(load_json(args.primary_registry, PRIMARY_BLOB))
    exploratory = rows_exploratory(load_json(args.secondary_registry, SECONDARY_BLOB))

    write_exact(args.output_dir / "table_primary_interactions.csv", csv_text(primary))
    write_exact(args.output_dir / "table_primary_interactions.md", markdown_text(primary, "PRIMARY"))
    write_exact(args.output_dir / "figure_primary_interactions.svg", svg_text(primary, "PRIMARY"))
    write_exact(args.output_dir / "table_exploratory_interactions.csv", csv_text(exploratory))
    write_exact(args.output_dir / "table_exploratory_interactions.md", markdown_text(exploratory, "EXPLORATORY"))
    write_exact(args.output_dir / "figure_exploratory_interactions.svg", svg_text(exploratory, "EXPLORATORY"))


if __name__ == "__main__":
    main()
