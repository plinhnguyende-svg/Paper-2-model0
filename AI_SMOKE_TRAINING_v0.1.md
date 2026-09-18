# AI Tiny Deterministic Smoke Training v0.1

## Purpose

This milestone is an **end-to-end software integration test**, not scientific AI training.

It checks the complete path:

\[
\text{legal observation}
\rightarrow
\text{actor-local policy}
\rightarrow
\text{bounded physical action}
\rightarrow
\text{Model 0 transition}
\rightarrow
\text{team reward}
\rightarrow
\text{actor-local rollout}
\rightarrow
\text{GAE}
\rightarrow
\text{PPO update}.
\]

It is deliberately tiny and deterministic so that software failures can be separated from learning-performance questions.

## Frozen base

The smoke branch starts from the merged PPO-core commit:

\`443113ef05fd2bd2c6f9d91fac3cf488aedc050f\`.

## Tiny environment

The smoke case uses:

- horizon: 8 days;
- warm-up: 0;
- shelf life: 3 days;
- exporter-to-importer lead time: 1 day;
- importer-to-retailer lead time: 1 day;
- retailer mean demand: \((10,10,10)\);
- smoothing weight: \(0.30\);
- deterministic 8-day demand path;
- deterministic exporter-availability path containing all key availability states;
- training seed: \`41001\`.

The exact same deterministic exogenous scenario is used for \(N,S,F\).

## Decision architecture

Six actor-local learnable controllers are exercised:

\[
R1,\ R2,\ R3,\ BQ,\ E1,\ E2.
\]

Importer allocation remains the frozen deterministic N/S/F institutional rule and is not learned.

## Reward

For day \(t\),

\[
r_t
=
-
\frac{
LostSales_t+Waste_t
}{
\bar\lambda
}.
\]

On the final day, the terminal leftover penalty is added:

\[
-
\frac{
OnHand_T+Pipeline_T
}{
\bar\lambda
}.
\]

The same team reward is attached to each actor-local transition from that environment day.

## Rollout semantics

Every actor has its own rollout buffer containing only:

- legal encoded local observation;
- latent action;
- log probability;
- local critic value;
- team reward;
- done flag.

The smoke harness requires exactly one decision record per actor per environment day and verifies day alignment before constructing PPO batches.

## Stochastic-action reproducibility hardening

The PPO-core review exposed a reproducibility weakness: stochastic actions originally depended on the global PyTorch RNG.

The smoke branch fixes this by giving each actor its own deterministic action generator derived from the pre-registered training seed.

Therefore unrelated calls to \`torch.manual_seed(...)\` cannot silently alter an actor's stochastic action stream.

This is an implementation reproducibility fix; it does not change the scientific AI specification.

## Smoke pass conditions

For each of \(N,S,F\):

1. all 8 environment days complete without physical-balance failure;
2. six actor traces are produced and aligned by day;
3. team rewards are finite;
4. six PPO batches are finite;
5. six PPO updates are finite;
6. each local network changes after its synthetic tiny update;
7. repeating the same regime/seed/scenario reproduces the same smoke result;
8. importer allocation still obeys the frozen N/S/F mechanism.

## Non-result statement

A smoke pass does **not** show that AI learns a good policy, converges, improves service, reduces waste, reduces bullwhip, or dominates RuleBased.

It only establishes that the implementation pipeline is internally connected and numerically executable on a tiny deterministic case.

## Gate

\[
\boxed{
\text{FULL 5-SEED} \times \text{1000-EPISODE TRAINING REMAINS PROHIBITED UNTIL THIS SMOKE PR IS REVIEWED AND FROZEN.}
\]
