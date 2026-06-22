# Astro-Mine-Prospect — Technology Architecture

> Layer: **World & environment models** · Phase: **0**
> Probabilistic resource-field models with explicit uncertainty — what is in the ground, and how unsure we are.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Prospect` models **what resources exist in a world and how uncertain that estimate
is**. It expresses resource fields — water ice, hydrogen, mineral and volatile concentration,
regolith composition, grade — as **geostatistical distributions with explicit uncertainty**,
not single deterministic guesses (conventions.md §1.6). Concretely it provides:

- **Ground-truth fields** — the simulator's "true" resource state for a scenario, sampled from a
  generative geostatistical model conditioned on real planetary priors. The swarm never sees
  these directly; [Sim](sim.md) reads them to synthesize realistic sensor returns.
- **Belief / posterior fields** — the swarm's *evolving estimate* of the resource field,
  initialized from priors and updated by Bayesian belief updating as sensor observations arrive.
- **Information-gain signals** — derivatives of the belief (posterior variance, mutual
  information, expected-information-gain maps) that tell autonomy *where it is most worth looking*.

This separation — **ground truth for the world, belief for the agents** — is the core idea of
the package and the substrate for the "plan to learn" loop: active perception, prospecting,
and adaptive sampling.

**Explicitly out of scope.** Prospect is *not* the terrain/physics substrate — gravity, DEMs,
regolith mechanics, illumination, and thermal belong to [Worlds](worlds.md); Prospect is a
field *layered on top of* a world's spatial domain and CRS. It does *not* simulate sensors
(that is [Sim](sim.md)), does *not* plan (that is [Mind](mind.md) / [Allocate](allocate.md)),
and does *not* decide what counts as "good enough" coverage (that is a [Bench](bench.md)
metric). It models distributions and updates them; it does not act on them.

**Primary users:** ISRU planners and planetary scientists (authoring priors, validating
fields), plus autonomy researchers who consume belief and information-gain signals.

**Charter alignment:** §5.1 (Prospect component), §7 ("Gaussian processes for uncertainty"),
§8 ("decision-making under deep uncertainty in resource fields … the swarm must plan to
learn"), §9 ("the sim-to-real chasm … disciplined uncertainty quantification"), §13 (lunar
polar water-ice prospecting as the anchor scenario).

---

## 2. Architecture principles

1. **Uncertainty is the product, not a footnote.** A Prospect field is a *distribution*. Every
   query returns at minimum a mean and a calibrated uncertainty (variance / quantiles /
   ensemble), never a bare point estimate. A point-estimate-only API is forbidden.
2. **Ground truth and belief are different objects with the same interface.** Both implement one
   `ResourceField` contract so a planner can run identically against a synthetic world and a
   live estimate, but they are distinct types with distinct provenance and access control — the
   swarm must never accidentally read ground truth.
3. **Belief updating is monotone in information, not in optimism.** Conditioning on observations
   reduces posterior uncertainty where sampled and propagates correlation elsewhere; it never
   silently overwrites priors. Updates are explicit, auditable, and reversible (replayable from
   the observation log).
4. **Priors are sourced and cited, not invented.** Default resource priors are derived from real
   planetary datasets (LOLA, Diviner, LEND/neutron, M³, LCROSS, MARSIS, etc.) with recorded
   provenance and a documented derivation. A field with no cited prior is a research artifact,
   flagged as such.
5. **Layered on a world, never freestanding.** A Prospect field binds to a [Worlds](worlds.md)
   spatial domain, its CRS, and its time frame (conventions.md §5). No implicit Earth/WGS84 or
   ungrounded grids.
6. **Designed for active perception.** Information-theoretic quantities (posterior variance,
   mutual information, expected information gain under a candidate observation set) are
   first-class, queryable outputs — the package exists to make "plan to learn" tractable.
7. **Model family is a plugin, the field contract is not.** GPs, MRFs, deep generative fields,
   and Bayesian grids are interchangeable backends behind one Core-blessed field interface
   (conventions.md §1.3). New geostatistical methods ship as plugins.
8. **Calibration is a hard requirement.** Reported uncertainty must be *calibrated* against
   ground truth (coverage of credible intervals); calibration diagnostics are part of every
   field's validation, not optional (conventions.md §11).
9. **Library first.** A scientist can `pip install astro-mine-prospect`, load a prior, sample a
   ground-truth ice field for a crater, and update a belief from a CSV of fake sensor hits on a
   laptop — before any service exists (conventions.md §1.4).

---

## 3. Application architecture

Prospect is primarily an **importable library** (field models + Bayesian updating + IO),
optionally fronted by a thin field service. Its modules:

```
astro_mine.prospect
├── fields/          # ResourceField contract + backends (GP, MRF, deep-gen, grid)
│   ├── gp/          #   Gaussian-process fields (GPyTorch primary), sparse/variational
│   ├── mrf/         #   Markov-random-field / GMRF lattice fields
│   ├── generative/  #   deep generative / normalizing-flow conditional fields
│   └── grid/        #   sequential Bayesian occupancy/concentration grids
├── priors/          # planetary-dataset-derived priors: ingest, fit, catalog, cite
├── belief/          # Bayesian updating: condition on observations, posterior, replay
├── infogain/        # active-perception objectives: variance, MI, EIG maps
├── sensors/         # observation models (likelihoods) shared with Sim's sensor sim
├── io/              # Zarr/COG readers-writers, schema, provenance, content addressing
├── crs/             # binding to Worlds domain/CRS/time (SPICE/PROJ via conventions §5)
├── eval/            # calibration, scoring, golden fields, validation harness
└── service/         # optional gRPC field service + Gymnasium info-gain env adapter
```

### Key abstractions exposed

- **`ResourceField`** — the central contract. Methods: `mean(points)`, `variance(points)`,
  `quantile(points, q)`, `sample(points, n, seed)`, `posterior(region)`, and metadata (units,
  resource species, CRS, domain, provenance). Implemented identically by ground-truth and
  belief variants. Maps onto the [Core](core.md) **Environment API** as the resource layer of
  an observation.
- **`GroundTruthField`** — a fixed, seeded realization for a scenario (access-controlled;
  consumed by Sim, never by policies).
- **`BeliefField`** — a posterior carrying a prior + an observation log; supports
  `update(observations) -> BeliefField` (returns a new, content-addressed posterior).
- **`Observation`** — a typed sensor return: location(s), value(s), the **sensor likelihood**
  (noise model, footprint, depth response), timestamp, and provenance. Authored against a Core
  message schema so Sim and Ops produce identical observation records.
- **`InfoGainObjective`** — a callable mapping a candidate observation plan to a scalar / map of
  expected information gain, consumed by planners.

### Extension points

- **Field backends** — implement `ResourceField` (+ a fit/condition routine) and register a Core
  plugin manifest. GP vs MRF vs deep-generative vs grid are all plugins behind this point.
- **Sensor/observation models** — pluggable likelihoods (neutron spectrometer, NIR
  reflectance, GPR, mass spec, drill assay) shared between Prospect's updating and Sim's
  forward sensor model so they stay consistent.
- **Prior recipes** — declarative pipelines that turn a named planetary dataset into a fitted
  prior, contributed as plugins and indexed by [Hub](hub.md).
- **Info-gain objectives** — alternative acquisition functions (max-variance, BALD/mutual
  information, expected value of information for ISRU yield).

### Interaction patterns

In-process library (default): backends loaded via Core's registry; fields read/written as Zarr.
Optionally a **field service** (gRPC) serves large shared fields and streams belief updates so a
distributed swarm sim shares one consistent posterior. A **Gymnasium/PettingZoo adapter**
(conventions.md §3) exposes the belief + info-gain map as an observation and the choice of
*where to sample next* as an action, for training active-perception policies in [Learn](learn.md).

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.11+** (conventions.md §2) — the geostatistics/Bayesian ecosystem is
  Python-native. Type-hinted, `mypy`/`pyright`-checked.
- **GP / Bayesian inference:** **GPyTorch** (recommended primary — GPU-accelerated, scalable
  variational/sparse GPs, exact GPs via blackbox matrix-multiply) on **PyTorch**
  (conventions.md §6). **GPflow** (TensorFlow) and **scikit-gstat** (classical
  variography/kriging) supported as alternative backends; classical **kriging** via
  `scikit-gstat`/`PyKrige` for the simple, dependency-light reference path.
- **Deep generative fields:** PyTorch (normalizing flows / score-based / conditional
  generative models) where non-Gaussian, multimodal resource structure must be captured.
- **MRF / GMRF:** sparse-precision lattice solvers (SciPy sparse, optional `sksparse`/CHOLMOD).
- **Numerics & arrays:** NumPy / SciPy; **xarray** for labeled n-D fields over a CRS grid.
- **Geospatial:** **GDAL/rasterio** for COG DEM/raster priors; **PROJ** + **SPICE** (via
  Worlds) for planetary CRS and frames (conventions.md §5).
- **Performance kernels:** hot inner loops (covariance assembly, conditional sampling at scale)
  drop to **C++20**/CUDA behind Python bindings only where profiling justifies it
  (conventions.md §2, §8) — GPyTorch already provides GPU kernels for the common path.
- **Config & schemas:** **JSON Schema + Pydantic v2** for field/prior specs (conventions.md §3).
- **Runtime model:** importable library; optional **FastAPI** (admin/REST) + **gRPC** field
  service (conventions.md §3, §4).
- **Build/packaging:** Python wheel `astro-mine-prospect`; OCI image for the field service;
  field/prior backends distributed as **OCI plugin artifacts** (conventions.md §7).

---

## 5. Data architecture

**Owned / produced:**

| Artifact | Format / store | Notes |
|---|---|---|
| Resource fields (ground-truth & belief), n-D probabilistic | **Zarr** (chunked, cloud-native; HDF5 for interop) | conventions.md §5; dims include species, depth, and a distribution axis (mean/var or ensemble members) |
| Raster-derived priors / DEM-aligned layers | **Cloud-Optimized GeoTIFF (COG)** via GDAL, cataloged with **STAC** | conventions.md §5 |
| Fitted prior / model parameters (kernels, hyperparameters, flow weights) | model bundle (Zarr + JSON manifest); large weights in **object store**, content-addressed | reproducible refit recipe recorded |
| Observation logs (drives belief updates) | **MCAP** (timestamped, schema-tagged) or **Parquet** for tabular assays | conventions.md §4, §5 |
| Calibration / validation results | **Parquet** | consumed by Bench/eval |
| Catalog metadata (fields, priors, provenance, CRS) | **PostgreSQL + PostGIS** | conventions.md §5 |

**Schema.** Field and observation message types are owned by [Core](core.md) (Protobuf wire form
+ JSON Schema for specs), so Sim, Ops, and Prospect exchange identical observations and field
descriptors (conventions.md §3). Each field declares: resource species and **SI units** (e.g.
wt-% water-equivalent hydrogen, kg/m³, mass fraction), CRS + domain (bound to a Worlds world),
depth model, the uncertainty representation in use (full posterior / ensemble / quantiles), and
the model-family tag.

**Distribution representation (a Zarr layout choice).** Three encodings are supported and tagged
per field: (a) **parametric** — `mean` + `variance`/covariance summary arrays; (b) **ensemble**
— a stacked `realization` axis of N samples; (c) **quantile** — a `quantile` axis. Parametric is
the default for GP/grid; ensemble for deep-generative/non-Gaussian; quantile for compact
downstream consumption (see §11).

**Lifecycle & provenance.** Every field records its inputs (prior content hashes, source-dataset
hashes), producing code version, environment lockfile, and **random seed** (conventions.md §5,
§1.5). Belief fields additionally record the **ordered observation log** so any posterior is
reproducible by replaying observations against the prior — a content-addressed chain from prior
→ each update → current posterior. Ground-truth fields are sealed (immutable + access-gated)
once realized for a scenario.

**Versioning.** Fields and priors are content-addressed and SemVer-tagged; a [Bench](bench.md)
scenario pins exact prior + ground-truth-field hashes so prospecting results reproduce exactly.

---

## 6. Integration architecture

Prospect sits in the **design/training loop** as a world-layer producer (charter §6) and plugs
into siblings through [Core](core.md) contracts:

- **[Worlds](worlds.md) (consumes):** a Prospect field binds to a Worlds spatial domain, CRS,
  DEM, and illumination/PSR mask — e.g., ice priors conditioned on Diviner temperature and
  permanently-shadowed-region geometry. Worlds is the substrate; Prospect is the layer.
- **[Core](core.md) (exposes):** resource fields are surfaced as the **resource layer of the
  Environment API** observation, and Prospect message types live in the Core schema catalog.
- **[Sim](sim.md) (consumes ground truth):** Sim reads the sealed **ground-truth field** plus
  the shared **sensor likelihood** models to synthesize realistic, noisy sensor returns
  (neutron counts, NIR reflectance, drill assays) at agent locations.
- **[Mind](mind.md) & [Allocate](allocate.md) (consume belief + info-gain):** the **belief
  field** and **information-gain maps** are inputs to prospecting/sampling/active-perception
  planning — *where to send whom to learn the most* — and to ISRU siting (where to dig).
  Allocate weighs information value against power/comms/terrain cost.
- **[Learn](learn.md) (consumes via env adapter):** the Gymnasium/PettingZoo info-gain
  environment trains active-perception and adaptive-sampling policies.
- **[Bench](bench.md) (provides):** Prospect supplies the **lunar polar water-prospecting**
  scenario family — sealed ground truth + scored belief-quality / discovery / regret metrics.
- **[Hub](hub.md) (distributes):** fields, priors, and prior-recipes are published, discovered,
  and reused as content-addressed artifacts.
- **[Ops](ops.md) (later):** in operations, real sensor observations feed the same belief
  updater, so the operational posterior is computed by identical code to the simulated one.

**Message flow (belief loop):** Sim emits `Observation` records (Core schema, MCAP) → Prospect
`belief.update()` conditions the posterior → updated `BeliefField` + `InfoGain` map exposed via
the Environment API → Mind/Allocate plan the next observation set → Sim executes it. The loop is
distributed over **NATS/JetStream** events when run as a service (conventions.md §4).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — library in a single Python env; fields as local Zarr; GP fit on CPU or one
     GPU. The full "load prior → sample world → update belief" loop MUST run on a workstation.
  2. **Cloud** — OCI-containerized **field service** on Kubernetes; large prior fits and
     ensemble generation fan out via **Ray**; GPU GP inference scheduled with **KubeRay +
     NVIDIA GPU Operator** (MIG sharing) (conventions.md §7).
- **Compute profile:**
  - *Belief queries / updates:* CPU-bound for grids/MRFs; **GPU-accelerated** for GP
    conditioning at scale (GPyTorch). Memory dominated by covariance / inducing-point structures
    — bounded by sparse/variational GPs (§8).
  - *Ground-truth realization & ensembles:* embarrassingly parallel sampling → Ray fan-out;
    bursty, not steady-state.
- **Storage:** fields stream from **S3-compatible object storage** (MinIO self-host; S3/GCS
  cloud) via chunked Zarr/COG so a worker reads only the slices it needs (conventions.md §5, §8).
- **Scaling:** stateless field service replicas behind a load balancer; posterior state in
  object store + Redis cache; updates serialized per-field to keep one consistent posterior.

---

## 8. Performance & scalability

**Targets (Phase 0, anchor scenario).** Interactive belief queries over a polar-region grid
(~10⁶–10⁷ cells) at sub-100 ms for a region tile; belief updates per observation batch in
sub-second; calibrated credible-interval coverage within tolerance on the golden field.

**Primary bottleneck: GP inference cost.** Exact GP training/conditioning is **O(n³)** in
observations and dense in memory — intractable for large grids and long observation logs. This
is *the* scaling problem for the GP backend.

**Mitigations:**

- **Sparse / variational GPs with inducing points** (SVGP / SGPR in GPyTorch) — the recommended
  default for large fields; reduces cost to O(n·m²) for m inducing points (§11).
- **Structured / grid-exploiting GPs** (KISS-GP / SKI, structured kernel interpolation) where
  data lie on or near the world's regular grid — near-linear scaling.
- **GMRF approximation** — represent the field as a Gauss-Markov random field with a *sparse
  precision* matrix; updates are sparse linear solves, scaling far better than dense GPs and
  natural for lattice/grid domains (the SPDE link to Matérn GPs).
- **Tiling & multi-resolution** — chunked Zarr + region-local conditioning so global cost never
  dominates an interactive query; coarse-to-fine refinement near sampled areas.
- **GPU batching** for many simultaneous queries (info-gain map evaluation over candidate
  locations is naturally batched).
- **Multi-fidelity** (conventions.md §8): cheap quantile/parametric belief for interactive
  planning; full ensemble only when downstream EVPI/EIG demands it.

Info-gain map computation (EIG over many candidate observation sets) is the other heavy path;
it is parallelized over candidates (Ray/GPU) and approximated (e.g. BALD) when exact EVPI is too
costly. Performance claims ship with reproducible benchmarks (conventions.md §8).

---

## 9. Security, safety & compliance

- **Ground-truth isolation (the key safety property).** `GroundTruthField` is access-controlled
  and never reachable through the policy/agent-facing Environment API — only Sim's sensor model
  reads it. This is enforced by Core capability tags (conventions.md §3, [Core](core.md) §9) and
  OPA policy: an information leak from ground truth into a belief would silently break every
  active-perception result. Contract tests assert agents cannot read ground truth.
- **AuthN/AuthZ:** OIDC + RBAC via **OPA** on the field service (conventions.md §9); read/write
  of priors and fields is policy-gated.
- **Supply chain:** prior-recipe and field-backend plugins are **signed (Sigstore/cosign)** with
  **SLSA** provenance and **SBOM** (conventions.md §9); the registry verifies before load.
- **Plugin isolation:** untrusted third-party field/prior plugins run **out-of-process**
  (sandboxed container, seccomp/gVisor) per conventions.md §9 — model code that fits arbitrary
  data should not run in-process with privileged services.
- **Export control / dual use:** resource *priors derived from public planetary datasets* and
  *synthetic* fields are squarely in the open science commons (conventions.md §12, charter
  §10.5). Genuinely sensitive **operational targeting data** — a real, mission-specific,
  high-resolution ground-truth resource map of an actual prospect — is **partitioned** into
  access-controlled storage and tagged with export-control capability flags, not committed to
  the open commons. Public ⇒ open; operational ⇒ gated.
- **Scientific safety:** uncertainty must be **honest** (charter §9, §12). Over-confident
  fields are a credibility hazard for downstream ISRU decisions; calibration gates in CI guard
  against shipping mis-calibrated priors.

---

## 10. Observability & operability

- **Telemetry:** OpenTelemetry traces/metrics/logs (conventions.md §10); a belief update is
  traceable end-to-end (Sim observation → Prospect update → Mind/Allocate replan).
- **Metrics:** posterior-entropy reduction per observation, update latency, GP inference time,
  inducing-point count, calibration drift — exported to Prometheus/Grafana.
- **Validation strategy (conventions.md §11):**
  - **Calibration tests** — credible-interval coverage and reliability diagrams against held-out
    ground truth; CI **fails** on mis-calibration beyond budget.
  - **Golden / determinism gates** — seeded ground-truth realizations and seeded belief-update
    chains compared to stored references (conventions.md §1.5, §11).
  - **Property-based tests (Hypothesis)** — invariants: conditioning never increases variance at
    a noiselessly-observed point; posterior reduces to prior under no observations; quantiles are
    monotone; units/CRS preserved across updates.
  - **Geostatistical sanity** — recovered variograms/length-scales match the generating model on
    synthetic data; kriging cross-validation (leave-one-out) error within bounds.
  - **Cross-backend agreement** — GP, GMRF, and grid backends agree (within stated tolerance) on
    a shared synthetic problem, so a backend swap is observable and bounded.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Geostatistical model family | Gaussian processes; Markov random fields (GMRF); deep generative / normalizing-flow fields; sequential Bayesian grids; classical kriging | **GP default** (GPyTorch) for the principled-uncertainty path; **GMRF** for large lattice domains; **deep-generative** as a plugin for non-Gaussian/multimodal structure; **grid** for the simple, fast reference. All behind one `ResourceField` contract. |
| GP inference scaling | Exact GP; **sparse/variational (SVGP/SGPR, inducing points)**; structured (KISS-GP/SKI); GMRF/SPDE approximation | **Sparse/variational GP with inducing points** as the default large-scale path; **KISS-GP** when data lie on the grid; exact GP only for small fields. |
| GP library | **GPyTorch**; GPflow; scikit-gstat/PyKrige; GPJax | **GPyTorch** (GPU, scalable, PyTorch-native per conventions.md §6); scikit-gstat/PyKrige for the classical reference path. |
| Uncertainty representation | Full posterior (parametric mean+cov); ensemble (sampled realizations); quantiles | **Parametric posterior** default (GP/grid); **ensemble** for non-Gaussian/deep-generative; **quantile** as a compact downstream encoding. Field declares which (Zarr-tagged). |
| Ground-truth vs belief | Single field with a "revealed" mask; **two distinct typed fields** sharing one interface | **Two distinct typed fields** (`GroundTruthField` sealed/gated, `BeliefField` updatable) implementing one `ResourceField` contract — clean isolation (§9) and clean replay (§5). |
| Field storage | **Zarr**; HDF5; NetCDF; in-Postgres rasters | **Zarr** (chunked, cloud-native, distribution axis) per conventions.md §5; COG for raster-aligned priors; HDF5 for interop. |
| Active-perception objective | Max-variance; **mutual information / BALD**; expected value of information (EVPI/EIG on ISRU yield) | **Mutual-information / EIG** default for prospecting; **EVPI** when tied to a concrete ISRU production objective. Pluggable. |
| Prior fitting | Manual kernels; **dataset-derived fitted priors (recipe plugins)**; learned generative priors | **Dataset-derived fitted priors** with cited provenance (charter §7); learned priors as a research plugin. |

**Open questions / research dependencies:**

- *Decision-making under deep uncertainty* (charter §8, §9): the right active-perception
  objective coupling prospecting to ISRU yield (information vs production) — co-designed with
  [Allocate](allocate.md) and [Mind](mind.md) and benchmarked in [Bench](bench.md).
- *Prior fidelity & sim-to-real* (charter §9): how faithfully public datasets (LOLA/Diviner/
  LEND/M³/LCROSS) can seed credible priors, and how to quantify prior-misspecification risk —
  a planetary-science + UQ research thread; uncertainty must remain honest.
- *Scaling exact-uncertainty inference* to global, multi-species, depth-resolved fields without
  collapsing to point estimates — the GP/GMRF scaling frontier (§8).
- *Calibration under non-stationarity*: planetary fields are strongly non-stationary
  (PSR boundaries, terrain); stationary-kernel GPs may need deep-kernel or GMRF treatment.

---

## 12. Roadmap alignment

- **Phase 0 (MVP, ships now).** Prospect is a **Phase-0 deliverable** (charter §11) supporting
  the anchor **lunar polar water-prospecting** scenario:
  - the `ResourceField` contract + **GP (GPyTorch, sparse/variational)** and **grid** backends;
  - **water-ice / hydrogen priors** derived from public lunar datasets, with provenance;
  - **ground-truth realization** (sealed) + **Bayesian belief updating** from observations;
  - basic **information-gain (variance/MI) maps**;
  - **Zarr** field IO, Core message schemas, calibration + golden-field validation;
  - one [Bench](bench.md) prospecting scenario with scored belief-quality metrics.
  This is enough for `Sim + Worlds + Fleet + Bench` to run the reference loop end-to-end
  (charter §11, §13) — a researcher can prospect a synthetic crater on a workstation.
- **Phase 1+ (later).** GMRF and deep-generative backends; richer active-perception objectives
  (EVPI tied to ISRU yield) for [Learn](learn.md)/[Allocate](allocate.md); multi-species,
  depth-resolved and Martian fields; the distributed field service; [Hub](hub.md)-published
  community priors and prior-recipes.
- **Phase 2+ (operations).** The same belief updater fed by **real sensor returns** through
  [Ops](ops.md)/[Bridge](bridge.md), so the operational resource posterior is computed by
  identical, validated code to the simulated one — closing the design-to-operations loop.
