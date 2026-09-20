# AI Final Evaluation Manuscript Presentation Protocol v0.1

**Status:** R3 PRESENTATION-ONLY LAYER

## 1. Frozen scientific inputs

R3 is permitted to read exactly two scientific result registries:

1. PRIMARY registry
   - path: `experiments/ai_final_evaluation_result_registry_v0.1.json`
   - frozen under R1 at `ai-final-evaluation-interpretation-v0.1-frozen`
   - R1 freeze SHA: `ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b`
   - Git blob SHA: `40d590f742c85f7e853bd3766a41fc335510b4b9`

2. EXPLORATORY registry
   - path: `experiments/ai_final_evaluation_secondary_result_registry_v0.1.json`
   - frozen at `ai-final-evaluation-secondary-v0.1-frozen`
   - R2 freeze SHA: `b8806be6fe79c3981b8d82eb781634c31926611d`
   - Git blob SHA: `3f99a7cca25e4ee7248d48e90d1db5aa45a08fe1`

R3 must not read the raw 3,600-row panel and must not import or call the scientific estimator.

## 2. Presentation outputs

R3 produces two fully separate result families:

- **PRIMARY — confirmatory presentation**
  - five primary outcomes;
  - Gamma_V and Gamma_H;
  - frozen mean, 95% interval, between-seed SD, five seed means.

- **EXPLORATORY — secondary presentation**
  - four registered secondary outcomes;
  - Gamma_V and Gamma_H;
  - frozen exploratory mean, 95% interval, between-seed SD, five seed means.

The layer emits:

- one CSV manuscript table per family;
- one Markdown manuscript table per family;
- one small-multiple interval SVG per family.

## 3. No scientific recomputation

R3 may transform stored numbers only for display:

- decimal rounding;
- table formatting;
- ordering and labels;
- SVG coordinate scaling.

It must not:

- reconstruct outcomes from trajectories;
- rerun bootstrap draws;
- recalculate Gamma estimands from raw data;
- select or drop seeds;
- change interval endpoints;
- create p-values or significance labels;
- combine PRIMARY and EXPLORATORY rows into one unlabeled table/figure.

## 4. Figure design

Because outcomes have different units, R3 must not place them on one shared numeric x-axis.

Each outcome receives its own panel and scale. Within each panel:

- Gamma_V and Gamma_H are shown separately;
- point estimate and frozen 95% interval are shown;
- zero is shown as the neutral reference;
- PRIMARY and EXPLORATORY figures are separate.

The figure is descriptive. An interval lying on one side of zero is not rendered with a significance symbol.

## 5. Labeling firewall

Every output must visibly contain one of:

- `PRIMARY`; or
- `EXPLORATORY`.

Exploratory rows must never be visually promoted above primary rows.

## 6. Reproducibility

The renderer must fail closed if either registry Git blob differs from the frozen blob SHA.

Committed R3 tables and figures are presentation artifacts only. The registries remain the scientific source of truth.

## 7. Next gate

After R3 is reviewed and frozen, the next admissible layer is manuscript prose/results-discussion assembly. That layer must cite R1 as the primary interpretation authority and R2 only as exploratory support.
