from __future__ import annotations

import numpy as np
import pandas as pd


def safe_variance_ratio(numerator, denominator) -> float:
    num = np.var(np.asarray(numerator, dtype=float), ddof=1)
    den = np.var(np.asarray(denominator, dtype=float), ddof=1)
    if den <= 1e-15:
        return float("nan")
    return float(num / den)


def replication_metrics(period_df: pd.DataFrame, warmup_days: int) -> dict:
    df = period_df.loc[period_df["day"] >= warmup_days].copy()
    demand = df["aggregate_consumer_demand"].to_numpy()
    retail_orders = df["aggregate_retailer_orders"].to_numpy()
    q = df["procurement_requirement"].to_numpy()

    demand_total = float(df["aggregate_consumer_demand"].sum())
    fulfilled_total = float(df["aggregate_fulfilled_consumer_demand"].sum())
    waste_total = float(df["total_waste"].sum())
    terminal_outflow_total = fulfilled_total + waste_total

    def readiness_vol(col: str) -> float:
        return safe_variance_ratio(df[col].to_numpy(), demand)

    metrics = {
        "service_level": fulfilled_total / demand_total if demand_total > 0 else float("nan"),
        # Window-consistent physical-loss metric: both numerator and denominator are
        # terminal exits observed within the measurement window. This avoids mixing
        # post-warm-up waste with only post-warm-up preparation cohorts.
        "waste_share_of_terminal_outflow": (
            waste_total / terminal_outflow_total
            if terminal_outflow_total > 0
            else float("nan")
        ),
        "retail_order_bullwhip": safe_variance_ratio(retail_orders, demand),
        "importer_procurement_bullwhip": safe_variance_ratio(q, demand),
        "exporter_1_allocation_volatility": safe_variance_ratio(df["allocation_1"], demand),
        "exporter_2_allocation_volatility": safe_variance_ratio(df["allocation_2"], demand),
        "exporter_1_readiness_volatility": readiness_vol("prepared_quantity_1"),
        "exporter_2_readiness_volatility": readiness_vol("prepared_quantity_2"),
        "mean_total_inventory": float(df["total_on_hand_inventory"].mean()),
        "total_lost_sales": float(df["aggregate_lost_sales"].sum()),
        "total_waste": waste_total,
        "mean_abs_target_allocation_gap_1": float(df["abs_target_allocation_gap_1"].mean()),
        "mean_abs_target_allocation_gap_2": float(df["abs_target_allocation_gap_2"].mean()),
        "mean_abs_stock_allocation_gap_1": float(df["abs_stock_allocation_gap_1"].mean()),
        "mean_abs_stock_allocation_gap_2": float(df["abs_stock_allocation_gap_2"].mean()),
    }
    return metrics
