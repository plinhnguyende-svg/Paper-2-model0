# Evaluation preflight audit, 2026-09-20

Status: HOLD. This is an implementation audit, not a scientific result.

PR #12 head fe2b293ddf1011088ec0e64057a3aed625e7d1ca passed CI,
AI Smoke Training and AI Full Training Freeze Gate. Passing these checks
does not establish compatibility with the fifteen actual training archives.

## Changes for the real-archive gate

The preflight workflow checks out the PR head, uses Ubuntu 24.04 and Python
3.12.14, and installs the training requirements and constraints unchanged.
It downloads the exact fifteen artifact IDs in the byte-bound registry,
verifies each ZIP digest, and invokes the production checkpoint loader.
The loader checks checkpoint and manifest hashes, runtime/config metadata,
six actor network states and finite tensors. The audit also compares the
complete training schedules across N/S/F for each seed. It performs no
simulation with trained policies and generates no held-out scenarios.

The successful audit JSON records the checked source SHA, runtime, registry
hash and fifteen checkpoint identities. Missing evidence is a failed gate.
The separate dry-run uses only the existing synthetic eight-day fixture.

Panel analysis now rejects evaluation seeds that differ from the fixed
SeedSequence(52001) schedule, even when treatment pairing is internally
consistent. Previously a consistently substituted seed schedule could pass.

## Execution and durability findings still blocking freeze

Uncommitted workspace candidates include a sharded runner, atomic row store,
collector and resume wrapper. These are not included in the preflight commit.
They require further review before publication or execution:

1. A caller-supplied environment SHA is not an independent freeze binding.
   The authorized source must be pinned by a reviewed execution workflow,
   with workflow ref/SHA and clean checkout checks before held-out access.
2. A missing prior shard artifact cannot imply that the shard never ran.
   Resume must fail closed when durable state is absent. Otherwise an
   interrupted runner can silently repeat previously committed trajectories.
3. Local fsync/rename establishes local atomicity, not remote durability.
   A step timeout needs reserved upload time; cancellation or runner loss
   can still lose local state. The execution protocol must state what is
   recoverable and stop when provenance cannot be recovered.
4. Restore must validate archive paths, duplicate members, row contracts,
   origin run, exact prior workflow/source and immutable completion records.
   Collector validation must bind the expected contract, not merely compare
   identical contracts supplied by the shards.
5. The final workflow, static shard matrix, first-run/resume authorization,
   partial failure behavior and final 3600-row collection need contract tests
   and a synthetic interruption/recovery exercise before freeze.

The candidate held-out entry point on PR #12 remains unconditionally closed.
No evaluation dispatch workflow is introduced by this preflight update.
Bootstrap seed 62001, percentile intervals and the existing crossed
seed/scenario resampling remain explicit implementation choices to freeze
before any held-out outcomes are generated.

Local validation for this update is syntax compilation and diff whitespace
checks. Local Python environments do not contain PyTorch; runtime and
integration results must come from the GitHub jobs, not inferred local tests.
