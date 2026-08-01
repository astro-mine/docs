# Astro-Mine — System Architecture

> The whole platform, end to end: what each component is, where it runs, who uses it, what
> data it touches, and exactly how the pieces communicate. Read this with
> [conventions.md](conventions.md) (the cross-cutting technology standards) and the per-component
> docs it links to.

---

## 1. How to read this document

The platform is a set of independently useful components bound by a small, stable contract layer
([Core](core.md)). Each component has its own architecture doc; this document is the **integration
view** — it describes the system as a running whole rather than any single part. The governing idea is
the charter's **thin, stable core with thick, swappable edges**: the contracts in §3 change slowly and
deliberately; everything else is a plugin.

**Components are not distributions.** A component — `Core`, `Sim`, `Worlds` — is a unit of design,
imported as `astro_mine.<name>`. What ships is four things (§4.1):
[`astro-mine-platform`](platform.md) (every component, one wheel, a library),
[`astro-mine-cli`](cli.md) (one executable), [`astro-mine-api`](api.md) (the REST tier), and
[`astro-mine-ui`](ui.md) (the browser front end). Everything below about *how components integrate* is
unchanged by that; what it changes is what enforces the integration, which is §3's last note.

The platform runs in **two modes over one shared core** (charter §3):

- **Design mode** — *goal in, design out*. Explore swarm compositions and policies in
  simulation. Front door: [Studio](studio.md). For complete interplanetary missions it also
  performs *mission architecture* — trajectories, fleet sizing, and economics (see §13).
- **Operate mode** — run a validated campaign, first as a digital-twin shadow, eventually
  commanding real assets. Front door: [Ops](ops.md).

Both modes drive the **same** simulation core and the **same** autonomy components, and feed a
**benchmark-and-hub backbone** that makes everything reproducible and shareable.

---

## 2. System context (who interacts, and how)

```
     Researchers     Mission        ISRU/      Educators/   Operators
       (MARL,       designers     NewSpace      students     (later)
      planning,    (agencies,     startups
       science)      primes)
          │             │             │             │           │
          ├─────────────┴──────┬──────┴─────────────┤           │
          ▼                    ▼                    ▼           │
   ┌────────────────────┐  ┌──────────────────────────┐         │
   │  astro-mine <comp> │  │  CONSOLE — the single    │         │
   │  <verb>            │  │  GUI front door (SPA)    │         │
   │  · the CLI         │  │  composing bench-ui ·    │         │
   │  · Python API      │  │  studio-ui · hub-ui · …  │         │
   └─────────┬──────────┘  └────────────┬─────────────┘         │
             │ in-process               │ HTTP                  │
             │                          ▼                       │
             │              ┌──────────────────────────┐        │
             │              │  astro-mine-api          │        │
             │              │  Hub · Studio · Cloud ·   │        │
             │              │  Bench REST surfaces     │        │
             │              └────────────┬─────────────┘        │
             ▼                           ▼                       ▼
   ┌──────────────────────────────────────────┐   ┌────────────────────────────┐
   │  DESIGN MODE                             │   │  OPERATE MODE              │
   │  Studio · Bench (leaderboards)           │   │  Ops console · View        │
   │  Hub (registry) · View (embedded)        │   │  (3D + dashboards)         │
   └───────────────────┬──────────────────────┘   └─────────────┬──────────────┘
                       │  Core contracts (SADF, Env/Policy API) │
                       ▼                                        ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │  SHARED SUBSTRATE — astro-mine-platform                                   │
   │  Sim (+Surrogate)  ·  Mind · Learn · Allocate · Guard                     │
   │  Worlds · Prospect · Link · Fleet  ·  Core · Spice · Seal                 │
   │  run at scale on Cloud · artifacts in Hub · scored by Bench               │
   └───────────────────────────────────────────────────────────────────────────┘
                                        │ Bridge (ROS 2 / cFS / F´ / CCSDS)
                                        ▼
                             Simulator today  →  real flight hardware (Phase 3)
```

Three clarifications on that picture.

First, the two "console"s are different things: **[Console](ui.md)** is the platform's single GUI
front door, the one application of [`astro-mine-ui`](ui.md); the **Ops console** is the operations
supervisory surface in [Ops](ops.md), Phase 2. They stay distinct: one is how a person reaches the
platform, the other is how an operator commands a live mission.

