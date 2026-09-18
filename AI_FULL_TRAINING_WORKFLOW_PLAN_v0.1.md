# AI Full Scientific Training Workflow Plan v0.1

**Status:** WORKFLOW IMPLEMENTATION / NOT DISPATCHED

**Frozen launcher base:** \`fb4f386703294990917e9d99e10013925a9a54d6\`

This milestone adds the operational GitHub Actions layer needed to execute the
already frozen 15-run launcher. It must not modify the frozen launcher,
runner, Model 0, PPO, reward, observations, actions, seeds, or scientific
budget.

## Exact scientific design

The workflow contains exactly:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\}
=
15\text{ jobs}.
\]

Each job remains:

\[
1000\text{ episodes}
\times
1000\text{ Model-0 days}.
\]

The workflow has no scientific-budget, hyperparameter, configuration, or
device inputs.

## Manual-only authorization

The workflow is triggered only by \`workflow_dispatch\`.

Before any training step it requires the exact typed confirmation:

\`RUN_FROZEN_AI_V0_1\`.

The workflow sets the launcher's two frozen authorization variables itself:

- \`PAPER2_AI_FULL_TRAINING_AUTHORIZED=YES\`;
- \`PAPER2_AI_FROZEN_LAUNCHER_SHA=fb4f386703294990917e9d99e10013925a9a54d6\`.

It also refuses execution unless the workflow ref is \`refs/heads/main\`.

Creating this workflow does not dispatch it.

## Reproducible execution environment

The scientific job is locked to CPU.

The workflow pins:

- Ubuntu 24.04;
- Python 3.12.14;
- pip 26.2.1;
- NumPy 2.5.3;
- pandas 3.0.6;
- PyYAML 6.0.3;
- PyTorch 2.14.0;
- the currently resolved transitive scientific dependencies in
  `constraints-ai-training-v0.1.txt`.

The GitHub Actions used for checkout, Python setup, artifact download and
artifact upload are pinned to full commit SHAs rather than mutable major tags.

The entrypoint additionally enables deterministic PyTorch algorithms, fixes CPU
thread counts to one, and fails fast if the direct runtime versions differ from
the frozen versions.

Each job records a sorted `pip freeze --all` snapshot and SHA-256 digest.
A resumed job must reproduce that same runtime digest.

Execution provenance records:

- the frozen launcher SHA used by the scientific manifest;
- the actual workflow execution SHA/run id/run attempt;
- the frozen workflow ref and repository;
- the GitHub runner image identifiers exposed by the runner;
- SHA-256 hashes of the workflow, operational entrypoint, direct requirements
  and transitive constraints;
- the complete normalized pip-freeze digest.

The Ubuntu hosted-runner image label is versioned but not an immutable container
digest. Therefore v0.1 claims version-pinned and provenance-recorded
reproducibility, not cross-image bitwise identity.

## Durable recovery across ephemeral GitHub runners

PR #9 guarantees atomic consistency only inside a surviving run directory.

This workflow supplies the durable transport layer.

An optional operational input, \`resume_run_id\`, may identify one previous
workflow run whose job artifacts should be restored.

This input does not alter the scientific design. Both manual dispatch strings
are passed into shell steps through environment variables rather than direct
expression interpolation; the resume id must be a positive decimal integer.

For each matrix job, the workflow restores exactly one artifact named:

\[
\texttt{ai-training-<regime>-seed-<training seed>}.
\]

When \`resume_run_id\` is supplied, a missing artifact is a hard failure. The
workflow never silently starts that job from episode 0.

The training step has a shorter timeout than the overall job. Therefore, if a
long scientific run reaches the operational step limit, the later
\`if: always()\` upload step still has time to preserve the last committed
episode boundary.

The restored launcher state itself then enforces:

- matching frozen source SHA;
- matching regime/seed;
- matching runtime fingerprint;
- matching config hash;
- matching canonical manifest/checkpoint hash;
- exact next episode.

## Failure semantics

Matrix \`fail-fast\` is disabled.

A failure in one pre-registered job does not cancel or replace another seed.

There is no fallback seed and no post-hoc extension.

A timed-out or failed job is resumed only from a previously committed episode
boundary.

The 300-minute training-step timeout is nested inside a 330-minute job timeout,
leaving an upload window for the `if: always()` recovery-artifact step. A
complete host-level runner loss can still lose progress made since the most
recent uploaded artifact; it cannot change the scientific trajectory, because a
subsequent run either resumes from the last durable committed artifact or, when
no prior durable artifact exists, deterministically restarts the same frozen
job from episode zero.

## Workflow freeze gate

Before this workflow may be manually dispatched:

1. its static 15-job matrix must be tested against the frozen launcher registry;
2. CI must prove there is no push, pull-request, or schedule trigger;
3. artifact restore/upload semantics must be audited;
4. environment/version locks must be audited;
5. the frozen runtime installation must pass a dedicated non-training CI gate;
6. the workflow and entrypoint must be frozen and a dedicated immutable-in-use
   workflow branch created from the audited head.

\[
\boxed{
\text{IMPLEMENT WORKFLOW}
\rightarrow
\text{AUDIT / FREEZE WORKFLOW}
\rightarrow
\text{ONLY THEN MANUAL DISPATCH}
}
\]
