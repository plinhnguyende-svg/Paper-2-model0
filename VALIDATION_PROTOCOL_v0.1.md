# Model 0 Verification & Validation Protocol v0.1

## Research purpose

This protocol asks whether the observed N/S/F contrasts are properties of the information mechanism or artifacts of initialization, simulation length, random seed, replication count, or a narrow parameterization.

The protocol does **not** add AI, pricing, bidding, bargaining, blockchain costs, or a new demand process. It preserves Model 0's physical network and decision rules.

## Identification target

The two primary paired contrasts remain:

- **Vertical verification effect:** S - N
- **Horizontal rival-visibility effect:** F - S

The protocol does not search for a universally "best" regime. It checks whether each contrast is stable, where it changes sign, and whether those changes can be tied to existing Model 0 primitives.

## Stage order

1. **Warm-up convergence**
   - Use common random numbers.
   - Run one long trajectory per replication/regime.
   - Evaluate fixed-length measurement windows after candidate warm-up cutoffs.
   - A fixed measurement-window length is used so warm-up comparisons are not confounded by unequal sample size.

2. **Replication sufficiency**
   - Generate a nested sequence of paired replications.
   - At each checkpoint, report the mean paired effect and its 95% normal-approximation CI.
   - Precision is diagnosed from CI half-width and stabilization of the paired mean, not from p-values alone.

3. **Seed stability**
   - Repeat the paired design under several independent master seeds.
   - Report seed-level paired means and confidence intervals.
   - The purpose is to detect dependence on one arbitrary master random stream.

4. **Parameter provenance**
   - Separate normalization/model-structure choices from empirical/calibration claims.
   - Current baseline values are treated as computational baselines unless a source is explicitly documented.
   - No parameter should be described as empirically calibrated merely because it is used in the baseline.

5. **One-factor-at-a-time sensitivity**
   - Vary only existing Model 0 primitives.
   - Default factors: symmetric exporter availability probability, shelf life, exporter-to-importer lead time, importer-to-retailer lead time, and forecast smoothing weight.
   - Consumer-demand variance is **not** an independent Model 0 primitive because Poisson demand links mean and variance. A separate demand-variability factor would require a deliberate model extension and is therefore excluded from this protocol.

6. **Robustness phase maps**
   - Evaluate two-dimensional parameter grids with paired common random numbers at each cell.
   - Classify each paired effect as positive, negative, or CI-overlapping-zero.
   - Sign reversals are retained and reported; they are not treated as failed simulations.

## Primary reported outcomes

- service_level
- waste_share_of_terminal_outflow
- retail_order_bullwhip
- importer_procurement_bullwhip
- mean_abs_target_allocation_gap_1 / _2
- mean_abs_stock_allocation_gap_1 / _2
- total_lost_sales
- total_waste
- mean_total_inventory

## Mechanism-vs-parameterization decision logic

Evidence is more consistent with a **mechanism property** when a paired contrast:

1. survives warm-up choices after transients have dissipated;
2. reaches stable precision as replications increase;
3. is not driven by one master seed;
4. persists over a non-trivial region of existing primitives; and
5. satisfies the already-implemented neutrality/isolation tests.

Evidence is more consistent with a **parameterization artifact** when the contrast:

1. changes materially with reasonable warm-up cutoffs;
2. remains unstable as paired replications increase;
3. depends strongly on one seed;
4. appears only at an isolated baseline point; or
5. disappears after correcting a measurement definition.

A sign reversal over economically meaningful parameter regions is neither automatically a mechanism failure nor a universal ranking. It is a boundary result to be explained.

## Reproducibility rule

Every validation run must record:

- model version / Git commit,
- configuration,
- master seed,
- replication count,
- regime set,
- parameter value(s),
- warm-up and measurement-window choices.

Generated large output files should be written under an output directory rather than committed by default.
