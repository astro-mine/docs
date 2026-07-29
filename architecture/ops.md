# Astro-Mine-Ops — Technology Architecture

> Layer: **Operations runtime (online mode)** · Phase: **2** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> The threshold from simulation to reality — one operator supervising many robots across minutes of latency.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Ops` is the **orchestration runtime**: the stateful, event-driven system that
actually *runs* a swarm. It takes a validated campaign authored in [Studio](studio.md),
maintains a live fleet-wide picture of state, executes the plan against assets, monitors for
deviation, and replans and handles anomalies when reality diverges from intent. It does this
with two defining features: a **human-in-the-loop supervisory console** through which operators
approve intent, override, and receive explanations; and a **digital-twin shadow** — a
[Sim](sim.md) instance running ahead of and in parallel to reality that vets every replan
*before* it is committed to hardware.

Concretely, Ops:

- maintains **fleet-wide state estimation** — collaborative localization/SLAM and sensor
  fusion across heterogeneous assets in feature-poor, GNSS-denied terrain;
- **executes** the active campaign as a long-running, durable, resumable workflow;
- **monitors** execution against expected trajectories, resource budgets, and constraints;
- **replans** on anomaly by calling [Mind](mind.md) and [Allocate](allocate.md) — the *same*
  autonomy components used in design — and **assures** every candidate through [Guard](guard.md)
  before any actuation;
- **vets** each replan in the shadow twin before commit;
- **drives** real hardware or a simulator through [Bridge](bridge.md) over the ROS 2/DDS data
  plane (conventions.md §4), and streams telemetry up to [View](view.md);
- operates under **delay-tolerant supervisory autonomy**: the operator approves intent on the
  ground, the edge executes it autonomously across the comms gap.

**Multi-phase mission operations (RFC-0001).** Beyond a single-body campaign, Ops *runs the live
phases* of a multi-regime [Mission](mission-model.md) — an ordered set of phases each in its own
regime (transit, proximity, surface, ascent/return). Per RFC-0001 Resolution R2, Ops owns the
**operational** half of phase sequencing: a per-phase executor mirrors [Sim](sim.md)'s
scenario-runtime sequencer mechanism, performs the `PhaseTransition` handoff (the terminal state
of one phase seeds the next), and applies cross-phase replanning *policy* authored in
[Studio](studio.md). The validated `MissionSpec` it runs comes from [Studio](studio.md); Core
learns the schema of a mission, never how to fly one. A single-`surface`-phase mission is exactly
today's campaign, so nothing in the existing loop changes.

**Explicitly out of scope.** Ops is an *orchestrator*, not a physics engine, planner, or
controller — it owns none of those, it *calls* them. It does not author campaigns (that is
[Studio](studio.md)); it does not implement the hardware/flight-software adapters (that is
[Bridge](bridge.md)); it does not implement safety shields (it *invokes* [Guard](guard.md));
it does not run flight-certified targeting — certification-grade flight code generation is
**explicitly excluded from the open core** (charter §2, §9.5, conventions.md §12). On-board
flight autonomy in Phase 3 is a [Bridge](bridge.md)/`Guard` concern, not an Ops feature.

**Primary users:** operators and mission-ops teams. Secondarily, integrators validating the
sim→ops threshold, and educators demonstrating supervised swarm operations.

**Charter alignment:** §5.6 (the operations runtime — orchestration, state estimation,
HITL console, digital-twin shadow); §6 ("the operations loop"); §8 research dependencies
("delay-tolerant supervisory autonomy"; "swarm state estimation and SLAM in feature-poor,
GNSS-denied environments"); §9 ("robust coordination under intermittent comms"; "verifiable
safety of learned policies under latency"); §11 Phase 2 ("cross the simulation-to-operations
threshold on Earth analogs").

---

## 2. Architecture principles

1. **The shadow gates the world.** No plan reaches an actuator until a [Sim](sim.md) shadow
   twin has simulated it forward and [Guard](guard.md) has cleared it. The twin is not a
   visualization — it is a mandatory pre-commit checkpoint on the command path.
2. **Approve intent, not keystrokes.** Across minutes of latency, direct teleoperation is
   impossible for most tasks. Operators approve *bounded intent* (goals + envelopes); the edge
   executes autonomously within that envelope. The default interaction model is **supervised /
   adjustable autonomy**, not teleoperation (charter §7).
3. **Reuse the design loop verbatim.** Replanning calls the identical [Mind](mind.md),
   [Allocate](allocate.md), and [Guard](guard.md) components used during design (charter §5,
   conventions.md §1.2 "contribute once, use everywhere"). Operations is the design loop closed
   in real time — not a parallel reimplementation.
4. **Event-sourced truth.** Fleet state is a fold over an append-only, replayable command-and-
   telemetry log (MCAP, conventions.md §4). Any past mission state is reconstructable; every
   command and its provenance are auditable. This is non-negotiable for an operations system.
5. **Degrade, don't collapse.** When comms drop or an asset goes dark, Ops sheds load, falls
   back to last-approved intent and `Guard`'s safe behaviors, and reconciles on reconnect —
   the swarm must survive partition (charter §8, conventions.md §8).
6. **Hard constraints are independent of learned components.** Safety floors (collision,
   power, keep-out) are enforced by [Guard](guard.md) on a path that does not trust any learned
   planner output. Assurance is structurally separate from optimization (conventions.md §9).
7. **Sim-faithful execution.** What ran in design must run identically in ops: the same SADF
   assets, the same Core Environment/Policy contracts, the same scenario semantics. The only
   thing that changes between "shadow against sim" and "command real hardware" is the
   [Bridge](bridge.md) backend behind a stable interface.
8. **Latency is a first-class input.** Earth-link windows, latency, and bandwidth from
   [Link](link.md) parameterize the approval workflow, command batching, and how far ahead the
   shadow twin must predict. The comms model is part of the control logic, not an afterthought.
9. **Library first, console second** (conventions.md §1.4). The orchestration runtime is an
   importable engine you can drive headless (CI, replay, analog field tests) before it is a
   web console for human operators.

---

## 3. Application architecture

Ops is a **stateful, long-running service** (unlike most components, which default to stateless
library-first). It is built from an importable orchestration engine plus the services and
console that deploy it.

```
astro_mine.ops
├── orchestrator/      # the runtime core: campaign loader, execution engine, command path
│   ├── engine/        # durable workflow execution (long-horizon, resumable, event-sourced)
│   ├── command/       # command lifecycle: propose → vet → assure → approve → dispatch → ack
│   └── eventlog/      # append-only command-&-telemetry log (event sourcing, MCAP-backed)
├── estimator/         # fleet-wide state estimation
│   ├── fusion/        # multi-sensor fusion per asset (EKF/UKF), comms-aware
│   ├── collab/        # collaborative localization / multi-robot SLAM (factor graph)
│   └── beliefs/       # fused belief store, with explicit uncertainty (conventions.md §1.6)
├── monitor/           # deviation, constraint, resource, anomaly, and health monitors
├── replanner/         # online replanning orchestration (calls Mind/Allocate; gates via Guard)
├── shadow/            # digital-twin manager: runs/syncs a Sim instance; plan-vetting gate
├── hitl/              # supervisory model: intent approval, override, adjustable autonomy, ToA
├── console_api/       # REST/OpenAPI + gRPC backend for the operator console & View
├── adapters/          # Bridge client (ROS 2/DDS), Link window provider, Hub artifact loader
└── store/             # Postgres/TimescaleDB (durable), Redis (live state), object store refs
```

### Key abstractions exposed

- **Mission session** — a running campaign instance: its plan, fleet roster (SADF assets via
  [Fleet](fleet.md)), bound world ([Worlds](worlds.md)/[Prospect](prospect.md)/[Link](link.md)),
  current belief state, the event-log stream, and the shadow-twin handle. Reconstructable from
  the event log alone. **Multi-regime (RFC-0001):** a session may span an ordered set of phases;
  it then carries the active phase, its regime, and the bound environment for that phase.
- **Phase executor (RFC-0001)** — the per-phase operational sequencer: it runs the live phase,
  evaluates its entry/exit conditions against the fleet belief, emits the typed `PhaseTransition`
  handoff, and re-binds the world/autonomy posture for the successor regime. It is the
  operations-side mirror of [Sim](sim.md)'s scenario-runtime sequencer (mechanism); the
  ordering and contingency *policy* it follows is authored in [Studio](studio.md).
- **Command-intent envelope** — the unit an operator approves: a goal + spatiotemporal/resource
  envelope + an expiry + the autonomy level granted. The Core Policy/Planner contract's
  "assignments/actions" are the body; Ops wraps them in approval, provenance, and a `Guard`
  clearance token.
- **Fleet belief** — the fused, uncertainty-carrying estimate of every asset's pose, health,
  power/thermal budget, and task progress, plus inter-asset relative-pose constraints. Consumed
  by monitors, the replanner, the shadow twin, and [View](view.md).
- **Vetting verdict** — the shadow twin's prediction for a candidate plan (outcome, constraint
  margins, uncertainty) plus the `Guard` clearance, which together gate commit.

### Extension/plugin points

Ops itself adds few plugins; it composes the platform's existing ones through Core contracts:

- **State-estimation backend** — the fusion/collab estimator is pluggable (factor-graph vs
  filtering vs learned; §11) behind a `FleetEstimator` interface.
- **Planner/allocator/shield** — discovered via the Core registry exactly as in design; Ops
  pins specific [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md) plugin versions per
  mission for reproducibility.
- **Shadow-twin fidelity profile** — which [Sim](sim.md) fidelity tier the shadow runs at is a
  plugin-selectable policy (interactive-fast for liveness vs high-fidelity for high-risk plans).
- **Bridge backend** — sim vs hardware vs a specific flight stack, selected behind the
  [Bridge](bridge.md) interface with no change to the orchestrator.

### Interaction patterns

The **command path** is the spine: `propose` (Mind/Allocate produce a candidate) → `vet` (the
shadow twin simulates it forward from current belief) → `assure` ([Guard](guard.md) clears hard
constraints) → `approve` (operator signs the intent envelope, latency-aware) → `dispatch`
([Bridge](bridge.md) over ROS 2/DDS) → `ack/telemetry` (folds back into the event log and
belief). The **monitor loop** runs continuously, comparing telemetry-derived belief against the
shadow twin's prediction; a flagged deviation re-enters the command path at `propose`.

---

## 4. Application programming & runtime platforms

- **Languages.** Python 3.12+ for the orchestration engine, monitors, replanner orchestration,
  HITL logic, and console backend (conventions.md §2). The collaborative-SLAM/factor-graph
  estimator's hot inner loops are **C++20** behind Pybind11 (it sits on the live telemetry
  path). **Rust** is recommended for the command-dispatch / clearance-token path that touches
  actuation — the highest-assurance code in Ops shares the safety-critical posture of
  [Guard](guard.md)/[Bridge](bridge.md) (conventions.md §2, §9). Console front-end is
  **TypeScript + React** (conventions.md §2), integrating OpenMCT and [View](view.md).
- **Estimation libraries.** **GTSAM** (factor graphs / iSAM2 for incremental collaborative
  SLAM) is the recommended backend; **Ceres** as an alternative bundle/optimizer; classical
  **EKF/UKF** (FilterPy-style, or a typed in-house filter) for the per-asset fusion layer.
  SPICE/PROJ-resolved planetary frames throughout (conventions.md §5 — no implicit WGS84).
- **Workflow/runtime.** A durable, event-sourced orchestration engine (§11): the recommendation
  is an **event-sourced/CQRS core** with a **Temporal** durable-execution backbone for the
  long-horizon, resumable campaign workflow. Async eventing inside the ground segment uses
  **NATS + JetStream** (conventions.md §4); the real-time robotics plane is **ROS 2/DDS** via
  [Bridge](bridge.md).
- **Shadow twin.** A standard [Sim](sim.md) instance driven through the Core Environment API; no
  special-cased fork.
- **APIs.** External/console surface is **REST + OpenAPI 3.1 via FastAPI**; internal
  service-to-service is **gRPC** over HTTP/2; high-rate telemetry uses FlatBuffers/Cap'n Proto
  encodings (conventions.md §3). GraphQL only where the console's query shape demands it.
- **Build/packaging.** Python wheel `astro-mine-ops`; OCI images for the orchestrator,
  estimator, shadow-manager, and console-backend services; the React console as a static
  bundle. SemVer; declares the Core interface major versions it supports (conventions.md §7,
  §13).

---

## 5. Data architecture

Ops is data-heavy and is the platform's canonical example of **time-series + relational + live
cache** (conventions.md §5).

| Data | Format / store | Notes |
|---|---|---|
| **Command-&-telemetry event log** | **MCAP** (conventions.md §4) | The system of record. Heterogeneous, timestamped, schema-tagged channels: commands, approvals, telemetry, beliefs, verdicts. Append-only; replayable; the source for event sourcing. |
| **High-rate operational telemetry / time-series** | **TimescaleDB** | Hypertables for live queries over pose/power/thermal/health histories ([View](view.md) dashboards, monitors). |
| **Mission/session metadata, audit trail, approvals** | **PostgreSQL** (+ **PostGIS**) | Sessions, plan/version lineage, operator approval ledger, anomaly records, geospatial keep-outs. |
| **Live fleet belief & ephemeral session state** | **Redis** | The hot belief snapshot, command-in-flight tracking, distributed locks; rebuildable from the event log. |
| **Tabular results / post-mission analysis** | **Apache Parquet** (Arrow in-memory) | Exported runs for [Bench](bench.md)-style scoring of operational campaigns. |
| **Large artifacts** (plans, recordings, policies) | **S3-compatible object store**, content-addressed | Pulled from [Hub](hub.md); recordings archived for replay/analog-test review. |
| **Live metrics** | **Prometheus** | Service health/SLOs (distinct from mission telemetry). |

**Schemas.** Commands, telemetry, beliefs, and approvals are Core message types (Protobuf
canonical; FlatBuffers/Cap'n Proto for per-tick telemetry — conventions.md §3). Assets are SADF
([Core](core.md)/[Fleet](fleet.md)); spatial state carries explicit planetary CRS/frames.

**Lifecycle.** Live state in Redis → durable history in Timescale/Postgres → cold MCAP/Parquet
in object storage. Approval and clearance records are retained for the mission's full audit
lifetime.

**Provenance & versioning.** Every command records its full lineage: which plan version, which
[Mind](mind.md)/[Allocate](allocate.md) plugin + version produced it, which shadow-twin verdict
and [Guard](guard.md) clearance gated it, which operator approved it, the belief snapshot it was
computed from, and the seed/env lockfile of the vetting run (conventions.md §5). This is what
makes an operations decision auditable and a mission reproducible.

---

## 6. Integration architecture

Ops is the hub of the **operations loop** (charter §5) and integrates almost the entire stack
through Core contracts — never private side-channels (conventions.md §1.1):

- **Consumes** a validated campaign + fleet roster (SADF) + bound world from
  [Studio](studio.md), referenced through [Hub](hub.md) by content hash.
- **Runs** a [Sim](sim.md) instance as the **shadow twin** via the Core Environment API —
  identical to design-time sim, just driven from the live belief and run ahead of reality.
- **Calls** [Mind](mind.md) (mission/task-and-motion planning) and [Allocate](allocate.md)
  (assignment/scheduling) through the Core Policy/Planner API to replan — the same components,
  same versions, as design (charter §5).
- **Gates** every candidate through [Guard](guard.md): no plan is dispatched without a `Guard`
  clearance, enforced independently of the planners (conventions.md §9).
- **Drives** real hardware or the simulator through [Bridge](bridge.md) over the **ROS 2/DDS**
  data plane (conventions.md §4) — `Bridge` is the boundary between Ops and the robotics/flight
  plane; the backend swap (sim ↔ cFS/F´/CCSDS) is invisible to the orchestrator.
- **Streams** telemetry, beliefs, and plan explanations up to [View](view.md) (Cesium/3D Tiles,
  OpenMCT) for human supervision.
- **Reads** comms geometry, latency, bandwidth, and Earth-link windows from [Link](link.md) to
  drive approval timing, command batching, and shadow look-ahead.
- **Depends on** [Core](core.md) for SADF, the Environment and Policy/Planner contracts, and
  message schemas; uses [Worlds](worlds.md)/[Prospect](prospect.md) as the bound world model.

**Multi-phase mission operations (RFC-0001).** For multi-regime missions, Ops consumes a
validated `MissionSpec` from [Studio](studio.md) (referenced via [Hub](hub.md) by content hash)
and runs its phases live through the phase executor, which **mirrors [Sim](sim.md)'s
scenario-runtime sequencer mechanism** (RFC-0001 R2): it performs each `PhaseTransition` handoff
on the Core Environment API and applies cross-phase replanning policy authored in
[Studio](studio.md). The shadow twin is multi-regime — it spans transit, proximity, and surface
phases and **vets each phase's plan via [Sim](sim.md) before commit**, switching the bound
environment ([Worlds](worlds.md) / Transit) per phase. The invariants are unchanged: every
dispatch still requires a [Guard](guard.md) clearance (now also gating phase transitions), and
all actuation goes through [Bridge](bridge.md). Latency, light-time, and Earth-link windows for
the active regime come from [Link](link.md). See the [mission-model](mission-model.md) for the
Mission/Phase/Regime schema.

**Message flows.** Control plane (propose/vet/approve, plugin calls): **gRPC**. Ground-segment
eventing (anomaly fan-out, monitor triggers): **NATS/JetStream**. Robot/flight data plane
(commands, telemetry): **ROS 2/DDS** via [Bridge](bridge.md). Recorded streams: **MCAP**.

---

## 7. Infrastructure & deployment

Ops is the canonical inhabitant of the **operations/ground tier** (conventions.md §7,
deployment tier 3): `Ops` + [Bridge](bridge.md) + [View](view.md) near operators, on the ROS
2/DDS data plane.

- **Deployment locus (split, §11).** A **ground-segment** deployment hosts the orchestrator,
  estimator, shadow twin, monitors, console, and stores. An **edge/onboard-analog** deployment
  hosts a thin executor that runs last-approved intent within its envelope under
  [Guard](guard.md) when the link is degraded — the delay-tolerant half of the model. The
  shadow twin always runs on the ground (it is compute-heavy).
- **Containerization & orchestration.** OCI images; **Kubernetes** for the ground segment
  (conventions.md §7). The shadow twin schedules onto the same GPU-capable
  Sim/[Cloud](cloud.md) substrate (KubeRay + NVIDIA GPU Operator) so it can run at meaningful
  fidelity ahead of real time.
- **Compute.**
  - *Orchestrator/monitors/console:* CPU-bound, modest memory; horizontally scalable stateless
    services with state in Postgres/Timescale/Redis.
  - *Estimator (collab SLAM/factor graph):* CPU-heavy, memory grows with map/graph size;
    incremental (iSAM2) to bound per-update cost; partitionable per region/sub-swarm.
  - *Shadow twin:* a full [Sim](sim.md) workload — GPU-accelerated, multi-fidelity; the heaviest
    Ops dependency, sized to keep ahead of wall-clock at the chosen fidelity.
- **Local/dev tier (must always work — conventions.md §7).** `docker compose` brings up
  orchestrator + Postgres/Timescale + Redis + a sim-backed [Bridge](bridge.md) so a developer
  runs a supervised mission end-to-end on a workstation, no hardware required.

---

## 8. Performance & scalability

**Targets (Phase-2 analog scale).**

- Supervise **tens to ~hundreds** of heterogeneous assets (charter §4.4) from one console.
- **Belief update:** sub-second fused-state update per asset at telemetry cadence; collaborative
  graph optimization incremental and bounded (iSAM2), not full re-batch.
- **Command-path latency (ground compute):** propose → vet → assure under a few seconds for
  routine replans, so it is dominated by the *comms* delay ([Link](link.md)), not Ops overhead.
- **Shadow twin:** runs *ahead of* real time at its chosen fidelity, so a verdict precedes
  commit. Look-ahead horizon scales with Earth-link latency.

**Bottlenecks & mitigations.**

- *Collaborative SLAM scaling* — global factor graphs grow super-linearly. Mitigate with
  incremental smoothing (iSAM2), region/sub-swarm graph partitioning, and sliding-window
  marginalization.
- *Shadow-twin keeping pace* — high fidelity may not stay ahead of real time. Mitigate with the
  multi-fidelity dial (conventions.md §8): interactive surrogate ([Surrogate](surrogate.md)) for
  routine vetting, high-fidelity reserved for high-risk plans; raise fidelity when latency
  budget allows.
- *Replan storms under cascading anomalies* — many monitors firing at once. Mitigate with
  back-pressure, anomaly debouncing/coalescing, and priority-tiered command queues
  (conventions.md §8 "back-pressure & graceful degradation").
- *Telemetry firehose* — zero-copy FlatBuffers/Cap'n Proto on the per-tick path; Timescale
  hypertable compression; bounded, load-shedding streaming to [View](view.md).

**Scaling strategy.** Stateless orchestrator/monitor/console replicas behind a load balancer,
state externalized (conventions.md §8). The estimator partitions by region/sub-swarm. The
shadow twin scales out onto Ray/K8s like any [Sim](sim.md)/[Cloud](cloud.md) job. Graceful
degradation is a scalability property here: under comms partition, Ops *sheds* coordination to
the edge rather than overloading the link.

---

## 9. Security, safety & compliance

This is a **safety-critical operations path** (conventions.md §9, §12) — held to the highest bar
alongside [Guard](guard.md) and [Bridge](bridge.md).

- **AuthN/AuthZ.** OIDC (Keycloak/cloud IdP); **RBAC via OPA** (conventions.md §9). Operator
  roles are fine-grained: who may *approve* an intent, who may *override* a shield, who may raise
  an autonomy level, who may command which assets — each an auditable OPA decision.
- **The command path is the trust boundary.** Every dispatched command carries a signed
  approval + a [Guard](guard.md) clearance token + a shadow verdict reference. The dispatcher
  refuses any command lacking a valid clearance — assurance enforced *independently* of the
  planners that proposed it (conventions.md §1, §9). Two-person rule available for high-risk or
  shield-override actions.
- **Service-to-service.** **mTLS** everywhere (conventions.md §9). Secrets via External Secrets
  Operator + Vault/KMS — none in images or repos.
- **Isolation.** Plugin planners/policies (Mind/Allocate) run under the platform's plugin
  isolation; untrusted ones run out-of-process/sandboxed (conventions.md §7, §9). The shadow
  twin executes in a sandbox; its verdicts inform but never directly actuate.
- **Safety model.** Last-approved-intent + `Guard` safe behaviors are the fallback under comms
  loss; envelopes carry expiry so stale intent cannot run unbounded. Hard floors (collision,
  power, keep-out) are `Guard`'s and are never delegated to a learned component.
- **Supply chain.** Signed OCI artifacts (Sigstore/cosign), SLSA provenance, SBOMs; org
  defaults (Dependabot, secret scanning, push protection) on (conventions.md §9).
- **Export control / dual use.** Ops is flagged in conventions.md §12 as export-sensitive.
  Posture: the open core operates against the **simulator and terrestrial analogs**; the
  software is general supervisory orchestration, not flight-certified or weaponizable targeting.
  Adapters to specific real flight assets and any genuinely sensitive operational capability are
  **partitioned** into separate, access-controlled repos with a documented EAR/ITAR posture
  (charter §9.5, conventions.md §12). Capability gating (Core capability tags + OPA) is
  first-class, not a bolt-on.

---

## 10. Observability & operability

- **Telemetry.** OpenTelemetry SDK across every Ops service (conventions.md §10). A single
  replan is **traceable end-to-end** — propose ([Mind](mind.md)) → allocate
  ([Allocate](allocate.md)) → vet ([Sim](sim.md) shadow) → assure ([Guard](guard.md)) → approve
  → dispatch ([Bridge](bridge.md)) — exactly the distributed trace conventions.md §10 calls out.
- **Metrics & dashboards.** Prometheus + Grafana for service SLOs; mission telemetry lives in
  Timescale and is surfaced operationally through [View](view.md)/OpenMCT (distinct from
  service-health Grafana).
- **Logs.** Structured JSON via Loki (conventions.md §10). The MCAP event log is the
  *mission-level* record, separate from service logs.
- **Replay-as-debugging.** Because the engine is event-sourced, any anomaly is reproduced by
  replaying the log into the orchestrator and shadow twin — the primary operability tool.
- **Testing & validation.**
  - *Unit/integration:* `pytest`; Hypothesis for state-machine and constraint invariants;
    `gtest` for the C++ estimator (conventions.md §11).
  - *Determinism gates:* seeded replays of recorded missions compared to stored references; CI
    fails on non-reproducibility (conventions.md §11).
  - *Estimator validation:* against simulated ground truth from [Sim](sim.md) and against
    recorded analog field data, with explicit error budgets on pose/uncertainty.
  - *Contract tests:* Ops proves it honors the Core Environment/Policy/message interface
    versions it consumes (consumer-driven, conventions.md §11).
  - *Latency-fault tests:* injected comms delay/dropout ([Link](link.md) models) to verify
    delay-tolerant fallback, envelope expiry, and reconnect reconciliation.
  - *Shadow-fidelity tests:* verify that lowering shadow fidelity for liveness does not let an
    unsafe plan slip past the `Guard` gate.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Orchestration runtime architecture** | Event-sourced/CQRS; actor model (Ray actors / Akka-style); workflow engine (Temporal, Argo) | **Event-sourced/CQRS core + Temporal durable-execution backbone** — event sourcing gives the audit/replay/reconstruct property operations demands; Temporal gives resumable long-horizon workflows. Actors used *within* services where they fit, not as the system spine. |
| **State-estimation backend** | Factor graphs (GTSAM/iSAM2); filtering (EKF/UKF); learned estimator | **Factor-graph collaborative SLAM (GTSAM/iSAM2) for the fleet-level map + EKF/UKF for per-asset fusion**; a learned front-end (place recognition/odometry) is pluggable. Factor graphs handle multi-robot relative constraints and loop closure in feature-poor terrain natively (charter §7). |
| **Shadow-twin sync & vetting gate** | Continuous lock-step twin; on-demand vet per replan; ahead-of-time predictive twin | **Predictive twin run ahead of real time + a mandatory on-demand vet at each commit.** Continuous lock-step is too costly at fidelity; the twin predicts forward from the live belief and every replan must clear a fresh vet before dispatch. |
| **Shadow-twin fidelity** | Always high-fidelity; always surrogate; adaptive | **Adaptive multi-fidelity** (conventions.md §8): [Surrogate](surrogate.md) for routine vetting to stay ahead of real time; escalate to high-fidelity [Sim](sim.md) for high-risk/low-margin plans. |
| **HITL supervisory model** | Direct teleoperation; supervised autonomy; adjustable/sliding autonomy | **Adjustable autonomy with intent-envelope approval** as default; teleoperation only for short-latency analog/contingency cases. Operator approves bounded intent; edge executes within it (charter §7). |
| **Phase-gated autonomy posture (RFC-0001)** | Fixed posture all mission; per-phase manual; **regime-gated automatic ratchet** | **Regime-gated ratchet:** the autonomy level steps up automatically for high-latency deep-space phases (`interplanetary_transit`/`proximity_orbit`) — the operator approves an intent envelope over tens-of-minutes light-time and the onboard-analog/edge executes it; it steps back down for low-latency surface/analog phases. Posture is bound to the phase's regime and re-evaluated at each `PhaseTransition`. |
| **Deployment locus** | Pure ground-station; pure edge/onboard; ground+edge split | **Ground+edge split:** heavy estimation/shadow/replanning on the ground; a thin `Guard`-wrapped intent executor at the edge for delay tolerance (conventions.md §7 tier 3). |
| **Live-state store** | Redis; in-memory only; Postgres only | **Redis** for hot live state, rebuildable from the MCAP event log (conventions.md §5). |
| **Ground eventing** | NATS/JetStream; Kafka; ROS 2 topics for everything | **NATS/JetStream** in the ground segment (conventions.md §4); **ROS 2/DDS only on the robot data plane** via [Bridge](bridge.md). Kafka only if a durable high-throughput replay log at scale is later required. |

**Open questions / research dependencies (charter §7, §8).**

- **Delay-tolerant supervisory autonomy** — the interaction/trust model for one operator over
  many robots across minutes of latency is an open research problem; the intent-envelope model
  is a starting hypothesis to validate on analogs (charter §7).
- **Swarm state estimation in GNSS-denied, feature-poor terrain** — collaborative localization
  where landmarks are scarce and absolute positioning is unavailable (charter §7); co-designed
  with [Sim](sim.md)'s sensor models and [Worlds](worlds.md).
- **Verifiable assurance under latency** — how strong a guarantee the shadow+`Guard` gate can
  give for learned plans with no recovery and minutes of delay (charter §8); co-designed with
  [Guard](guard.md).
- **Sim-faithful shadow** — quantifying the sim-to-real gap of the shadow twin so a vet verdict
  is trustworthy; the sim-to-real credibility problem (charter §8, conventions.md §1.6),
  bounded with [Surrogate](surrogate.md) error tracking.
- **Operational evaluation science** — what "good" means for a live multi-week campaign;
  co-designed with [Bench](bench.md) (charter §7).

---

## 12. Roadmap alignment

- **Phase 2 (~30–54 mo) — Operations bridge (charter §10).** Ops ships with [Bridge](bridge.md)
  and [View](view.md) to **cross the simulation-to-operations threshold on Earth analogs**.
  - **MVP:** the orchestration runtime in **digital-twin shadow mode** — execute a
    [Studio](studio.md)-authored campaign against a [Sim](sim.md) backend through
    [Bridge](bridge.md), with fleet-wide state estimation, the command path (propose → vet →
    assure → approve → dispatch), the supervisory console + [View](view.md), and the event-
    sourced MCAP log. The full loop runs with *no real hardware* — sim is the world.
  - **Then:** drive **terrestrial analog rover-swarm field tests** through [Bridge](bridge.md)'s
    ROS 2 backend (charter §10 Phase 2 goal); harden delay-tolerant fallback, the edge executor,
    and reconnect reconciliation against real comms dropout; mature adjustable-autonomy and
    explanation in the console.
- **Phase 3 (54 mo+) — Flight & ecosystem.** Real flight-asset operation via [Bridge](bridge.md)
  adapters (cFS/F´/CCSDS), with the genuinely sensitive/flight-specific capability **partitioned
  out of the open core** per the dual-use posture (charter §9.5, conventions.md §12). The open
  Ops runtime remains the general, sim-and-analog-grade supervisory orchestrator.
  - **Multi-regime mission operations (RFC-0001, Phase 3).** The phase executor, multi-regime
    shadow twin, and phase-gated adjustable autonomy land here; Ops's only Phase-1 obligation is
    that Core reserves the `MissionSpec`/`PhaseTransition` schema hooks the executor consumes
    (RFC-0001 R5). The track is opt-in and must not gate the Phase-2 lunar/analog MVP.

The discipline (charter §11 "scope explosion"): Ops must resist re-implementing planning,
physics, or safety. Its job is to *orchestrate* the components that already exist — that
restraint is what keeps the operations runtime thin and the platform an ecosystem.
