# Astro-Mine-Sim — Technology Architecture

> Layer: **Multi-physics simulation** · Phase: **0** · Ships in: [`astro-mine-platform`](platform.md) · Extended for multi-regime missions (Phase 3)
> The beating heart — the execution substrate every other component runs against.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Sim` is the **multi-physics engine and scenario runtime**. It couples the physical
regimes a planetary swarm spans — orbital propagation, terramechanics (wheel/soil and rigid
contact), manipulation and granular excavation, power/thermal evolution, and sensor simulation —
behind one stable contract, and drives them through a **multi-fidelity scheduler** that trades
accuracy for speed *per task*. It is the single piece every other package ultimately exercises:
high fidelity for validation, mid fidelity for interactive design, low fidelity (or surrogates)
for swarm-scale training. The same engine also runs as a **digital-twin shadow** alongside
[Ops](ops.md), predicting outcomes and vetting each replan before it is committed (charter §5).

Sim does, and only does:

- **implement the [Core](core.md) Environment API** — `reset()/step(action) -> observation,
  reward?, info` over multi-agent, partial-observability, variable-timestep, comms-masked worlds;
- **orchestrate physics** across regimes by routing each to a fidelity-appropriate engine and
  exchanging state at coupling boundaries;
- **schedule fidelity** — pick, per task and per region, the cheapest engine/surrogate that meets
  a stated error budget, and track that error;
- **simulate sensors** — produce the observations agents actually receive (range, imaging, IMU,
  spectrometer, contact, comms link state);
- **execute deterministically** — seeded, reproducible rollouts in both **headless/batch** and
  **interactive** modes, recording everything to **MCAP**.

**Explicitly out of scope.** Sim is *not* a physics-engine monoculture and does not reimplement
solvers — it integrates and couples mature engines. It defines no asset format (that is SADF in
[Core](core.md)/[Fleet](fleet.md)), no world or resource model ([Worlds](worlds.md),
[Prospect](prospect.md), [Link](link.md)), no policy or planner ([Mind](mind.md),
[Learn](learn.md), [Allocate](allocate.md), [Guard](guard.md)), no scoring ([Bench](bench.md)),
no UI ([View](view.md), [Studio](studio.md)), and no cluster orchestration ([Cloud](cloud.md)) —
it is the *library* those services deploy. Surrogate *models* live in
[Surrogate](surrogate.md); Sim only consumes them as a fidelity tier.

**Multi-regime & multi-phase.** [multi-regime missions](mission-model.md)
generalizes a single-world campaign into a [Mission](mission-model.md) of phases across regimes
(`launch_ascent · interplanetary_transit · proximity_orbit · surface · ascent_return ·
earth_interface`). Sim extends to be that mission's execution substrate in three additive ways:
a **microgravity contact/anchoring/proximity-ops** physics domain (distinct from surface-gravity
terramechanics), **multi-regime propagation** that couples free-space, body-proximity, and
surface dynamics, and a thin **multi-phase sequencer** in the runtime. Per
[mission-model.md](mission-model.md), the sequencer is *mechanism* only — the
*policy* (phase ordering, contingencies) stays in [Studio](studio.md)/[Ops](ops.md), and
[Core](core.md) owns only the schema. Sim still **validates and propagates** trajectories from
[Trajectory](trajectory.md); it never *optimizes* them. All of this lands in Phase 3 (see §12).

**Primary users:** everyone — Sim is the execution substrate. Directly: autonomy and RL
researchers (training/eval), mission designers (trade studies via [Studio](studio.md)),
operators (digital twin via [Ops](ops.md)), and benchmark authors ([Bench](bench.md)).

**Charter alignment:** §5.3 ("the beating heart"), §7 (simulation/physics & astrodynamics
stack), §9 (fidelity–speed frontier; granular physics at interactive speed; a durable abstraction
across orbital/surface/manipulation/ISRU without an engine monoculture), §11 Phase 0.

---

## 2. Architecture principles

1. **Engine-pluralist, contract-singular.** There is one public surface — the [Core](core.md)
   Environment API — and *many* engines behind it. Sim routes each physical regime to a
   specialist (Drake for contact-rich manipulation, MuJoCo/Brax for fast contact, Basilisk/Orekit
   for orbital, Isaac for GPU-scale surface) rather than forcing one engine to do everything. No
   engine ever leaks through the waist.
2. **Fidelity is a dial, not a fork.** Every regime exposes a fidelity ladder (analytic →
   reduced-order → full-physics → surrogate). The *same* scenario runs at any rung; choosing a
   rung never changes the API, only the cost/accuracy point.
3. **Error budgets travel with results.** A lower-fidelity result is only admissible against a
   stated tolerance. Sim tracks per-tier error against the high-fidelity reference and refuses
   silent accuracy loss — "a single guess" is an anti-pattern (conventions.md §1, §8).
4. **Determinism is a hard requirement, not a hope.** Same inputs + same seed + same pinned engine
   versions ⇒ bit-reproducible (or tolerance-reproducible, documented per engine) results.
   Determinism gates fail CI (conventions.md §5, §11). This is what makes [Bench](bench.md) and
   the digital twin trustworthy.
5. **Library first, service second.** Sim runs in one Python process on a workstation before it is
   a Ray actor on a cluster. The local tier MUST always work (conventions.md §4, §7).
6. **Headless and interactive are one runtime.** Batch rollouts and a live-rendered design loop
   are the same stepping core with different output sinks — never two divergent codepaths.
7. **Stream, don't accumulate.** Outputs are bounded, back-pressured MCAP channels; a 200-robot,
   14-day rollout must not require holding the full trajectory in memory (conventions.md §8).
8. **Couple explicitly, in declared frames and SI units.** Cross-regime state exchange (orbital ↔
   surface ↔ contact) happens at named coupling boundaries with explicit SPICE-backed frames and
   units; no implicit conversions (conventions.md §5, [Core](core.md) §2).
9. **Validate against oracles, always.** Every engine integration carries a regression suite
   against an external oracle (STK/GMAT/Basilisk for orbits; analytic + lab data for
   terramechanics) with an explicit error budget (conventions.md §11).

---

## 3. Application architecture

Sim is a **library with an optional gRPC service skin**. The core is a deterministic stepping
loop over a graph of regime engines, fed by world/asset/comms providers and emitting MCAP.

```
astro_mine.sim
├── runtime/         # the stepping core: scenario loader, clock, RNG/seed manager, episode loop
│   ├── scenario     #   scenario spec → resolved world + assets + agents + termination
│   ├── clock        #   multi-rate time: SPICE epochs (TDB/ET), variable & sub-stepped dt
│   ├── episode      #   reset/step driver implementing the Core Environment API
│   └── sequencer    #   multi-phase runtime: runs phases in order, evaluates
│                    #     entry/exit conditions, performs the PhaseTransition handoff (mechanism only)
├── engines/         # physics-engine adapters (plugins), one per backend
│   ├── orbital/     #   Basilisk / Orekit adapters; SPICE ephemerides & frames
│   ├── contact/     #   MuJoCo, Brax adapters (fast/differentiable rigid contact)
│   ├── manip/       #   Drake adapter (contact-rich manipulation, grasp/excavator linkages)
│   ├── granular/    #   DEM / MPM granular-excavation backend + Surrogate tier hook
│   ├── microg/      #   microgravity contact/anchoring/proximity-ops: cohesion-
│   │                #     dominated low-g DEM contact (Project Chrono) — distinct from terramechanics
│   ├── surface/     #   Isaac Sim / Omniverse + Gazebo adapters (GPU-scale terrain mobility)
│   └── powertherm/  #   power & thermal ODE/network solver (battery, radiator, RTG, eclipse)
├── coupling/        # multi-domain coupler: state exchange, time sync, frame/unit bridging
├── scheduler/       # multi-fidelity scheduler: tier selection + error-budget tracking
├── sensors/         # sensor models: imaging, range/LIDAR, IMU/odometry, spectrometer, contact
├── comms/           # consumes Link models → per-tick observation/comms masks
├── record/          # MCAP writer/reader, channel/schema registration, provenance stamping
├── service/         # gRPC EnvironmentService + Ray-actor wrapper (the "service skin")
└── validate/        # oracle harnesses, golden/determinism gates, error-budget reports
```

### Key abstractions exposed

- **`Environment`** — the [Core](core.md) Environment API implementation. The *only* contract
  most consumers see; also surfaced as a [Gymnasium](https://gymnasium.farama.org) /
  PettingZoo view by [Learn](learn.md) (conventions.md §3).
- **`Scenario`** — a versioned, content-addressed spec binding a [Worlds](worlds.md) world, a
  [Prospect](prospect.md) resource field, a [Link](link.md) comms environment, [Fleet](fleet.md)
  assets (SADF), agents, initial conditions, fidelity policy, seed, and termination — the
  reproducibility unit [Bench](bench.md) pins.
- **`FidelityPolicy`** — declarative request: per-regime/region target error or wall-clock
  budget; the scheduler resolves it to concrete tiers.
- **`RegimeEngine`** (extension point) — adapter interface every backend implements: `advance(dt,
  state) -> state`, `export_coupling_state()`, `import_coupling_state()`, plus declared frames,
  determinism class, and a fidelity descriptor.

### Key abstractions consumed

- **SADF** assets and the message/units/frames vocabulary from [Core](core.md).
- **World, resource, and comms providers** from [Worlds](worlds.md) / [Prospect](prospect.md) /
  [Link](link.md) (Zarr/COG fields, geostatistical priors, link geometry).
- **Surrogate models** from [Surrogate](surrogate.md), loaded as a granular/contact fidelity tier
  via ONNX (conventions.md §6).

### Extension / plugin points

- **Physics engines** — new backends register a `RegimeEngine` plugin via the [Core](core.md)
  registry/manifest; routing them is configuration, never a Sim code change (conventions.md §1,
  §7). Untrusted/non-Python engines run **out-of-process** (gRPC, sandboxed container).
- **Sensor models** and **coupling schemes** are likewise registry-discovered plugins.
- **Fidelity tiers** (including learned surrogates) plug into the scheduler by declaring an error
  descriptor and a validation reference.

### Interaction patterns

In-process **library** for local/dev and embedding in [Learn](learn.md)/[Bench](bench.md). As a
**gRPC `EnvironmentService`** (server-streaming `step`) wrapped in a **Ray actor** for distributed
rollouts on [Cloud](cloud.md). As a **digital-twin shadow**: a long-lived instance fed live state
estimates from [Ops](ops.md), running ahead of reality to vet replans. Live frames stream to
[View](view.md); recordings stream to MCAP for [Bench](bench.md)/[View](view.md) replay.

**Multi-regime & multi-phase.** The same engine-pluralist routing absorbs the new
**microgravity contact** domain as just another `RegimeEngine` behind the waist (no new public
surface), and **multi-regime propagation** is the existing co-simulation coupler spanning the
[Transit](transit.md) free-space dynamics ↔ body-proximity ↔ surface boundaries via the
`PhaseTransition` state handoff. The `runtime/sequencer` is a thin scheduler over `episode`: it
drives the ordered phases of a [Mission](mission-model.md), evaluates each phase's entry/exit
conditions, and exchanges terminal→initial state at the boundary — purely *mechanism*. The
*policy* (which phases, in what order, with what contingencies) is authored in
[Studio](studio.md) and executed live by [Ops](ops.md); [Core](core.md) holds only the
`MissionSpec`/`PhaseTransition` schema ([mission-model.md](mission-model.md)).

---

## 4. Application programming & runtime platforms

- **Languages.** **Python 3.12+** for the runtime, scheduler, coupler, adapters, and service
  (the public surface is Python per conventions.md §2). **C++20** for hot inner loops and native
  engine integration (Drake, MuJoCo, Isaac, the DEM/MPM granular kernels) via pybind11. **CUDA**
  for GPU contact/granular kernels and parallel rollouts, behind device-agnostic interfaces.
- **Physics & robotics engines (charter §6).**
  - *Orbital:* **Basilisk** (spacecraft dynamics/GNC, flight-like) and **Orekit** (propagation,
    events, frames); **SPICE/NAIF** via the shared **`astro_mine.spice`** foundation ([Spice](spice.md); SpiceyPy under the hood) for ephemerides, frames, and time; **GMAT/STK**
    as external verification oracles only (conventions.md §11).
  - *Contact-rich manipulation:* **Drake** (rigorous multibody, grasp/excavator linkages,
    hydroelastic contact).
  - *Fast / differentiable contact:* **MuJoCo** (incl. MJX) and **Brax** (JAX, massively parallel,
    differentiable) for training-speed rigid contact and mobility.
  - *GPU-scale surface sim & rendering:* **NVIDIA Isaac Sim / Omniverse** (USD-native, sensor
    rendering, thousands of parallel envs) and **Gazebo** (ROS-native interop, lighter weight).
  - *Granular/excavation:* DEM/MPM backend (e.g. **Project Chrono** / Taichi-MPM class methods)
    for ground truth, accelerated by [Surrogate](surrogate.md) at interactive speed.
- **Frameworks/libraries.** **JAX** (Brax, differentiable/parallel rollouts) and **PyTorch**
  (surrogate inference); **NumPy/SciPy**; **Gymnasium/PettingZoo** env views; **Pydantic v2** +
  **JSON Schema** for scenario/fidelity specs; **gRPC** + Protobuf (control), **FlatBuffers/Cap'n
  Proto** for per-tick sensor/telemetry payloads (conventions.md §3); **Ray** for distribution
  (conventions.md §6, §7); **mcap** + **foxglove** schemas for recordings.
- **Runtime model.** A deterministic episode loop: `reset` resolves the scenario and seeds all
  RNGs; each `step` advances every active regime engine over its sub-rate, runs the coupler at
  boundaries, samples sensors, applies comms masks, accumulates info, and emits MCAP. Multi-rate
  by design (orbital minutes; mobility milliseconds; granular sub-millisecond). Headless and
  interactive share this loop; only output sinks differ.
- **Build/packaging.** Ships in the [`astro-mine-platform`](platform.md) wheel; native engines
  vendored as pinned C++/CUDA extensions or pulled as containerized out-of-process backends, behind
  `sim-*` extras so the local tier stays installable without them (conventions.md §7.1). **OCI
  images** per deployment tier (CPU base; CUDA base; Isaac/Omniverse base) with pinned engine
  versions for reproducible builds.

---

## 5. Data architecture

**Owned / produced.**

- **Scenario specs** — YAML/JSON validated by JSON Schema + Pydantic v2; content-addressed and
  versioned; the canonical reproducibility unit (conventions.md §3, §5).
- **Recordings/trajectories** — **MCAP** containers carrying heterogeneous, timestamped,
  schema-tagged channels (state, actions, sensor frames, comms state, power/thermal, events). The
  one output format for replays, the digital-twin trace, and [Bench](bench.md) scoring
  (conventions.md §4, §5).
- **Provenance manifest** — every recording stamps input content hashes (scenario, world,
  resource field, assets, surrogate models), engine versions and tiers used, the environment
  lockfile, the seed, and per-tier error-budget outcomes (conventions.md §5).
- **Error-budget reports** — Parquet tables of surrogate/low-fidelity deviation vs. the
  high-fidelity reference, consumed by the scheduler and surfaced to [Bench](bench.md).

**Consumed.**

- **Worlds/terrain** — DEMs/rasters as **COG** (via GDAL/PROJ), physical fields as **Zarr**
  (range-read only the chunks a region needs), from [Worlds](worlds.md) (conventions.md §5).
- **Resource fields** — geostatistical distributions with explicit uncertainty (Zarr) from
  [Prospect](prospect.md) — Sim renders sensor observations *of* these fields, never a point guess.
- **Comms environment** — link geometry/latency/bandwidth/windows from [Link](link.md), turned
  into per-tick observation and comms masks.
- **Assets** — SADF documents + USD/glTF geometry from [Fleet](fleet.md)/[Core](core.md).
- **Surrogate models** — **ONNX** artifacts from [Surrogate](surrogate.md) (conventions.md §6).

**Multi-regime & multi-phase.** A `Scenario` is the per-phase reproducibility unit; a
multi-phase [Mission](mission-model.md) is run as an ordered set of phase scenarios joined by
`PhaseTransition` handoffs, each recording carrying its phase's `regime` and the terminal→initial
state. Sim **consumes** descriptive `TrajectoryRef`/`ManeuverBudget` artifacts from
[Trajectory](trajectory.md) as inputs to *validate and propagate* — never as executable guidance
— and consumes microgravity-contact surrogates from [Surrogate](surrogate.md) as an additional
fidelity tier with its own error budget.

**Storage & lifecycle.** Specs and recordings are **content-addressed** in an S3-compatible
object store (MinIO self-host; S3/GCS in cloud); relational scenario/run metadata in
**PostgreSQL** (+ PostGIS); ephemeral run state and the digital-twin live buffer in **Redis**
(conventions.md §5, §7). Interactive frames are transient; batch recordings are retained and
content-addressed for exact replay. **CRS/frames/time** are SPICE-backed (TDB/ET, body-fixed and
inertial); all spatial data carries an explicit planetary CRS — no Earth/WGS84 defaults
(conventions.md §5). Schemas are versioned with the package that owns them.

---

## 6. Integration architecture

Sim is the hub of the design/training loop and the shadow of the operations loop (charter §5).

- **Implements** the [Core](core.md) **Environment API** — the single contract through which it is
  consumed; all message/sensor schemas derive from Core's catalog (conventions.md §3).
- **Consumes** worlds from [Worlds](worlds.md), resource ground-truth from [Prospect](prospect.md),
  comms models from [Link](link.md), and SADF assets from [Fleet](fleet.md).
- **Validates trajectories from** [Trajectory](trajectory.md): Sim *propagates and
  checks* the descriptive `TrajectoryRef`/`ManeuverBudget` arcs Trajectory designs — feasibility,
  margins, regime coupling — and **never optimizes** them; for the free-space legs it runs against
  the [Transit](transit.md) environment.
- **Fidelity-accelerated by** [Surrogate](surrogate.md): learned surrogates (ONNX) slot in as
  granular/contact fidelity tiers under the scheduler, with error tracked against the
  high-fidelity engine.
- **Wrapped as RL environments by** [Learn](learn.md) via Gymnasium/PettingZoo adapters over the
  Environment API.
- **Executes policies/planners from** [Mind](mind.md), [Allocate](allocate.md), and
  [Guard](guard.md): they implement the Core Policy/Planner API and drive `step` actions; Guard's
  shield wraps actions before they enter the physics.
- **No runtime lateral dependency on [Bench](bench.md).** `astro_mine.sim.bench` used to import
  Bench's metric and harness types (`EpisodeTrace`, `ScoringContext`, `RunOutcome`,
  `BeliefSnapshot`, `ScoringRefused`) so Sim could satisfy Bench's runner contract — a runtime
  lateral edge, and the one `conventions.md` §3.2 rule 3 named as its example of an arrow pointing
  up the layer table. The design was never in doubt: **Bench runs Sim** through the `EpisodeRunner`
  seam and deliberately never imports Sim. The import went the other way only because the scoring
  vocabulary lived in Bench rather than at the waist. It now lives in `astro_mine.core.scoring`, and
  the arrow points the way the design always described.

  One import was not a move. `SimHarnessRunner` also called Bench's `resolve_metrics`/`score`,
  because a `RunOutcome` carries metric values — so it takes an injected Core `EpisodeScorer`, and
  Bench passes its own when it constructs the runner. That is the mirror image of the content
  `store` Bench hands Sim: each side is given what the other owns rather than importing it. Sim
  still names Bench's *scenario* types under `TYPE_CHECKING`, which §3.2 rule 4 permits and the
  layering suite reports rather than fails.
- **Scored by** [Bench](bench.md): Sim runs pinned scenarios deterministically; Bench ingests the
  MCAP recording + provenance and computes metrics.
- **Streamed to** [View](view.md): live frames over gRPC server-streaming during interactive runs;
  recorded MCAP for replay/explanation.
- **Runs in shadow for** [Ops](ops.md): a long-lived twin instance ingests live state estimates
  (ROS 2/DDS via [Bridge](bridge.md), bridged into the control plane) and runs ahead to vet
  replans before commit.
- **Scaled on** [Cloud](cloud.md): the gRPC service is wrapped as Ray actors; sweeps fan out via
  KubeRay; DAG sweeps via Argo Workflows (conventions.md §7).

**Message flows.** Control plane: **gRPC** `EnvironmentService` (server-streaming `step`,
Protobuf). Per-tick sensor/telemetry payloads: **FlatBuffers/Cap'n Proto** to avoid decode
overhead at swarm scale (conventions.md §3, [Core](core.md) §8). Job lifecycle / sweep events:
**NATS + JetStream** (conventions.md §4). Recorded streams: **MCAP**. Ops data plane (twin
ingest): **ROS 2/DDS** at the [Bridge](bridge.md) boundary.

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — one workstation, single Python env or `docker compose`; CPU-only fallback for
     all regimes (Brax/MuJoCo CPU, Basilisk/Orekit, reduced-order granular) so a researcher can
     clone, run a scenario, and score a baseline in an afternoon. *This tier MUST always work.*
  2. **Cloud** — K8s + **Ray** (KubeRay) for parallel rollouts/sweeps; **NVIDIA GPU Operator**
     (MIG for sharing) for Isaac/Brax/CUDA-granular workers; **Argo Workflows** for sweep DAGs.
  3. **Operations/ground** — the digital-twin shadow co-located near operators with [Ops](ops.md)
     /[View](view.md); fed via [Bridge](bridge.md) over ROS 2/DDS.
- **Compute profile.**
  - *CPU:* orbital propagation, power/thermal ODEs, Drake manipulation, reduced-order tiers,
    coupling/scheduling — comfortable on commodity multicore.
  - *GPU:* Isaac surface sim + sensor rendering, Brax/MJX parallel rollouts, DEM/MPM granular and
    surrogate inference. Surface/sensor rendering is memory-bound (8–24 GB+/scene); large parallel
    training packs many envs per GPU via MIG/Brax batching.
  - *Memory:* dominated by terrain tiles (stream from Zarr/COG, don't preload) and parallel env
    batches; the streaming/back-pressure design keeps long-horizon rollouts bounded.
- **Containerization.** Multi-arch OCI images, pinned bases; separate CUDA / Isaac-Omniverse /
  CPU image variants. Out-of-process engines run as sidecar containers (gRPC), sandboxed
  (conventions.md §7, §9).
- **Orchestration & scaling.** Stateless Sim service replicas behind Ray; state in
  Postgres/Redis/object store. Scale **horizontally** for throughput (more rollout actors) and
  **vertically/MIG** for per-episode GPU fidelity. Back-pressure on streaming sinks; graceful
  degradation by dropping to cheaper tiers under load.

---

## 8. Performance & scalability

- **Targets (Phase-0 indicative).** Mid-fidelity rover-mobility episode at **≥ real-time** on a
  workstation; **thousands of low-fidelity parallel rollouts** per GPU-hour for training (Brax/MJX
  batching); high-fidelity granular excavation accelerated to **interactive (~≥10× speed-up)** by
  [Surrogate](surrogate.md); a **200-robot / 14-day** campaign completes headless within a sweep
  budget via aggressive tier selection. All targets are reproducible benchmarks (conventions.md
  §8).
- **Bottlenecks.** (1) **Granular/excavation physics** — the charter's single hardest piece (§9);
  DEM/MPM is expensive and fast approximations are unreliable. (2) **GPU memory** for surface
  rendering and large env batches. (3) **Cross-regime coupling** — synchronizing multi-rate
  domains without stalling the fastest one. (4) **MCAP write throughput** at swarm scale.
- **Mitigations.** Multi-fidelity scheduling with **bounded-error surrogates** for granular
  contact (the central architectural answer to the fidelity–speed frontier, charter §8); **Brax/
  MJX** GPU batching for massively parallel training; **multi-rate sub-stepping** so orbital
  regimes are not stepped at mobility rates; chunked **Zarr/COG** range reads so workers stream
  only needed slices; bounded, back-pressured, async MCAP writers (conventions.md §8).
- **Scaling strategy.** Horizontal fan-out of stateless rollout actors via **Ray/KubeRay** on
  [Cloud](cloud.md); GPU sharing via **MIG**; the scheduler degrades fidelity rather than
  collapsing under load. Performance claims ship as reproducible benchmarks per conventions.md §8.

---

## 9. Security, safety & compliance

- **AuthN/Z.** The Sim service authenticates via **OIDC** and authorizes via **RBAC + OPA**;
  service-to-service is **mTLS** (conventions.md §9). Scenario submission and result ingestion are
  policy-gated.
- **Plugin/engine isolation.** This is Sim's sharpest security surface: engines and scenarios are
  *executable* content. Untrusted or non-Python engines run **out-of-process** in containers with
  **seccomp/gVisor**; **WASM (wasmtime)** is the forward-looking sandbox for untrusted compute.
  Sim never executes an unsigned plugin — manifests are verified (Sigstore/cosign) at load
  (conventions.md §7, §9; [Core](core.md) §9).
- **Supply chain.** Signed OCI images and wheels (**cosign**), **SLSA** provenance, **SBOM**
  (Syft/CycloneDX); pinned engine versions; org defaults (Dependabot, secret scanning, push
  protection) on (conventions.md §9).
- **Safety (digital-twin role).** As [Ops](ops.md)' shadow, Sim *predicts* — it is **advisory, not
  authoritative**: it never commands hardware directly (that is [Bridge](bridge.md)), and its
  predictions are vetted by [Guard](guard.md)'s independent shield before any commit. The twin's
  fidelity tier and tracked error are surfaced so operators see prediction confidence. Determinism
  + provenance make every twin prediction auditable and replayable.
- **Export control / dual use.** The science/simulation commons is **default-open**
  (conventions.md §12, charter §9.5). Sensitive coupling — e.g. high-fidelity, certification-grade
  flight-targeting dynamics — is gated via [Core](core.md) capability tags + OPA at load time and,
  where genuinely sensitive, partitioned into access-controlled repos. Sim itself is scientific
  simulation; the EAR/ITAR-sensitive boundary lives at [Bridge](bridge.md)/[Ops](ops.md).

---

## 10. Observability & operability

- **Telemetry.** **OpenTelemetry** in the service → traces/metrics/logs; structured JSON logs to
  **Loki**; metrics to **Prometheus** + **Grafana** (conventions.md §10). Distributed traces span
  the design loop (a [Learn](learn.md) rollout) and the ops loop (an [Ops](ops.md) replan traced
  through the twin, [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md)).
- **Sim-specific signals.** Per-tier fidelity selections, error-budget headroom, surrogate
  deviation vs. ground truth, coupling residuals, step wall-clock vs. sim-time (real-time factor),
  and determinism-hash per episode.
- **Testing & validation strategy** (conventions.md §11):
  - **Unit/integration:** `pytest`; **Hypothesis** property tests for coupling invariants
    (energy/momentum continuity, frame round-trips) and schema validity; `gtest` for C++ kernels.
  - **Physics validation:** regression of orbital propagation against **STK/GMAT/Basilisk**;
    terramechanics against analytic cases and lab/terrestrial-analog data — each with an explicit
    error budget. This is the credibility backbone for the sim-to-real chasm (charter §8).
  - **Determinism gates:** seeded golden runs hash-compared (or tolerance-compared, per engine
    determinism class) to stored references; **CI fails on non-reproducibility**.
  - **Contract tests:** consumer-driven tests prove Sim honors the [Core](core.md) Environment API
    versions it claims.
  - **Surrogate-error gates:** a tier is admissible only while its tracked deviation stays inside
    the requested budget; drift trips re-validation against the high-fidelity engine.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Physics-engine strategy** | (a) Single engine (e.g. Isaac for everything); (b) **Pluggable multi-engine** routing regimes to specialists behind the Core Environment API | **(b) Pluggable multi-engine.** No single engine is validation-grade across orbital + contact + granular + GPU-scale; routing Drake (manip), MuJoCo/Brax (fast contact), Basilisk/Orekit (orbital), Isaac (surface) behind the waist avoids a monoculture (charter §8) and is the principled answer to "durable abstraction across regimes." |
| **Multi-domain coupling** | Monolithic single-state engine; explicit operator-splitting/co-simulation coupler with frame/unit bridging; functional-mockup (FMI) style | **Explicit co-sim coupler** with named coupling boundaries, multi-rate sub-stepping, SPICE-frame/SI bridging, and tracked coupling residuals — the only scheme that spans heterogeneous engines. |
| **Multi-fidelity scheduling** | Manual per-scenario fidelity choice; rule/heuristic tier selection; **error-budget-driven scheduler** (auto-select cheapest tier meeting tolerance) | **Error-budget-driven scheduler** with per-tier tracked deviation vs. high-fidelity reference (conventions.md §8). Start rule-based in Phase 0; evolve toward learned tier selection. |
| **Granular/excavation backend** | DEM only (accurate, slow); MPM; **DEM/MPM ground truth + learned surrogate tier** | **Ground-truth DEM/MPM + [Surrogate](surrogate.md) tier** with bounded-error gating — interactive speed with quantified fidelity (charter §8). |
| **Microgravity contact/anchoring** | Reuse the terramechanics/contact engines; **a distinct low-g cohesion-dominated DEM domain** routed separately | **Distinct routed domain** (cohesion-dominated, low-g contact via **Project Chrono**-class DEM) behind the same pluggable multi-engine waist, with a [Surrogate](surrogate.md) tier — surface-gravity terramechanics does not transfer to proximity-ops/anchoring. Phase 3. |
| **GPU vs CPU rollouts** | CPU-only; GPU-only; **hybrid (CPU specialist regimes + GPU for parallel/contact/render)** | **Hybrid.** CPU for orbital/power-thermal/Drake and the always-works local tier; GPU (Brax/MJX/Isaac/CUDA-granular) for parallel training and rendering. |
| **Fast-contact training engine** | MuJoCo (MJX); Brax; both | **Both, MuJoCo/MJX default, Brax for differentiable/JAX-native** massively parallel rollouts (conventions.md §6). |
| **Orbital backend** | Orekit; Basilisk; SPICE-only propagation | **Basilisk + Orekit** (flight-like dynamics + propagation/events), **SPICE** for frames/time, **GMAT/STK** as oracles only (conventions.md §11). |
| **Determinism across engines** | Best-effort; per-engine determinism class + tolerance gates; strict bit-exactness everywhere | **Per-engine determinism class + tolerance gates.** Bit-exact where feasible (Basilisk, fixed-seed MuJoCo); documented tolerance bounds where GPU non-associativity prevents it — gated in CI. |
| **Per-tick payload encoding** | Protobuf; FlatBuffers; Cap'n Proto | **FlatBuffers/Cap'n Proto** for per-tick sensor/telemetry; Protobuf for control-plane RPCs (conventions.md §3). |
| **Recording format** | MCAP; ROS bag; HDF5 | **MCAP** — heterogeneous, schema-tagged, timestamped (conventions.md §4). |

**Open questions / research dependencies:**

- **Trustworthy surrogate-error bounds.** What guarantees make a learned granular tier admissible
  for *validation*, not just training? Co-designed with [Surrogate](surrogate.md) and
  [Bench](bench.md) (charter §8).
- **Coupling stability** across stiff multi-rate boundaries (orbital ↔ contact ↔ granular) without
  energy drift — the co-simulation numerics problem.
- **Determinism vs. GPU performance** — how much reproducibility must be sacrificed for Brax/Isaac
  throughput, and where the tolerance line sits for [Bench](bench.md).
- **Sim-to-real terramechanics** — calibrating low-gravity granular models against the scarce
  available data and terrestrial analogs (charter §7, §7); a Phase-2 validation dependency.
- **Environment API shape** for variable-fidelity + comms-masked observation — co-designed with
  [Core](core.md) and [Learn](learn.md) ([Core](core.md) §11).

---

## 12. Roadmap alignment

- **Phase 0 (commons seed).** Ship a runnable Sim that implements the [Core](core.md) Environment
  API for the **anchor scenario — lunar polar water-ice prospecting** — with: the deterministic
  stepping core; the multi-engine adapter framework with an **initial set of engines** (orbital via
  Basilisk/Orekit + SPICE; mobility/contact via MuJoCo/Brax; manipulation via Drake; a
  reduced-order + DEM/MPM granular path); a **first-cut, rule-based multi-fidelity scheduler** with
  error tracking; baseline sensor models; power/thermal evolution; headless + interactive modes;
  MCAP output; and oracle-validated orbital regression. This, with [Worlds](worlds.md),
  [Fleet](fleet.md), and [Bench](bench.md), lets a researcher clone, run the scenario, and score a
  baseline in an afternoon (charter §10, §11). **MVP priority:** correctness + determinism +
  the always-works local tier over breadth of regimes.
- **Phase 1.** Tighten [Surrogate](surrogate.md) integration (interactive-speed granular);
  Brax/MJX swarm-scale parallel training for [Learn](learn.md); richer sensor models; Ray fan-out
  on [Cloud](cloud.md); error-budget-driven (vs. purely rule-based) scheduling.
- **Phase 2.** **Digital-twin shadow** for [Ops](ops.md); terramechanics validation against
  terrestrial-analog rover-swarm field tests; live streaming to [View](view.md).
- **Phase 3.** Flight-adjacent fidelity tiers feeding [Bridge](bridge.md); new regimes (asteroids,
  icy moons) added purely as engine/world plugins — the measure of success being how *little* the
  Sim core changes as regimes grow. **Multi-regime missions:** the microgravity-contact
  engine, multi-regime propagation (coupling [Transit](transit.md)), and the multi-phase runtime
  `sequencer` land here — consuming the additive `MissionSpec`/`regime`/`PhaseTransition`
  [Core](core.md) schema hooks **reserved in Phase 1** ([mission-model.md](mission-model.md)).
