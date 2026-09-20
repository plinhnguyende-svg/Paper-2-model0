# AI Training Result Audit v0.1

**Status:** POST-TRAINING AUDIT CANDIDATE / CHECKPOINT REGISTRY LOCKS ONLY WHEN THIS PR IS MERGED

## 1. Frozen scientific run inspected

The first admissible full scientific run on the frozen workflow ref is:

- workflow: `AI Full Scientific Training v0.1`;
- workflow run id: `35439893662`;
- workflow execution SHA: `0b455dd3e03c0597ec806f8aac73db0172f02262`;
- frozen launcher source SHA: `fb4f386703294990917e9d99e10013925a9a54d6`;
- frozen ref: `ai-full-training-v0.1-frozen`;
- conclusion: **success**.

An earlier dispatch on moving `main` failed immediately at the frozen-ref guard and is not a scientific training run.

## 2. Completion and artifact audit

All 15 pre-registered jobs completed successfully:

\[
\{N,S,F\}\times\{41001,41002,41003,41004,41005\}.
\]

For every one of the 15 job artifacts, the audit verified:

- ZIP integrity;
- exactly 1000 committed episodes in the final manifest;
- `latest.json` committed episode count = 1000;
- exactly 1000 diagnostic rows;
- final manifest SHA-256 agrees across `workflow_result.json`, `latest.json`, and the final checkpoint;
- final checkpoint metadata agrees with regime and training seed;
- all six actor states `R1,R2,R3,BQ,E1,E2` are present;
- all floating checkpoint tensors are finite;
- total recorded non-finite-event count = 0;
- source SHA is the frozen launcher SHA;
- workflow provenance points to run `35439893662` and the frozen execution SHA.

The exact artifact/checkpoint identities are recorded in
`experiments/ai_training_checkpoint_registry_v0.1.json`.

## 3. Common-random-number audit

For each of the five training seeds, the complete 1000-episode sequence of:

\[
(episode\ index,\ episode\ seed,\ scenario\ id)
\]

is exactly identical across N, S, and F.

Thus the pre-registered N/S/F common-exogenous training schedule was actually
realized, not merely intended.

## 4. Training-stability result

The pre-registered stability rule requires both:

\[
\left|
\frac{\bar R_{801:1000}-\bar R_{601:800}}{\bar R_{601:800}}
\right|\le 0.05
\]

and a 95% CI for the final-window reward slope that contains zero.

Only **1 of 15** runs satisfies both conditions:

- `N / seed 41003`: relative change = 0.0192133; slope = 0.0290898;
  95% CI = [-0.100323, 0.158502].

The other **14 of 15** runs are correctly labeled:

`not stabilized under the pre-registered budget`.

The audit independently recomputed every stability statistic from
`diagnostics/episodes.csv`; all stored means, relative changes, slopes, 95%
intervals, and labels match the recomputation.

## 5. Interpretation of the non-stability result

This does **not** authorize retraining, checkpoint selection, or a larger
budget.

The locked specification explicitly states that the 1000-episode budget is a
pre-registered computational budget and is **not an assumption that every seed
must mathematically converge**.

Therefore:

\[
\boxed{
\text{14/15 not stabilized}
\quad\Rightarrow\quad
\text{report it}
\neq
\text{extend training}
}
\]

The fixed-budget final checkpoint remains the pre-specified model-selection
rule for every regime/seed pair.

Accordingly all 15 episode-1000 checkpoints remain part of the confirmatory
evaluation set. Stability status must be reported as a limitation and may be
used for descriptive sensitivity discussion only; it must not be used to
exclude seeds or choose checkpoints.

## 6. Checkpoint freeze rule

The 15 learned policies are not considered frozen merely because the workflow
finished.

They become the sole confirmatory AI checkpoint set only when this audit PR is
merged and the registry is recorded from the exact artifact/checkpoint hashes.

After that merge:

- no checkpoint may be replaced;
- no seed may be dropped because it is unstable;
- no seed may be retrained;
- no alternative checkpoint may be selected;
- evaluation code must verify checkpoint SHA-256 before loading.

## 7. Next scientific gate

The next stage is the final paired evaluation implementation:

\[
\boxed{
\text{freeze 15-checkpoint registry}
\rightarrow
\text{implement final evaluation runner}
\rightarrow
\text{dry-run/audit}
\rightarrow
\text{run held-out evaluation}
}
\]

The final evaluation itself must not start from this PR.