Second, the console is the **GUI** front door, not the only door. The CLI and the Python API reach the
platform *in process* — no HTTP, no service, nothing running — and for several audiences that is the
primary path. The GUI's HTTP hop through [`astro-mine-api`](api.md) is what a browser requires, not
what the platform requires.

Third, each audience enters through a different *entry point* but everything below it is shared. The
table below names the one each audience ultimately drives — and note what it also shows: **before the
console, every row named a different entry point and there was no shared one at all.** Two audiences
the charter names explicitly (mission designers, educators/students) could not reach the platform
without one, which is the gap the console exists to close. The console does not replace these entry
points; it is the one door that leads to all of them.

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
   FlatBuffers/Cap'n Proto for per-tick hot paths — see conventions.md §3). Includes the
   **`ObjectiveSpec`** and the objective→metric **binding** — the shared objective contract
   authored by [Studio](studio.md), measured/valued by [Bench](bench.md)/[Ledger](ledger.md), and
   tracked by [Ops](ops.md)/[View](view.md) — and the **`Plan`/`ContingentPlan`** vocabulary that
   [Mind](mind.md) produces, [Guard](guard.md) clears, and [Ops](ops.md) executes.
5. **Plugin manifest & registry** — how content is discovered, version-negotiated, signed, and
   loaded. Indexed by [Hub](hub.md); capability tags here are the substrate for export-control
   gating.

**Contribute once, use everywhere**: a new world, robot, planner, policy, or ISRU process is
authored against these contracts and is then immediately usable in design, training,
operations, and benchmarks — without touching Core or any other component. That single property
is what makes the collection an ecosystem rather than a bundle.

**Versioning:** interface versions are independent of implementation versions; each component
declares the Core interface major versions it supports, and `Core`'s `compat` layer refuses
incompatible loads (conventions.md §3, §13). The contract evolves under a strict **additive,
append-only, never-break** rule, and CI enforces it — see below.

**What enforces the waist now that components share one distribution.** An arrow crossing a Core
contract used to be, in part, a fact about packaging: reaching into another component's internals
meant declaring a dependency on another package. That friction is gone, and the enforcement moved into
the build (conventions.md §3.1, §11):

- Schemas are addressed by published **`$id`** and resolved through Core's registry — never by a
  path that happens to work inside one tree.
- Proto fields are append-only and `buf breaking` fails the build; a Core change runs every
  consumer's schema tests in the same job.
- The schema set has a **content address** a scenario pins, so a run against a different contract is
  a different task rather than silently the same one.
- **Layering tests** assert the import graph against the tiers of `conventions.md` §3.2: the graph
  is a DAG, Core depends on nothing, the companions (Spice, Seal) depend only on Core, and any
  component may depend on those three freely. A lateral component-to-component edge is allowed but
  must be argued and recorded; **dependency inversion** (§3.3) is the standing alternative, and the
  reason there are only three such edges today.

A contributor can still write a shortcut past the waist. CI is what refuses it — which is a better
guarantee than a repository boundary was, because a repository boundary never stopped anyone who was
willing to add a dependency.

**Multi-regime missions.** These five contracts gained *additive* extensions — the
Mission/Phase/Regime schema, a bounded `regime` dimension and `PhaseTransition` events on the
Environment API, propulsion/return SADF capabilities, and the descriptive design-time
`TrajectoryRef` schema — reserved in Core in Phase 1. They generalize "a campaign on a world"
into a **Mission** of **Phases** across **Regimes** without widening the waist into per-regime
interfaces; see [mission-model.md](mission-model.md) and §13.

**Shared SPICE foundation.** Core defines the frame/time *vocabulary* (`Epoch`,
`ReferenceFrame`, `PlanetaryCRS`) but defers name→geometry *resolution* (kernels, `spkpos`, `pxform`)
because `spiceypy`/`numpy` are the heavy dependencies the waist must never carry (core.md §2 principle
3). That resolution lives in **[Spice](spice.md)** (`astro_mine.spice`), a thin **Core companion** that
every SPICE consumer — [Worlds](worlds.md), [Link](link.md), [Sim](sim.md)'s orbital engine, later
[Transit](transit.md) — depends on, so the waist stays thin while frame/aberration conventions stay
singular across the platform. Spice resolves Core's vocabulary into positions/rotations/topocentric
scalars and nothing more (window search stays in Link, terrain occlusion in Worlds via the Core
`WorldProvider` contract); Core does not depend on it. That every install now carries `spiceypy`
regardless is beside the point: the rule was never that a user could avoid the dependency, it is that
exactly one code path resolves a frame. See [spice.md](spice.md) and conventions.md §5.

