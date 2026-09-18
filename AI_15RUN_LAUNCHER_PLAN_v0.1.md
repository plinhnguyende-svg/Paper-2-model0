# AI 15-Run Launcher Plan v0.1

**Status:** LAUNCHER IMPLEMENTATION BRANCH OPEN / FULL SCIENTIFIC TRAINING NOT AUTHORIZED

**Frozen runner base:** \`d310ad960a410d03b87b123dfdc45b2bbf45946d\`

This branch may implement orchestration only. It must not alter the frozen
runner, Model 0 institution, information architecture, AI observations/actions,
reward definition, PPO hyperparameters, training seeds, scenario-seed
protocol, episode budget, or checkpoint semantics.

## 1. Exact confirmatory job registry

The launcher must expose exactly:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\},
\]

giving:

\[
\boxed{15\ \text{scientific training jobs}.}
\]

The launcher must obtain this registry from the frozen
\`training_run_keys()\` contract rather than accepting an arbitrary
user-supplied matrix.

## 2. Per-job budget

Every job must run exactly:

\[
1000\ \text{episodes}
\times
1000\ \text{Model-0 days}.
\]

Episode \(e\) must use the frozen common-random-number mapping:

\[
seed_{s,e}=1000s+e.
\]

No launcher option may change:

- information regime outside \(N,S,F\);
- training seed outside \(41001,\ldots,41005\);
- episode count;
- episode horizon;
- PPO settings;
- scenario-seed mapping.

## 3. Run lifecycle

For one \((regime,training\ seed)\) job:

1. validate the frozen scientific training contract;
2. create the run manifest before episode 0;
3. initialize the six actor-local agents from the locked training seed;
4. for episode \(e=0,\ldots,999\):
   - derive the locked episode seed;
   - generate the immutable exogenous scenario;
   - run one boundary-aware 1000-day training episode;
   - append episode seed/scenario id and diagnostics to the run record;
   - write a crash-recovery checkpoint only at an episode boundary;
5. after episode 999, save the fixed-budget final checkpoint;
6. compute the pre-registered training-stability diagnostic;
7. never select a checkpoint by reward or evaluation performance.

## 4. Crash recovery

Resume must:

- load the manifest first;
- verify its source commit/runtime/config/seed/regime contract;
- load only a checkpoint cryptographically bound to that manifest;
- continue from exactly \`completed_episode_count\`;
- use the next pre-registered episode seed;
- never replay a completed episode or skip an episode;
- never substitute another seed after failure.

Intermediate checkpoints are operational recovery artifacts, not candidate
models.

## 5. Required diagnostics

Per episode, record at least:

- episode index;
- episode seed;
- scenario id;
- total team reward;
- actor policy loss;
- actor value loss;
- actor entropy;
- actor approximate KL;
- actor clip fraction;
- actor gradient norm;
- transformed-action summaries;
- exporter active-decision fractions;
- non-finite event count.

The final run artifact must retain the complete manifest and diagnostic table.

## 6. Training-stability report

After exactly 1000 episodes:

- compare mean reward over episodes 601--800 vs. 801--1000;
- compute absolute relative mean change;
- regress reward on episode index over 801--1000;
- report slope and 95% confidence interval.

The locked label \`training-stable\` requires both:

\[
\left|
\frac{
\bar R_{801:1000}-\bar R_{601:800}
}{
\bar R_{601:800}
}
\right|
\le 0.05
\]

and a final-window reward-slope 95% CI containing zero.

Failure of that rule is reported as:

\[
\boxed{\text{not stabilized under the pre-registered budget}}
\]

with no post-hoc training extension.

## 7. Launcher safety gate

Before any full 15-job execution, the launcher PR must prove with dry-run and
tiny orchestration tests that:

- the job registry contains exactly 15 unique locked pairs;
- no arbitrary regime/seed/budget/PPO override is accepted;
- N/S/F use matched scenario seeds for every sampled episode index;
- manifests are created before training and updated contiguously;
- resume starts at the exact next episode;
- final checkpoint occurs only after episode 1000;
- failures stop the job instead of replacing seeds;
- launcher output paths are deterministic and collision-free;
- CI never starts a full scientific training run.

## 8. Workflow rule

Any GitHub Actions workflow added in this branch must be safe by default.

Until a separate launcher freeze decision:

- pull-request and push events may run tests/dry-runs only;
- no event may execute a full 1000-episode job;
- no matrix of 15 scientific jobs may auto-start;
- a future full-training workflow must require an explicit post-freeze action.

## Current gate

\[
\boxed{
\text{LAUNCHER IMPLEMENTATION ALLOWED}
\quad;\quad
\text{FULL SCIENTIFIC TRAINING NOT STARTED}
}
\]
