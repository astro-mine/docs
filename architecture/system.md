# Astro-Mine — System Architecture

> The whole platform, end to end: what each component is, where it runs, who uses it, what
> data it touches, and exactly how the pieces communicate. Read this with
> [conventions.md](conventions.md) (the cross-cutting technology standards) and the per-component
> docs it links to.

---

## 1. How to read this document

The platform is a set of independently useful `Astro-Mine-*` packages bound by a small,
stable contract layer ([Core](core.md)). Each package has its own architecture doc; this
document is the **integration view** — it describes the system as a running whole rather than
any single part. The governing idea is the charter's **thin, stable core with thick, swappable
edges**: the contracts in §3 change slowly and deliberately; everything else is a plugin.

The platform runs in **two modes over one shared core** (charter §3):

- **Design mode** — *goal in, design out*. Explore swarm compositions and policies in
  simulation. Front door: [Studio](studio.md).
- **Operate mode** — run a validated campaign, first as a digital-twin shadow, eventually
  commanding real assets. Front door: [Ops](ops.md).

Both modes drive the **same** simulation core and the **same** autonomy components, and feed a
**benchmark-and-hub backbone** that makes everything reproducible and shareable.

---

## 2. System context (who interacts, and how)

```
        Researchers   Mission designers   ISRU/NewSpace   Educators/    Operators
        (MARL,        (agencies,          startups        students      (later)
         planning,     primes)                                          
         science)         │                   │              │              │
            │             │                   │              │              │
            ▼             ▼                   ▼              ▼              ▼
   ┌─────────────────────────────────────────┐   ┌───────────────────────────┐
   │  DESIGN MODE                             │   │  OPERATE MODE              │
   │  Studio (web)  ·  Bench (leaderboards)   │   │  Ops console  ·  View      │
   │  Hub (registry) · View (embedded)        │   │  (3D + dashboards)         │
   └───────────────────┬─────────────────────┘   └────────────┬──────────────┘
                       │  Core contracts (SADF, Env API, Policy API, messages)   │
                       ▼                                          ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  SHARED SUBSTRATE                                                          │
   │  Sim (+Surrogate)  ·  Mind · Learn · Allocate · Guard                      │
   │  Worlds · Prospect · Link · Fleet                                          │
   │  run at scale on Cloud · artifacts in Hub · scored by Bench               │
   └──────────────────────────────────────────────────────────────────────────┘
                                          │ Bridge (ROS 2 / cFS / F´ / CCSDS)
                                          ▼
                               Simulator today  →  real flight hardware (Phase 3)
```

Each audience enters through a different surface but everything below the surface is shared:

| Audience | Primary surface | What they ultimately drive |
|---|---|---|
| Multi-agent autonomy / RL researchers | [Learn](learn.md), [Bench](bench.md), [Hub](hub.md) | train policies vs [Sim](sim.md), publish to leaderboards |
| Planetary scientists | [Worlds](worlds.md), [Prospect](prospect.md) | author worlds & resource fields |
| Planning researchers | [Allocate](allocate.md), [Mind](mind.md) | new planners/allocators behind Core APIs |
| Mission designers | [Studio](studio.md) | goal → swarm design via the design loop |
| Roboticists | [Fleet](fleet.md) | contribute SADF assets |
| Operators (later) | [Ops](ops.md) + [View](view.md) | run campaigns through [Bridge](bridge.md) |
| Educators/students | [Studio](studio.md), [View](view.md), [Bench](bench.md) | runnable coursework & competitions |

---

## 3. The narrow waist: how everything integrates

Every arrow in the system crosses a **[Core](core.md)** contract. Core defines five things and
nothing else:

1. **SADF (Swarm Asset Description Format)** — how an asset is described. Authored by
   [Fleet](fleet.md), instantiated by [Sim](sim.md), reasoned over by [Mind](mind.md)/
   [Allocate](allocate.md), shown in [Studio](studio.md)/[View](view.md), mapped to hardware by
   [Bridge](bridge.md).