**Shared artifact-integrity foundation.** Core owns the *shape* of integrity (the
`Signature` envelope, the `Verifier` protocol, the `hashing` primitive) but ships **no crypto** —
`cryptography` is another heavy dependency the waist must never carry (core.md §2 principle 3). That
crypto lives in **[Seal](seal.md)** (`astro_mine.seal`), a thin **Core companion** that every producer
and verifier — [Fleet](fleet.md), [Hub](hub.md), [Guard](guard.md), later
[Learn](learn.md)/[Worlds](worlds.md)/[Prospect](prospect.md) — depends on, so
signing/verification/SLSA/SBOM is one byte-stable implementation instead of three hand-copied signers
(conventions.md §9). Seal owns the *mechanism* of integrity and stops there (the production trust-root
policy is decided with Hub); Core does not depend on it. See [seal.md](seal.md) and
[guard.md](guard.md) §9.5.

---

## 4. Component catalog

### 4.1 What ships

| Distribution | Kind | Contains | Doc |
|---|---|---|---|
| `astro-mine-platform` | Python wheel | every component below whose runtime is a library or a gRPC service | [platform.md](platform.md) |
| `astro-mine-cli` | Python wheel | the one `astro-mine` executable, `astro-mine <component> <verb>` | [cli.md](cli.md) |
| `astro-mine-api` | wheel + image | the Hub, Studio, Cloud and Bench REST surfaces | [api.md](api.md) |
| `astro-mine-ui` | npm `@astro-mine/*` | the console application, the generated API client, the design system, View, and the artifact inspectors | [ui.md](ui.md) |

A component with more than one kind of surface is split by *kind*, not forked: Hub's client, index and
registry are library code in the platform; its registry API is a route module in the API distribution;
its browser surface is a package in the UI distribution. The design of all three lives in
[hub.md](hub.md).

### 4.2 Role · runtime · data · talks-to

