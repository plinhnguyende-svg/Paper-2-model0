# AI 15-Run Launcher Final Audit v0.1

## Scope

This document is the final pre-freeze audit of PR #9.

The audit asks whether the launcher can be frozen without permitting any
scientific-contract drift before the later explicit full-training workflow is
added.

The five audited areas are:

1. atomic crash recovery;
2. manifest-history immutability and provenance;
3. full-training authorization;
4. training-stability definition;
5. hidden execution paths that could alter or bypass the confirmatory design.

The frozen runner base remains:

\[
\boxed{\texttt{d310ad960a410d03b87b123dfdc45b2bbf45946d}}
\]

PR #9 does not modify that runner, Model 0, PPO implementation, reward
definition, information architecture, or observation/action interfaces.

## 1. Atomic crash recovery

### Intended transaction boundary

A scientific job is committed only at an episode boundary.

For completed episode count \(k\), the launcher writes:

\[
\text{manifest}_k
\rightarrow
\text{checkpoint}_k
\rightarrow
\text{diagnostics}_{0:k-1}
\rightarrow
\texttt{latest.json}.
\]

The final operation is an atomic replacement of \`latest.json\`.

Therefore:

\[
\boxed{
\texttt{latest.json}
=
\text{sole committed-boundary pointer}
}
\]

If the process dies before that final pointer replacement, the prior pointer is
authoritative.

### Audit finding and correction

The first implementation removed higher-count completed files after a crash,
but a partial temporary file such as:

- \`manifest_episode_0001.json.tmp\`;
- \`checkpoint_episode_0001.pt.tmp\`;
- \`episodes.csv.tmp\`

could survive because its suffix was not recognized as an episode number.

The final-audit correction now:

- recognizes episode counts even when a temporary suffix is present;
- deletes all state-directory \`.tmp\` files on recovery;
- deletes a diagnostics temporary file on recovery;
- removes higher-count manifest/checkpoint orphans;
- truncates diagnostics written ahead of the committed pointer;
- deletes a premature stability report when the committed count is below 1000.

Tests explicitly simulate these crash residues.

### Scope of the atomicity guarantee

This is a **local-filesystem transaction guarantee**. It protects against a
process interruption when the run directory itself survives.

GitHub-hosted runners are ephemeral, so PR #9 does **not** claim that local
files alone survive loss of an entire runner VM. The later explicit
full-training workflow must provide the durable transport layer by:

- restoring the latest committed job artifact before a resumed run;
- uploading the committed job directory with an `if: always()` recovery step;
- preserving `latest.json`, its referenced manifest/checkpoint, and
  diagnostics together;
- refusing resume when the durable artifact is incomplete or belongs to a
  different frozen launcher/job.

That persistence mechanism belongs to the separately audited workflow layer
and is deliberately not implemented by PR #9.

### Replay/skip protection

A new boundary can be committed only when:

\[
k_{\text{new}}=k_{\text{committed}}+1.
\]

Replaying the same episode or jumping over an episode raises before the pointer
can advance.

## 2. Manifest-history immutability and provenance

Every scientific launcher manifest remains bound to:

- the exact launcher protocol version;
- the frozen runner base;
- one of the 15 registered \((regime,seed)\) jobs;
- the exact baseline \`SimulationConfig\` hash;
- CPU execution;
- the full source commit SHA;
- the runtime fingerprint;
- the runner/checkpoint/scenario-seed protocol versions;
- the fixed 1000-episode budget and 1000-day horizon.

At every new commit, the new manifest must preserve the entire previously
committed episode prefix exactly.

The following cannot change within one job:

\[
\boxed{
\text{source commit}
+
\text{runtime fingerprint}
+
\text{config hash}
+
\text{episode history}
}
\]

### Scenario provenance strengthening

The generic runner manifest already fixes the episode index and episode seed.
The launcher audit adds a stronger check: the recorded \`scenario_id\` must be
the exact ID produced by the frozen baseline configuration and that locked
episode seed.

During normal training only the newly appended episode is regenerated and
verified. This keeps the 1000-episode path linear rather than accidentally
creating an \(O(n^2)\) scenario-regeneration cost.

On resume, the complete committed manifest receives a one-time full
scenario-ID audit.

### Diagnostics/manifest binding

The audit also found that diagnostics and manifest rows had previously been
validated independently.

The final version now requires, episode by episode:

\[
\boxed{
(\text{episode index},\text{episode seed},\text{scenario id})_{\text{diagnostics}}
=
(\text{episode index},\text{episode seed},\text{scenario id})_{\text{manifest}}
}
\]

before a boundary can be committed or resumed.

Thus a valid checkpoint cannot be paired with a diagnostics table describing a
different exogenous realization.

## 3. Authorization gate

The scientific training function accepts no user override for:

- regime outside \(N,S,F\);
- seed outside \(41001,\ldots,41005\);
- episode count;
- episode horizon;
- \`SimulationConfig\`;
- PPO hyperparameters;
- training device;
- scenario-seed mapping.

The exact job registry remains:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\}.
\]

The confirmatory device is locked to:

\[
\boxed{\texttt{cpu}}.
\]

The callable full-training path additionally requires both:

- \`PAPER2_AI_FULL_TRAINING_AUTHORIZED=YES\`;
- \`PAPER2_AI_FROZEN_LAUNCHER_SHA\` equal to the supplied frozen source SHA.

These variables are deliberately absent from all repository workflows and
scripts in PR #9.

### Hidden-path audit

Every file under:

- \`.github/workflows/*.yml\`;
- \`.github/workflows/*.yaml\`;
- \`scripts/*.py\`

was audited for:

- \`run_locked_training_job\`;
- \`PAPER2_AI_FULL_TRAINING_AUTHORIZED\`;
- \`PAPER2_AI_FROZEN_LAUNCHER_SHA\`.

PR #9 contains no repository workflow/script entry point that invokes or
authorizes scientific full training.

The only GitHub Actions workflow added by PR #9 is a dry-run gate.

The unit test repeats this repository scan so a later pre-freeze edit that
introduces a hidden executable path fails CI.

## 4. Training-stability definition

The stability diagnostic is descriptive and is computed only after the exact
1000-episode budget has completed.

The two fixed reward windows are:

\[
601{:}800
\qquad\text{and}\qquad
801{:}1000.
\]

The first criterion is:

\[
\left|
\frac{
\bar R_{801:1000}-\bar R_{601:800}
}{
\bar R_{601:800}
}
\right|
\le 0.05.
\]

If the earlier mean is exactly zero and the later mean is non-zero, the
relative change is explicitly undefined and the job cannot receive the
\`training-stable\` label.

The second criterion is an OLS regression of reward on episode index over
episodes 801--1000.

The frozen v0.1 interval is the pre-specified normal-approximation interval:

\[
\widehat\beta
\pm
1.96\,SE(\widehat\beta).
\]

The interval must contain zero.

Hence:

\[
\boxed{
\text{training-stable}
\iff
\text{relative change}\le5\%
\ \land\
0\in CI_{95\%}(\widehat\beta)
}
\]

Otherwise the locked label is:

\[
\boxed{
\text{not stabilized under the pre-registered budget}
}
\]

and:

\[
\boxed{
\text{post-hoc training extension is not allowed}.
}
\]

Tests cover a flat stable path, the exact 5% boundary, a non-zero final trend,
an undefined relative-change case, and rejection of any diagnostics vector
shorter than 1000 episodes.

This stability diagnostic is not a checkpoint-selection rule and does not
authorize additional training.

## 5. Scientific-contract drift audit

The launcher has no caller-facing argument for budget, horizon, PPO settings,
configuration, or device.

The production path reconstructs the locked baseline configuration internally,
derives the job only from the 15-entry registry, and derives every episode seed
from:

\[
seed_{s,e}=1000s+e.
\]

The evaluation master seed remains excluded by the frozen runner protocol.

Per-job output directories are deterministic and unique.

A failed job is not substituted with another seed.

Intermediate checkpoints are crash-recovery artifacts only; they are not
candidate-model selection points.

## 6. What remains outside PR #9

PR #9 still contains no:

- automatic 15-job scientific workflow;
- 1000-episode scientific result;
- learned confirmatory checkpoint;
- AI-vs-RuleBased performance result;
- confirmatory evaluation result.

The later full-training workflow must be created only from the final merged
launcher commit and must be audited separately before it is manually
dispatched.

## Freeze criterion

PR #9 is freeze-ready only if its final head satisfies all of the following:

1. Python 3.12 and 3.13 CI pass;
2. AI smoke training passes;
3. the launcher dry-run gate passes;
4. the dry-run artifact states \`full_training_authorized=false\`;
5. no unresolved review thread remains;
6. the diff from the frozen runner modifies launcher-only files;
7. no workflow or script invokes the full-training callable.

After merge, the merge commit becomes the sole frozen launcher base.

\[
\boxed{
\text{FREEZE PR \#9}
\rightarrow
\text{CREATE EXPLICIT MANUAL FULL-TRAINING WORKFLOW}
\rightarrow
\text{AUDIT WORKFLOW}
\rightarrow
\text{ONLY THEN DISPATCH}
}
\]
