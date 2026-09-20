# Final evaluation runner candidate v0.1

Status: IMPLEMENTATION FOR REVIEW. Held-out execution remains unconditionally
closed. This PR must not be interpreted as a scientific evaluation result or
as permission to launch final evaluation.

## Registry freeze completed

PR #11 merged at `85bd9686985f994a3f4557198e966bdbd07c53da` after both PR
workflows (CI and AI Full Training Freeze Gate) completed successfully on head
`2a1df11c46d45bc99ceac3f2fbc8ecad3601a4a1`.

Before merge, the 15 registry artifact IDs, names and ZIP digests were compared
with the live GitHub artifacts endpoint for run `35439893662`: all matched;
none was expired. The two registry contract checks also passed locally.
This was a metadata/provenance recheck; it did not repeat the earlier binary
checkpoint and diagnostic recomputation audit recorded in PR #11.

Frozen registry byte SHA-256:
`0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a`.

The registry's historical candidate-status text is retained byte-for-byte.
Its merge at the commit above is the freeze event specified by PR #11.
No training, simulation, information-firewall, metric-definition, specification,
or registered-checkpoint files are modified in this implementation PR.

## Candidate implementation

- `evaluation.py` binds registry bytes to the freeze digest, checks ZIP and
  checkpoint bytes before deserialization, verifies canonical manifest hash,
  exact config/runtime, metadata and all six finite network states.
- ZIP contents are read in memory; archives are not extracted. Checkpoint
  loading uses `weights_only=True`, CPU, strict network state loading.
- Only network weights are restored. Networks are put in evaluation mode,
  gradients disabled, policies deterministic, and all PPO updaters removed.
  Each scenario starts a fresh physical model; decision traces are cleared.
- Evaluation seeds use the existing Model-0 `SeedSequence(52001).spawn(200)`
  uint64 convention. Seed identities are checked against all 5,000 training
  episode seeds. Generating seed integers does not instantiate held-out paths.
  Actual scenario generation remains behind the closed execution gate.
- The candidate orchestration writes 600 RuleBased and 3,000 AI rows, preserving
  scenario index/id/seed, training seed, checkpoint SHA and code/registry SHA.
  An existing output directory is rejected; incomplete execution has no
  `COMPLETE.json`. Automatic resume and overwrite are intentionally absent.
- Existing post-warmup metrics are reused. Exporter-average target/stock gaps
  are arithmetic means of the two exporter metrics. Undefined outcomes remain
  null in raw rows; analysis rejects them instead of dropping observations.
- Analysis checks the complete 18-treatment-policy rows per scenario, unique
  scenario IDs/seeds, checkpoint provenance, source consistency, and finite
  outcomes. It computes Gamma_V and Gamma_H with the preregistered signs.
- Each of 10,000 bootstrap draws independently resamples the five training-seed
  labels and the 200 scenario labels, with common draws across regimes and
  outcomes. The same RuleBased scenario effect is subtracted once from the
  seed-averaged AI effect. This is the crossed seed/scenario implementation of
  the plan, preserving shared scenarios across sampled seeds.
- Bootstrap Monte Carlo seed `62001` and percentile 95% intervals are explicit
  implementation choices proposed for review before evaluation freeze. The
  specification fixed the resample count and pairing, not these two details.
  Between-seed SD is computed over five scenario-averaged interaction values.
- Outputs are estimates and intervals only: no p-values or significance claims.
  A later significance layer would require reviewed p-value construction and
  Holm adjustment over the ten confirmatory tests.

## Validation performed

`python -m pytest -q`: 143 tests passed locally, including 18 new evaluation
checks. The new tests cover synthetic production-shaped checkpoint loading,
ZIP/checkpoint tampering, wrong checkpoint metadata, missing actors, nonfinite
weights, frozen registry drift, deterministic repeatability, unchanged network
weights and action RNGs, disabled learning, warmup/metric accounting, complete
panel validation, known interaction values, shared scenario bootstrap draws,
and between-seed uncertainty.

`python scripts/run_ai_evaluation_dry_run.py`: 18 synthetic trajectories
(3 RuleBased + 15 untrained AI policies) on the existing 8-day fixture,
seed `909001`. No trained checkpoint or held-out scenario is used. These are
software checks, not scientific policy outcomes.

## Required next gate

Before this candidate can become a frozen final evaluator:

1. Review implementation, metric conventions, bootstrap choices and error paths.
2. Perform loader integration with the actual 15 registered ZIP archives on
   the exact recorded runtime; fail rather than relax a hash/runtime mismatch.
   Synthetic loader tests do not establish actual-archive compatibility.
3. Add and audit the execution wrapper with exact source/ref authorization,
   pinned runtime/thread settings, durable output upload and interruption
   handling. It must not permit scientific parameter overrides or silently
   rerun partially completed held-out experiments.
4. Freeze that reviewed implementation, then authorize the first held-out run.

`require_evaluation_freeze()` currently always raises, before files are loaded,
outputs are created or held-out scenarios are generated. No environment flag
or CLI option can open it. This PR provides only a synthetic dry-run CLI and
must remain unmerged pending review/CI. There is no new dispatch workflow.
