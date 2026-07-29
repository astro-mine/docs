# Astro-Mine-Bridge — Technology Architecture

> Layer: **Design & operations** (operations runtime, online mode) · Phase: **2** (flight-software integration matures in Phase 3)
> **Designed, not built.** Ships in: [`astro-mine-platform`](platform.md), as a new subpackage · Extended for multi-regime missions (Phase 3)
> The hardware and flight-software abstraction layer. The boundary between Astro-Mine's planes and the ROS 2/DDS + flight-software world.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Bridge` is the **embodiment layer**: it makes a single committed plan drive *either*
the simulator *or* real flight hardware, without anything above it knowing which. It is a
collection of **adapters** that translate the [Core](core.md) command/action and telemetry
message schemas to and from external robotics and flight-software stacks, and a **switch** that
selects the target backend for an otherwise identical plan.

Concretely, Bridge does:

- **Egress (commands down):** consume [Guard](guard.md)-assured, [Ops](ops.md)-committed action
  and command messages (Core schemas) and emit them as native ROS 2 topics/actions/services,
  cFS Software Bus messages, F´ commands, or CCSDS telecommand (TC) frames.
- **Ingress (telemetry up):** receive native telemetry from the same stacks and normalize it
  back into Core telemetry/state messages for [Ops](ops.md) and [View](view.md).
- **Target selection:** a single configuration switch routes the *same* committed plan to
  [Sim](sim.md) (digital-twin / today) or to real hardware (later), so sim-validated and
  flown plans are byte-for-byte the same artifact.
- **Time, frame & unit translation:** reconcile Astro-Mine's SPICE-backed TDB/ET clocks and
  body-fixed frames (conventions.md §5) with each stack's clock and frame conventions.
- **Link-aware delivery:** back-pressure, store-and-forward, and store-and-replay for the
  delayed, intermittent links modeled by [Link](link.md) and met for real in operations.

**Explicitly out of scope** (these matter — they are the dual-use boundary):

- **No certification-grade flight-code or targeting generation.** Bridge does *not* synthesize,
  optimize, or emit certifiable flight software, guidance/targeting solutions, or trajectory
  burns for real vehicles. That is the deliberately excluded P3 capability (charter §9.5, §9.5). Bridge *transports and translates* plans produced upstream; it does not *author*
  operational targeting.
- **No planning, allocation, or autonomy.** Decisions come from [Mind](mind.md),
  [Allocate](allocate.md), [Learn](learn.md); assurance from [Guard](guard.md); commitment from
  [Ops](ops.md). Bridge is mechanism, not policy.
- **No physics.** The simulator is [Sim](sim.md); Bridge merely speaks to it like any backend.
- **No mission-control UI.** That is [View](view.md) (OpenMCT/Cesium).

**Deep-space stacks & the targeting boundary.** Multi-regime missions add
*operational-phase* flight-stack and protocol adapters for the long-delay, deep-space phases —
**DSN telecommand/telemetry**, **CCSDS** (including **CFDP** for file transfer) and **DTN / Bundle
Protocol (BPv7)** for delay-tolerant links — alongside the existing ROS 2 / cFS / F´ adapters.
This is purely more *translation*: it carries plans and telemetry over harder links, it does not
add decisions. Critically, the dual-use line is **reaffirmed, not weakened**: operational
**maneuver targeting** stays **partitioned and excluded** from the open commons. Bridge does
**not** turn [Trajectory](trajectory.md)'s descriptive `TrajectoryRef` reference arcs into
executable guidance for real flight hardware; the reserved `operational_targeting` capability tag
gates this boundary at the registry/Bridge edge ([mission-model.md](mission-model.md) §4).

**Primary users:** flight-software engineers and integrators who write or maintain the adapter
for a given robot/flight stack, and operations engineers who configure the sim-vs-hardware
target.

