# AI Full Scientific Training Workflow Final Audit v0.1

## Scope

This is the final pre-freeze audit of PR #10.

The workflow layer is operational infrastructure only. It must execute the
scientific contract already frozen in launcher commit:

\[
\boxed{\texttt{fb4f386703294990917e9d99e10013925a9a54d6}}
\]

without introducing a new route for changing the information regimes, training
seeds, episode budget, episode horizon, PPO hyperparameters, Model 0
configuration, reward, action space, observation space, or training device.

The audit focuses on:

1. artifact durability across ephemeral runners;
2. resume-run provenance;
3. timeout and upload semantics;
4. exact static matrix;
5. pinned runtime reproducibility;
6. protection against scientific-contract drift at manual dispatch.

## 1. Exact static matrix

The workflow matrix is not derived from user input.

It contains exactly:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\}
=
15\text{ jobs}.
\]

The matrix is tested directly against the frozen launcher registry.

The strategy is:

- \`fail-fast: false\`;
- \`max-parallel: 5\`.

Therefore a failed pre-registered job does not cancel the remaining
pre-registered jobs and is never replaced by another seed.

No workflow-dispatch input can change regime or training seed.

## 2. Manual-dispatch surface

The full scientific workflow has exactly two manual inputs:

- \`confirmation\`;
- \`resume_run_id\`.

The first is an authorization acknowledgement. The second is an operational
recovery pointer.

Neither is a scientific parameter.

The workflow has no input for:

- number of episodes;
- episode horizon;
- rollout length;
- Model 0 configuration;
- PPO hyperparameters;
- learning rate;
- discount factor;
- action bounds;
- device;
- regime;
- training seed.

The scientific entrypoint exposes no corresponding command-line override.

## 3. Frozen workflow ref

The workflow refuses scientific execution unless:

\[
\boxed{
\texttt{GITHUB\_REF}
=
\texttt{refs/heads/ai-full-training-v0.1-frozen}
}
\]

and the repository is exactly:

\[
\boxed{
\texttt{plinhnguyende-svg/Paper-2-model0}.
}
\]

The dedicated frozen branch is created only after the audited PR head is
finalized.

The checkout step uses the exact \`github.sha\` resolved from that frozen ref.

The entrypoint additionally requires:

- GitHub Actions execution;
- \`workflow_dispatch\` as the event;
- a full 40-character execution SHA;
- the frozen launcher authorization variables.

Thus normal push, pull-request, scheduled, or local execution is not an
accepted scientific execution context.

## 4. GitHub Action supply-chain pins

The four actions used by the scientific workflow are pinned to complete commit
SHAs rather than mutable major-version tags:

- \`actions/checkout\`:
  \`11d5960a326750d5838078e36cf38b85af677262\`;
- \`actions/setup-python\`:
  \`a26af69be951a213d495a4c3e4e4022e16d87065\`;
- \`actions/download-artifact\`:
  \`d3f86a106a0bac45b974a628896c90dbdf5c8093\`;
- \`actions/upload-artifact\`:
  \`ea165f8d65b6e75b540449e92b4886f43607fa02\`.

The audit resolved those commits from the corresponding GitHub major-version
refs before pinning them.

## 5. Scientific runtime

The execution environment is locked to:

- Ubuntu 24.04 runner label;
- Python 3.12.14;
- pip 26.2.1;
- NumPy 2.5.3;
- pandas 3.0.6;
- PyYAML 6.0.3;
- PyTorch 2.14.0 base version;
- the transitive dependency versions recorded in
  \`constraints-ai-training-v0.1.txt\`;
- CPU execution;
- one computational thread for the major CPU thread pools.

The workflow runs \`pip check\` before scientific execution.

The entrypoint independently fails if the direct runtime versions differ from
the frozen versions.

PyTorch deterministic algorithms are enabled and actor-local/random-shuffle RNG
state remains governed by the frozen launcher/checkpoint protocol.

### Hosted-runner limitation

\`ubuntu-24.04\` is a versioned GitHub-hosted runner label, not a container
image digest.

Therefore v0.1 claims:

\[
\boxed{
\text{version-pinned + provenance-recorded reproducibility}
}
\]

rather than cross-image bitwise identity.

The workflow records the GitHub runner image identifiers exposed at execution
time so any infrastructure drift is visible in the provenance.

## 6. Runtime lock

Each scientific job computes a normalized:

\[
\texttt{pip freeze --all}
\]

snapshot and its SHA-256 digest.

That snapshot is stored inside the job artifact.

A resumed run is rejected when its current runtime freeze digest differs from
the prior durable artifact.

This makes dependency drift a fail-fast event rather than a silent change in
the resumed learning process.

## 7. Artifact durability and episode-boundary semantics

The frozen launcher already defines the scientific transaction boundary as a
completed episode.

Within one runner, the launcher commits:

\[
\text{manifest}
\rightarrow
\text{checkpoint}
\rightarrow
\text{diagnostics}
\rightarrow
\texttt{latest.json}.
\]

\`latest.json\` is advanced last.

The workflow layer then transports that committed state between ephemeral
runners as one per-job artifact named:

\[
\texttt{ai-training-<regime>-seed-<training seed>}.
\]

The artifact path is deterministic and job-specific.

A missing requested resume artifact is a hard failure. There is no silent
fallback to a fresh episode-zero run.

## 8. Resume-run provenance

When \`resume_run_id\` is supplied, the restored artifact must contain a
provenance file for that exact prior workflow run id.

Before the launcher loads the checkpoint, the operational entrypoint verifies:

\[
\boxed{
\begin{aligned}
&\text{frozen launcher SHA},\\
&\text{workflow execution SHA},\\
&\text{frozen workflow ref},\\
&\text{repository},\\
&\text{regime},\\
&\text{training seed},\\
&\text{workflow file hash},\\
&\text{entrypoint file hash},\\
&\text{requirements hash},\\
&\text{constraints hash},\\
&\text{pip-freeze hash}.
\end{aligned}
}
\]

The previous workflow execution SHA must equal the current execution SHA.

Only after this workflow-level provenance check does the frozen launcher perform
its own manifest/checkpoint/runtime/config/episode-sequence validation.

The two layers therefore answer different questions:

\[
\text{workflow provenance}
\quad+\quad
\text{scientific checkpoint provenance}.
\]

## 9. Timeout and upload semantics

The scientific training step is capped at 300 minutes.

The enclosing job is capped at 330 minutes.

Therefore:

\[
\boxed{
300\text{ min training}
<
330\text{ min job}
}
\]

leaving an operational window for the subsequent recovery upload.

The recovery upload uses \`if: always()\` and \`if-no-files-found: error\`.

Thus a normal training exception or step-level timeout still proceeds to an
attempt to persist the last completed launcher transaction.

### Host-loss boundary

No GitHub Actions workflow can guarantee that a physically lost hosted runner
will execute its final upload step.

Accordingly the guarantee is:

- step failure/timeout: attempt to upload the latest committed local boundary;
- complete runner loss: resume later from the most recent previously uploaded
  artifact;
- no previous artifact: deterministically rerun the same frozen job from
  episode zero.

This can increase computation but does not authorize a different seed, budget,
configuration, or model-selection rule.

## 10. No post-hoc adaptation

The workflow cannot:

- add a replacement training seed;
- extend a job past 1000 episodes;
- choose a checkpoint based on observed performance;
- modify the pre-registered stability diagnostic;
- switch to GPU;
- change PPO settings;
- change the Model 0 baseline configuration.

The final job label remains determined by the frozen launcher:

\[
\text{training-stable}
\]

or:

\[
\text{not stabilized under the pre-registered budget}.
\]

A non-stable job does not trigger additional training.

## 11. Audit findings corrected in PR #10

The final audit identified and corrected the following pre-freeze weaknesses.

First, GitHub Actions were originally referenced through mutable major tags.
They are now commit-pinned.

Second, direct package versions were pinned but the transitive scientific
runtime was not. A constraints file, pip pin, runtime installation gate and
pip-freeze provenance were added.

Third, resume originally proved the existence of \`latest.json\` but did not
cryptographically bind the restored workflow artifact to the previous workflow
run. Resume provenance now binds the prior run id, workflow SHA, contract files,
runtime digest, regime and seed before checkpoint loading.

Fourth, dispatch originally required \`main\`, which is a moving branch. The
scientific workflow now requires a dedicated frozen workflow ref created from
the final audited head.

Fifth, the runtime entrypoint originally relied primarily on the workflow to
supply the intended environment. It now independently rejects wrong event,
repository, ref, SHA shape and direct runtime versions.

Sixth, runtime constraints were validated by adding a dedicated
**non-training** freeze-gate workflow. That gate installs the frozen runtime and
executes only workflow/launcher contract tests; it never authorizes or invokes
scientific full training.

## 12. Freeze criterion

PR #10 is freeze-ready only when its final head satisfies all of the following:

1. standard CI passes on Python 3.12 and Python 3.13;
2. the existing AI launcher dry-run gate passes;
3. the AI Full Training Freeze Gate successfully installs the pinned runtime;
4. the freeze gate confirms the exact runtime versions;
5. workflow/launcher contract tests pass;
6. the diff from frozen launcher commit
   \`fb4f386703294990917e9d99e10013925a9a54d6\` contains no modification to
   Model 0, PPO, reward, observations, action transforms, training runner, or
   launcher implementation;
7. no unresolved review thread remains;
8. the scientific full-training workflow has never been dispatched before
   freeze.

After those conditions hold:

\[
\boxed{
\text{merge PR \#10}
\rightarrow
\text{create frozen workflow ref from audited head}
\rightarrow
\text{manual dispatch gate opens}
}
\]

Creation of the frozen ref is not itself authorization to launch the 15 jobs.

The 15-job dispatch remains an explicit separate action.
