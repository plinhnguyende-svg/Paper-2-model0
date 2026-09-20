# AI Final Evaluation Secondary / Exploratory Protocol v0.1

**Status:** R2 EXPLORATORY-ONLY ANALYSIS

## 1. Hard prerequisites

R2 is admissible only because both upstream packages are already frozen:

- result package: `ai-final-evaluation-results-v0.1-frozen` at `7ea4ff9099525d1ee221905380f665f6d7627ff3`;
- R1 interpretation package: `ai-final-evaluation-interpretation-v0.1-frozen` at `ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b`.

R2 must not modify or supersede either package.

## 2. Exploratory outcomes

R2 contains exactly the four secondary outcomes registered before held-out evaluation:

1. retail-order bullwhip;
2. total lost sales;
3. total waste;
4. mean absolute stock-allocation gap averaged across exporters.

No additional outcome is introduced after observing the panel.

## 3. Frozen data and estimator

R2 reads the same immutable 3,600-row held-out panel:

- scientific run `35531760845`, attempt 1;
- panel JSONL SHA-256 `6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c`;
- evaluator SHA `9e42c4a39e6bc8be94d1ed44e993899e4d916481`;
- checkpoint-registry SHA-256 `0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a`.

The secondary interactions use the same estimator that was implemented and reviewed before held-out execution in
`src/paper2_model0/ai/evaluation_analysis.py`, Git blob
`d85cc1b9f673d0ecd801f9eb12142e9e861aecc2`.

That frozen module already accepts both primary and secondary registered metrics through `panel_arrays` and `paired_bootstrap`.

Thus R2 does **not** introduce a post-hoc uncertainty method. It uses:

- `Gamma_V = (S_AI-N_AI) - (S_RB-N_RB)`;
- `Gamma_H = (F_AI-S_AI) - (F_RB-S_RB)`;
- 10,000 crossed training-seed/scenario bootstrap draws;
- Monte Carlo seed 62001;
- percentile 95% intervals;
- between-training-seed SD.

## 4. Interpretation firewall

R2 is exploratory. It must not:

- change any R1 primary estimate, wording constraint, or interpretation lock;
- promote a secondary finding into a confirmatory result;
- use a secondary result to select or drop a training seed;
- retrain any policy or extend the pre-registered budget;
- generate new held-out trajectories;
- alter bootstrap settings;
- add p-values or significance language;
- claim that an exploratory interval on one side of zero is confirmatory evidence;
- claim universal N/S/F or AI/RuleBased rankings.

Permitted language includes "exploratory estimate", "exploratory interval lies above/below zero", "interval spans zero", and "seed-specific estimates are heterogeneous."

## 5. Stability disclosure

All five training seeds remain included for every AI regime. The R1 disclosure remains binding: only 1/15 training jobs met the preregistered stability criterion, while 14/15 did not stabilize under the preregistered finite budget.

Stability is not an inclusion criterion.

## 6. Required R2 outputs

For each of the four secondary metrics, R2 records:

- absolute means for N/S/F under RuleBased;
- absolute means for N/S/F under AI pooled over all five frozen seeds;
- RuleBased and AI S-N / F-S contrasts;
- exploratory Gamma_V / Gamma_H means;
- frozen-method 95% bootstrap intervals;
- between-seed SD;
- all five seed-specific interaction means.

## 7. Gate after R2

Only after R2 is reviewed and frozen may the project move to a manuscript-facing figure/table layer that combines R1 and R2 while preserving their confirmatory/exploratory distinction.
