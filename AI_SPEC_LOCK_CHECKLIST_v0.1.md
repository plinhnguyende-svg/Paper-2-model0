# AI Specification Lock Checklist v0.1

Scientific audit status before merge:

- [x] PR contains specification/configuration/audit/contract tests only; no training output or learned weights.
- [x] PR #3 actor-isolated firewall remains unchanged.
- [x] Learnable decision nodes are fixed.
- [x] Importer allocation remains the frozen N/S/F institutional rule.
- [x] Observation vectors and unknown-state encoding are fixed.
- [x] Forecast-state transition is fixed and identical to RuleBased.
- [x] Action transforms and bounds are fixed.
- [x] Reward and terminal penalty are fixed.
- [x] PPO architecture and hyperparameters are fixed.
- [x] Training seeds and fixed training budget are fixed.
- [x] Training-stability diagnostic is fixed.
- [x] Held-out evaluation master seed and replication count are fixed.
- [x] Primary outcomes and interaction estimands are fixed.
- [x] Hierarchical bootstrap and multiplicity rule are fixed.
- [x] Scientific audit is recorded.
- [x] CI passes on the audited branch.
- [ ] PR #4 is merged into \`main\`.
- [ ] Merge commit is recorded as the sole base for the AI implementation branch.

Until the final two items are completed:

\[
\boxed{\text{NO AI TRAINING RUNS}}
\]
