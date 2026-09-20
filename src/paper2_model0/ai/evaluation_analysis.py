"""Paired interactions and crossed seed/scenario bootstrap for the frozen design."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .evaluation import PRIMARY, SECONDARY, REGISTRY_SHA256, frozen_registry
from .training_protocol import INFORMATION_REGIMES, TRAINING_SEEDS


def panel_arrays(panel: pd.DataFrame, metric: str):
    if metric not in PRIMARY + SECONDARY:
        raise ValueError('unknown outcome')
    entries = {(e['regime'], e['training_seed']): e for e in frozen_registry()['entries']}
    if len(panel) != 3600 or set(panel.scenario_index) != set(range(200)):
        raise ValueError('expected complete 3600-row panel and 200 scenarios')
    metadata = ['scenario_index', 'scenario_id', 'evaluation_scenario_seed',
                'regime', 'decision_architecture', 'source_sha', 'registry_sha256']
    if panel[metadata].isna().any().any():
        raise ValueError('missing panel provenance')
    if panel.source_sha.nunique() != 1 or panel.registry_sha256.ne(REGISTRY_SHA256).any():
        raise ValueError('mixed source or registry provenance')
    source = str(panel.source_sha.iloc[0])
    if len(source) != 40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('invalid source SHA')
    rb = np.empty((3, 200))
    ai = np.empty((3, 5, 200))
    expected = {(r, 'RuleBased', None) for r in INFORMATION_REGIMES} | {
        (r, 'AI', s) for r in INFORMATION_REGIMES for s in TRAINING_SEEDS}
    for index, group in panel.groupby('scenario_index'):
        if len(group) != 18 or group.scenario_id.nunique() != 1 or group.evaluation_scenario_seed.nunique() != 1:
            raise ValueError('scenario pairing violated')
        keys = set()
        for row in group.itertuples():
            seed = None if pd.isna(row.training_seed) else row.training_seed
            key = (row.regime, row.decision_architecture, seed)
            if key not in expected or key in keys:
                raise ValueError('duplicate, missing or unexpected treatment')
            keys.add(key)
            r = INFORMATION_REGIMES.index(row.regime)
            if seed is None:
                if not pd.isna(row.checkpoint_sha256):
                    raise ValueError('RuleBased row must not reference a checkpoint')
                rb[r, index] = getattr(row, metric)
            else:
                if row.checkpoint_sha256 != entries[row.regime, seed]['final_checkpoint_sha256']:
                    raise ValueError('checkpoint provenance mismatch')
                ai[r, TRAINING_SEEDS.index(seed), index] = getattr(row, metric)
        if keys != expected:
            raise ValueError('missing treatment')
    if panel[['scenario_index', 'scenario_id']].drop_duplicates().scenario_id.nunique() != 200:
        raise ValueError('scenario IDs must be unique')
    if panel[['scenario_index', 'evaluation_scenario_seed']].drop_duplicates().evaluation_scenario_seed.nunique() != 200:
        raise ValueError('scenario seeds must be unique')
    if not np.isfinite(rb).all() or not np.isfinite(ai).all():
        raise ValueError('undefined outcome: retain raw rows; do not drop observations')
    return rb, ai


def paired_bootstrap(rb: np.ndarray, ai: np.ndarray) -> dict:
    rb, ai = np.asarray(rb, dtype=float), np.asarray(ai, dtype=float)
    if rb.shape != (3, 200) or ai.shape != (3, 5, 200):
        raise ValueError('expected 3 regimes x 5 training seeds x 200 paired scenarios')
    if not np.isfinite(rb).all() or not np.isfinite(ai).all():
        raise ValueError('bootstrap requires finite complete outcomes')
    # Common draws for both interactions and all outcomes. This numeric seed
    # controls Monte Carlo integration only, never simulation or selection.
    rng = np.random.default_rng(62001)
    contrasts = np.diff(ai, axis=0) - np.diff(rb, axis=0)[:, None, :]
    draws = np.empty((10000, 2))
    for b in range(10000):
        seeds = rng.integers(0, 5, size=5)
        scenarios = rng.integers(0, 200, size=200)
        draws[b] = contrasts[:, seeds][:, :, scenarios].mean(axis=(1, 2))
    result = {}
    for i, name in enumerate(('Gamma_V', 'Gamma_H')):
        result[name] = {
            'mean': float(contrasts[i].mean()),
            'ci95': np.quantile(draws[:, i], [0.025, 0.975]).tolist(),
            'between_seed_sd': float(contrasts[i].mean(axis=1).std(ddof=1)),
            'seed_means': contrasts[i].mean(axis=1).tolist(),
        }
    return result


def analyze_final_panel(panel: pd.DataFrame) -> dict:
    # Descriptive estimates/CIs only. No p-values or significance claims;
    # Holm across ten tests is mandatory if a later reviewed layer adds them.
    return {metric: paired_bootstrap(*panel_arrays(panel, metric)) for metric in PRIMARY}
