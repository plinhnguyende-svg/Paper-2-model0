"""Candidate final evaluation implementation; held-out execution remains closed."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

import numpy as np
import pandas as pd
import torch

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.experiments.metrics import replication_metrics
from .environment import ActorLocalAIDecisionArchitecture, tiny_deterministic_smoke_case
from .training_protocol import (
    TRAINING_SEEDS, INFORMATION_REGIMES, CHECKPOINT_VERSION,
    RUNNER_PROTOCOL_VERSION, SCENARIO_SEED_PROTOCOL_VERSION,
    FROZEN_SMOKE_BASE, AI_SPEC_BASE, simulation_config_payload,
    simulation_config_hash, episode_seed_schedule, runtime_fingerprint,
    run_manifest_hash,
)

REGISTRY_FREEZE_COMMIT = '85bd9686985f994a3f4557198e966bdbd07c53da'
REGISTRY_SHA256 = '0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a'
REGISTRY_PATH = Path(__file__).resolve().parents[3] / 'experiments/ai_training_checkpoint_registry_v0.1.json'
PRIMARY = (
    'service_level', 'waste_share_of_terminal_outflow',
    'importer_procurement_bullwhip', 'mean_total_inventory',
    'mean_abs_target_allocation_gap_exporter_average',
)
SECONDARY = (
    'retail_order_bullwhip', 'total_lost_sales', 'total_waste',
    'mean_abs_stock_allocation_gap_exporter_average',
)


FROZEN_EVALUATION_REPOSITORY = 'plinhnguyende-svg/Paper-2-model0'
FROZEN_EVALUATION_REF = 'refs/heads/ai-final-evaluation-v0.1-frozen'
FROZEN_EVALUATION_WORKFLOW_PATH = '.github/workflows/ai_final_evaluation_v0.1.yml'


def _full_git_sha(value: str, label: str) -> str:
    value = str(value).strip().lower()
    if len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
        raise PermissionError(f'{label} must be an exact 40-character git SHA')
    return value


def require_evaluation_freeze() -> dict:
    """Fail closed unless a later frozen workflow supplies exact provenance."""
    if os.environ.get('PAPER2_AI_FINAL_EVALUATION_AUTHORIZED') != 'YES':
        raise PermissionError('Final evaluation runner is not frozen/authorized')
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise PermissionError('Final evaluation is authorized only in GitHub Actions')
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise PermissionError('Final evaluation requires manual workflow_dispatch')
    if os.environ.get('GITHUB_REPOSITORY') != FROZEN_EVALUATION_REPOSITORY:
        raise PermissionError('Final evaluation repository mismatch')
    if os.environ.get('GITHUB_REF') != FROZEN_EVALUATION_REF:
        raise PermissionError('Final evaluation frozen ref mismatch')
    expected_workflow_ref = (
        f'{FROZEN_EVALUATION_REPOSITORY}/{FROZEN_EVALUATION_WORKFLOW_PATH}'
        f'@{FROZEN_EVALUATION_REF}'
    )
    if os.environ.get('GITHUB_WORKFLOW_REF') != expected_workflow_ref:
        raise PermissionError('Final evaluation workflow ref/path mismatch')
    evaluator_sha = _full_git_sha(
        os.environ.get('PAPER2_AI_FROZEN_EVALUATOR_SHA', ''),
        'PAPER2_AI_FROZEN_EVALUATOR_SHA',
    )
    workflow_sha = _full_git_sha(
        os.environ.get('PAPER2_AI_FROZEN_WORKFLOW_SHA', ''),
        'PAPER2_AI_FROZEN_WORKFLOW_SHA',
    )
    if _full_git_sha(os.environ.get('GITHUB_SHA', ''), 'GITHUB_SHA') != workflow_sha:
        raise PermissionError('workflow execution SHA differs from frozen workflow SHA')
    repo_root = Path(__file__).resolve().parents[3]
    actual_source = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=repo_root, text=True
    ).strip().lower()
    if _full_git_sha(actual_source, 'checked-out evaluator SHA') != evaluator_sha:
        raise PermissionError('checked-out evaluator source differs from frozen evaluator SHA')
    try:
        run_id = int(os.environ.get('GITHUB_RUN_ID', ''))
        run_attempt = int(os.environ.get('GITHUB_RUN_ATTEMPT', ''))
    except ValueError as exc:
        raise PermissionError('GitHub run provenance is invalid') from exc
    if run_id <= 0 or run_attempt <= 0:
        raise PermissionError('GitHub run provenance must be positive')
    return {
        'evaluator_sha': evaluator_sha,
        'workflow_sha': workflow_sha,
        'run_id': run_id,
        'run_attempt': run_attempt,
        'workflow_ref': expected_workflow_ref,
    }


def frozen_registry() -> dict:
    data = REGISTRY_PATH.read_bytes()
    if hashlib.sha256(data).hexdigest() != REGISTRY_SHA256:
        raise ValueError('frozen checkpoint registry hash mismatch')
    return json.loads(data)


def evaluation_seed_schedule() -> tuple[int, ...]:
    """Existing Model-0 SeedSequence convention, without generating outcomes."""
    children = np.random.SeedSequence(52001).spawn(200)
    seeds = tuple(int(child.generate_state(1, dtype=np.uint64)[0]) for child in children)
    training = {seed for s in TRAINING_SEEDS for seed in episode_seed_schedule(s)}
    if len(set(seeds)) != 200 or training.intersection(seeds):
        raise ValueError('evaluation seed collision')
    return seeds


def _network_architecture(payload: dict, config: SimulationConfig, seed: int):
    architecture = ActorLocalAIDecisionArchitecture(config, training_seed=seed, deterministic=True)
    if set(payload['actors']) != set(architecture.agents):
        raise ValueError('checkpoint must contain exactly six actors')
    for name, agent in architecture.agents.items():
        state = payload['actors'][name]['network']
        if any(not torch.isfinite(t).all() for t in state.values()):
            raise ValueError('non-finite network state')
        agent.network.load_state_dict(state, strict=True)
        agent.network.eval()
        agent.network.requires_grad_(False)
        # Evaluation never restores an optimizer or action RNG from training.
        # Disable the updater explicitly as well as omitting all update calls.
        agent.updater = None
    return architecture


def load_registered_policy(archive: Path, regime: str, training_seed: int):
    registry = frozen_registry()
    matches = [e for e in registry['entries']
               if (e['regime'], e['training_seed']) == (regime, training_seed)]
    if len(matches) != 1:
        raise ValueError('policy is not in the frozen registry')
    entry = matches[0]
    data = archive.read_bytes()
    if 'sha256:' + hashlib.sha256(data).hexdigest() != entry['artifact_digest']:
        raise ValueError('artifact ZIP digest mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        # Read exact bytes in memory; never extract archive paths to disk.
        checkpoints = [n for n in z.namelist() if Path(n).name == entry['final_checkpoint_file']]
        manifests = [n for n in z.namelist() if Path(n).name == 'manifest_episode_1000.json']
        if len(checkpoints) != 1 or len(manifests) != 1:
            raise ValueError('artifact requires exactly one final checkpoint and manifest')
        checkpoint = z.read(checkpoints[0])
        manifest = json.loads(z.read(manifests[0]))
    if hashlib.sha256(checkpoint).hexdigest() != entry['final_checkpoint_sha256']:
        raise ValueError('checkpoint SHA-256 mismatch')
    if run_manifest_hash(manifest) != entry['final_manifest_sha256']:
        raise ValueError('manifest SHA-256 mismatch')
    config = SimulationConfig()
    for key, expected in {
        'regime': regime, 'training_seed': training_seed,
        'completed_episode_count': 1000,
        'source_commit_sha': registry['frozen_launcher_source_sha'],
        'simulation_config': simulation_config_payload(config),
        'runtime_fingerprint': runtime_fingerprint(),
    }.items():
        if manifest.get(key) != expected:
            raise ValueError(f'manifest {key} mismatch')
    payload = torch.load(io.BytesIO(checkpoint), map_location='cpu', weights_only=True)
    expected_metadata = {
        'checkpoint_version': CHECKPOINT_VERSION,
        'runner_protocol_version': RUNNER_PROTOCOL_VERSION,
        'scenario_seed_protocol_version': SCENARIO_SEED_PROTOCOL_VERSION,
        'frozen_smoke_base': FROZEN_SMOKE_BASE, 'ai_spec_base': AI_SPEC_BASE,
        'regime': regime, 'training_seed': training_seed, 'completed_episode_count': 1000,
        'simulation_config': simulation_config_payload(config),
        'simulation_config_sha256': simulation_config_hash(config),
        'run_manifest_sha256': entry['final_manifest_sha256'],
    }
    if any(payload.get(k) != v for k, v in expected_metadata.items()):
        raise ValueError('checkpoint metadata mismatch')
    return _network_architecture(payload, config, training_seed), entry, manifest


def evaluation_metrics(periods: pd.DataFrame, warmup: int) -> dict:
    metrics = replication_metrics(periods, warmup)
    for kind in ('target', 'stock'):
        metrics[f'mean_abs_{kind}_allocation_gap_exporter_average'] = (
            metrics[f'mean_abs_{kind}_allocation_gap_1']
            + metrics[f'mean_abs_{kind}_allocation_gap_2']
        ) / 2
    # Retain undefined outcomes as null, never silently drop trajectories.
    return {k: float(metrics[k]) if np.isfinite(metrics[k]) else None
            for k in PRIMARY + SECONDARY}


def _evaluate_one(config, scenario, regime, architecture=None):
    if architecture is not None:
        architecture.clear_episode_records()
        if any(agent.updater is not None for agent in architecture.agents.values()):
            raise ValueError('evaluation architecture must have learning disabled')
        policies = (*architecture.retailer_policies, architecture.importer_policy,
                    *architecture.exporter_policies)
        if any(not p.deterministic or p.before_decision is not None for p in policies):
            raise ValueError('evaluation requires deterministic policies without hooks')
    with torch.inference_mode():
        periods = SupplyChainModel(config, regime, scenario,
                                   decision_architecture=architecture).run()
    return evaluation_metrics(periods, config.warmup_days)


def run_final_evaluation(archive_dir: Path, output_dir: Path, source_sha: str):
    # Permanently disabled. Once the authorization gate is opened, the only
    # admissible held-out path is the audited sharded execution protocol.
    raise PermissionError(
        'Monolithic final evaluation is disabled; use the frozen sharded evaluator'
    )

def run_synthetic_dry_run() -> dict:
    """All 18 policy/regime combinations, using only the existing 8-day fixture."""
    config, scenario = tiny_deterministic_smoke_case()
    rows = []
    for regime in INFORMATION_REGIMES:
        rows.append({'regime': regime, 'training_seed': None,
                     **_evaluate_one(config, scenario, regime)})
        for seed in TRAINING_SEEDS:
            initial = ActorLocalAIDecisionArchitecture(config, training_seed=seed, deterministic=True)
            payload = {'actors': {n: {'network': a.network.state_dict()}
                                  for n, a in initial.agents.items()}}
            policy = _network_architecture(payload, config, seed)
            rows.append({'regime': regime, 'training_seed': seed,
                         **_evaluate_one(config, scenario, regime, policy)})
    return {'status': 'SYNTHETIC_ONLY_NOT_SCIENTIFIC_RESULTS',
            'fixture_seed': scenario.replication_seed, 'horizon': 8,
            'trajectory_count': len(rows), 'rows': rows}
