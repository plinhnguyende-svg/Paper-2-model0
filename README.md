# Paper 2 — Model 0 v0.1

Executable baseline for the locked architecture:

- `N-H`: no blockchain / rule-based decisions
- `S-H`: selective permissioned blockchain / rule-based decisions
- `F-H`: full rival-availability visibility / rule-based decisions

Network: 2 exporters → 1 importer → 3 retailers → consumers, one perishable SKU.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Test

```bash
pytest -q
```

## Deterministic mechanism demo

```bash
python scripts/run_deterministic_demo.py
```

## Baseline stochastic experiment

```bash
python scripts/run_baseline.py \
  --config experiments/baseline.yaml \
  --output outputs/baseline
```

The run writes:

- `replication_level.csv`
- `paired_effects.csv`
- `regime_summary.csv`
- `manifest.json`

## Identification

`N → S` changes whether the importer observes verified exporter availability before allocation.

`S → F` keeps importer information/allocation unchanged and additionally reveals current rival availability to each exporter before readiness preparation.

The same exogenous demand and availability path is reused across N/S/F within every replication.

## AI gate

No RL or LLM policy is present in Model 0. The later AI branch should replace decision-policy classes while preserving the same observation objects and information rights.
