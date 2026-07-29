# Phase 2 — Operations bridge

> **Window:** ~30–54 mo · **Theme:** Operations bridge · **Roadmap home:** [README](README.md)
> **Goal:** cross the **simulation-to-operations threshold on terrestrial analogs** — run a
> validated campaign first as a digital-twin shadow, then drive an analog rover swarm (charter §9;
> system.md §11).

**Status: next.** Nothing below is built.

**Entry dependencies:** Phase 1 complete — a closed, scored design loop producing a Studio
[Campaign](../architecture/studio.md); the autonomy stack (Mind/Allocate/Guard) and Sim validated and
publishable. **Met.** Additionally, `RM-DIST-03` and `RM-DIST-04` ([the distribution
track](README.md#the-distribution-track)) should land first: Ops and Bridge arrive as new platform
subpackages, the ops console as a new front-end surface, and both are cheaper to add once the REST and
front-end distributions exist than to add and then move.

**Integration milestones:**

- **M2.1 — Digital-twin shadow mode:** [Ops](../architecture/ops.md) executes a Studio Campaign
  against a [Sim](../architecture/sim.md) backend through [Bridge](../architecture/bridge.md), with
  fleet-wide state estimation, the full command path (propose → vet → assure → approve → dispatch),
  the supervisory console + [View](../architecture/view.md), and the event-sourced MCAP log — **no
  real hardware** (sim is the world).
- **M2.2 — Earth-analog field test:** the same Campaign drives a **terrestrial analog rover swarm**
  over Bridge's ROS 2 backend, with delay-tolerant fallback and reconnect reconciliation hardened
  against real comms dropout.

**Phase exit criteria:** M2.1 + M2.2 met; the **identical-plan invariant** holds (sim and hardware
driven by the same committed plan bytes, verified by conformance test); every dispatched command
carries a [Guard](../architecture/guard.md) clearance + shadow verdict; the design loop and operations
loop demonstrably **share** Mind/Allocate/Guard/Sim (charter §5).

**Cross-cutting this phase — [CX-S2R](README.md#cross-cutting-workstreams):** Phase 2 is where
sim-to-real credibility stops being a claim and gets *measured* — terramechanics validation against
analog field data, and the sim↔HIL/SIL conformance tolerance, are first-class deliverables.

---

## Ops — the orchestration runtime

> Architecture: [ops.md](../architecture/ops.md). **Safety-critical operations path.** Stateful,
> event-driven; the shadow gates the world.

**Scope & deliverables**

- **RM-P2-OPS-01** — **Durable, event-sourced orchestration engine** (event-sourced/CQRS core +
  Temporal backbone): campaign loader, the long-horizon resumable execution engine, and the
  append-only MCAP **command-&-telemetry event log** as the system of record. *(trace: ops.md §3, §11)*
- **RM-P2-OPS-02** — **The command path**: `propose → vet → assure → approve → dispatch → ack`, each
  command carrying plan-version/plugin/verdict/clearance/operator provenance; the dispatcher refuses
  any command lacking a valid Guard clearance. *(trace: ops.md §3, §9; `LUNAR-UX-003`)*
- **RM-P2-OPS-03** — **Fleet-wide state estimation**: factor-graph collaborative SLAM (GTSAM/iSAM2)
  + per-asset EKF/UKF fusion, comms-aware, in GNSS-denied feature-poor terrain; uncertainty-carrying
  **fleet belief**. *(trace: ops.md §3, §11; charter §7; `LUNAR-FR`-adjacent)*
- **RM-P2-OPS-04** — **Digital-twin shadow manager**: a [Sim](../architecture/sim.md) instance run
  *ahead of* real time from the live belief, **vetting every replan before commit** (predictive twin
  + mandatory on-demand vet; adaptive multi-fidelity to stay ahead). *(trace: ops.md §2, §11)*
- **RM-P2-OPS-05** — **Online replanning** through the **same** Mind/Allocate/Guard used in design
  (anomaly/monitor breach → propose). *(trace: ops.md §3, §6; charter §5)*
- **RM-P2-OPS-06** — **Delay-tolerant supervisory model (HITL)**: **intent-envelope approval** with
  expiry + autonomy level, not teleoperation; pre-approved contingency branches for comms-denied PSR
  intervals; fine-grained OPA operator roles + two-person rule for shield overrides. *(trace: ops.md §3, §9, §11; `LUNAR-UX-003`; charter §7)*
- **RM-P2-OPS-07** — **Ground+edge split**: heavy estimation/shadow/replanning on the ground; a thin
  Guard-wrapped intent executor at the edge for partition tolerance; replay-as-debugging from the
  event log. *(trace: ops.md §3, §7, §11)*
- **RM-P2-OPS-08** — **Local/dev tier**: `docker compose` brings up orchestrator + stores + a
  sim-backed Bridge so a supervised mission runs end-to-end on a workstation, no hardware. *(trace: ops.md §7; [CX-LOCAL](README.md#cross-cutting-workstreams))*

**Dependencies:** Studio Campaign, Sim (shadow), Mind/Allocate/Guard, Bridge, View, Link (Earth-link
windows). **Exit criteria:** M2.1 (shadow mode) then M2.2 (analog field test). **Deferred → P3:**
real flight-asset operation; multi-phase mission ops + the phase executor.

---

## Bridge — hardware & flight-software abstraction

> Architecture: [bridge.md](../architecture/bridge.md). **The principal export-control / dual-use
> boundary.** Hexagonal: one port, many adapters. Translation, never decision.

**Scope & deliverables**

- **RM-P2-BRIDGE-01** — **Hexagonal port + adapter framework** (the Core command/telemetry contract
  as the single port; adapters as Core plugins with capability tags). *(trace: bridge.md §2, §3, §11)*
- **RM-P2-BRIDGE-02** — **`sim` adapter + generic `ros2`/DDS adapter**, the two that ship in the open
  package. *(trace: bridge.md §3, §9, §12)*
- **RM-P2-BRIDGE-03** — **`BridgeTarget` runtime switch + the identical-plan conformance test** (the
  *same* committed plan drives sim and a SIL target; boundary recordings must match within a declared
  tolerance — a CI gate that *proves* charter §4.6). *(trace: bridge.md §2, §10, §12)*
- **RM-P2-BRIDGE-04** — **`transform` services**: SPICE TDB/ET ⇄ stack clocks (measured, bounded,
  surfaced skew), SPICE frames ⇄ stack frames (tf2), SI ⇄ stack units, per-adapter codec registry.
  *(trace: bridge.md §3, §11)*
- **RM-P2-BRIDGE-05** — **Link-aware `delivery`**: bounded back-pressure, durable store-and-forward
  queue + idempotent ack ledger (no double-actuation over flaky links). *(trace: bridge.md §3, §8)*
- **RM-P2-BRIDGE-06** — **Fail-safe + capability gating + arm/disarm + MCAP boundary recording**: a
  real-hardware Session starts disarmed; arming requires Guard-cleared plan + healthy link + clock
  correlation + capability/RBAC; refuse rather than guess. *(trace: bridge.md §2, §9, §10)*
- **RM-P2-BRIDGE-07** — **Baseline CCSDS SPP + TC/TM** for ground-link analogs. *(trace: bridge.md §11, §12)*

**Dependencies:** Core command/telemetry schemas + capability-tag taxonomy (designed in P0/P1),
Guard verdicts, Link profiles, Ops, Sim. **Exit criteria:** identical-plan conformance test green
(sim ↔ SIL); analog rover swarm driven over ROS 2 (M2.2). **Deferred → P3:** cFS/F´ adapters,
CFDP/DTN-BP, full HIL, deep-space DSN adapters — sensitive ones partitioned. The certification-grade
flight-code/targeting generator is **permanently out of scope** (charter §9.5, §9.5).

---

## View — visualization, telemetry & explanation

> Architecture: [view.md](../architecture/view.md). Read-mostly, command-free. (A thin slice was
> reused from P0/1 for demos; the full operations viewer lands here.)

**Scope & deliverables**

- **RM-P2-VIEW-01** — **3D geospatial scene** (CesiumJS + 3D Tiles): lunar terrain from Worlds,
  assets/trajectories/keep-out, **illumination/PSR overlay**, and **Prospect resource-field +
  uncertainty** overlays (no false-precision heatmaps). *(trace: view.md §3, §11; `LUNAR-UX-002`)*
- **RM-P2-VIEW-02** — **Mission-control dashboards** (OpenMCT embed): per-asset/fleet telemetry,
  time-series, alarm/event tables, comms-window timelines. *(trace: view.md §3, §11)*
- **RM-P2-VIEW-03** — **One viewer, two clocks**: shared live-follow / scrub timeline driving live
  ([Ops](../architecture/ops.md)/[Sim](../architecture/sim.md)) and **MCAP replay** identically. *(trace: view.md §2, §3)*
- **RM-P2-VIEW-04** — **Plan-&-assignment explanation**: render Mind/Allocate/Guard decision traces
  as a "why this, not that" timeline (chosen plan, alternatives/scores, active constraints, replan
  trigger, Guard intervention). *(trace: view.md §3, §11; `LUNAR-UX-003,004`)*
- **RM-P2-VIEW-05** — **Stateless View Gateway** (decimation, back-pressure, tile proxy/cache,
  rosbridge/Foxglove for the ROS 2 plane) + **embeddable component library** consumed by Studio/Ops.
  *(trace: view.md §3, §7)*
- **RM-P2-VIEW-06** — **Command-free safety posture**: View originates no command; user intents are
  routed to Ops; it always shows live Guard/constraint state so an operator is never misled. *(trace: view.md §2, §9)*

**Dependencies:** Ops, Sim, Worlds, Prospect, Mind/Allocate/Guard traces. **Exit criteria:** an
operator supervises the analog field test through View — 3D + dashboards + explanation — under
latency. **Deferred → P3:** heliocentric/multi-body trajectory view, mission timeline across regimes,
cinematic server-side streaming.

---

## Phase-2 extensions to Phase-0/1 components

These are **hardening and online-mode** extensions, not first-lands; each is sized as a workstream
under its owning component.

- **RM-P2-SIM-20 — Digital-twin shadow + terramechanics validation.** Sim as Ops' long-lived shadow
  instance (advisory, never authoritative; Guard-gated); validate low-gravity granular models against
  **terrestrial-analog rover-swarm field data** with explicit error budgets ([CX-S2R](README.md#cross-cutting-workstreams)).
  *(trace: sim.md §12; conventions §11)*
- **RM-P2-SURR-20 — Field surrogates + ops drift.** Neural-operator (thermal) field surrogates; GP
  emulators for screening; **online drift monitoring inside the Ops digital twin**. *(trace: surrogate.md §12)*
- **RM-P2-MIND-20 — Online replanning + ground/edge split.** Mind runs inside Ops as a service; the
  per-agent executive + controller + Guard sidecar validated on analog hardware. *(trace: mind.md §12)*
- **RM-P2-ALLOC-20 — Online-replan hardening + the MILP/learned/decomposition track.** Anytime
  re-solve under hard ops deadlines; **MILP backend (HiGHS/SCIP)** + cross-solver consistency;
  **learned warm-starts/branching** from Learn traces; **rolling-horizon/spatial decomposition** for
  scale; **auction fallback** under comms loss; stochastic/robust formulations. *(trace: allocate.md §11, §12)*
- **RM-P2-GUARD-20 — Multi-agent latency-aware shielding.** `coord` responsibility-partitioning +
  worst-case-staleness margins; HJ-reachability filters for harder dynamics; the **edge-sidecar +
  central supervisor** deployment; verdict overlays in View. *(trace: guard.md §12; `LUNAR-SR-004`)*
- **RM-P2-LEARN-20 — Curricula, learned allocation heuristics, sim-to-real.** Automatic-curriculum
  plugins; learned allocation heuristics handed to Allocate; transfer-/sim-to-real-aware training
  validated against the analog field tests. *(trace: learn.md §12)*
- **RM-P2-PROSPECT-20 — Operational belief from real sensors.** The **same** belief updater fed by
  real analog sensor returns, so the operational posterior is computed by identical, validated code to
  the simulated one. *(trace: prospect.md §12)*
- **RM-P2-LINK-20 — Optional RF fidelity + live-mission prediction.** ns-3 packet-level fidelity
  plugin (where a benchmark needs it); **live-mission link prediction, capability-gated** for Ops.
  *(trace: link.md §12)*
- **RM-P2-FLEET-20 — Bridge hardware mapping.** SADF (and URDF/SDF export) backs Bridge hardware
  mapping for analog rovers; tighten export-control gating on hardware-mappable assets. *(trace: fleet.md §12)*
- **RM-P2-STUDIO-20 — Campaign→Ops hand-off matured.** The design→operations loop: a Studio-authored
  Campaign drives the operations runtime over Earth analogs (no translation layer). *(trace: studio.md §12)*
- **RM-P2-BENCH-20 — Analog / digital-twin validation scenarios.** Bench scenarios alongside Ops/
  Bridge for operational evaluation science; hidden test scenarios; multi-objective ranking. *(trace: bench.md §12)*
- **RM-P2-HUB-20 — Replication & offline mirrors.** Multi-region replication and offline/air-gapped
  mirrors for Ops; richer curation/review. *(trace: hub.md §12)*
- **RM-P2-CLOUD-20 — Stronger tenancy + ops-tier hosting.** vCluster/per-tenant isolation; host the
  operations-tier services as the platform crosses into the operations loop. *(trace: cloud.md §12)*

**Dependencies (block):** Ops/Bridge/View first-lands above; the analog field-test campaign.
**Exit criteria (block):** each extension is exercised in M2.1/M2.2 and its claims are reproducible.

---

← [Phase 1](phase-1-autonomy-studio.md) · [Roadmap index](README.md) · [Phase 3 →](phase-3-flight-mission-architecture.md)