| Component | Layer | Role (one line) | Runtime / where it runs | Ships in | Key data it touches | Talks to (via) |
|---|---|---|---|---|---|---|
| [Core](core.md) | Backbone | The narrow-waist contracts | In-process library, everywhere | platform | Schemas only (SADF, messages, manifests) | (depended on by all) |
| [Spice](spice.md) | Backbone | SPICE-backed frame/time/geometry resolution (Core companion) | In-process library; kernels furnished locally | platform | NAIF kernels (SPK/PCK/FK/LSK) → positions/rotations | Worlds, Link, Sim, Transit; depends on Core |
| [Seal](seal.md) | Backbone | Artifact integrity: signing, verification, SLSA, SBOM (Core companion) | In-process library; keys furnished by host | platform | Content digests + keys → Signature / provenance / SBOM | Fleet, Hub, Guard (+ producer frontier); depends on Core |
| [Worlds](worlds.md) | World | Celestial-body environments from real DEMs | Library; data prep on Cloud | platform | COG/Zarr terrain, SPICE frames, 3D Tiles | Sim, Prospect, Link, View (Env API) |
| [Prospect](prospect.md) | World | Probabilistic resource fields w/ uncertainty | Library + gRPC service; inference on Cloud | platform | Zarr ground-truth + belief fields | Sim, Mind, Allocate, Bench (Env API) |
| [Link](link.md) | World | Comms environment (LOS, windows, latency) | Library; precompute on Cloud | platform | SPICE geometry, contact graphs, time-series | Sim, Allocate, Mind, Ops (Env API) |
| [Transit](transit.md) † | World | Deep-space / free-space dynamical + hazard environment | Library; precompute on Cloud | platform (P3) | n-body ephemerides, gravity, radiation/thermal/MMOD fields | Sim, Trajectory, Link (Env API) |
| [Fleet](fleet.md) | Assets | SADF asset library (orbiters→ISRU plants) | Library + content artifacts | platform | SADF docs, USD/glTF geometry | Sim, Mind, Studio, Hub, Bridge (SADF) |
| [Sim](sim.md) | Simulation | Multi-physics engine + scenario runtime | Library (local) / Ray workers (Cloud) / gRPC service | platform | Env state, MCAP recordings | implements Env API; consumes Worlds/Prospect/Link/Fleet; Surrogate |
| [Surrogate](surrogate.md) | Simulation | Learned fast physics w/ error bounds | GPU train (Cloud); ONNX inference in Sim | platform | Training sets, ONNX models, error reports | Sim (fidelity tier), Learn, Hub |
| [Mind](mind.md) | Autonomy | Hierarchical autonomy (plan→TAMP→control) | Library; ground+edge in Ops | platform | Plans, behavior trees, capability decls | implements Policy API; Allocate, Learn, Guard, Sim |
| [Learn](learn.md) | Autonomy | MARL toolkit (PettingZoo, RLlib) | Ray training on Cloud | platform | Rollouts, ONNX policies, MLflow runs | wraps Sim as RL env; Surrogate, Hub, Bench |
| [Allocate](allocate.md) | Autonomy | Task allocation & scheduling (CP-SAT + learned) | Library; large solves on Cloud | platform | Constraint models, assignments | implements Policy API; Mind, Link/Worlds/Prospect |
| [Guard](guard.md) | Autonomy | Runtime assurance / safety shields | Rust core in the wheel; edge + central in Ops | platform | Safety specs, verdicts | wraps Policy API outputs; Sim, Ops→Bridge |
| [Trajectory](trajectory.md) † | Mission arch. | Design-time trajectory & maneuver optimization | Library; sweeps on Cloud | platform (P3) | Reference trajectories, Δv/ToF budgets (descriptive) | Transit, Allocate, Sizing, Studio, Sim (validate) |
| [Sizing](sizing.md) † | Mission arch. | Spacecraft & payload systems-engineering sizing | Library (OpenMDAO); sweeps on Cloud | platform (P3) | Mass/power/propellant budgets → sized SADF | Trajectory, Fleet, Ledger, Studio |
| [Ledger](ledger.md) † | Mission arch. | Open techno-economic value model (uncertainty) | Library (OpenMDAO/MC); on Cloud | platform (P3) | Cost/value/risk distributions | Sizing, Trajectory, Prospect, Studio, Bench |
| [Studio](studio.md) | Design | Goal-in/design-out authoring + trade studies | Library + orchestration worker; REST + surface | platform · api · ui | ObjectiveSpec, DesignCandidate, Campaign | orchestrates Sim/Learn/Mind/Allocate/Guard; Hub, Bench, View |
| [Ops](ops.md) | Operations | Online orchestration + digital-twin shadow | Stateful service; ground + edge | platform (P2) | Event-sourced state, telemetry, SLAM map | Sim (shadow), Mind/Allocate/Guard, Bridge, View |
| [Bridge](bridge.md) | Operations | Hardware/flight-software abstraction | Adapters: ground + flight-adjacent | platform (P2) | Core msgs ↔ ROS 2/cFS/F´/CCSDS | Ops; targets Sim or real hardware |
| [View](view.md) | Operations | Visualization, telemetry, plan explanation | Embeddable React library (Cesium/OpenMCT) | ui | Telemetry, 3D Tiles, MCAP replays | embedded by the console and by surfaces; reads Ops/Sim/Worlds data |
| [Console](ui.md) | Design & ops | The single GUI front door: one multi-page application | Static export (TypeScript + React + Next.js); no server | ui | None owned — renders what the API serves | the API distribution; embeds View |
| [Bench](bench.md) | Backbone | Benchmarks, scenario zoo, leaderboards | Library + eval workers; REST + surface | platform · api · ui | Scenario specs, metrics, results | pins Core; runs Sim; Hub submissions; Cloud |
| [Hub](hub.md) | Backbone | Registry for policies/worlds/assets/plugins | Tier-1 local OCI client; hosted registry + Postgres | platform · api · ui | OCI artifacts, manifests, provenance | indexed by Core manifest; all producers/consumers |
| [Cloud](cloud.md) | Backbone | Distributed sim/training orchestration | Kubernetes + Ray + Argo; local backend | platform · api | Content-addressed datasets/artifacts | runs Sim/Learn/Allocate/Surrogate/Bench |

† Not yet built — the **mission architecture & logistics** layer and [Transit](transit.md) are Phase 3
(§13). Existing components are also *extended* for multi-regime scope; see §13.2.

