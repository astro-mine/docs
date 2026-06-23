# Astro-Mine-Ledger — Technology Architecture

> Status: **Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) — implementation Phase 3.
> Layer: **Mission architecture & logistics** (NEW layer) · Phase: **3** (proposed)
> Open techno-economic & logistics modeling — cost / value / risk under explicit uncertainty: the mission-level objective / value function for trade studies.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Ledger` models **what a mission costs, what it is worth, and how uncertain both of
those are** — and exposes that as the **mission-level objective / value function** that trade
studies optimize against. It is to *economics and logistics* what [Prospect](prospect.md) is to
*resource fields*: a distribution, never a single deterministic guess (conventions.md §1.6). It
supplies the `objective` referenced by the [mission-model](mission-model.md) `MissionSpec` and
turns a candidate design — a fleet, a trajectory plan, a campaign — into a scored value with
calibrated error bars. Concretely it provides:

- **Cost models** — launch cost, development/asset (non-recurring + recurring) cost, and
  operations cost, expressed as **parametric cost-estimating relationships (CERs)** over the
  mass/power/complexity drivers supplied by [Sizing](sizing.md) and the Δv/time-of-flight budgets
  supplied by [Trajectory](trajectory.md), each carrying a CER residual distribution.
- **Value models** — delivered-resource value (mass × grade × price), in-space-vs-Earth delivery
  premiums, and reusable-asset amortization, with value uncertainty *propagated from*
  [Prospect](prospect.md)'s resource-field posterior, not assumed away.
- **Risk & schedule models** — probability of partial/total loss, schedule/logistics feasibility
  (launch cadence, fuelling, reuse cycles), and their effect on expected value.
- **An objective interface** — a `ValueModel` that maps a costed mission to a (possibly
  multi-objective) **distribution over ROI / NPV / delivered-mass / risk**, consumed directly by
  [Studio](studio.md)'s trade-study engine and [Bench](bench.md)'s mission-level scoring.

**Commons boundary (load-bearing — restated in §9).** Ledger ships an **open parametric
*framework*** plus **generic, public, citable cost/value models** (published CERs, textbook
amortization, public launch list prices). The **sensitive economics** — proprietary cost
databases, negotiated launch pricing, commodity/market price curves, and ROI-tuning calibrations —
stay in the **commercial layer above the open core** (charter §3 positioning) as
**access-controlled cost-data plugins** distributed via [Hub](hub.md). The framework is open; the
proprietary data is a plugin. **Proprietary economics MUST NOT be baked into the commons** — a
public clone of the repo must run end-to-end on public models and produce honestly-wide error
bars, exactly as a real mission analyst would before buying a private cost database.

**Explicitly out of scope.** Ledger is *not* the mass/power sizer ([Sizing](sizing.md)), *not* the
trajectory designer ([Trajectory](trajectory.md)), and *not* the resource estimator
([Prospect](prospect.md)); it *consumes* their outputs. It does not run the search loop (that is
[Studio](studio.md)'s `designspace`) — it supplies the objective that loop optimizes. It is not an
accounting/ERP system and holds no real financial ledgers; "Ledger" denotes the *value model*, not
bookkeeping. It also advances the charter §8 research gap **"evaluation science for swarm
campaigns"** by extending "what does *good* mean" from per-episode swarm metrics up to **mission
value** — co-owned with [Bench](bench.md).

**Primary users:** mission designers and ISRU/business analysts running Phase-0/A concept trades;
researchers studying mission-level evaluation science; commercial teams attaching private cost
data above the open framework.

**Charter alignment:** §3 (the commercial layer of proprietary tuning/economics sits *above* the
open core), §5.5 (Studio trade studies), §7 (parametric models, OpenMDAO-style MDO, Monte-Carlo
UQ), §8 (evaluation science for swarm campaigns), §10.4 (Apache-2.0 explicitly invites the
proprietary layer that sustains the commons).

---

## 2. Architecture principles

1. **Uncertainty is the product, not a footnote.** A Ledger result is a *distribution* over
   cost/value/ROI — mean **and** a calibrated spread (variance / quantiles / Monte-Carlo
   ensemble), never a bare point estimate. A point-estimate-only objective is an anti-pattern,
   mirroring [Prospect](prospect.md) §2.1.
2. **Ground truth vs belief, carried through.** Resource value is computed against
   [Prospect](prospect.md)'s **belief** posterior (what the swarm currently estimates), not its
   sealed **ground truth**. A design optimized against ground-truth value would be cheating in
   exactly the way a policy reading ground truth would be (Prospect §9). Ledger therefore consumes
   only belief-side fields, and contract tests assert it cannot reach ground truth.
3. **The framework is open; the sensitive data is a plugin.** Every CER, value, and risk model is
   a registered plugin behind a stable contract. Public models ship in-repo as *replaceable
   examples*; proprietary models attach as access-gated plugins (conventions.md §1.3, §12). No
   private number is ever a hard-coded constant in the commons.
4. **Provenance and citation are mandatory.** Every cost/value model records its source
   (publication, dataset, model-fit recipe) and its validity envelope. An uncited CER is a
   research artifact, flagged as such — the same discipline [Prospect](prospect.md) applies to
   priors (§2.4).
5. **Honest about extrapolation.** CERs are valid only inside the data range they were fit on.
   Querying a model outside its envelope (e.g., a 100× larger excavator than any datapoint) widens
   uncertainty and emits a warning rather than silently extrapolating a confident number.
6. **It is the objective, not the optimizer.** Ledger exposes a differentiable-where-possible
   `ValueModel`; [Studio](studio.md) and the OpenMDAO MDO graph *call* it as the objective.
   Search strategy, Pareto computation, and design-of-experiments live in [Studio](studio.md).
7. **Library first.** An analyst can `pip install astro-mine-ledger`, load public CERs, feed a
   `MissionSpec` plus a Prospect field, and Monte-Carlo an ROI distribution on a laptop — before
   any service exists (conventions.md §1.4).
8. **Composable accounting, traceable to source.** Mission value decomposes into per-phase,
   per-asset, per-leg line items (mission-model §1) so a number is always explainable: any ROI
   traces back to which CER, which Δv leg, which resource posterior produced it.
9. **Multi-objective by default, scalarized on request.** Cost, value, risk, and schedule are
   distinct axes; collapsing them to one scalar is a *choice the caller declares* (weights / utility
   function), not a baked-in assumption — this is what feeds [Studio](studio.md)'s Pareto front.

---

## 3. Application architecture

Ledger is primarily an **importable library** (cost/value/risk models + Monte-Carlo engine + an
OpenMDAO component wrapper), optionally fronted by a thin objective service for shared trade
studies. Its modules:

```
astro_mine.ledger
├── value/          # ValueModel contract: costed mission → distribution over objectives
├── cost/           # cost models behind a CostModel contract
│   ├── cer/        #   parametric cost-estimating relationships (public, fitted)
│   ├── activity/   #   activity/process-based bottom-up costing (ops, ISRU throughput)
│   └── learned/    #   data-driven cost surrogates (plugin; commercial calibrations gated)
├── revenue/        # delivered-resource value, delivery premiums, market-price model (price = plugin)
├── reuse/          # reusable-asset economics: amortization, refurb, fleet cycle accounting
├── risk/           # loss probability, risk-adjusted value, schedule/logistics feasibility
├── uncertainty/    # Monte-Carlo & analytic propagation; correlation handling; calibration
├── mdo/            # OpenMDAO ExplicitComponent wrapper (objective for Sizing/Studio MDO graph)
├── couple/         # adapters: Sizing mass/cost, Trajectory Δv/ToF, Prospect resource posterior
├── io/             # Parquet/Arrow results, model-bundle schema, provenance, content addressing
├── eval/           # calibration, backtesting, golden missions, validation harness
└── service/        # optional gRPC objective service + Studio/Bench objective adapter
```

### Key abstractions exposed

- **`ValueModel`** — the central contract. `evaluate(mission, context) -> ValueDistribution`,
  where `mission` is a [mission-model](mission-model.md) `MissionSpec` and the result is a
  **distribution over named objectives** (ROI, NPV, delivered-mass, expected-loss, makespan), with
  per-objective mean, variance/quantiles or ensemble, plus a line-item breakdown. This is the
  object the Mission `objective` field resolves to (mission-model §1).
- **`CostModel`** — `cost(drivers) -> CostDistribution`. A CER, activity model, or learned
  surrogate behind one interface; `drivers` are the mass/power/complexity parameters from
  [Sizing](sizing.md) and the Δv/duration from [Trajectory](trajectory.md). Declares its data
  source, fit recipe, residual model, and **validity envelope**.
- **`RevenueModel`** — `value(delivered_mass_distribution, grade, price) -> ValueDistribution`,
  where `delivered_mass` and `grade` carry uncertainty from [Prospect](prospect.md) and `price` is
  supplied by a (often proprietary) **price plugin**; the public default uses a flat,
  documented reference price with explicit caveats.
- **`UncertaintyEngine`** — propagates input distributions (CER residuals, resource posterior,
  price, loss probability) through the value computation. Backed by Monte-Carlo by default;
  analytic/first-order propagation and a [Prospect](prospect.md)-shared GP/ensemble path are
  selectable (§11).
- **`LedgerComponent`** — an OpenMDAO `ExplicitComponent` exposing `ValueModel` as the objective
  (and optionally its gradient) inside a multidisciplinary optimization graph shared with
  [Sizing](sizing.md).

### Extension points

- **Cost / value / risk models** — implement `CostModel`/`RevenueModel`/`RiskModel` and register a
  [Core](core.md) plugin manifest. Public CERs ship as replaceable examples; **proprietary cost
  databases, market-price curves, and ROI calibrations are access-gated plugins** (§9).
- **Price feeds** — `RevenueModel` price inputs are pluggable; the open default is a documented
  reference price, commercial feeds attach via [Hub](hub.md) under access control.
- **Uncertainty methods** — Monte-Carlo, analytic, and GP/ensemble propagators are interchangeable
  behind `UncertaintyEngine`.
- **Objective recipes** — utility/scalarization functions (weighted ROI, risk-adjusted NPV,
  constrained-value) registered as objectives consumable by [Studio](studio.md)/[Bench](bench.md).

### Interaction patterns

In-process library (default): models loaded via Core's registry; results written as Parquet/Arrow.
In a trade study, [Studio](studio.md)'s `designspace` calls `ValueModel.evaluate` per candidate —
or, in tighter co-optimization, Ledger is an OpenMDAO component in the same MDO problem as
[Sizing](sizing.md), so the optimizer sees fleet/trajectory/economics coupled in one graph. An
optional **objective service** (gRPC) serves shared, versioned models so a distributed sweep scores
against one consistent economic model; orchestrated over **NATS/JetStream** when run at scale
(conventions.md §4).

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.11+** (conventions.md §2) — the techno-economic, MDO, and probabilistic-
  programming ecosystem is Python-native. Type-hinted, `mypy`/`pyright`-checked.
- **Multidisciplinary optimization:** **OpenMDAO** (charter §7) — Ledger ships a `LedgerComponent`
  that plugs in as the objective alongside [Sizing](sizing.md)'s sizing components, so fleet ⇄
  trajectory ⇄ economics co-optimize in one MDO graph with analytic/complex-step derivatives where
  available.
- **Uncertainty propagation:** **Monte-Carlo** as the default (NumPy-vectorized; sampling input
  distributions and propagating through the value computation). **SALib** for global sensitivity
  (Sobol/Morris) so cost drivers are ranked, not guessed. Optional **first-order/analytic**
  propagation for cheap interactive feedback, and an optional **GPyTorch** GP-surrogate path that
  matches [Prospect](prospect.md)'s representation when the value model itself is expensive (§11).
- **Probabilistic modeling (research path):** **PyMC**/**NumPyro** for hierarchical Bayesian CER
  fits where the residual structure warrants it; classical regression fits via
  **statsmodels**/scikit-learn for the dependency-light reference path.
- **Numerics & data:** NumPy / SciPy; **pandas**/**Apache Arrow** for tabular cost/value line items
  and **Parquet** results (conventions.md §5).
- **Config & schemas:** **JSON Schema + Pydantic v2** for model/objective specs; the `ValueModel`
  result and the Mission `objective` reference are **[Core](core.md)-owned schemas**
  (conventions.md §3).
- **Runtime model:** importable library; optional **FastAPI** (admin/REST) + **gRPC** objective
  service (conventions.md §3, §4).
- **Build/packaging:** Python wheel `astro-mine-ledger`; OCI image for the objective service;
  cost/value/price backends distributed as **OCI plugin artifacts**, **access-gated for proprietary
  models** (conventions.md §7, §12).

---

## 5. Data architecture

**Owned / produced:**

| Artifact | Format / store | Notes |
|---|---|---|
| Value/objective results (distributions over ROI/NPV/mass/risk) + line-item breakdown | **Apache Parquet** / **Arrow** | conventions.md §5; one row-group per candidate / Monte-Carlo run; queryable by Studio/Bench |
| Cost/value **model bundles** (fitted CER coefficients, residual models, validity envelopes) | model bundle (JSON manifest + Parquet/Arrow); large learned weights in **object store**, content-addressed | reproducible refit recipe recorded |
| Monte-Carlo sample ensembles (when retained for downstream EVPI) | **Parquet** (a `sample` axis) | sampled per-objective realizations |
| Catalog metadata (models, sources, citations, provenance, access class) | **PostgreSQL** | conventions.md §5; access-class column drives gating |
| Sensitivity / calibration / backtest results | **Parquet** | consumed by `eval`/[Bench](bench.md) |

**Schema.** The `ValueModel` result and the Mission `objective` reference are **[Core](core.md)-
owned** message types (Protobuf wire form + JSON Schema specs), so [Studio](studio.md),
[Bench](bench.md), and Ledger exchange identical objective descriptors (conventions.md §3). Every
quantity carries **explicit SI / currency units and a declared uncertainty representation** —
mirroring [Prospect](prospect.md)'s units discipline. Currency is explicit (unit + year +
real/nominal) so no implicit-dollar assumptions leak; there is no implicit Earth-economy default.

**Uncertainty representation (a result-layout choice).** Three encodings, tagged per result,
exactly paralleling [Prospect](prospect.md) §5: (a) **parametric** — `mean` + `variance` per
objective (default for analytic propagation); (b) **ensemble** — a stacked `sample` axis of
Monte-Carlo realizations (default for MC, and what preserves correlation across objectives for a
correct Pareto front); (c) **quantile** — a compact `quantile` axis for downstream consumption.

**Coupling representation.** Resource-value uncertainty is *carried through, not collapsed*: Ledger
ingests a [Prospect](prospect.md) belief field (or its delivered-mass posterior) and **samples it
jointly** with cost and price distributions so correlations (e.g., grade ↔ delivered value) are
preserved — averaging the resource field first and costing the mean would understate spread (§8).

**Lifecycle & provenance.** Every result records its inputs (model bundle hashes, the
[Sizing](sizing.md) design hash, the [Trajectory](trajectory.md) `ManeuverBudget` hash, the
[Prospect](prospect.md) field hash), producing code version, environment lockfile, and **random
seed** (conventions.md §5, §1.5), so any ROI distribution is reproducible by replay — the same
content-addressed discipline as a [Bench](bench.md) scorecard. **Proprietary model bundles are
content-addressed but access-class-tagged and stored gated** (§9); a public result references a
proprietary input by hash without exposing its contents.

**Versioning.** Models and objectives are content-addressed and SemVer-tagged; a [Bench](bench.md)
mission-level scenario pins exact model-bundle hashes so an economic comparison reproduces exactly
and is auditable for which cost assumptions produced a ranking.

---

## 6. Integration architecture

Ledger sits in the **design/training loop** as the mission-level objective producer (charter §6),
plugging into siblings through [Core](core.md) contracts and the [mission-model](mission-model.md)
`MissionSpec`:

- **[mission-model](mission-model.md) (supplies the objective):** Ledger is what the Mission
  `objective` field resolves to — the value/score model for the whole multi-phase mission. It reads
  the phase/leg/asset structure to attribute cost and value per phase.
- **[Sizing](sizing.md) (consumes):** fleet mass, power, propellant, and recurring/non-recurring
  cost drivers feed Ledger's CERs. In co-optimization, both are **OpenMDAO components in one MDO
  graph** so sizing and economics solve together.
- **[Trajectory](trajectory.md) (consumes):** the descriptive `TrajectoryRef` / `ManeuverBudget`
  (Δv, time-of-flight, window feasibility — mission-model §2.3) drive propellant cost, mission
  duration (→ operations cost and NPV discounting), and reuse-cycle timing. Ledger consumes only
  the **design-time descriptive artifact**, never executable guidance (export boundary, §9).
- **[Prospect](prospect.md) (consumes uncertainty):** the **belief** resource posterior supplies
  delivered-mass and grade distributions, propagated jointly into value (not averaged first). This
  is the resource-value coupling that makes ROI uncertain in a *grounded* way.
- **[Core](core.md) (exposes):** the `ValueModel` result and `objective` reference are Core schema
  catalog types; Ledger models are discovered through Core's plugin registry/manifest.
- **[Studio](studio.md) (provides the objective):** Studio's `designspace` trade-study engine
  calls `ValueModel.evaluate` to score and **Pareto-rank** candidates against the mission value
  function; objectives/scalarizations Ledger publishes appear as Studio objectives.
- **[Bench](bench.md) (provides mission-level metrics):** Ledger contributes **mission-level value
  metrics** as Bench metric plugins — extending Bench's evaluation science (charter §8) from
  per-episode swarm scores to whole-mission ROI/value-at-risk, with the same uncertainty-aware
  metric contract Bench already defines.
- **[Hub](hub.md) (distributes):** public model bundles are published, discovered, and reused as
  content-addressed artifacts; **proprietary cost-data / price plugins are distributed
  access-controlled via Hub** (§9), the commercial layer attaching above the commons.

**Message flow (trade-study objective loop):** [Studio](studio.md) proposes a candidate →
[Sizing](sizing.md) sizes the fleet, [Trajectory](trajectory.md) budgets the legs → Ledger
`evaluate` samples cost × price × the [Prospect](prospect.md) resource posterior through the
`UncertaintyEngine` → returns a `ValueDistribution` → Studio's `pareto` ranks; [Bench](bench.md)
scores the same value for the leaderboard. Distributed over **NATS/JetStream** events when run as a
service (conventions.md §4).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — library in a single Python env; public CERs, a `MissionSpec`, and a Prospect
     field; a Monte-Carlo ROI distribution on a workstation in seconds-to-minutes. The full "load
     public models → evaluate a mission → get a distribution" loop MUST run locally on public data.
  2. **Cloud** — OCI-containerized **objective service** on Kubernetes; large Monte-Carlo ensembles
     and global-sensitivity sweeps fan out via **Ray**; trade-study co-optimization runs inside
     [Studio](studio.md)'s/[Cloud](https://github.com/astro-mine/cloud)'s scale-out
     (conventions.md §7).
- **Compute profile:** mostly **CPU-bound** — Monte-Carlo sampling and CER evaluation are cheap and
  embarrassingly parallel (Ray fan-out over samples/candidates); the cost center is *upstream*
  ([Sim](sim.md) candidate evaluation), so Ledger imposes negligible marginal cost per candidate.
  The optional GP-surrogate uncertainty path may use a GPU (GPyTorch) for expensive value models.
- **Storage:** results stream from **S3-compatible object storage** (MinIO self-host; S3/GCS cloud)
  as chunked Parquet; **proprietary model bundles live in an access-gated bucket/registry** separate
  from public artifacts (§9).
- **Scaling:** stateless objective-service replicas behind a load balancer; model bundles cached in
  Redis/object store; deterministic, seeded evaluation so replicas agree.

---

## 8. Performance & scalability

**Targets (Phase 3, mission trade studies).** A single mission `evaluate` with a default
Monte-Carlo budget (~10⁴ samples) in sub-second to a few seconds on a workstation; a Studio trade
study of 10²–10⁴ candidates parallelized so Ledger is never the bottleneck; calibrated objective
distributions (credible-interval coverage in tolerance) on the golden missions.

**Primary cost = Monte-Carlo budget × candidate count.** Each candidate is sampled through cost ×
price × resource-posterior distributions. This is cheap per sample but multiplies across a large
design space.

**Mitigations:**

- **Vectorized Monte-Carlo** (NumPy/Arrow) over the whole sample batch; **Ray fan-out** across
  candidates and samples (conventions.md §8).
- **Analytic / first-order propagation** for interactive feedback during authoring, reserving full
  Monte-Carlo for committed trade-study runs (a **multi-fidelity** dial, conventions.md §8).
- **Quasi-Monte-Carlo / variance reduction** (Sobol sequences, common random numbers across
  candidates) so fewer samples reach a target confidence and candidate *rankings* are low-variance.
- **GP value-surrogate** for genuinely expensive value models — and, importantly, **shared random
  state / correlation handling** so resource-field uncertainty from [Prospect](prospect.md) is
  sampled *jointly* with cost rather than convolved naively (correctness, not just speed: averaging
  the resource field before costing understates ROI spread — §5).
- **Global sensitivity (SALib)** to prune low-impact cost drivers, shrinking the effective
  uncertainty space.

Performance claims ship with reproducible benchmarks (conventions.md §8).

---

## 9. Security, safety & compliance

- **The commons / commercial boundary (the key property).** Ledger's open framework + public models
  are squarely in the science/economics commons (Apache-2.0, charter §3, §10.4). **Proprietary cost
  databases, market/commodity price feeds, and ROI-tuning calibrations are partitioned into
  access-controlled plugins** in the commercial layer above the core — they are **never committed
  to the open repo and never hard-coded as constants**. This is enforced by [Core](core.md)
  capability tags + **OPA** policy and an `access-class` on every model bundle; the registry refuses
  to surface a gated model to an unauthorized caller (conventions.md §9, §12). A public checkout
  must produce a valid, honestly-uncertain result with no proprietary input present.
- **Ground-truth isolation, inherited.** Ledger evaluates value against [Prospect](prospect.md)'s
  **belief** field only; contract tests assert it cannot reach a `GroundTruthField` (Prospect §9) —
  optimizing economics against ground-truth resources would be the same leak class.
- **AuthN/AuthZ:** OIDC + RBAC via **OPA** on the objective service; read of gated model bundles is
  policy-gated (conventions.md §9).
- **Supply chain:** model-backend and price plugins are **signed (Sigstore/cosign)** with **SLSA**
  provenance and **SBOM**; the registry verifies before load (conventions.md §9).
- **Plugin isolation:** untrusted third-party cost/value plugins run **out-of-process** (sandboxed
  container, seccomp/gVisor) per conventions.md §9 — third-party model code should not run
  in-process with privileged services.
- **Export control / dual use:** generic public CERs and Δv-driven cost models are open. Ledger
  consumes only **descriptive** [Trajectory](trajectory.md) artifacts (Δv/ToF budgets), **not**
  executable guidance, so it never crosses the `operational_targeting` line (mission-model §4,
  [EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md)). Economics
  is not itself export-sensitive; the sensitivity here is *commercial confidentiality*, handled by
  the same gating mechanism.
- **Scientific & decision safety:** uncertainty must be **honest** (charter §9). An over-confident
  ROI is a credibility hazard for an ISRU investment decision; calibration gates in CI guard against
  shipping mis-calibrated cost/value models, exactly as [Prospect](prospect.md) gates priors.

---

## 10. Observability & operability

- **Telemetry:** OpenTelemetry traces/metrics/logs (conventions.md §10); a value evaluation is
  traceable end-to-end (Studio candidate → Sizing/Trajectory drivers → Prospect posterior →
  Ledger `evaluate` → Studio Pareto / Bench score).
- **Metrics:** evaluation latency, Monte-Carlo sample count vs. achieved confidence, fraction of
  queries hitting a CER **validity-envelope warning**, calibration drift, gated-model access
  decisions — exported to Prometheus/Grafana.
- **Explainability:** every result carries a **line-item cost/value breakdown** and a
  **sensitivity ranking** of the dominant cost drivers, so a designer sees *why* one mission scores
  above another, not just that it does (principle §8).
- **Validation strategy (conventions.md §11):**
  - **Calibration / backtesting** — predicted cost/value distributions checked against historical
    mission cost outturns (public datasets) and held-out CER data; CI **fails** on mis-calibration
    beyond budget.
  - **Golden / determinism gates** — seeded reference missions with stored expected value
    distributions; CI fails on non-reproducibility (conventions.md §1.5, §11).
  - **Property-based tests (Hypothesis)** — invariants: value monotone in delivered mass and price,
    monotone-decreasing in cost; zero resource ⇒ zero revenue; tighter resource posterior ⇒ no wider
    value spread, all else equal; units and currency preserved; an out-of-envelope query widens
    (never narrows) uncertainty.
  - **Cross-method agreement** — Monte-Carlo, analytic, and GP-surrogate propagation agree within
    stated tolerance on a shared problem, so a method swap is observable and bounded (mirroring
    [Prospect](prospect.md) §10 cross-backend agreement).
  - **No-proprietary-leak test** — a public-only build produces a complete result; CI asserts no
    gated constant or dataset is reachable in the open package.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Cost-model approach | **Parametric CERs**; activity/process-based bottom-up; learned/data-driven surrogates | **Parametric CERs (public, fitted) as the open default** for the generic framework; **activity-based** for ops/ISRU-throughput costs where a CER is too coarse; **learned surrogates as plugins** (commercial calibrations gated). All behind one `CostModel` contract. |
| Uncertainty method | **Monte-Carlo**; analytic/first-order propagation; the GP/ensemble approach shared with [Prospect](prospect.md) | **Monte-Carlo default** (preserves cross-objective correlation, handles arbitrary input distributions, simple to trust); **analytic** as a cheap multi-fidelity interactive path; **GP-surrogate** (GPyTorch, Prospect-aligned) only when the value model itself is expensive. |
| Open-framework vs proprietary-data boundary | Bake economics into the commons; **open framework + generic public models, proprietary data as access-gated plugins**; close the whole component | **Open framework + public generic models; proprietary cost DBs / prices / ROI tuning as access-controlled [Hub](hub.md) plugins** above the core (charter §3). A public clone must run end-to-end. Never hard-code a private number. |
| Resource-value coupling to [Prospect](prospect.md) | Use the resource **mean** only; **sample the resource posterior jointly** with cost/price; full EVPI on resource information | **Sample the [Prospect](prospect.md) belief posterior jointly** with cost/price so grade↔value correlation and ROI spread are correct; **EVPI** (value of better prospecting) as a research path tying Ledger value back to Prospect's info-gain objective (Prospect §11). |
| Objective shape | **Single scalar** (e.g., weighted ROI); **multi-objective / Pareto** (cost, value, risk, schedule) | **Multi-objective by default**, feeding [Studio](studio.md)'s Pareto front; **scalarization is a caller-declared utility/weight recipe**, never baked in (principle §9). |
| Optimization integration | Ledger drives its own optimizer; **expose an OpenMDAO component as the objective**; black-box callable only | **OpenMDAO `ExplicitComponent`** as the objective (charter §7), co-optimized in one MDO graph with [Sizing](sizing.md); also a plain `ValueModel.evaluate` callable for Studio's black-box `designspace` search. |
| CER fitting method | Manual/literature coefficients; **classical regression fits**; hierarchical Bayesian fits | **Classical regression** for the dependency-light reference path; **hierarchical Bayesian (PyMC/NumPyro)** as a research plugin where residual structure and small-sample uncertainty warrant it; literature coefficients always cited. |

**Open questions / research dependencies:**

- *Evaluation science for mission value* (charter §8): what is the right mission-level objective —
  risk-adjusted NPV, expected delivered mass per dollar, value-at-risk — and how it composes with
  per-episode swarm metrics in [Bench](bench.md). Co-designed with [Bench](bench.md)/[Studio](studio.md).
- *Coupling resource uncertainty to value of information*: formalizing **EVPI** so "is more
  prospecting worth it?" is answered by Ledger value against [Prospect](prospect.md) info-gain — the
  economics half of "plan to learn" (Prospect §8, §11).
- *CER fidelity & extrapolation risk*: public CERs are fit on a thin, Earth-launch-biased data set;
  quantifying mis-specification risk for novel asteroid-mining architectures without proprietary
  data is itself a research problem (honest uncertainty over confident extrapolation).
- *Where the commercial boundary sits exactly*: which calibrations are "generic enough" to be
  commons vs. genuinely proprietary — a governance question resolved via the RFC process and
  EXPORT_CONTROL/commercial-layer policy, not unilaterally in code.
- *Scalarization vs. true Pareto in co-optimization*: how tightly the MDO graph should encode a
  scalar objective vs. handing a multi-objective front to [Studio](studio.md) (mission-model §6).

---

## 12. Roadmap alignment

- **Phase 3 (proposed — gated on [RFC-0001](../rfc/0001-multi-regime-missions.md)).**
  Ledger is part of the multi-regime/interplanetary extension and lands with its siblings
  ([Sizing](sizing.md), [Trajectory](trajectory.md)) once the [mission-model](mission-model.md)
  `MissionSpec`/`objective` schema hooks exist in Core. Initial deliverable:
  - the `ValueModel`/`CostModel`/`RevenueModel`/`RiskModel` contracts + the **Monte-Carlo
    `UncertaintyEngine`**;
  - **public parametric CERs** (launch, development, operations) with cited provenance and validity
    envelopes;
  - **resource-value coupling** sampling the [Prospect](prospect.md) belief posterior jointly;
  - the **OpenMDAO `LedgerComponent`** as the objective shared with [Sizing](sizing.md);
  - **Parquet** result IO, Core objective schemas, calibration + golden-mission validation;
  - one [Bench](bench.md) **mission-level value metric** and a [Studio](studio.md) multi-objective
    trade-study integration — enough to ROI-rank candidate asteroid-mining mission architectures on
    public data.
- **Schema-hook prerequisite (Phase 1).** The Mission `objective` reference must land as a Core
  schema hook during Phase 1 alongside the other mission-model hooks (mission-model §3), even though
  Ledger's implementation is Phase 3 — retrofitting the objective into a frozen waist later is the
  leaky-interface failure the charter warns against.
- **Beyond Phase 3.** Hierarchical-Bayesian CER fits and EVPI-tied resource-information economics;
  richer reusable-asset/logistics modeling (depots, in-space refuelling cycles); the distributed
  objective service; and a maturing **commercial-plugin ecosystem** of proprietary cost/price models
  attaching above the open framework via [Hub](hub.md) — the charter's commercial layer sustaining
  the commons (charter §3, §10.4).