**Charter alignment:** §5.6 (Bridge: "adapters to ROS 2, cFS, F´, and CCSDS, so identical plans
drive either the simulator or real flight hardware … without changing the layers above it"),
§7 ("flight software and protocols" + "ROS 2 / DDS as the interoperability lingua franca"),
§10.5 ("interop-first, and honest about dual use"), and conventions.md §4, §9, §12.

---

## 2. Architecture principles

1. **Hexagonal / ports-and-adapters, strictly.** Bridge has one **port** (the Core
   command/telemetry contract) and many **adapters** (ROS 2, cFS, F´, CCSDS, Sim). The port
   never depends on an adapter; adapters never leak upward. Adding a stack = adding an adapter.
2. **Identical-plan invariant.** The committed plan artifact targeting [Sim](sim.md) and the one
   targeting hardware MUST be the same bytes. The only difference is Bridge configuration. This
   is the whole point of the layer (charter §4.6); it is enforced by test (§8, §10).
3. **Translation, never decision.** Bridge maps representations and rates; it never alters
   intent, re-plans, or relaxes a constraint. Anything that changes *what the swarm does*
   belongs above Bridge. Violating this would silently move targeting capability into the
   open layer — forbidden by §9.
4. **Fail safe, never fail open.** On a mapping failure, schema mismatch, lost link, or
   un-acknowledged command, Bridge withholds, buffers, or escalates to [Ops](ops.md)/[Guard](guard.md)
   — it never invents a command or guesses a value. There are no second chances in space
   (charter §8).
5. **Time and frame are explicit, always.** No command crosses an adapter without an explicit
   epoch (TDB/ET) and reference frame (conventions.md §5). Clock and frame skew are measured,
   bounded, and surfaced — never assumed away.
6. **Link-honest.** Bridge assumes intermittent, delayed, bandwidth-limited links by default
   (charter §7, §7). Back-pressure and store-and-forward are baseline behavior, not an
   add-on; the path degrades gracefully (conventions.md §8).
7. **Capability-partitioned by construction.** The open, default-shipped adapters are sim and
   generic/standard interop (ROS 2, CCSDS basics). Adapters that bind to specific sensitive
   hardware or controlled flight stacks live in **separate, access-controlled repos** and load
   only behind capability gates (§9, conventions.md §12).
8. **Auditable boundary.** Every command Bridge emits and every telemetry frame it ingests is
   logged with provenance (which plan, which Core schema version, which adapter, what epoch),
   because this is the platform's accountability line between the digital and the physical.
9. **Interop over reinvention.** Bridge builds on `ros2`/`rclpy`/`rclcpp`, the cFS Software Bus,
   the F´ ground/uplink interfaces, and existing CCSDS libraries — it does not reimplement
   robotics middleware or flight software (charter §6, conventions.md §1.7).

---

## 3. Application architecture

Bridge is **library-first** (conventions.md §1.4): an importable `astro_mine.bridge` that an
[Ops](ops.md) process embeds, and a thin **bridge daemon** when it must run as a long-lived
co-process near the data plane (e.g., a ROS 2 node lifecycle, a ground station gateway).

```
astro_mine.bridge
├── port/              # the Core-facing contract (the single hexagon port)
│   ├── commands/      #   ingest committed Core action/command messages
│   ├── telemetry/     #   emit normalized Core telemetry/state messages upstream
│   └── lifecycle/     #   target-select, session, health, arm/disarm gating
├── adapters/          # one subpackage per backend (the swappable edges)
│   ├── sim/           #   → Astro-Mine-Sim (digital twin) — default, ships first
│   ├── ros2/          #   → ROS 2 / DDS topics, actions, services (rcl)
│   ├── cfs/           #   → NASA cFS Software Bus (SB) apps/messages
│   ├── fprime/        #   → JPL F´ commands / channelized telemetry
│   ├── ccsds/         #   → Space Packet Protocol, TC/TM, (opt.) CFDP / BP-DTN
│   └── dsn/           #   → DSN telecommand/telemetry for deep-space phases (Phase 3, sensitive → §9)
├── transform/         # shared translation services used by every adapter
│   ├── timebase/      #   SPICE TDB/ET ⇄ stack clocks; correlation & skew
│   ├── frames/        #   SPICE body-fixed/inertial ⇄ stack frames (tf2, etc.)
│   ├── units/         #   SI ⇄ stack units (Core units module, conventions.md §3)
│   └── codec/         #   schema-to-wire mapping registry (per adapter)
├── delivery/          # link-aware delivery semantics
│   ├── backpressure/  #   bounded queues, shed/throttle (conventions.md §8)
│   ├── store_forward/ #   persist-and-replay over delayed/intermittent links
│   └── ack/           #   command receipt/exec acks, idempotency, dedup, retry
├── hil/               # hardware-in-the-loop & software-in-the-loop test harness
└── registry/          # adapter discovery via Core plugin manifests + capability tags
```

### Key abstractions exposed

- **`BridgeTarget`** — a resolved backend (sim | ros2 | cfs | fprime | ccsds-endpoint) plus its
  config (transport, frames, clock source, link profile). The **switch** is "pick a
  `BridgeTarget`"; everything above is unchanged.
- **`Adapter`** — the plugin interface every backend implements: `connect()`,
  `send_command(CoreCommand) -> Ack`, `subscribe_telemetry() -> stream[CoreTelemetry]`,
  `capabilities()`, `health()`. Adapters are [Core](core.md) plugins (manifest + capability
  tags), discovered through the registry (conventions.md §7).
- **`Codec`** — a per-adapter, versioned mapping between a Core message type (a specific Core
  interface version) and the stack's native representation (a ROS 2 `.msg`/`.action`, a cFS SB
  message ID + struct, an F´ command opcode + args, a CCSDS APID + packet layout).
