from __future__ import annotations
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest
import torch

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai.evaluation_analysis import panel_arrays, paired_bootstrap
from paper2_model0.ai.training_protocol import (
    TRAINING_SEEDS, build_run_manifest, checkpoint_payload, episode_scenario_seed,
    run_manifest_hash,
)
from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario


def test_candidate_cannot_touch_heldout_or_create_output(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('held-out execution touched a protected resource')
    monkeypatch.setattr(ev, 'generate_scenario', forbidden)
    monkeypatch.setattr(ev, 'load_registered_policy', forbidden)
    with pytest.raises(PermissionError, match='not frozen'):
        ev.run_final_evaluation(tmp_path, tmp_path / 'output', 'a' * 40)
    assert not (tmp_path / 'output').exists()


def test_registry_hash_binding_and_seed_disjointness(tmp_path, monkeypatch):
    assert len(ev.frozen_registry()['entries']) == 15
    seeds = ev.evaluation_seed_schedule()
    assert len(set(seeds)) == 200
    assert seeds == ev.evaluation_seed_schedule()
    assert not set(seeds).intersection(range(41001000, 41006000))
    altered = tmp_path / 'registry.json'
    altered.write_bytes(ev.REGISTRY_PATH.read_bytes() + b' ')
    monkeypatch.setattr(ev, 'REGISTRY_PATH', altered)
    with pytest.raises(ValueError, match='hash mismatch'):
        ev.frozen_registry()


def test_synthetic_dry_run_never_generates_or_reads_heldout(monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('dry-run accessed scientific data')
    monkeypatch.setattr(ev, 'generate_scenario', forbidden)
    monkeypatch.setattr(ev, 'load_registered_policy', forbidden)
    result = ev.run_synthetic_dry_run()
    assert result['trajectory_count'] == 18
    assert result['horizon'] == 8
    assert result['fixture_seed'] == 909001
    assert all(row[k] is not None for row in result['rows'] for k in ev.PRIMARY)


def test_deterministic_inference_preserves_weights_and_rngs():
    config, scenario = ev.tiny_deterministic_smoke_case()
    initial = ev.ActorLocalAIDecisionArchitecture(config, training_seed=41001, deterministic=True)
    payload = {'actors': {n: {'network': copy.deepcopy(a.network.state_dict())}
                          for n, a in initial.agents.items()}}
    policy = ev._network_architecture(payload, config, 41001)
    rng = {n: a.action_generator.get_state().clone() for n, a in policy.agents.items()}
    first = ev._evaluate_one(config, scenario, 'N', policy)
    second = ev._evaluate_one(config, scenario, 'N', policy)
    assert first == second
    for n, a in policy.agents.items():
        assert a.updater is None
        assert not a.network.training
        assert all(not p.requires_grad for p in a.network.parameters())
        assert torch.equal(rng[n], a.action_generator.get_state())
        for key, value in a.network.state_dict().items():
            assert torch.equal(value, payload['actors'][n]['network'][key])
    policy.importer_policy.deterministic = False
    with pytest.raises(ValueError, match='deterministic'):
        ev._evaluate_one(config, scenario, 'N', policy)


def test_metric_warmup_and_exporter_average():
    config, scenario = ev.tiny_deterministic_smoke_case()
    df = ev.SupplyChainModel(config, 'S', scenario).run()
    measured = df.loc[df.day >= 3]
    metrics = ev.evaluation_metrics(df, 3)
    assert metrics['total_lost_sales'] == measured.aggregate_lost_sales.sum()
    assert metrics['mean_abs_target_allocation_gap_exporter_average'] == pytest.approx(
        (measured.abs_target_allocation_gap_1.mean() + measured.abs_target_allocation_gap_2.mean()) / 2)
    df.loc[:, 'aggregate_consumer_demand'] = 10
    assert ev.evaluation_metrics(df, 3)['importer_procurement_bullwhip'] is None


def _synthetic_archive(tmp_path, monkeypatch, mutation=None):
    # Production-shaped synthetic checkpoint, no training or held-out scenario.
    config = SimulationConfig()
    registry = ev.frozen_registry()
    entry = next(e for e in registry['entries'] if (e['regime'], e['training_seed']) == ('N', 41001))
    manifest = build_run_manifest(
        regime='N', training_seed=41001, config=config,
        source_commit_sha=registry['frozen_launcher_source_sha'],
        episode_records=[{'episode_index': i, 'episode_seed': episode_scenario_seed(41001, i),
                          'scenario_id': f'synthetic-training-id-{i}'} for i in range(1000)])
    architecture = ev.ActorLocalAIDecisionArchitecture(config, training_seed=41001)
    payload = checkpoint_payload(architecture=architecture, regime='N',
                                 completed_episode_count=1000, config=config, manifest=manifest)
    if mutation:
        mutation(payload)
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    data = buffer.getvalue()
    entry['final_checkpoint_sha256'] = hashlib.sha256(data).hexdigest()
    entry['final_manifest_sha256'] = run_manifest_hash(manifest)
    archive = tmp_path / 'synthetic.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('state/checkpoint_episode_1000.pt', data)
        z.writestr('state/manifest_episode_1000.json', json.dumps(manifest))
    entry['artifact_digest'] = 'sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(ev, 'frozen_registry', lambda: registry)
    return archive, entry


def test_loader_verifies_bytes_before_decode_and_loads_only_network(tmp_path, monkeypatch):
    archive, entry = _synthetic_archive(tmp_path, monkeypatch)
    policy, _, _ = ev.load_registered_policy(archive, 'N', 41001)
    assert all(a.updater is None for a in policy.agents.values())
    entry['final_checkpoint_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checkpoint SHA'):
        ev.load_registered_policy(archive, 'N', 41001)
    archive.write_bytes(archive.read_bytes() + b'tampered')
    monkeypatch.setattr(torch, 'load', lambda *a, **k: pytest.fail('decoded before hash verification'))
    with pytest.raises(ValueError, match='ZIP digest'):
        ev.load_registered_policy(archive, 'N', 41001)


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(completed_episode_count=999),
    lambda p: p.update(regime='F'),
    lambda p: p['actors'].pop('E2'),
    lambda p: next(iter(p['actors']['R1']['network'].values())).fill_(float('nan')),
])
def test_loader_rejects_invalid_final_checkpoint(tmp_path, monkeypatch, mutation):
    archive, _ = _synthetic_archive(tmp_path, monkeypatch, mutation)
    with pytest.raises(ValueError):
        ev.load_registered_policy(archive, 'N', 41001)