**Where a component has no runtime of its own.** [Core](core.md), [Spice](spice.md) and
[Seal](seal.md) are libraries other components call; they own no service and no user surface, which is
the whole point of a companion (§3). The CLI is not in this table because it is not a component: it
owns no capability, defines no schema, and holds no state — it is a surface over the components that
do ([cli.md](cli.md)).

---

## 5. Communication & integration fabric

The system uses **three communication planes**, chosen per latency and criticality
(conventions.md §4). Keeping them distinct is a deliberate architectural decision: a research
laptop never needs DDS, and a flight-adjacent controller never needs Kafka.

Before any of them: **in-process is a plane too, and it is the default.** The CLI and the Python API
call library functions directly. A local workflow — score the anchor, run an episode, validate an
asset, train a policy — crosses no network at all, and that is a requirement rather than an
optimization (§12 principle 1).

### 5.1 Control plane — synchronous, typed (gRPC / REST)
Service-to-service calls between running services use **gRPC over HTTP/2** with Protobuf contracts
generated from Core schemas; [Sim](sim.md) and [Prospect](prospect.md) serve theirs from the platform
wheel. Browser- and tool-facing edges are **REST + OpenAPI 3.1** via FastAPI, and they all live in
[`astro-mine-api`](api.md): the Hub registry, the Studio API, Cloud's submission service, and the Bench
leaderboard. mTLS between services; OIDC + OPA for authz.

**The API distribution is a composition, not a gateway.** It mounts each component's route modules
into one deployable so REST conventions, auth, and telemetry are decided once. It adds **no**
aggregation endpoint, **no** request rewriting, and **no** backend-for-frontend: a console surface
still calls the routes of the component it is a surface for. The practical difference from the earlier
per-component services is operational — one image, and one origin to configure instead of four. A true
gateway, with its own composed API, remains a Phase-2-at-the-earliest question and would need its own
justification.

**The GUI adds no edge of its own.** [Console](ui.md) is a static export; endpoint configuration is
loaded at boot rather than compiled in, so one build is deployable by someone other than its builder.
Note that [View](view.md)'s telemetry/tile fan-out backend, where it exists, is View's own and is not a
platform API gateway; the two are unrelated.

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

Every arrow in that diagram is an **in-process call** in a local run: the loop is library code
calling library code, in one process, from one wheel. The service tiers change where it runs, not what
calls what.

For complete multi-regime missions, [Studio](studio.md)'s **Mission Architect** mode wraps this
loop in an outer **trajectory ⇄ fleet ⇄ swarm ⇄ economics** co-optimization that adds
[Trajectory](trajectory.md), [Sizing](sizing.md), and [Ledger](ledger.md) — detailed in §13.

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
in operations. One wheel makes that literal — the operations loop imports the same modules the
design loop did, at the same version, with no possibility of the two drifting apart.

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

**One consequence of one wheel worth stating.** "Producing code version" used to mean a set of
component versions, and reproducing a result meant reconstructing that set. It is now a single
version, which is a real simplification — and it is *not* what the reproducibility guarantee rests on.
That still rests on the content addresses and the pinned schema digest, because an environment pin is
over-sensitive (any unrelated dependency bump changes it) and unavailable to a non-Python consumer.

---

## 8. Deployment topology

The platform is designed so the **local/dev tier always works without the cloud** — a
researcher can install, run a scenario, and score a baseline in an afternoon (charter §12).
Higher tiers are accelerators and operational surfaces, never hard dependencies.