- **`Session`** — an arm/disarm-gated execution context binding a committed plan to a target,
  carrying provenance and the capability assertions required to actuate it.

### Key abstractions consumed

- [Core](core.md) command/action and telemetry **message schemas** (proto3 for control,
  FlatBuffers/Cap'n Proto for per-tick telemetry — conventions.md §3), the **units/frames/time**
  helpers, and the **plugin manifest/registry**.
- [Link](link.md) **comm-window/latency profiles** to parameterize delivery semantics (in
  operations these become real link state).
- [Guard](guard.md) **assurance verdicts** — Bridge will not open a `Session` for a plan that is
  not Guard-cleared (a refusal, not a re-check).

### Extension / plugin points

- **New backend** = new `Adapter` plugin (sensitive ones in access-controlled repos, §9).
- **New robot/payload on an existing backend** = new/extended `Codec` registered against a Core
  schema version.
- **New link profile / delivery policy** = a `delivery` strategy plugin.
- **Deep-space stacks** = additional `Adapter`s (DSN, extended CCSDS/CFDP, DTN/BP)
  behind the *same* hexagon port — no new port, no new decision surface. The very long light-times
  of deep-space phases lean hard on the existing `delivery` (store-and-forward) machinery rather
  than adding new mechanism.

### Interaction patterns

[Ops](ops.md) commits a plan → opens a `Session` against a chosen `BridgeTarget` → streams Core
commands into `port/commands` → Bridge `codec`/`transform` translate → `adapters/*` emit native
egress → backend executes → native telemetry returns through `adapters/*` → normalized in
`port/telemetry` → flows up to [Ops](ops.md) and [View](view.md). Replans from
[Mind](mind.md)/[Allocate](allocate.md) re-enter the same path after [Guard](guard.md).

---

## 4. Application programming & runtime platforms

- **Languages** (conventions.md §2):
  - **Python 3.12+** for the port, orchestration glue, `transform`, `delivery`, registry, and
    the `rclpy`-based ROS 2 adapter — keeps the public API Python-reachable (conventions.md §2
    rule).
  - **C++20** where it must speak native flight/robotics ABIs: `rclcpp` for high-rate ROS 2,
    linking the **cFS** Software Bus, and the **F´** ground interface, plus any hot
    serialization inner loops (Pybind11 bindings up to Python).
  - **Rust** is recommended for the **CCSDS codec** and the `ack`/idempotency/store-forward
    state machine — a high-assurance, memory-safe boundary handling untrusted wire bytes
    (conventions.md §2, §9). It is also the natural place for the capability-gate enforcement.
- **External stacks & libraries** (charter §6):
  - **ROS 2** (Humble/Jazzy LTS) over **DDS** (rmw_cyclonedds default; rmw_fastrtps supported) —
    the interop lingua franca and the operations data plane (conventions.md §4).
  - **NASA core Flight System (cFS)** — Software Bus, cFE, and the standard apps; integrated via
    a cFS bridge app + SB message routing.
  - **JPL F´ (F Prime)** — commands and channelized telemetry via its ground data interface
    (GDS/`fprime-gds`), bound through the F´ uplink/downlink ports.
  - **CCSDS** — Space Packet Protocol (SPP), TC/TM Space Data Link, optionally **CFDP** for file
    transfer and **DTN Bundle Protocol (BPv7)** for delay-tolerant store-and-forward. Built on
    existing libraries where available rather than hand-rolled.
  - **SPICE/NAIF** via the shared **`astro_mine.spice`** foundation ([Spice](spice.md); SpiceyPy under the hood) for time/frame transforms; **tf2** for ROS 2 frame trees.
- **Codegen:** adapter `Codec`s are generated where possible — `buf` for the Core proto side
  (conventions.md §3), and per-stack generators (`rosidl` for ROS 2 `.msg`, cFS message-ID/struct
  tables, F´ XML topologies, CCSDS packet definitions) — so a schema bump regenerates mappings
  and breaking changes are caught in CI.
- **Runtime model:** in-process library inside [Ops](ops.md) for the sim/digital-twin path; a
  **lifecycle-managed daemon** (ROS 2 lifecycle node and/or a gateway service) for the
  operations data plane and ground-station endpoints. Stateless control logic; durable state
  (store-forward queue, ack ledger) externalized (§5).
- **Build/packaging:** ships in the [`astro-mine-platform`](platform.md) wheel; native adapters as OCI images and,
  for ROS 2, a colcon/ament overlay. Open adapters ship in the main package; sensitive adapters
  are **separate, access-controlled OCI artifacts/repos** (§9, conventions.md §7, §12).

---

## 5. Data architecture

Bridge owns **mappings and delivery state**, not domain data.

- **Owned:**
  - **Codec map registry** — versioned bindings from Core schema versions to each stack's native
    representation (ROS 2 type, cFS msg-ID/struct, F´ opcode, CCSDS APID/layout). Authored as
    declarative specs (YAML/JSON validated by JSON Schema, conventions.md §3) plus generated
    code; itself **content-addressed and versioned** so a replay reproduces the exact mapping.
  - **Store-and-forward queue** — durable, ordered, idempotent command buffer for delayed links.
  - **Ack ledger** — command-receipt/exec acknowledgements, retries, and dedup keys.
- **Produced:**
  - **Boundary recording** — every command emitted and telemetry frame ingested, written as an
    **MCAP** stream (conventions.md §4) with heterogeneous, timestamped, schema-tagged channels.
    This is the authoritative record of what actually crossed the digital/physical line and is
    the substrate for replay, post-mortem, and HIL/SIL comparison.
  - **Normalized Core telemetry** for [Ops](ops.md)/[View](view.md); operational metrics
    (latencies, queue depth, ack rates, clock skew) to **Prometheus/TimescaleDB**
    (conventions.md §5, §10).
- **Consumed:** Core command/action/telemetry messages; [Link](link.md) profiles; [Guard](guard.md)
  verdicts; SPICE kernels (SPK/PCK/LSK/FK) for time and frame transforms.
- **Formats:** proto3 for control-plane commands; FlatBuffers/Cap'n Proto for per-tick
  telemetry payloads (conventions.md §3); **MCAP** for recordings; SPP/TC/TM frames on the
  CCSDS wire.
- **Storage & lifecycle:** durable queue + ack ledger in **PostgreSQL** (or Redis for ephemeral
  fast paths) (conventions.md §5); MCAP recordings to the **S3-compatible content-addressed
  object store** (MinIO/S3) with a retention policy — operations recordings are retained for
  audit and sim-to-real validation. SPICE kernels are pinned and content-addressed for
  reproducibility.
- **Provenance & versioning (conventions.md §5, §13):** every recorded command carries its
  source plan hash, the Core schema version, the codec-map version, the adapter version, and the
  epoch — so any flown command is traceable to the committed (and Guard-cleared) plan that
  produced it. SemVer on codec maps; the Core interface major versions an adapter supports are
  declared in its manifest.

---

## 6. Integration architecture

Bridge sits at the bottom of the operations loop (charter §5), between the platform's planes and
the robots/flight stacks.

- **Upstream — invoked by [Ops](ops.md):** [Ops](ops.md) commits a plan that
  [Guard](guard.md) has assured, then drives it through Bridge. Bridge consumes the
  [Core](core.md) command/action schemas and returns normalized telemetry/state up to
  [Ops](ops.md) (for replan/monitoring) and to [View](view.md) (for human supervision via
  OpenMCT/Cesium). Replans from [Mind](mind.md)/[Allocate](allocate.md) re-enter via the same
  [Guard](guard.md) → [Ops](ops.md) → Bridge path.
- **Downstream — two interchangeable targets:**
  - **[Sim](sim.md)** (today / Phase 2): the `sim` adapter speaks to the [Sim](sim.md)
    Environment API so [Sim](sim.md) runs as the **digital-twin shadow** [Ops](ops.md) vets
    plans against before commitment (charter §4.6, §4).
  - **Real flight hardware** (Phase 3): ROS 2/DDS robots, or vehicles fronted by cFS / F´, and
    ground links via CCSDS — selected by the same switch.
- **Core interfaces used:** the command/action and telemetry **message schemas**, the
  **units/frames/time** conventions, and the **plugin manifest/registry** for adapter discovery
  and capability gating ([Core](core.md) §3, §6; conventions.md §3).
- **Protocols & planes:** Bridge **is** the boundary to the **ROS 2 / DDS real-time data plane**
  (conventions.md §4). Internally it is reachable via **gRPC** (control plane) from [Ops](ops.md)
  when run as a daemon; recorded streams are **MCAP**.
- **Sibling boundaries it does *not* cross:** it never calls [Mind](mind.md)/[Allocate](allocate.md)/
  [Learn](learn.md) directly (no decisions), never bypasses [Guard](guard.md), and exposes no
  side-channel that skips the Core contract (conventions.md §1.1).

---

## 7. Infrastructure & deployment

- **Deployment tier (conventions.md §7):** primarily **Tier 3 — Operations / ground** (`Ops` +
  `Bridge` + `View` near operators, ROS 2/DDS data plane) and, in Phase 3, **Tier 4 —
  flight-adjacent** (cFS/F´ adapters, mostly out of open scope). The **sim path also runs in
  Tier 1 (local/dev)** so a researcher can exercise the identical-plan switch on a workstation.
- **Compute:** modest and **CPU-bound** — Bridge is I/O and translation, not physics or ML. A
  few cores and low-GB memory per bridge daemon; **no GPU**. Heavy lifting (the twin) is
  [Sim](sim.md). Latency and jitter matter far more than throughput.
- **Containerization:** OCI images (conventions.md §7); the ROS 2 adapter as an ament/colcon
  overlay image. Real-time paths may pin CPUs / use a low-latency kernel and run outside the
  default scheduler.
- **Orchestration:** **Kubernetes** for the ground/cloud-adjacent daemons and gateways; ROS 2
  lifecycle for node bring-up. Flight-adjacent (Tier 4) deployments run on the target's own
  runtime (cFS/F´), reached through a controlled gateway — **not** scheduled by K8s.
- **Topology & scaling:** one bridge instance (or sharded set) per **fleet segment / link** —
  e.g., per relay orbiter or per ground-station endpoint — so back-pressure and store-forward
  are bounded per link (charter §4.3, [Link](link.md)). Horizontal scale is by partitioning
  assets/links across instances; each instance is otherwise stateless with durable state
  externalized (§5).
- **Deployment placement (export-relevant):** sensitive hardware adapters deploy only in
  controlled environments (operator/integrator premises, access-gated registries); the open
  build deploys anywhere (§9).

---

## 8. Performance & scalability

- **Targets:**
  - **Control-plane command path** (commit → native egress, excluding link delay): **sub-10 ms**
    p99 translation overhead for typical commands.
  - **Telemetry ingest:** keep up with per-tick swarm telemetry — target **tens of kHz aggregate
    messages/s** per instance using zero-copy FlatBuffers/Cap'n Proto decode (conventions.md §3),
    bounded by DDS/transport, not by Bridge.
  - **Clock correlation:** maintain and report TDB/ET ⇄ stack-clock skew within a bounded,
    surfaced error budget; never silently drift.
- **Bottlenecks:**
  - **Serialization/translation** on hot telemetry → zero-copy codecs and C++/Rust on those
    paths.
  - **DDS QoS / discovery** at swarm scale → tuned QoS profiles, partitions, and Zenoh/DDS
    bridging for WAN segments.
  - **Delayed links** → the store-and-forward queue is the buffer that absorbs minutes of latency
    and outages; queue depth is a first-class SLO.
- **Mitigations & strategy (conventions.md §8):** bounded queues with **back-pressure** and load
  shedding on telemetry; **store-and-forward** with idempotent, ordered, ack'd delivery on
  commands; **graceful degradation** — when a link drops, Bridge buffers and surfaces the
  outage, it does not stall the whole operation or fabricate state. Scale **horizontally** by
  per-link/per-segment instances; everything stateless behind durable queues. Every adapter
  ships representative benchmarks (conventions.md §8 "measure before optimizing").

---

## 9. Security, safety & compliance

Bridge is the platform's **principal export-control / dual-use boundary** and its physical
actuation line. This section is deliberately the most thorough (charter §9.5; conventions.md §9,
§12).

### Capability partitioning (the core posture)

- **Open by default:** the **sim adapter**, the **generic ROS 2/DDS adapter**, and **standard
  CCSDS handling** ship in the open package. These are the science/simulation/coordination
  commons (conventions.md §12).
- **Partitioned and access-controlled:** adapters that bind to **specific sensitive hardware**,
  **controlled flight stacks**, or particular mission targets live in **separate, access-gated
  repositories and registries**. They are discovered only when their capability tags
  ([Core](core.md) §9) are satisfied and an **OPA** policy authorizes the requesting identity at
  load/`Session`-open time (conventions.md §9).
- **Explicit exclusion (out of scope):** Bridge does **not** generate certification-grade flight
  code, guidance/targeting solutions, or burn/maneuver synthesis for real vehicles — the
  excluded P3 capability (charter §9.5, §9.5). This is enforced architecturally: Bridge has no
  planner/solver and the principle "translation, never decision" (§2.3) is a contract test, not
  just a guideline. Genuinely sensitive operational targeting is therefore *structurally* absent
  from the open layer, not merely discouraged.
- **Deep-space adapters & operational targeting.** The new deep-space stacks add
  *links*, not *decisions*: Bridge still never converts [Trajectory](trajectory.md)'s descriptive
  `TrajectoryRef` reference arcs into executable maneuver guidance — operational targeting remains
  **partitioned out of the open commons** and gated by the `operational_targeting` capability tag
  at the registry/`Session` edge ([mission-model.md](mission-model.md) §4). Generic CCSDS
  handling stays open; **DSN, mission-specific, and operational-targeting-adjacent adapters are
  treated as potentially controlled** and live in **access-controlled repos** under the EAR/ITAR
  posture below (conventions.md §12).

### AuthN / AuthZ

- **AuthN:** OIDC (Keycloak / cloud IdP); **AuthZ:** RBAC via **OPA** (conventions.md §9).
  Opening a `Session` (binding a committed plan to a real-hardware target) requires an
  explicit, audited authorization distinct from sim — actuating reality is a privileged action.
- **Arm/disarm gating:** a real-hardware `Session` starts **disarmed**; arming is a separate,
  logged, multi-condition step (Guard-cleared plan present, link healthy, clock correlated,
  capability + RBAC satisfied).

### Isolation & supply chain

- **Service-to-service mTLS** (conventions.md §9). Untrusted/third-party adapters run
  **out-of-process** (gRPC + sandboxed container, seccomp/gVisor; WASM forward-looking) per
  conventions.md §7, §9 — Bridge never loads an unvetted native adapter in-process near the
  actuation path.
- **Supply chain:** signed artifacts (**Sigstore/cosign**), **SLSA** provenance, **SBOM** — and,
  crucially, the **boundary recording (MCAP)** gives a tamper-evident audit trail of every
  command that crossed to a real asset (§5).

### Safety

- **Fail-safe** (§2.4): mapping failure, schema/version mismatch, lost link, missing/expired
  Guard verdict, or clock-correlation loss ⇒ withhold/buffer/escalate, never actuate on a guess.
- **Independent of learned components:** Bridge enforces its boundary checks (capability,
  arm-state, schema validity, frame/epoch presence) independently of any learned policy upstream,
  consistent with the [Guard](guard.md) assurance model (conventions.md §9 "hard constraints
  enforced independently of learned components").
- **Idempotency & no duplicate actuation:** the ack ledger + dedup keys ensure a retried command
  over a flaky link cannot double-actuate hardware.

### Export-control posture (EAR / ITAR)

- Follow `astro-mine/.github` **EXPORT_CONTROL.md** and document Bridge's posture per
  conventions.md §12. The **open commons** (sim, generic interop, CCSDS basics) is intended to be
  EAR-99-grade / publicly available "fundamental research" tooling. **Adapters touching
  controlled hardware, controlled flight software, or specific mission targeting are treated as
  potentially ITAR/EAR-controlled** and kept in access-controlled repos with screened access,
  per-jurisdiction gating, and a documented classification per adapter.
- "Open does not mean naive" (charter §9.5): capability gating, RBAC, and repo partitioning are
  **first-class design elements** of Bridge, not bolt-ons. Each access-controlled adapter repo
  carries its own export classification and access policy.

---

## 10. Observability & operability

- **Telemetry (conventions.md §10):** **OpenTelemetry** traces span the full operations loop —
  a replan is traceable from [Mind](mind.md)/[Allocate](allocate.md) through [Guard](guard.md)
  and [Ops](ops.md) into the exact Bridge command that crossed to the backend (conventions.md
  §10). Structured JSON logs → **Loki**; metrics → **Prometheus/Grafana** (command latency,
  queue depth, ack/timeout rates, clock skew, link state, per-adapter health), with high-rate
  operational series in **TimescaleDB**.
- **The MCAP boundary recording** is the operability cornerstone: a complete, replayable record
  of the digital/physical boundary for live monitoring, post-mortem, and sim-to-real comparison.
- **Health:** standard liveness/readiness; per-`Session` health (link up, clock correlated,
  Guard verdict fresh); SLOs on command latency and store-forward queue depth.
- **Testing & validation strategy:**
  - **Identical-plan conformance test** (the headline gate): the same committed plan is driven
    through the **sim** adapter and through a **HIL/SIL** target; the two boundary recordings
    must match within a declared tolerance. This *proves* charter §4.6 and is a CI gate.
  - **Software-in-the-loop (SIL):** adapters tested against cFS/F´ running in software and a ROS 2
    sim backend.
  - **Hardware-in-the-loop (HIL):** Phase-3 adapters tested against real flight units / engineering
    models behind the access-controlled boundary, with terrestrial analog rover-swarm field tests
    (charter §10 Phase 2 goal).
  - **Contract tests** against [Core](core.md) interface versions (conventions.md §11); codec maps
    fuzzed and **property-tested** (Hypothesis) for round-trip and frame/unit/epoch invariants;
    **golden/determinism** comparisons on recorded boundaries (conventions.md §11).
  - **Fault injection:** simulated link dropouts, delays, reordering, and clock skew to validate
    back-pressure, store-forward, idempotency, and fail-safe behavior.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Adapter architecture** | Monolithic per-stack translators; **per-stack plugins behind one Bridge port (hexagonal)**; codegen-only | **Per-stack plugins behind a common port (hexagonal)** — the only architecture that preserves the identical-plan invariant and clean capability partitioning |
| **Sim-path transport** | **ROS 2 bridge**; **gRPC**; **shared memory** | **gRPC by default** for the sim/digital-twin path (typed, streaming, matches conventions.md §4 control plane); **shared memory** for co-located high-rate twin; ROS 2 used when the twin already lives on the DDS plane |
| **Robotics data plane** | ROS 2/DDS; custom transport | **ROS 2 / DDS** (rmw_cyclonedds default; Zenoh bridge for WAN) — the charter lingua franca (conventions.md §4); not negotiable |
| **CCSDS handling depth** | Minimal SPP only; **SPP + TC/TM**; full stack incl. CFDP + DTN/BP | **SPP + TC/TM as baseline; CFDP and DTN Bundle Protocol (BPv7) added as link delay/file-transfer needs demand** — don't build the full stack before a real link requires it. Deep-space phases are what *demand* CFDP + DTN/BP; the **DSN telecommand/telemetry adapter** that rides on them is a Phase-3, access-controlled addition (§9) |
| **cFS / F´ binding** | Reimplement; **link native (cFS SB app, F´ GDS ports)**; ground-only | **Link native** via a cFS Software Bus bridge app and the F´ ground data interface (charter §6) — interop, not reinvention |
| **Sim-vs-hardware switch** | Build-time flag; **runtime `BridgeTarget` config**; separate binaries | **Runtime `BridgeTarget` selection** with an **identical-plan conformance test** (HIL/SIL) as the CI gate — config differs, the plan bytes do not |
| **Clock / time-sync** | Trust each stack's clock; **SPICE TDB/ET as canonical + measured correlation**; PTP/NTP only | **SPICE TDB/ET canonical**, with measured, bounded, surfaced correlation to each stack's clock (PTP/NTP where the medium allows) — explicit time, never assumed (conventions.md §5) |
| **Hot-path implementation language** | All Python; **C++/Rust on hot/boundary paths + Python control** | **C++ for native ABIs (rclcpp, cFS, F´), Rust for the CCSDS codec & ack/store-forward state machine, Python everywhere else** (conventions.md §2) |
| **Delivery durability store** | In-memory; **Postgres-backed queue + ack ledger**; Kafka log | **Postgres-backed durable queue + ack ledger** (conventions.md §5); Kafka only if a high-throughput replayable command log is later required at scale |

**Open questions / research dependencies:**

- **What is the minimal, durable command/telemetry vocabulary** that maps cleanly onto ROS 2,
  cFS, F´, *and* CCSDS without becoming a leaky god-schema? Co-designed with [Core](core.md)
  (charter §8 "durable abstraction across orbital, surface, manipulation, and ISRU").
- **How tight can the identical-plan conformance tolerance be** between sim and HIL, given
  unavoidable real-world timing/quantization differences? This *is* the sim-to-real credibility
  question (charter §8) localized to the boundary; co-designed with [Sim](sim.md) and
  [Guard](guard.md).
- **Delay-tolerant supervisory semantics** (charter §7): how store-and-forward, acks, and
  arm/disarm should behave under minutes of latency so an operator's intent is neither lost nor
  stale-actuated — co-designed with [Ops](ops.md) and [View](view.md).
- **Export-control classification taxonomy per adapter** — the concrete mapping from capability
  tags to EAR/ITAR posture and access policy; co-designed with governance/export-control
  (conventions.md §12; [Core](core.md) §9).

---

## 12. Roadmap alignment

- **Phase 0–1 (foundation, mostly elsewhere):** Bridge does not ship, but the [Core](core.md)
  command/telemetry **message schemas** and **capability-tag taxonomy** Bridge depends on are
  designed now — Bridge's needs (clean egress mapping, frame/epoch explicitness, capability
  gating) are an input to Core v0.1 so the waist is right before Bridge exists.
- **Phase 2 — Operations bridge (Bridge's debut, charter §10):** ship the **hexagonal Bridge
  port + the `sim` adapter + the generic ROS 2/DDS adapter**, the `BridgeTarget` runtime switch,
  time/frame/unit `transform`, and link-aware `delivery` (back-pressure + store-and-forward).
  This makes [Ops](ops.md)'s **digital-twin shadow mode** real and is validated against
  **terrestrial analog rover-swarm field tests** over ROS 2 — crossing the
  simulation-to-operations threshold on Earth analogs.
  - **MVP:** sim + ROS 2 adapters, runtime switch, the **identical-plan conformance test**
    (sim ↔ SIL), back-pressure + store-and-forward, MCAP boundary recording, OTel/Prometheus
    observability, capability-gated registry.
  - **Later in Phase 2:** baseline **CCSDS SPP + TC/TM** for ground-link analogs; richer link
    profiles from [Link](link.md); HIL harness scaffolding.
- **Phase 3 — Flight & ecosystem (charter §10):** **cFS** and **F´** adapters mature for real
  flight-software integration; **CFDP / DTN-BP** added as real delayed links demand; full
  **hardware-in-the-loop** validation; sensitive hardware/mission adapters delivered through
  **access-controlled repos** under the documented EAR/ITAR posture (§9). The certification-grade
  flight-code/targeting generator remains **permanently out of scope** (charter §9.5, §9.5).
  - **Multi-regime deep-space stacks:** the **DSN telecommand/telemetry**, extended
    **CCSDS/CFDP**, and **DTN/BP** operational-phase adapters land in **Phase 3** (the
    `MissionSpec`/`regime`/`PhaseTransition` Core hooks and the `operational_targeting` capability
    tag Bridge gates on are reserved in **Phase 1**); operational maneuver targeting stays
    partitioned and excluded throughout ([mission-model](mission-model.md) §4).
