# Parameter Provenance Registry v0.1

This registry distinguishes **model structure**, **computational baseline choices**, and any future **empirical calibration**. At this stage, the repository does not contain evidence that the baseline numeric values are empirically calibrated.

| Primitive | Baseline | Role | Current status | Validation treatment |
|---|---:|---|---|---|
| number_of_retailers | 3 | network size | locked Model 0 structure | not varied |
| retailer_mean_demand | (10,10,10) | Poisson demand means | computational baseline / scale choice | held fixed in v0.1 |
| exporter_availability_probability | (0.8,0.8) | operational reliability | computational baseline | symmetric OFAT + phase maps |
| shelf_life_days | 7 | perishability | computational baseline | OFAT + phase maps |
| exporter_to_importer_lead_time_days | 2 | upstream logistics delay | computational baseline | OFAT + phase maps |
| importer_to_retailer_lead_time_days | 1 | downstream logistics delay | computational baseline | OFAT |
| demand_forecast_smoothing_weight | 0.30 | rule-based forecasting response | computational baseline | OFAT |
| simulation_horizon_days | 1000 | numerical horizon | computational design choice | audited via warm-up / fixed window |
| warmup_days | 200 | transient removal | computational design choice | explicitly audited |
| master_seed | 20260917 | reproducibility | computational design choice | explicitly audited |

## Important scope note

Poisson demand implies conditional variance equals the mean. Therefore "demand variability" cannot be varied independently while keeping the same Model 0 demand process. Introducing an independent variance parameter would change the stochastic demand model and belongs to a later robustness extension, not silent validation tuning.

## Update rule

When a parameter later receives a literature source, field estimate, or calibration target, add:
- source,
- empirical population/context,
- transformation/normalization,
- admissible range,
- whether the source supports the exact numeric value or only the qualitative range.
