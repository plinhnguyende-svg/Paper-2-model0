# AI Specification Lock Checklist v0.1

This checklist must be completed before any AI training run.

- [ ] PR contains specification/configuration only; no training output or learned weights.
- [ ] PR #3 actor-isolated firewall remains unchanged.
- [ ] Decision nodes are fixed.
- [ ] Observation vectors and unknown-state encoding are fixed.
- [ ] Action transforms and feasibility masks are fixed.
- [ ] Reward and terminal penalty are fixed.
- [ ] PPO architecture and hyperparameters are fixed.
- [ ] Training seeds and fixed training budget are fixed.
- [ ] Held-out evaluation master seed and replication count are fixed.
- [ ] Primary outcomes and interaction estimands are fixed.
- [ ] Hierarchical bootstrap rule is fixed.
- [ ] CI passes.
- [ ] Specification PR is reviewed and merged.
- [ ] Merge commit is recorded as the sole base for the AI-training implementation branch.

Until every item is satisfied, the project remains under:

[
\boxed{\text{NO AI TRAINING RUNS}}
]