2. **Environment API** — how a simulatable world is observed and acted on. Implemented by
   [Sim](sim.md); fed by [Worlds](worlds.md)/[Prospect](prospect.md)/[Link](link.md); wrapped
   as Gymnasium/PettingZoo by [Learn](learn.md).
3. **Policy / Planner API** — how decisions are computed and composed. Implemented by
   [Mind](mind.md), [Allocate](allocate.md), and learned policies from [Learn](learn.md);
   wrapped by [Guard](guard.md).
4. **Message schemas** — the typed vocabulary every plane exchanges (Protobuf default;
   FlatBuffers/Cap'n Proto for per-tick hot paths — see conventions.md §3).
5. **Plugin manifest & registry** — how content is discovered, version-negotiated, signed, and
   loaded. Indexed by [Hub](hub.md); capability tags here are the substrate for export-control
   gating.

**Contribute once, use everywhere**: a new world, robot, planner, policy, or ISRU process is
authored against these contracts and is then immediately usable in design, training,
operations, and benchmarks — without touching Core or any other package. That single property
is what makes the collection an ecosystem rather than a bundle.

**Versioning:** interface versions are independent of implementation versions; each component
declares the Core interface major versions it supports, and `Core`'s `compat` layer refuses
incompatible loads (conventions.md §3, §13). Changes to Core go through the RFC process.

---

## 4. Component catalog — role · runtime · data · talks-to

| Component | Layer | Role (one line) | Runtime / where it runs | Key data it touches | Talks to (via) |
|---|---|---|---|---|---|
| [Core](core.md) | Backbone | The narrow-waist contracts | In-process library, everywhere | Schemas only (SADF, messages, manifests) | (depended on by all) |
| [Worlds](worlds.md) | World | Celestial-body environments from real DEMs | Library; data prep on Cloud | COG/Zarr terrain, SPICE frames, 3D Tiles | Sim, Prospect, Link, View (Env API) |
| [Prospect](prospect.md) | World | Probabilistic resource fields w/ uncertainty | Library; inference on Cloud | Zarr ground-truth + belief fields | Sim, Mind, Allocate, Bench (Env API) |
| [Link](link.md) | World | Comms environment (LOS, windows, latency) | Library; precompute on Cloud | SPICE geometry, contact graphs, time-series | Sim, Allocate, Mind, Ops (Env API) |
| [Fleet](fleet.md) | Assets | SADF asset library (orbiters→ISRU plants) | Library + content artifacts | SADF docs, USD/glTF geometry | Sim, Mind, Studio, Hub, Bridge (SADF) |
| [Sim](sim.md) | Simulation | Multi-physics engine + scenario runtime | Library (local) / Ray workers (Cloud) | Env state, MCAP recordings | implements Env API; consumes Worlds/Prospect/Link/Fleet; Surrogate |
| [Surrogate](surrogate.md) | Simulation | Learned fast physics w/ error bounds | GPU train (Cloud); ONNX inference in Sim | Training sets, ONNX models, error reports | Sim (fidelity tier), Learn, Hub |
| [Mind](mind.md) | Autonomy | Hierarchical autonomy (plan→TAMP→control) | Library; ground+edge in Ops | Plans, behavior trees, capability decls | implements Policy API; Allocate, Learn, Guard, Sim |
| [Learn](learn.md) | Autonomy | MARL toolkit (PettingZoo, RLlib) | Ray training on Cloud | Rollouts, ONNX policies, MLflow runs | wraps Sim as RL env; Surrogate, Hub, Bench |
| [Allocate](allocate.md) | Autonomy | Task allocation & scheduling (CP-SAT + learned) | Library; large solves on Cloud | Constraint models, assignments | implements Policy API; Mind, Link/Worlds/Prospect |
| [Guard](guard.md) | Autonomy | Runtime assurance / safety shields | Rust core; edge + central in Ops | Safety specs, verdicts | wraps Policy API outputs; Sim, Ops→Bridge |
| [Studio](studio.md) | Design | Goal-in/design-out authoring + trade studies | Web app (React + FastAPI) on Cloud | ObjectiveSpec, DesignCandidate, Campaign | orchestrates Sim/Learn/Mind/Allocate/Guard; Hub, Bench, View |
| [Ops](ops.md) | Operations | Online orchestration + digital-twin shadow | Stateful service; ground + edge | Event-sourced state, telemetry, SLAM map | Sim (shadow), Mind/Allocate/Guard, Bridge, View |
| [Bridge](bridge.md) | Operations | Hardware/flight-software abstraction | Adapters: ground + flight-adjacent | Core msgs ↔ ROS 2/cFS/F´/CCSDS | Ops; targets Sim or real hardware |
| [View](view.md) | Operations | Visualization, telemetry, plan explanation | Web app (React + Cesium/OpenMCT) | Telemetry, 3D Tiles, MCAP replays | Ops, Sim, Worlds, embedded in Studio |
| [Bench](bench.md) | Backbone | Benchmarks, scenario zoo, leaderboards | FastAPI + Postgres; eval on Cloud | Scenario specs, metrics, results | pins Core; runs Sim; Hub submissions; Cloud |
| [Hub](hub.md) | Backbone | Registry for policies/worlds/assets/plugins | OCI registry + Postgres on Cloud | OCI artifacts, manifests, provenance | indexed by Core manifest; all producers/consumers |
| [Cloud](cloud.md) | Backbone | Distributed sim/training orchestration | Kubernetes + Ray + Argo | Content-addressed datasets/artifacts | runs Sim/Learn/Allocate/Surrogate/Bench |

---

## 5. Communication & integration fabric

The system uses **three communication planes**, chosen per latency and criticality
(conventions.md §4). Keeping them distinct is a deliberate architectural decision: a research
laptop never needs DDS, and a flight-adjacent controller never needs Kafka.

### 5.1 Control plane — synchronous, typed (gRPC / REST)
Service-to-service calls (Studio→Sim, Ops→Mind, Bench→Sim, etc.) use **gRPC over HTTP/2** with
Protobuf contracts generated from Core schemas. Browser- and tool-facing edges
([Studio](studio.md), [Hub](hub.md), [Bench](bench.md), [View](view.md)) expose **REST +
OpenAPI 3.1** via FastAPI. mTLS between services; OIDC + OPA for authz.

### 5.2 Eventing / orchestration plane — asynchronous (NATS / Kafka)
Job lifecycles, hub events, bench-result ingestion, and Studio's long-running design jobs flow
over **NATS + JetStream** (Kafka where a durable high-throughput log is needed). This is how
[Cloud](cloud.md) dispatches work and how producers notify [Hub](hub.md)/[Bench](bench.md) of
new artifacts/results.

### 5.3 Real-time data plane — robotics/ops (ROS 2 / DDS)
Fleet telemetry and commands in operate mode use **ROS 2 / DDS**. [Bridge](bridge.md) is the
sole boundary between this plane and the rest of the platform; [View](view.md) reaches it
through a web bridge (Foxglove/rosbridge). Recorded streams everywhere use **MCAP** so one file
carries heterogeneous, timestamped, schema-tagged channels.

### 5.4 Data interchange
Arrays/fields as **Zarr** (+HDF5); terrain/rasters as **Cloud-Optimized GeoTIFF** (GDAL,
STAC-cataloged); tabular/results as **Parquet/Arrow**; portable policies/surrogates as
**ONNX**; large artifacts as **content-addressed OCI** in [Hub](hub.md) over S3-compatible
object storage. All spatial data carries an explicit planetary CRS resolved via SPICE/PROJ — no
implicit Earth/WGS84 (conventions.md §5).

---

## 6. The two loops in detail

### 6.1 Design & training loop

```
 Worlds ─┐
 Prospect├─► Sim ◄── Surrogate (fast fidelity tier)
 Link  ──┘    ▲           │
 Fleet ───────┘           │ Env API (Gymnasium/PettingZoo)
                          ▼
            Learn ──► policies (ONNX) ──► Mind ──► Allocate
                                           │          │
                                           ▼          ▼
                                          Guard (assure) 
                                           │
        Studio orchestrates the whole loop ▼  ── scored by ──► Bench
                  │                       results                 │
                  └────────► Hub (store/share artifacts) ◄────────┘
                         everything runs at scale on Cloud
```

A designer states a goal in [Studio](studio.md) (optionally LLM-assisted intent capture via the
Claude API → a Core-validated `ObjectiveSpec`). Studio composes candidate designs from
[Fleet](fleet.md) assets and explores them with a trade-study engine. Each candidate is
simulated by [Sim](sim.md) — drawing its world from [Worlds](worlds.md), resource ground truth
from [Prospect](prospect.md), comms from [Link](link.md), and accelerated by
[Surrogate](surrogate.md) when error bounds permit. [Learn](learn.md) trains cooperative
policies against that simulation; [Mind](mind.md) composes them with planners and delegates
assignment to [Allocate](allocate.md); [Guard](guard.md) wraps the result so hard constraints
hold. [Bench](bench.md) scores candidates on shared scenarios; [Hub](hub.md) stores and shares
everything produced; [Cloud](cloud.md) runs it all at scale. **Wall-clock and cost are governed
by Sim's multi-fidelity scheduler trusting Surrogate's tracked error bounds.**

### 6.2 Operations loop

```
  validated Campaign (from Studio)
            │
            ▼
          Ops ──► state estimation (factor-graph SLAM + filters)
            │  ── digital-twin shadow: a Sim instance vets each replan ──┐
            │                                                            │
   anomaly / new goal                                                    │
            ▼                                                            │
   Mind ─► Allocate ─► (replan) ─► Guard (assure + clearance token) ─────┘
            │
            ▼
         Bridge ─► ROS 2 / cFS / F´ / CCSDS ─► Sim today | real hardware (Phase 3)
            │
            ▼  telemetry up
          View (3D + dashboards + plan explanation)  ·  operator supervises
```

[Ops](ops.md) takes a validated `Campaign` from [Studio](studio.md) and executes it. It
maintains fleet-wide state (collaborative SLAM via factor graphs + per-asset filters), and runs
a **[Sim](sim.md) instance in shadow** that predicts outcomes and vets every replan *before
commit*. Anomalies trigger replanning through the **same** [Mind](mind.md)/[Allocate](allocate.md)
components used in design; every dispatched command first earns a [Guard](guard.md) clearance
token. [Bridge](bridge.md) translates committed, assured plans into the real-time plane —
driving the simulator today and real hardware later, with the *same plan bytes*. Telemetry
flows back through [View](view.md), where the operator supervises under latency via
intent-envelope approval (delay-tolerant adjustable autonomy).

**The reuse is the point:** Mind, Allocate, Guard, and Sim appear in *both* loops. A planner
improved for design improves operations; a scenario validated in design becomes the shadow twin
in operations.

---

## 7. Data architecture across the system

| Stage | Produced by | Format | Stored / moved via | Consumed by |
|---|---|---|---|---|
| Terrain & environment | Worlds | COG, Zarr, 3D Tiles | Object store (STAC catalog) | Sim, View, Link, Prospect |
| Resource fields (truth + belief) | Prospect | Zarr (w/ distribution axis) | Object store | Sim (truth, access-gated), Mind/Allocate (belief) |
| Comms availability | Link | contact graph + time-series | Object store / in-memory | Sim, Allocate, Mind, Ops |
| Assets | Fleet | SADF (YAML/proto) + USD/glTF | OCI artifacts (Hub) | Sim, Mind, Studio, Bridge |
| Simulation traces | Sim | MCAP, Parquet | Object store | Bench, View, Learn, Ops |
| Policies | Learn | ONNX + metadata sidecar | OCI artifacts (Hub) | Mind, Guard, Bench |
| Surrogate models | Surrogate | ONNX + error report | OCI artifacts (Hub) | Sim, Learn, Studio |
| Designs / campaigns | Studio | Core-schema docs | Postgres + Hub | Ops, Bench |
| Operational state & telemetry | Ops | event log, MCAP, TimescaleDB | Postgres/Timescale/Redis | View, replanners, audit |
| Results / leaderboards | Bench | Parquet + Postgres | Postgres + object store | Studio, View, community |

**Provenance & reproducibility (conventions.md §5, §11):** every generated artifact records its
inputs (content hashes), producing code version, environment lockfile, and random seed.
Datasets, policies, surrogates, and scenarios are **content-addressed**, so any
[Bench](bench.md) result can be reproduced byte-for-byte. This is the technical foundation of
the academic flywheel — a leaderboard number is meaningless if it cannot be reproduced.

---

## 8. Deployment topology

The platform is designed so the **local/dev tier always works without the cloud** — a
researcher can clone, run a scenario, and score a baseline in an afternoon (charter §13).
Higher tiers are accelerators and operational surfaces, never hard dependencies.

| Tier | What runs | Substrate | Notes |
|---|---|---|---|
| **Local / dev** | Core + Sim + Worlds + Fleet + Bench (+ Mind/Learn at small scale) | One workstation, `docker compose` / single Python env | The MVP loop; `Cloud` not required |
| **Cloud** | Sim sweeps, Learn training, Allocate solves, Surrogate training, Bench eval; Hub + Studio backends | Kubernetes + Ray (KubeRay) + Argo; GPU Operator | Horizontal scale-out ([Cloud](cloud.md)); spot/preemptible + checkpointing |
| **Operations / ground** | Ops, View, Studio; Bridge (ground side); Guard central supervisor | K8s or on-prem; ROS 2/DDS data plane | Operator-facing; delay-tolerant |
| **Edge / onboard-analog** | Per-agent Mind executive + controllers + Guard shield | Edge runtime (ONNX Runtime, Rust Guard core) | Runs off-network for hard-constraint enforcement |
| **Flight-adjacent** (Phase 3) | Bridge flight adapters (cFS/F´/CCSDS) | Ground systems near mission | Mostly out of open scope; access-controlled |

---

## 9. Cross-cutting concerns, realized system-wide

- **Identity & authz:** OIDC across services; **OPA** policy decisions gate sensitive actions
  and, crucially, *capability-tagged* artifacts and adapters (export-control gating).
- **The safety chain:** learned/planned decisions are never actuated raw. Every action crosses
  [Guard](guard.md) — an independent, Rust-cored, fail-safe assurance layer that does **not**
  depend on the components it protects — before reaching [Sim](sim.md) (design) or
  [Bridge](bridge.md) (operations). In operations, dispatch additionally requires a shadow-twin
  verdict from [Ops](ops.md).
- **Supply-chain integrity:** all shared artifacts are signed (Sigstore/cosign), carry SLSA
  provenance + SBOMs, and are re-verified at pull by [Hub](hub.md); plugins load only after
  manifest signature + Core version checks. Untrusted plugins run sandboxed (containers/gVisor;
  WASM later).
- **Observability:** OpenTelemetry traces span both loops, so a replan in [Ops](ops.md) is
  traceable through [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md); Prometheus +
  Grafana + Loki for metrics/logs.
- **Export control / dual use (conventions.md §12):** the open commons is the science,
  simulation, and coordination layer. Genuinely sensitive operational capability concentrates
  at [Bridge](bridge.md) (and parts of [Ops](ops.md)/[Mind](mind.md)/[Allocate](allocate.md)),
  is partitioned into access-controlled repos, and the certification-grade flight-code/targeting
  generator is structurally excluded from scope.

---

## 10. End-to-end walkthrough — lunar polar water-ice prospecting (the anchor scenario)

1. **Author the world.** A planetary scientist configures [Worlds](worlds.md) for the
   Shackleton crater rim (LOLA DEM → COG/Zarr, SPICE-driven illumination with PSR detection)
   and lays a [Prospect](prospect.md) ice-probability field (a GP posterior with explicit
   uncertainty) over it. [Link](link.md) precomputes relay/Earth contact windows.
2. **Assemble the fleet.** A roboticist selects SADF rovers, a hopper, and an ISRU plant from
   [Fleet](fleet.md) (pulled from [Hub](hub.md)).
3. **State the goal.** In [Studio](studio.md): "produce 10 t of water/month from this crater."
   Optional Claude-API intent capture turns the sentence into a Core-validated `ObjectiveSpec`;
   a human reviews it.
4. **Explore designs.** Studio runs a trade study: candidate swarm compositions are simulated by
   [Sim](sim.md) on [Cloud](cloud.md), accelerated by [Surrogate](surrogate.md) for the
   expensive excavation/granular physics. [Learn](learn.md) trains a comms-limited cooperative
   prospecting policy; [Allocate](allocate.md) schedules who prospects where under power and
   contact-window constraints; [Mind](mind.md) composes it; [Guard](guard.md) wraps it.
5. **Score & share.** [Bench](bench.md) scores each design on the standard polar-prospecting
   scenario (content-pinned, reproducible). The winning design + policy are published to
   [Hub](hub.md).
6. **Operate.** The validated `Campaign` moves to [Ops](ops.md). A [Sim](sim.md) shadow twin
   vets each replan; [Guard](guard.md) clears each command; [Bridge](bridge.md) drives the
   simulator today (real rovers later) over ROS 2. The operator watches in [View](view.md) — 3D
   terrain, swarm state, and a "why this assignment" explanation — approving intent envelopes
   under multi-minute latency.
7. **Close the loop.** Field/sim telemetry refines [Prospect](prospect.md)'s belief field and
   feeds new [Bench](bench.md) scenarios — the commons compounds.

---

## 11. Roadmap view — how the system grows

| Phase | Components stood up | System capability |
|---|---|---|
| **0 · 0–12 mo** | [Core](core.md) v0.1, [Sim](sim.md), [Worlds](worlds.md), [Fleet](fleet.md), [Bench](bench.md) (+ [Prospect](prospect.md), local [Cloud](cloud.md)) | A runnable, reproducible benchmark on the anchor scenario |
| **1 · 12–30 mo** | [Mind](mind.md), [Learn](learn.md), [Allocate](allocate.md), [Guard](guard.md), [Studio](studio.md), [Hub](hub.md), [Surrogate](surrogate.md), [Link](link.md), full [Cloud](cloud.md) | The MARL + planning commons; public leaderboards & plugins |
| **2 · 30–54 mo** | [Ops](ops.md), [Bridge](bridge.md), [View](view.md) | Cross the sim→operations threshold on Earth analogs |
| **3 · 54 mo+** | [Bridge](bridge.md) flight adapters; new bodies as plugins | Default stack as the cislunar economy matures |

The narrow waist is what makes this sequencing safe: later phases add edges, not core
rewrites. Success is measured by how *little* [Core](core.md) changes as the platform grows.

---

## 12. System-level principles & open questions

**Principles** (in addition to each component's own):

1. The local/dev loop is sacred — it must run with no cloud, no accounts, no services.
2. One contract per concern, owned by Core; no private side-channels between components.
3. Decisions are never actuated unassured — Guard is on every path to actuation.
4. Reproducibility is a system property, not a feature of Bench — content-addressing and
   provenance are pervasive.
5. The three communication planes stay separate; Bridge is the only door between the platform
   and the robotics/flight plane.
6. Capability is declared and gated, not assumed — the same mechanism serves autonomy
   negotiation and export control.

**Cross-cutting open questions** (each elaborated in the relevant component doc):

- The exact shape of the Core Environment API for **variable-fidelity + comms-masked**
  observation (co-design: [Core](core.md) ↔ [Sim](sim.md) ↔ [Learn](learn.md)).
- The **error-bound contract** by which Sim's scheduler trusts a Surrogate tier
  ([Sim](sim.md) ↔ [Surrogate](surrogate.md)).
- The **capability-tag taxonomy** for dual-use gating (Core ↔ governance/export-control).
- **Evaluation science**: what "good" means for a multi-week ISRU campaign ([Bench](bench.md)).
- **Sim-to-real credibility** without on-world data — the central trust problem the whole
  stack must eventually answer (charter §9).
