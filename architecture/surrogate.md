# Astro-Mine-Surrogate — Technology Architecture

> Layer: **Multi-physics simulation** · Phase: **1** · Ships in: [`astro-mine-platform`](platform.md) · Extended for multi-regime missions (Phase 3)
> Learned, fast surrogates for the most expensive physics — with error you can trust.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Surrogate` trains and serves **learned surrogate models** that approximate the
most expensive physics in [Sim](sim.md) — above all **granular media and excavation contact**,
but also wheel/soil terramechanics, manipulation contact, and slow thermal evolution — orders
of magnitude faster than the high-fidelity solver, while carrying **explicit, tracked error
bounds** against ground truth. A surrogate is not a clever guess; it is an approximation that
*knows how wrong it might be* and says so.

What it does:

- **Trains** surrogate models from high-fidelity rollouts produced by [Sim](sim.md).
- **Quantifies uncertainty** per prediction (calibrated error bars, not point estimates).
- **Packages** trained surrogates as portable [Core](core.md)-described plugins (ONNX where
  feasible) that [Sim](sim.md) loads as a **low-cost fidelity tier**.
- **Detects drift** and **re-validates / resamples** against ground truth on a schedule or a
  trigger, so a surrogate that has wandered out of its trust region is caught and retired.

**Microgravity contact / anchoring surrogates.** The multi-regime extension adds a new
surrogate *domain*: small-body / microgravity regolith contact and anchoring, for the
`proximity_orbit` and `surface` phases of asteroid-mining and NEO-sample-return missions (see
[mission-model](mission-model.md), [Worlds](worlds.md)'s small-body work). This is the
**lowest-data, hardest case** the platform faces — there is almost no ground truth for small-body
regolith mechanics or microgravity contact dynamics — so it is the most demanding test of the same
bounded-error contract Surrogate already runs for lunar terramechanics, not a new contract. It is
trained, packaged, and ONNX-served exactly like every other surrogate domain.

**Explicitly out of scope:**

- Surrogate **does not** run scenarios, own the multi-fidelity *scheduler*, or define the
  Environment API — that is [Sim](sim.md) and [Core](core.md). Surrogate *produces* a fidelity
  tier; Sim *decides when to use it*.
- It **does not** train *policies* (that is [Learn](learn.md)) — it accelerates the environment
  those policies train in.
- It contains **no** high-fidelity solver; it is a consumer and approximator of one.
- It is **not** a general MLOps platform; experiment tracking and artifact storage are delegated
  to [Hub](hub.md) and the conventions.md §6 stack.

**Primary users:** ML researchers building/benchmarking physics surrogates; anyone running large
sweeps or interactive design who needs swarm-scale rollouts to be tractable; [Learn](learn.md)
(fast training rollouts) and [Studio](studio.md) (interactive iteration) as programmatic
consumers.

**Charter alignment:** §5.3 (the package definition: "learned, fast surrogates … with explicit
error tracking"); §8 ("fast, bounded-error surrogates for contact and granular physics");
§9 ("granular and excavation physics at interactive speed"; "the fidelity–speed frontier …
with trustworthy surrogate-error bounds"). §7 names the model families (GNNs, neural operators,
Gaussian processes), frameworks (PyTorch, JAX), and the portable artifact format (ONNX).

---

## 2. Architecture principles

1. **Error is the product, not an afterthought.** A surrogate ships with a calibrated
   uncertainty estimate or it does not ship. Per conventions.md §6 and §8, uncertainty is
   first-class; an unbounded surrogate is an anti-pattern. The headline deliverable is
   *bounded* error, not *low* error.
2. **The surrogate is a fidelity *tier*, not a fork.** A trained surrogate is a plugin behind
   the same [Core](core.md) Environment-step contract the high-fidelity solver implements, so
   [Sim](sim.md)'s scheduler can swap it in per task without code changes (conventions.md §1,
   §8). One contract, many speeds.
3. **Trust regions are explicit and enforced.** Every surrogate declares the input domain it was
   trained/validated on. Queries outside that domain raise uncertainty (and a flag), never a
   confident extrapolation. Out-of-distribution silence is forbidden.
4. **Ground truth is the only authority.** Surrogate quality is *always* measured against
   [Sim](sim.md) high-fidelity output, never against itself or another surrogate. Validation
   datasets are held out and content-addressed.
5. **Reproducible by construction.** Training data, code version, environment lockfile, seed,
   and hyperparameters are recorded for every surrogate (conventions.md §5, §11). The same
   inputs reproduce the same model and the same error report.
6. **Physics-aware over physics-blind.** Where it cheaply improves data efficiency and
   extrapolation — conservation laws, contact symmetries, frame/unit invariance — encode
   inductive bias (GNN message passing on particle graphs, physics-informed losses) rather than
   relying on a generic black box.
7. **Continual, but gated.** Surrogates can be retrained as new ground-truth data arrives, but
   any model promoted into [Sim](sim.md) must first pass an automated validation gate against a
   frozen oracle set. No silent online weight updates inside a running sim.
8. **Portable inference, framework-free deploy.** Training may use PyTorch or JAX, but the
   *served* artifact is ONNX (conventions.md §6) wherever the architecture allows, so [Sim](sim.md)
   and [Cloud](cloud.md) inference does not drag in a training framework.
9. **Per-domain model freedom, common interface.** The best surrogate family differs by physics
   domain (a GNN for granular flow, a neural operator for fields, a GP for low-dimensional
   emulation). The platform fixes the *interface and the error contract*, not the architecture.

---

## 3. Application architecture

Surrogate is a **library + training/serving toolkit**, not a monolithic service. Per
conventions.md §1.4 it is importable on a workstation first; the cloud trainer is a deployment
of the same code. Modules (library-only — there is no CLI):

```
astro_mine.surrogate
├── model.py        # SurrogateModel Protocol + the Prediction dataclass (the runtime seam)
├── report.py       # ErrorReport + its sub-models (the calibrated error bound)
├── manifest.py     # SurrogateAttributes + build_surrogate_manifest() (Core PluginManifest builder)
├── enums.py        # closed vocabularies (ChannelKind, PhysicsDomain, ServedBackend)
├── wire.py         # ErrorReport <-> Protobuf canonical wire form
├── datagen/        # high-fidelity sampling: design experiments, query Sim, label, archive
├── models/         # surrogate families + their training & uncertainty: GNN particle sim, losses,
│                   #   curricula, deep ensembles, split-conformal, trust regions
├── eval/           # validation against ground truth, error budgets, the promotion gate
├── retrain/        # offline retrain + gated-promotion harness
├── drift/          # OOD detection, drift monitors, re-validation & resampling triggers
└── serve/          # ONNX export, inference runtime, Core-tier adapter for Sim, signed Hub publish/load
```

### Key abstractions exposed

- **`SurrogateModel`** — a `@runtime_checkable` Protocol for the physics-step of its domain (a
  Surrogate-owned contract, since Core has no single-transition `predict` seam). Its
  `predict(state, action=None) -> Prediction` returns a frozen `Prediction`: per-channel `channels`
  + calibrated `uncertainty`, an `in_domain` flag and a signed `ood_margin`, plus optional
  per-particle `fields` / `field_uncertainty` for the learned-DEM extension. `action` is optional —
  a field-query surrogate has none.
- **`ErrorReport`** — the machine-readable artifact a surrogate carries: per-channel error
  distribution vs. ground truth (RMSE, calibration/coverage, tail behavior), the validation
  dataset hash, the declared trust region, and a recommended fidelity-substitution policy. This
  is what [Sim](sim.md)'s multi-fidelity scheduler *consumes* to decide whether the surrogate is
  acceptable for a given task tolerance (conventions.md §8).
- **`SurrogateAttributes` + `build_surrogate_manifest()`** — Core's `PluginManifest` is
  `extra="forbid"` and cannot be subclassed, so there is **no** `SurrogateManifest` type. Instead
  `build_surrogate_manifest()` constructs a plain Core `PluginManifest` and folds the surrogate
  facets — physics domain, input/output channels, trust-region bounds, recommended error budget,
  served backend, and the `ErrorReport` digest — into its open `attributes` map via a
  `SurrogateAttributes` model.
- **`SamplingPolicy`** — declarative spec for how `datagen` queries [Sim](sim.md) (e.g.,
  Latin-hypercube / Sobol over excavation parameters, active-learning acquisition over residual
  uncertainty).

### Key abstractions consumed

- [Core](core.md) Environment / physics-step contracts (the interface a surrogate must satisfy),
  the SADF/state schemas, and the plugin manifest/registry it publishes into (via `attributes`).
- [Sim](sim.md)'s high-fidelity runner (as a data source) and its fidelity-tier loading
  mechanism (as the deploy target).

### Extension points

- **New surrogate family** — implement `SurrogateModel` + an `uncertainty` adapter, register a
  manifest. No core change (conventions.md §1.3).
- **New uncertainty method** — pluggable: deep ensembles, conformal wrappers, GP residual
  models, Bayesian NN — all expose the same `uncertainty` interface.
- **New physics domain** — declare the state/action space and a `SamplingPolicy`; the rest of
  the pipeline (datagen → train → eval → drift → serve) is reused. **Microgravity contact /
  anchoring** is exactly such an additive domain: it registers a `SurrogateModel` +
  `ErrorReport` like any other and changes no Surrogate–[Sim](sim.md) contract.

### Interaction patterns

Two loops. **Offline (build):** `datagen` drives [Sim](sim.md) → `models` (train + calibrated
uncertainty) → `eval` (validation gate) → `serve.export` (ONNX) → `manifest` → `serve.publish` to
[Hub](hub.md); `retrain` re-runs the loop on a gated schedule.
**Inline (use):** [Sim](sim.md) loads the surrogate as a fidelity tier and calls `predict`
in-process per tick; `drift` monitors live queries for OOD/drift and, on trigger, schedules a
ground-truth re-validation and resample. Surrogate exposes a gRPC training/serving service
(conventions.md §4) only for the cloud-scale deployment; the in-sim path is in-process for
latency.

---

## 4. Application programming & runtime platforms

- **Languages:** Python 3.12+ for the whole control surface, training, and APIs
  (conventions.md §2). Hot inference kernels and custom GNN ops drop to C++/CUDA behind pybind11
  where profiling demands it; the public API stays Python-reachable (conventions.md §2 rule).
- **ML frameworks:** **PyTorch** as the primary training framework; **JAX** (with Brax/`jraph`)
  where differentiable, massively-parallel rollouts or `jit`/`vmap` give a decisive speedup
  (conventions.md §6). The choice is per-model and recorded in provenance.
- **Model libraries:** `torch_geometric`/`jraph` for GNN particle simulators; `neuraloperator`
  (FNO) and DeepONet implementations for neural operators; **GPyTorch** / **GPJax** for Gaussian
  processes; `torchcp`/`MAPIE` for conformal prediction.
- **Inference runtime:** **ONNX Runtime** (CPU/CUDA execution providers) for served surrogates;
  the in-sim path may also run the native PyTorch/JAX graph when ONNX cannot express an op
  (e.g., some dynamic GNN gathers) — that fallback is flagged in the manifest.
- **Distributed training:** **Ray** (Ray Train / Tune) on **KubeRay** with the **NVIDIA GPU
  Operator** (conventions.md §6, §7); **Argo Workflows** for DAG-style datagen→train→eval
  sweeps.
- **Runtime model:** library-first — `import astro_mine.surrogate` on a workstation for
  single-GPU training and local serving; the same code packaged as an OCI image for [Cloud](cloud.md)
  scale-out. Inference inside [Sim](sim.md) is an in-process call, not a network hop.
- **Build/packaging:** ships in the [`astro-mine-platform`](platform.md) wheel; OCI
  training/serving images; trained surrogates are **OCI artifacts** (ONNX + `ErrorReport` + manifest)
  per conventions.md §7, SemVer-tagged and content-addressed. The model is the versioned thing here,
  not the code that trained it.

---

## 5. Data architecture

**Owned / produced:**

- **Training & validation datasets** — high-fidelity rollouts sampled from [Sim](sim.md):
  state/action/next-state tuples and physical fields. Stored as **Zarr** (chunked N-D arrays
  for particle/field data) and **Parquet** (tabular features/scalars), per conventions.md §5;
  recorded rollouts as **MCAP** where time-series replay is wanted.
- **Trained surrogate artifacts** — **ONNX** model (portable; conventions.md §6) plus
  training-framework checkpoint (internal), the **`ErrorReport`**, calibration tables, and the
  **`SurrogateManifest`**, bundled as a content-addressed OCI artifact in the object store
  (MinIO/S3/GCS, conventions.md §5, §7).
- **Drift & validation records** — time-series of live-query OOD scores, periodic re-validation
  error vs. ground truth, and resampling decisions, in TimescaleDB/Parquet for queryability.

**Consumed:**

- High-fidelity outputs and the SADF/state schemas from [Sim](sim.md)/[Core](core.md);
  [Prospect](prospect.md)/[Worlds](worlds.md) parameters indirectly (via the scenarios sampled).

**Schemas:** state/action spaces are the [Core](core.md) schemas; the `ErrorReport`,
`SurrogateManifest`, and `SamplingPolicy` are JSON-Schema + Pydantic v2 (conventions.md §3),
with a canonical Protobuf wire form for the manifest/error report so [Sim](sim.md)'s scheduler
can consume them across languages.

**Lifecycle:** datasets are **immutable, content-addressed, versioned**; a surrogate references
the exact dataset hashes it was trained and validated against. Models are SemVer-tagged and
never overwritten — a retrain produces a new version, and the prior remains reproducible.
Stale or drifted surrogates are **deprecated**, not deleted (the `ErrorReport` history is
audit-relevant). Spatial/temporal data carries explicit planetary CRS and SPICE-backed frames/
time (conventions.md §5) inherited from the source scenario.

**Provenance:** every artifact records input dataset hashes, source [Sim](sim.md) version and
solver config, code version, environment lockfile, seed, and hyperparameters (conventions.md §5,
§11) — sufficient to reproduce both the model *and* its error report exactly.

---

## 6. Integration architecture

Surrogate sits inside the simulation layer and connects through [Core](core.md) contracts
(conventions.md §1 narrow waist):

- **[Sim](sim.md) — bidirectional, the central relationship.** *Inbound:* Surrogate's `datagen`
  drives high-fidelity [Sim](sim.md) runs to generate labeled data. *Outbound:* a trained
  surrogate is loaded back into [Sim](sim.md) as a **low-cost fidelity tier** behind the
  [Core](core.md) physics-step contract. Crucially, the surrogate's **`ErrorReport` is consumed
  by Sim's multi-fidelity scheduler** (conventions.md §8): the scheduler reads declared error
  bounds and trust regions to decide, per task and per accuracy tolerance, whether to dispatch
  to the surrogate or fall back to ground truth. The error contract is the integration seam —
  bounds must be *machine-consumable and calibrated*, not prose.
- **[Core](core.md).** Implements the physics-step sub-interface and extends the plugin
  manifest/registry; uses Core's units/frames/state schemas and version negotiation.
- **[Learn](learn.md) — heavy consumer.** Multi-agent RL training runs millions of rollouts;
  surrogates make swarm-scale training tractable. Learn requests rollouts at a fidelity tier and
  the surrogate serves them, with uncertainty available so Learn can detect when a policy is
  exploiting surrogate error (a known sim-to-real risk).
- **[Studio](studio.md).** Interactive design iteration uses surrogates for sub-second feedback
  on excavation/hauling trade studies, escalating to high-fidelity [Sim](sim.md) for committed
  candidates.
- **[Hub](hub.md).** Trained surrogates, their `ErrorReport`s, and training datasets are
  published, discovered, and reused as content-addressed artifacts; experiment runs link to
  [Bench](bench.md) results by hash (conventions.md §6).
- **[Cloud](cloud.md).** Large training jobs and datagen sweeps run on K8s + Ray/KubeRay
  (conventions.md §7).
- **[Bench](bench.md).** A "surrogate fidelity vs. speed vs. error" benchmark belongs in the
  scenario zoo; surrogate error budgets are a first-class benchmarked quantity.

**Protocols/flows:** in-process calls for the latency-critical in-sim inference path; **gRPC**
for the cloud training/serving service and **NATS/JetStream** for job lifecycle and drift events
(conventions.md §4). Datasets/models move as content-addressed objects.

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — workstation training (single GPU) and in-process serving inside a local
     [Sim](sim.md). This tier MUST always work: a researcher trains a small surrogate, sees its
     error report, and runs it in a scenario in one session.
  2. **Cloud** — KubeRay-driven distributed training and large datagen sweeps; Argo Workflows
     for the datagen→train→eval→export DAG; served surrogates as OCI artifacts.
  3. **Operations/ground** — surrogates ride along *inside* the digital-twin [Sim](sim.md)
     instance used by [Ops](ops.md); Surrogate itself runs no operational service.
- **Compute:** **GPU-bound for training** (NVIDIA, CUDA; MIG to share GPUs across smaller jobs
  via the GPU Operator). Datagen is **CPU/GPU-heavy on the [Sim](sim.md) side**, not the
  surrogate. **Inference is cheap** — by design, a served surrogate runs on CPU or a small GPU
  slice; that cheapness is the entire point. Memory scales with batch/particle count for GNN
  models; neural operators are comparatively light.
- **Containerization:** OCI images, pinned/reproducible builds, multi-arch where relevant
  (conventions.md §7).
- **Orchestration:** Kubernetes substrate; Ray for distributed training; Argo for batch DAGs.
- **Scaling:** training scales horizontally across GPUs (data/model parallel via Ray Train);
  datagen fans out across [Sim](sim.md) workers; inference scales trivially (stateless, cheap,
  replicate behind the consumer).

---

## 8. Performance & scalability

- **Targets.** The defining number is **speedup at bounded error**: a useful granular/excavation
  surrogate should deliver **10²–10⁴× wall-clock speedup** over the high-fidelity DEM/contact
  solver while holding a **declared, calibrated error bound** within the task tolerance. The
  enabling goal is interactive iteration in [Studio](studio.md) and tractable swarm-scale
  rollouts in [Learn](learn.md) (charter §8).
- **Bottlenecks.**
  - *Training data generation* is the dominant cost — high-fidelity granular runs are expensive,
    so producing enough labeled data is the gate. Mitigation: **active learning** (sample where
    surrogate residual uncertainty is highest, not uniformly), Sobol/Latin-hypercube design, and
    reuse of datasets across surrogates via [Hub](hub.md).
  - *Inference latency at swarm scale* — thousands of contact queries per tick. Mitigation:
    batched GPU inference, ONNX Runtime, and operator-fused kernels; neural operators amortize
    field-scale predictions in one shot.
  - *Long-horizon error accumulation* — autoregressive rollouts drift. Mitigation: noise
    injection / pushforward training, periodic reanchoring to high-fidelity checkpoints, and
    uncertainty growth that the scheduler can see and act on.
  - *Data scarcity in microgravity contact* — small-body regolith/microgravity
    contact has almost no real ground truth, so the data-generation bottleneck is sharper and the
    *honesty* of the bound matters more than its tightness. Mitigation: **conservative trust
    regions and wider calibrated error bounds** (the [Sim](sim.md) scheduler is expected to fall
    back to ground truth more often here than for lunar terramechanics), aggressive **active
    resampling**, and lower drift/OOD thresholds that re-validate sooner — see §11.
- **Scaling strategy** (conventions.md §8): multi-fidelity everywhere — the surrogate *is* the
  cheap dial; horizontal scale-out for training (Ray/K8s) and datagen ([Sim](sim.md) fan-out);
  cloud-native chunked data (Zarr/Parquet) so workers stream only the slices they need.
- **Measure before optimizing:** Surrogate ships reproducible speed/error benchmarks
  (conventions.md §8, §11); every published surrogate's `ErrorReport` is itself the performance
  claim, and it is reproducible.

---

## 9. Security, safety & compliance

- **AuthN/Z & supply chain:** standard stack — OIDC, RBAC via OPA for who may publish surrogates;
  artifacts signed with Sigstore/cosign, SLSA provenance, SBOM (conventions.md §9). A surrogate
  manifest is signed and verified before [Sim](sim.md) loads it (mirrors [Core](core.md)'s
  manifest-signing rule).
- **Isolation:** untrusted third-party surrogates from [Hub](hub.md) run **out-of-process**
  (gRPC + sandboxed container, seccomp/gVisor; WASM forward-looking) per conventions.md §7, §9 —
  a downloaded model is untrusted code/weights until validated. First-party in-process loading is
  reserved for signed, registry-resolved artifacts.
- **Safety — the trust contract.** Surrogate is *not* a safety-critical runtime path
  ([Guard](guard.md) and high-fidelity [Sim](sim.md) hold that role), but it carries a real
  **epistemic-safety** obligation: a surrogate that under-reports its error can silently corrupt
  a design or training result and break the sim-to-real credibility the whole platform depends on
  (charter §8, §11). Mitigations are structural: calibrated, validated uncertainty; enforced
  trust regions with OOD flagging; the validation gate before promotion; and drift monitoring
  that retires stale models. **Safety-relevant decisions never trust a surrogate alone** — they
  escalate to ground truth.
- **Export control / dual use:** Surrogate is squarely in the open scientific/simulation commons
  (charter §9.5, conventions.md §12) — fast physics emulation is low-sensitivity. It carries no
  operational targeting capability and inherits the default-open posture; capability tags from
  [Core](core.md) gate any edge cases at the registry.

---

## 10. Observability & operability

- **Telemetry:** OpenTelemetry traces/metrics/logs across training jobs, datagen sweeps, and the
  serving path; Prometheus + Grafana dashboards; structured JSON logs via Loki (conventions.md §10).
- **Surrogate-specific metrics:** live **OOD/drift scores**, prediction-uncertainty
  distributions, periodic **error-vs-ground-truth** measurements, calibration/coverage, and
  long-horizon rollout error — surfaced as Prometheus series and stored for trend analysis.
  Drift events publish to NATS so re-validation can be triggered automatically.
- **Experiment tracking:** MLflow (W&B optional), runs linked to [Hub](hub.md) artifacts and
  [Bench](bench.md) results by content hash (conventions.md §6).
- **Testing & validation strategy** (conventions.md §11):
  - **Validation against the oracle** — every surrogate is regression-tested against held-out
    high-fidelity [Sim](sim.md) data with an explicit **error budget**; CI fails if the budget is
    exceeded or calibration degrades. This is the analog of conventions.md §11's physics-
    validation rule, with [Sim](sim.md) as the oracle.
  - **Calibration tests** — coverage/reliability checks (e.g., do 90% intervals contain truth
    ~90% of the time) gate promotion; an over-confident surrogate fails.
  - **Determinism & golden tests** — seeded training/inference compared to stored references;
    CI fails on non-reproducibility.
  - **Contract tests** — proves the surrogate honors the [Core](core.md) physics-step interface
    versions it claims (consumer-driven contract tests).
  - **Property-based tests** (Hypothesis) for physical invariants (mass conservation, frame/unit
    equivariance) the surrogate must respect.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Surrogate family — granular/excavation contact** | GNN particle simulator (learned DEM); neural operator (FNO/DeepONet); GP emulator; hybrid physics-informed NN | **GNN particle simulator** (e.g., GNS/MeshGraphNet-style) — best fit for particle/contact dynamics and graph-structured granular media; physics-informed losses added |
| **Surrogate family — microgravity contact / anchoring** | GNN particle simulator (low-g cohesive DEM); GP emulator; hybrid physics-informed NN | **GNN particle simulator with conservative uncertainty** — same family as excavation contact but tuned for low-g cohesion/anchoring; given the scarce ground truth, **calibrated bounds and trust-region width are weighted over point accuracy**, with the validation gate held strict |
| **Surrogate family — fields (thermal, continuum)** | Neural operator (FNO/DeepONet); CNN/U-Net; GP | **Neural operator (FNO)** — resolution-independent, fast field-to-field maps |
| **Surrogate family — low-dim emulation (scalar I/O, screening)** | GP; small MLP ensemble; polynomial chaos | **Gaussian process** — native calibrated uncertainty, data-efficient for low-dim |
| **Uncertainty / error-bound method** | Deep ensembles; conformal prediction; GP residual model; Bayesian NN | **Deep ensembles + conformal calibration** as default (scalable, well-calibrated, distribution-free coverage); **GP** where it is the model. Bayesian NN deferred |
| **Training framework** | PyTorch; JAX; both | **PyTorch primary, JAX where differentiable/massively-parallel rollouts win** — recorded per model (conventions.md §6) |
| **Served artifact** | ONNX; framework checkpoint; TorchScript | **ONNX** (conventions.md §6); native-graph fallback flagged in manifest when ops are inexpressible |
| **Retraining mode** | Offline-only; online/continual | **Offline retrain + gated promotion**; continual *data collection* allowed, but weights enter Sim only through the validation gate (principle 7) |
| **Re-validation trigger** | Fixed schedule; drift-triggered; hybrid | **Hybrid** — periodic schedule *plus* drift-/OOD-triggered re-validation and active resampling |
| **How error bounds reach Sim's scheduler** | Static manifest bound; live per-query uncertainty; both | **Both** — static `ErrorReport` (trust region + budget) for admission, plus live per-query uncertainty for in-loop fallback decisions |

**Open questions / research dependencies:**

- **Trustworthy, calibrated error bounds for autoregressive contact rollouts** is an open
  research problem (charter §7, §8). Conformal methods give marginal coverage; *conditional*,
  long-horizon coverage that the scheduler can rely on is unresolved — co-developed with
  [Sim](sim.md) and [Bench](bench.md).
- **The error-contract API with [Sim](sim.md)'s scheduler:** exact shape of the bound the
  scheduler consumes (single scalar tolerance? per-channel? distributional?) — co-designed with
  [Sim](sim.md).
- **Sim-to-real layering:** a surrogate approximates the high-fidelity *solver*, which itself has
  a sim-to-real gap (charter §7). How surrogate error composes with solver error in an honest
  end-to-end uncertainty budget is a research thread shared with [Worlds](worlds.md)/[Prospect](prospect.md).
- **Active-learning acquisition** for granular physics: which sampling policy most cheaply shrinks
  the trust region — co-developed against [Sim](sim.md) datagen cost.
- **Calibration with almost no ground truth:** for microgravity contact/anchoring there
  is little real-world data to anchor against, so honest calibration must lean on physics-informed
  priors and conservative, possibly worst-case bounds. How to certify a surrogate as "trustworthy
  enough to substitute" when the oracle itself is sparsely validated is an open thread shared with
  [Worlds](worlds.md)/[Sim](sim.md).

---

## 12. Roadmap alignment

- **Phase 1** (autonomy & studio) is where Surrogate ships, enabling the swarm-scale training
  ([Learn](learn.md)) and interactive design ([Studio](studio.md)) that define this phase.
- **Phase-0 dependency:** Surrogate consumes the [Core](core.md) physics-step interface, the
  manifest/registry, and a working high-fidelity [Sim](sim.md) — all Phase-0 deliverables — so it
  builds *after* the minimum runnable loop exists.
- **MVP (Phase 1):** one **granular/excavation surrogate** for the anchor lunar-polar-prospecting
  scenario, a **GNN particle simulator** with **deep-ensemble + conformal** error bounds, an
  ONNX-served fidelity tier loaded by [Sim](sim.md), an `ErrorReport` its scheduler consumes, and
  offline retraining with scheduled+drift-triggered re-validation. The deliverable that proves
  the package: *demonstrated speedup at a published, calibrated error bound* on a [Bench](bench.md)
  scenario.
- **Later (Phase 1→2):** neural-operator field surrogates (thermal), GP emulators for screening,
  the active-learning datagen loop, online drift monitoring in the [Ops](ops.md) digital-twin,
  and a [Hub](hub.md)-driven community catalog of surrogates with comparable error reports — the
  "beat-the-leaderboard" flywheel applied to physics fidelity itself.
- **Phase 3 (multi-regime missions, [multi-regime missions](mission-model.md)):**
  microgravity contact / anchoring surrogates for small-body work land with the broader multi-regime
  extension. No Core hooks are needed beyond those reserved in Phase 1 (the surrogate reuses the
  unchanged [Sim](sim.md) `ErrorReport`/fidelity-tier contract); only the new physics domain and its
  datagen are added (see [mission-model](mission-model.md)).
