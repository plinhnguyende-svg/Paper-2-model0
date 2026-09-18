# AI Tiny Deterministic Smoke Result v0.1

## Run identity

- Workflow: \`AI Smoke Training\`
- GitHub Actions run: \`35361069674\`
- Experiment head: \`0a3477aa2cf6c8d3860841673fa1b3a53d1b0ea1\`
- Artifact: \`ai-smoke-35361069674\`
- Artifact id: \`10554780062\`
- Artifact SHA-256: \`a30e08a817bc49dbe6b130fbdd5415a18b54c8ab47ff6990a18c6b5a46b806c3\`
- Scenario id: \`33d3737fe65e521b\`
- Training seed used for smoke wiring: \`41001\`
- Horizon: 8 days

The branch commit immediately after the experiment adds only the generated-output ignore path; it does not change smoke code or results.

## Gate checks

The dedicated smoke workflow completed successfully.

For each of \(N,S,F\):

- all 8 Model 0 days completed;
- all six actor-local buffers contain exactly 8 transitions;
- the same deterministic exogenous scenario id is preserved;
- team rewards are finite;
- all six PPO updates are finite;
- all six local networks change after the tiny update;
- the frozen importer allocation mechanism remains in force.

Across three regimes this gives:

\[
3\times6=18
\]

finite actor-local PPO updates.

Normal CI run \`35361069475\` also completed successfully:

- Python 3.12: 71 passed;
- Python 3.13: 71 passed.

## Smoke-only reward totals

The generated diagnostic totals were:

- \(N\): \(-11.1108857060\)
- \(S\): \(-10.1233640126\)
- \(F\): \(-10.0090161275\)

These values are retained only to make the smoke run reproducible.

They are **not research findings**, are not estimates of treatment effects, and must not be used to rank \(N,S,F\). The scenario is eight deterministic days and the policies receive only one tiny PPO update.

## Reproducibility hardening

The smoke integration review found that stochastic policy sampling in the frozen PPO core depended on the global PyTorch RNG.

The branch replaces that dependency with one actor-local random generator per policy, deterministically derived from the training seed.

The test suite verifies that unrelated calls to \`torch.manual_seed\` do not change the actor's stochastic action sequence.

## Interpretation

The smoke run establishes only that the complete software path is executable:

\[
\text{observation}
\rightarrow
\text{policy}
\rightarrow
\text{bounded action}
\rightarrow
\text{Model 0}
\rightarrow
\text{reward}
\rightarrow
\text{rollout}
\rightarrow
\text{GAE}
\rightarrow
\text{PPO update}.
\]

It does not establish convergence, policy quality, external validity, or operational superiority.

## Gate decision

\[
\boxed{
\text{END-TO-END SMOKE PASSED; FULL PRE-REGISTERED TRAINING REMAINS BLOCKED UNTIL PR \#7 REVIEW/FREEZE.}
}
\]
