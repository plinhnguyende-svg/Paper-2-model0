"""Synthetic fixture only; cannot dispatch or open held-out evaluation."""
import json
from paper2_model0.ai.evaluation import run_synthetic_dry_run

if __name__ == '__main__':
    print(json.dumps(run_synthetic_dry_run(), sort_keys=True, allow_nan=False))