def synthetic_panel():
    entries = {(e['regime'], e['training_seed']): e for e in ev.frozen_registry()['entries']}
    rows = []
    schedule = ev.evaluation_seed_schedule()
    for i in range(200):
        for r, regime in enumerate(('N', 'S', 'F')):
            for seed in (None, *TRAINING_SEEDS):
                value = 20 * r + i
                if seed is not None:
                    value += [0, 3, 8][r]
                rows.append(dict(scenario_index=i, scenario_id=f'synthetic-{i}',
                    evaluation_scenario_seed=str(schedule[i]), regime=regime,
                    decision_architecture='RuleBased' if seed is None else 'AI',
                    training_seed=seed, source_sha='a' * 40, registry_sha256=ev.REGISTRY_SHA256,
                    checkpoint_sha256=None if seed is None else entries[regime, seed]['final_checkpoint_sha256'],
                    **{k: value for k in ev.PRIMARY + ev.SECONDARY}))
    return pd.DataFrame(rows)


def test_known_interactions_bootstrap_and_single_rulebased_panel():
    panel = synthetic_panel()
    assert panel.decision_architecture.eq('RuleBased').sum() == 600
    rb, ai = panel_arrays(panel.sample(frac=1, random_state=5), ev.PRIMARY[0])
    result = paired_bootstrap(rb, ai)
    assert result['Gamma_V']['mean'] == pytest.approx(3)
    assert result['Gamma_V']['ci95'] == pytest.approx([3, 3])
    assert result['Gamma_H']['ci95'] == pytest.approx([5, 5])
    assert result['Gamma_H']['between_seed_sd'] == 0


def test_bootstrap_seed_uncertainty_and_common_scenario_draws():
    rb = np.zeros((3, 200))
    rb[1] = np.arange(200) * 100
    rb[2] = np.arange(200) * 400
    ai = np.repeat(rb[:, None, :], 5, axis=1)
    ai[1] += np.arange(5)[:, None]
    ai[2] += 2 * np.arange(5)[:, None]
    result = paired_bootstrap(rb, ai)
    assert result['Gamma_V'] == result['Gamma_H']
    assert result['Gamma_V']['mean'] == 2
    assert result['Gamma_V']['between_seed_sd'] == pytest.approx(np.std(range(5), ddof=1))
    assert result['Gamma_V']['ci95'][0] < 2 < result['Gamma_V']['ci95'][1]


@pytest.mark.parametrize('case', ['duplicate', 'missing', 'pairing', 'checkpoint', 'source', 'nan', 'seed_schedule'])
def test_panel_rejects_invalid_evidence(case):
    panel = synthetic_panel()
    if case == 'duplicate': panel.iloc[1] = panel.iloc[0]
    if case == 'missing': panel = panel.iloc[:-1]
    if case == 'pairing': panel.loc[0, 'scenario_id'] = 'wrong'
    if case == 'checkpoint': panel.loc[1, 'checkpoint_sha256'] = '0' * 64
    if case == 'source': panel.loc[0, 'source_sha'] = 'b' * 40
    if case == 'nan': panel.loc[0, ev.PRIMARY[0]] = np.nan
    if case == 'seed_schedule': panel.loc[panel.scenario_index == 0, 'evaluation_scenario_seed'] = '123'
    with pytest.raises(ValueError):
        panel_arrays(panel, ev.PRIMARY[0])
