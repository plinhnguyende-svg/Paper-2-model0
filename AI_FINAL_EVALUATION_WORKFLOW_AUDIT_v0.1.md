# AI Final Evaluation Workflow Audit v0.1

Status: CANDIDATE / PRE-HELD-OUT. This branch does not authorize or dispatch the
final held-out evaluation.

## Frozen scientific inputs

- Corrected frozen evaluator:
  `9e42c4a39e6bc8be94d1ed44e993899e4d916481`
- Immutable evaluator ref:
  `refs/heads/ai-final-evaluator-collector-hotfix-v0.1-frozen`
- Frozen checkpoint-registry byte SHA-256:
  `0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a`
- Final workflow execution ref required by the evaluator:
  `refs/heads/ai-final-evaluation-v0.1-frozen`
- Final workflow path:
  `.github/workflows/ai_final_evaluation_v0.1.yml`
- Audited workflow file Git blob SHA:
  `c5be85429f673b648fe19c11095e1ff2c2bf54e7`

The legacy evaluator ref at
`0c9c35b78c9740aa38f85a75a2ac383bcf2260ad` is not moved or rewritten.
The corrected evaluator is bound by a new immutable evaluator ref.

## Exact scientific matrix

The workflow exposes no scientific design input. The static matrix is exactly

```
40 shards × 5 held-out scenarios per shard × 18 treatment/policy rows
= 200 scenarios × 18 rows
= 3,600 trajectories.
```

The 18 rows per scenario remain the frozen three RuleBased regimes plus
three regimes × five registered AI training seeds.

## Manual authorization boundary

The scientific workflow has only `workflow_dispatch` and exactly two inputs:

1. `confirmation`, which must equal
   `RUN_FROZEN_AI_EVALUATION_V0_1`;
2. optional `resume_run_id`, which is operational provenance only.

There is no input for regime, seed, scenario count, horizon, Model-0
configuration, PPO setting, metric, bootstrap setting, device, or policy
selection.

The workflow rejects every GitHub re-run attempt with
`GITHUB_RUN_ATTEMPT != 1`. Recovery is therefore a new explicit
`workflow_dispatch` with a prior `resume_run_id`; the GitHub "re-run failed
jobs" path cannot replay held-out work.

## Workflow-commit binding without a self-SHA fixed point

A Git commit cannot contain a literal copy of its own SHA without changing that
SHA. The workflow therefore does not pretend to solve an impossible literal
self-reference.

Instead, the frozen execution is jointly bound by:

- exact repository, workflow path, and frozen branch ref;
- `github.workflow_sha` / `GITHUB_WORKFLOW_SHA`, required to equal
  `GITHUB_SHA`;
- the exact frozen evaluator SHA, checked out separately;
- a hard-coded Git blob SHA for the audited workflow file itself;
- the immutable run contract persisted as an artifact.

After exact-head audit, the execution ref may be advanced to the audited
workflow commit. Until that step and a separate explicit dispatch
authorization, the 3,600 held-out trajectories remain unexecuted.

## Runtime and action pins

- runner: `ubuntu-24.04`;
- Python: `3.12.14`;
- pip: `26.2.1`;
- exact scientific requirements and transitive constraints reused from the
  frozen training runtime;
- `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`,
  `PYTHONHASHSEED=0`;
- checkout, setup-python, download-artifact, and upload-artifact actions are
  pinned to full commit SHAs.

The workflow checks out the control/workflow commit and the evaluator commit in
separate directories. Real checkpoint archive verification runs from inside the
evaluator checkout so its recorded `git rev-parse HEAD` is the frozen evaluator
SHA rather than the workflow SHA.

## Durable execution and resume contract

The prepare job downloads and verifies all fifteen registered training
archives before any shard job. It persists both a verified checkpoint bundle
and an immutable run contract.

Each shard:

- restores only its named prior artifact when `resume_run_id` is supplied;
- validates the current run contract independently;
- validates the restored evaluator shard contract and immutable committed
  history before continuation;
- resumes from the exact next uncommitted scenario;
- uploads committed recovery state with `if: always()`;
- has a 300-minute scientific step inside a 330-minute job, leaving an upload
  window.

A completed shard may be restored and finalized idempotently without replay.
A missing requested prior artifact, mismatched run lineage, wrong source/workflow
SHA, ambiguous local evidence, or incomplete shard fails closed.

A complete hosted-runner loss before artifact upload cannot be made
transactional by GitHub Actions. Such a case must stop the scientific pipeline
for manual provenance review; it must not be silently classified as "never
ran" and automatically rerun.

## Collector contract

Collection starts only after the 40-shard matrix reports success. The collector
requires exactly `shard-000` through `shard-039`, verifies every evaluator
contract, committed-history digest, completion marker, row count, and total
trajectory count, then invokes the frozen evaluator collector.

The corrected evaluator additionally refuses to overwrite an existing final
panel.

## Synthetic/no-held-out audit cases

The PR-only workflow gate tests, without calling held-out scenario generation:

- first run;
- partial-failure resume;
- completed-shard resume;
- missing prior artifact;
- wrong prior run ID;
- wrong ref;
- wrong workflow SHA;
- forbidden GitHub re-run attempt;
- incomplete collector input;
- exact synthetic 40-shard / 200-scenario / 3,600-row durable evidence set.

The tests monkeypatch `generate_scenario` to raise if called in the synthetic
resume/collector exercises. The gate artifact records
`heldout_scenarios_generated: 0` and
`scientific_evaluation_dispatched: false`.

## Freeze rule

Do not dispatch the scientific workflow from this candidate branch.

Only after all exact-head PR gates are green:

1. record the exact audited PR head and workflow blob;
2. merge the workflow PR without modifying its audited contents;
3. advance `refs/heads/ai-final-evaluation-v0.1-frozen` to the exact audited
   workflow commit;
4. recheck the frozen ref, workflow file blob, evaluator SHA, registry hash,
   workflow-dispatch count, and checkpoint availability;
5. require a separate explicit user authorization before the first scientific
   `workflow_dispatch`.

The workflow freeze itself does not authorize the 3,600 trajectories.