| Tier | What runs | Distributions | Substrate | Notes |
|---|---|---|---|---|
| **Local / dev** | Core + Sim + Worlds + Fleet + Bench (+ Mind/Learn at small scale) | platform · cli | One workstation, one Python environment | The MVP loop; no service, no account, no cloud |
| **Cloud** | Sim sweeps, Learn training, Allocate solves, Surrogate training, Bench eval; the hosted registry, leaderboard and Studio backends | platform · api | Kubernetes + Ray (KubeRay) + Argo; GPU Operator | Horizontal scale-out ([Cloud](cloud.md)); spot/preemptible + checkpointing |
| **GUI** | The console SPA, served statically against a configured API origin | ui (+ api) | Any static host / CDN | No server of its own (§5.1) |
| **Operations / ground** | Ops, View, Studio; Bridge (ground side); Guard central supervisor | platform · api · ui | K8s or on-prem; ROS 2/DDS data plane | Operator-facing; delay-tolerant |
| **Edge / onboard-analog** | Per-agent Mind executive + controllers + Guard shield | platform | Edge runtime (ONNX Runtime, Guard's Rust core) | Runs off-network for hard-constraint enforcement |
| **Flight-adjacent** (Phase 3) | Bridge flight adapters (cFS/F´/CCSDS) | platform (partitioned) | Ground systems near mission | Mostly out of open scope; access-controlled |

The edge tier is the one place one wheel is a genuine cost: an onboard-analog install carries the
whole base dependency set to run a shield and a controller. That is a known tension and the reason
Guard's trusted core is a self-contained compiled extension rather than a Python stack — the
assurance path does not depend on the rest of the wheel being reachable, only on being installed.

---

## 9. Cross-cutting concerns, realized system-wide

- **Identity & authz:** OIDC across services; **OPA** policy decisions gate sensitive actions
  and, crucially, *capability-tagged* artifacts and adapters (export-control gating). The two places
  a tag is actually checked are [Hub](hub.md) admission and [Bridge](bridge.md) dispatch — the
  boundaries where a capability leaves the commons (conventions.md §12).
- **The safety chain:** learned/planned decisions are never actuated raw. Every action crosses
  [Guard](guard.md) — an independent, Rust-cored, fail-safe assurance layer that does **not**
  depend on the components it protects — before reaching [Sim](sim.md) (design) or
  [Bridge](bridge.md) (operations). In operations, dispatch additionally requires a shadow-twin
  verdict from [Ops](ops.md). Guard's independence is now an import-graph property a layering test
  asserts, not a fact about which repository it lived in.
- **Supply-chain integrity:** all shared artifacts are signed (Sigstore/cosign), carry SLSA
  provenance + SBOMs, and are re-verified at pull by [Hub](hub.md); plugins load only after
  manifest signature + Core version checks. One implementation of all of it, in [Seal](seal.md).
  Untrusted plugins run sandboxed (containers/gVisor; WASM later).
- **Observability:** OpenTelemetry traces span both loops, so a replan in [Ops](ops.md) is
  traceable through [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md); Prometheus +
  Grafana + Loki for metrics/logs.
- **Export control / dual use (conventions.md §12):** the open commons is the science,
  simulation, and coordination layer. Genuinely sensitive operational capability concentrates
  at [Bridge](bridge.md) (and parts of [Ops](ops.md)/[Mind](mind.md)/[Allocate](allocate.md)),
  is gated by capability tag and partitioned out of the open library where the code itself is the
  concern, and the certification-grade flight-code/targeting generator is structurally excluded from
  scope.

---

## 10. End-to-end walkthrough — lunar polar water-ice prospecting (the anchor scenario)

> Integration-view summary. The full scenario specification — objective, fleet, ConOps, derived
> requirements, and metrics — is [scenarios/1-lunar-polar-ice-prospecting.md](../scenarios/1-lunar-polar-ice-prospecting.md).

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

Steps 1–5 run today, on one workstation, from `astro-mine-cli` and the console; the
[guide](../guide/README.md) walks them. Step 6 is Phase 2.

---

## 11. Roadmap view — how the system grows

> The **detailed, planner-ready roadmap** — per-phase, per-component scope and requirements with
> stable `RM-*` item IDs — lives in [roadmap/](../roadmap/README.md). This section is the integration
> summary.

| Phase | Components stood up | System capability | State |
|---|---|---|---|
| **0** | [Core](core.md) v0.1, [Spice](spice.md), [Sim](sim.md), [Worlds](worlds.md), [Fleet](fleet.md), [Bench](bench.md) (+ [Prospect](prospect.md), [Link](link.md) MVP, local [Cloud](cloud.md)) | A runnable, reproducible benchmark on the anchor scenario | **built** |
| **1** | [Mind](mind.md), [Learn](learn.md), [Allocate](allocate.md), [Guard](guard.md), [Studio](studio.md), [Hub](hub.md), [Surrogate](surrogate.md), [Seal](seal.md), full [Link](link.md) and [Cloud](cloud.md); the [console](ui.md) and the [CLI](cli.md) | The MARL + planning commons; public leaderboards & plugins | **built** |
| — | *(no new components)* | The four distributions: consolidate the components into one wheel, move the CLI out, then stand up [`astro-mine-api`](api.md) and [`astro-mine-ui`](ui.md) | **in progress** |
| **2** | [Ops](ops.md), [Bridge](bridge.md), the full [View](view.md) ops viewer | Cross the sim→operations threshold on Earth analogs | next |
| **3** | [Bridge](bridge.md) flight adapters; the **mission-architecture track** ([Transit](transit.md), [Trajectory](trajectory.md), [Sizing](sizing.md), [Ledger](ledger.md)) + small-body/microgravity extensions; **NEO sample-return** then **asteroid-mining** scenarios; new bodies as plugins | Default stack — surface ISRU *and* interplanetary resource missions — as the cislunar economy matures | later |

The narrow waist is what makes this sequencing safe: later phases add edges, not core
rewrites. Success is measured by how *little* [Core](core.md) changes as the platform grows — and the
consolidation is evidence for the claim rather than against it: eighteen repositories collapsed into
four distributions with import paths, schemas, `$id`s, entry points and public APIs unchanged, which
is only possible if the contracts were where the value was.

The multi-regime mission-architecture track (§13) is **opt-in and gated behind the lunar MVP**; its
only Phase-1 obligation is reserving the additive Mission/Phase/Regime Core schema hooks.

---

## 12. System-level principles & open questions

**Principles** (in addition to each component's own):

1. The local/dev loop is sacred — it must run with no cloud, no accounts, no services.
2. One contract per concern, owned by Core; no private side-channels between components — and now
   that there is no packaging barrier, that is asserted by a layering test rather than assumed.
3. Decisions are never actuated unassured — Guard is on every path to actuation.
4. Reproducibility is a system property, not a feature of Bench — content-addressing and
   provenance are pervasive.
5. The three communication planes stay separate; Bridge is the only door between the platform
   and the robotics/flight plane. In-process is the default plane, not a degraded one.
6. Capability is declared and gated, not assumed — the same mechanism serves autonomy
   negotiation and export control, and it is checked at a boundary rather than honoured by
   convention.
7. A component owns capability; a distribution owns release. Confusing the two is what produced
   eighteen release processes for one platform.

**Cross-cutting open questions** (each elaborated in the relevant component doc):

- The exact shape of the Core Environment API for **variable-fidelity + comms-masked**
  observation (co-design: [Core](core.md) ↔ [Sim](sim.md) ↔ [Learn](learn.md)).
- The **error-bound contract** by which Sim's scheduler trusts a Surrogate tier
  ([Sim](sim.md) ↔ [Surrogate](surrogate.md)).
- The **capability-tag taxonomy** for dual-use gating (Core ↔ governance/export-control).
- **Evaluation science**: what "good" means for a multi-week ISRU campaign ([Bench](bench.md)).
- **Sim-to-real credibility** without on-world data — the central trust problem the whole
  stack must eventually answer (charter §8).
- **The edge install.** One wheel is the right answer for a workstation and an awkward one for an
  onboard-analog target (§8). Whether the assurance path eventually needs a distribution of its own
  is an open question, not a settled one.

---

## 13. Multi-regime missions

The platform extends from single-body surface campaigns to complete **interplanetary missions** —
asteroid mining, NEO sample-return, cislunar logistics — without becoming a different system. The
generalization is additive and specified in [mission-model.md](mission-model.md); this section shows
how it threads through the system above. Implementation is Phase 3.

### 13.1 The Mission / Phase / Regime model
A **Mission** is an ordered set of **Phases**, each in a **Regime** (`launch_ascent ·
interplanetary_transit · proximity_orbit · surface · ascent_return · earth_interface`), sharing
one fleet and a value model. A single-`surface`-phase Mission is exactly today's campaign, so
every component and scenario above runs unchanged. Core gains only *schema* (the `MissionSpec`, a
bounded `regime` dimension + `PhaseTransition` events, propulsion SADF capabilities); the
phase-sequencing **mechanism** lives in the [Sim](sim.md)/[Ops](ops.md) runtime and the
**policy** in [Studio](studio.md)/Ops.

### 13.2 New components
- **[Transit](transit.md)** (environment) — the interplanetary / free-space dynamical + hazard
  environment between bodies; what [Worlds](worlds.md) is to a body.
- **Mission architecture & logistics** (new layer): **[Trajectory](trajectory.md)** (design-time
  trajectory/maneuver optimization — descriptive, never executable guidance),
  **[Sizing](sizing.md)** (spacecraft/payload systems-engineering sizing → SADF), and
  **[Ledger](ledger.md)** (open techno-economic value model under uncertainty).
- Existing components are **extended, not replaced** — small bodies ([Worlds](worlds.md)),
  microgravity contact ([Sim](sim.md)/[Surrogate](surrogate.md)), deep-space comms
  ([Link](link.md)), propulsion ([Fleet](fleet.md)), window-gated planning
  ([Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md)), multi-phase ops
  ([Ops](ops.md)/[Bridge](bridge.md)/[View](view.md)), mission scenarios ([Bench](bench.md)),
  and artifacts ([Hub](hub.md)/[Cloud](cloud.md)). See [mission-model.md](mission-model.md).
- All four new components land as subpackages of [`astro-mine-platform`](platform.md). The track
  adds a *layer* to the architecture and **no** distribution — which is a useful test of the
  distribution model: if a whole new layer needs no new release process, the model is carrying its
  weight.

### 13.3 The mission-architecture loop
[Studio](studio.md)'s **Mission Architect** mode wraps the design loop (§6.1) in an outer
co-optimization: [Trajectory](trajectory.md) finds feasible transfers/windows and Δv budgets →
[Sizing](sizing.md) turns Δv + throughput needs into sized spacecraft (written back as SADF) →
[Ledger](ledger.md) scores delivered value under uncertainty → [Allocate](allocate.md) solves the
joint **asset ↔ target ↔ window ↔ trajectory** assignment → the per-phase swarm campaigns run
through the existing Sim/Mind/Guard loop. Sizing and Ledger share one OpenMDAO graph for the tight
vehicle⇄economics inner loop; the result is a declarative `MissionSpec` handed to [Ops](ops.md).

### 13.4 End-to-end — asteroid mining
> Integration-view summary. The full scenario specification is [scenarios/2-asteroid-mining.md](../scenarios/2-asteroid-mining.md).

1. **Targets & environment.** [Transit](transit.md) supplies NEO ephemerides and the deep-space
   environment; [Worlds](worlds.md) provides small-body shape/gravity; [Prospect](prospect.md)
   the (volumetric, uncertain) ore field; [Link](link.md) DSN windows and light-time.
2. **Architect the mission.** In Studio's Mission Architect: state "return *N* tonnes of ore."
   [Trajectory](trajectory.md) scans launch/transfer/return windows; [Sizing](sizing.md) sizes
   miners, haulers, comms relays, and the return vehicle (reusing LEO assets where possible);
   [Ledger](ledger.md) values candidates; [Allocate](allocate.md) assigns assets to asteroids and
   windows.
3. **Design each per-asteroid swarm.** Every `proximity_orbit`/`surface` phase is the familiar
   prospect → allocate → mine loop, now with microgravity contact/anchoring physics
   ([Sim](sim.md) + [Surrogate](surrogate.md)) and window-gated, high-latency assurance
   ([Guard](guard.md)).
4. **Score & operate.** [Bench](bench.md) scores the mission (delivered mass, Δv efficiency, ROI);
   [Ops](ops.md) runs it phase by phase with a regime-spanning shadow twin; [Bridge](bridge.md)
   speaks DSN/CCSDS/DTN — but **operational maneuver targeting stays out of scope**, gated by the
   `operational_targeting` capability tag.

### 13.5 What stays out
Operational maneuver targeting, guided atmospheric entry/recovery, and proprietary mission
economics are deliberately excluded or partitioned (charter §9.5, conventions.md §12).
[Trajectory](trajectory.md) is design-time exploration only; its `TrajectoryRef` artifacts omit
any executable-guidance fields by schema — which is the strongest form of the gate, because a field
that does not exist cannot be populated by a caller who means well.

### 13.6 Deployment & roadmap
The mission-architecture engines are design-time **batch** workloads — trajectory window /
global-optimization sweeps and OpenMDAO design sweeps — that fit the existing [Cloud](cloud.md)
Ray/Argo substrate (mostly CPU-bound). The track is **opt-in, Phase 3**, gated behind the lunar
MVP; only the additive Core schema hooks are reserved in **Phase 1**.
