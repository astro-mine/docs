# Phase 3 — Flight, mission architecture & ecosystem

> **Window:** 54 mo + · **Theme:** Flight, mission architecture & ecosystem · **Roadmap home:** [README](README.md)
> **Goal:** become the **default stack** — for surface ISRU *and* full interplanetary resource
> missions — as the cislunar economy matures (charter §10; system.md §11).

**Entry dependencies:** Phase 2 complete (sim→ops threshold crossed on analogs); the **RFC-0001 Core
schema hooks reserved in Phase 1** (`RM-P1-CORE-04`) — without them this phase would require
retrofitting the frozen waist, the exact failure the charter warns against.

**This phase has two largely independent tracks:**

- **Track A — Flight integration** (continues the operations line): real flight-software adapters and
  flight-asset operation, with sensitive capability **partitioned out of the open core**.
- **Track B — Mission architecture** *(RFC-0001, opt-in)*: the new
  **Transit · Trajectory · Sizing · Ledger** layer + small-body/microgravity extensions, delivering
  end-to-end interplanetary missions. **A single-`surface`-phase mission is unchanged**, so Track B
  never disturbs existing scenarios.

**Integration milestones:**

- **M3.1 — NEO rendezvous + sample-return** ([scenario 2](../scenarios/2-asteroid-mining.md) baseline,
  the RFC-0001 R5 stepping-stone): a `MissionSpec` spanning all six regimes is architected in Studio's
  Mission Architect, validated in Sim, scored on Bench with mission-level metrics, and runnable in
  multi-phase Ops against the sim backend.
- **M3.2 — Multi-asteroid mining + ore return** (Phase-3 capstone): sustained anchored excavation +
  in-situ extraction, a multi-target tour.
- **M3.3 — Real flight-asset operation** (Track A): a campaign drives real flight hardware via Bridge
  cFS/F´/CCSDS adapters (access-controlled).

**Phase exit criteria:** M3.1 met (the named benchmark); the mission-architecture layer is in the
zoo and the flywheel; new bodies arrive purely as plugins; the **dual-use boundary holds** (below).

**Phase-level cross-cutting — the dual-use boundary (load-bearing):**
[Trajectory](../architecture/trajectory.md) is the most export-sensitive component the platform will
host. The line is drawn **in the schema**: `TrajectoryRef`/`ManeuverBudget` are **descriptive,
design-time** artifacts (reference arcs, Δv/ToF, window feasibility) and **omit by schema** any
executable-guidance fields. **Operational maneuver targeting** and **guided atmospheric EDL** stay
**partitioned out**, gated by the `operational_targeting` capability tag at the registry/[Bridge](../architecture/bridge.md)
boundary. `earth_interface` is a **delivery/recovery event with mass/Δv accounting, not a guided
re-entry simulator** (RFC-0001 §6, R3; mission-model §4; conventions §12;
[EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md)).

---

## Transit — the deep-space environment (new)

> Architecture: [transit.md](../architecture/transit.md). Environment, not maneuvers — the free-space
> analog of [Worlds](../architecture/worlds.md).

**Scope & deliverables**

- **RM-P3-TRANSIT-01** — **`TransitEnvSpec` + content-addressed environment bundle** (gravitationally
  relevant bodies, central frame, epoch range, SPICE meta-kernel, enabled force/hazard models). *(trace: transit.md §3, §5)*
- **RM-P3-TRANSIT-02** — **Force-model assembly behind one `ForceModel`** at three fidelity tiers
  (point-mass patched-conic → **perturbed n-body** default → high-precision), wrapping **Orekit/
  Basilisk** validated models + a native polyhedral/mascon small-body kernel; returns acceleration +
  state-transition partials. *(trace: transit.md §3, §11; `AST-TR-001,003`)*
- **RM-P3-TRANSIT-03** — **Deep-space `HazardField`**: radiation dose (trapped AE8/AP8-class, SEP,
  GCR), thermal/eclipse, micrometeoroid (Grün/MEM-class) — precomputed Zarr fields with carried
  uncertainty, consumed by [Sim](../architecture/sim.md) for survival modeling. *(trace: transit.md §3, §11; scenario §5)*
- **RM-P3-TRANSIT-04** — **Free-space Environment-API profile + shared `GeometryService`** (no
  terrain, n-body frame context, `PhaseTransition` handoffs; eclipse/occultation shared with
  [Link](../architecture/link.md)). *(trace: transit.md §6; mission-model §2.2)*
- **RM-P3-TRANSIT-05** — **Small-body gravity packs** (polyhedral exact in proximity + harmonic
  far-field) paired with a Worlds surface body-pack, sharing the body frame/SPICE ID. *(trace: transit.md §3, §11)*
- **RM-P3-TRANSIT-06** — **Oracle validation** (GMAT/Orekit/Basilisk/STK; SPENVIS-style hazard
  references) with explicit error budgets; determinism + frame/epoch sanity gates. *(trace: transit.md §10; `AST-TR-003`)*

**Dependencies:** Core mission hooks (`RM-P1-CORE-04`), the shared [`astro-mine-spice`](../architecture/spice.md)
foundation ([RFC-0002](../rfc/0002-shared-spice-foundation.md)). **Exit criteria:** a designer
propagates/scores an interplanetary baseline cruise locally; arcs validated against oracles. **Deferred:**
new target bodies / time-resolved SEP / learned force-hazard surrogates as later packs.

---

## Trajectory — design-time trajectory optimization (new)

> Architecture: [trajectory.md](../architecture/trajectory.md). **The most export-sensitive component.**
> Descriptive, never executable. The platform's first component that *optimizes* trajectories.

**Scope & deliverables**

- **RM-P3-TRAJ-01** — **Core trajectory-optimization sub-interface** (`LegRequest → TrajectoryRef +
  ManeuverBudget`); the descriptive-only schema is **Core-owned** (`RM-P1-CORE-04`), Trajectory
  *produces* it. *(trace: trajectory.md §3; mission-model §2.3)*
- **RM-P3-TRAJ-02** — **Impulsive tier (MVP first)**: Lambert/patched-conic + **porkchop / launch-&
  return-window scans** via pykep/poliastro. *(trace: trajectory.md §11, §12; `AST-FR-002`)*
- **RM-P3-TRAJ-03** — **Descriptive `TrajectoryRef` discipline**: boundary states + maneuver budget +
  coarse-epoch reference control envelope; **schema omits** actuator command channels, closed-loop
  gains, and flight-clock binding (a contract test asserts their absence). *(trace: trajectory.md §5, §9; RFC-0001 R3; dual-use note above)*
- **RM-P3-TRAJ-04** — **Validation downstream of optimization**: every `TrajectoryRef` is propagated
  and checked in [Sim](../architecture/sim.md) (and against GMAT/STK/Copernicus oracles, license-gated)
  before it is trusted. *(trace: trajectory.md §6, §11; `AST-TR-003`)*
- **RM-P3-TRAJ-05** — **Low-thrust + global tiers (after MVP)**: Sims-Flanagan → collocation; pygmo
  global/island-model for multi-flyby/NEO tours; uncertainty-annotated budgets; cloud-scale window
  sweeps. *(trace: trajectory.md §11, §12)*
- **RM-P3-TRAJ-06** — **Capability-tag + topology controls**: declares only design-time tags (never
  `operational_targeting`); no operational/flight deployment tier; outputs flow only to design
  siblings + Sim validation. *(trace: trajectory.md §9; mission-model §4)*

**Dependencies:** Transit (force models), Core mission hooks, Fleet propulsion SADF, Sim (validation).
**Exit criteria:** one reference Earth→NEO→Earth mission's windows/Δv are optimized, validated, and
fed to Allocate/Sizing inside a Studio Mission Architect trade study (toward M3.1). **Deferred:** new
regimes (icy moons, multi-target tours) as optimizer/dynamics plugins.

---

## Sizing — spacecraft & payload systems-engineering sizing (new)

> Architecture: [sizing.md](../architecture/sizing.md). Produce SADF, never widen it. Conceptual/
> preliminary (pre-Phase-A), not detailed design.

**Scope & deliverables**

- **RM-P3-SIZING-01** — **Coupled-subsystem MDAO closure (OpenMDAO)**: propulsion/power/thermal/
  structure/payload solved as a converged system (analytic/coupled derivatives), with margins as
  *probability of closure*, failing loud on non-closure. *(trace: sizing.md §3, §11; `AST-FR-003`)*
- **RM-P3-SIZING-02** — **Rocket-equation/staging math + reusable-LEO inventory accounting** (fixed
  assets by default, promotable to MDO design variables). *(trace: sizing.md §3, §11)*
- **RM-P3-SIZING-03** — **Launch manifesting** (mass-to-orbit + fairing-volume packing via OR-Tools
  CP-SAT; multi-launch split) with realistic launch-vehicle data plugins. *(trace: sizing.md §3, §11; `AST-FR-012`)*
- **RM-P3-SIZING-04** — **SADF emit**: converged design → a **valid sized SADF patch against a Fleet
  parametric template** (propulsion/staging/return per mission-model §2.1), held by Fleet, flown by
  Sim, priced by Ledger — no Sizing-private format. *(trace: sizing.md §3, §6; `AST-FR-003`)*
- **RM-P3-SIZING-05** — **Trajectory↔sizing coupling**: sequential Δv→sizing default, **fully-coupled
  trajectory⇄vehicle MDO** available for final trades; Sizing+Ledger share one OpenMDAO graph (R4).
  *(trace: sizing.md §11; RFC-0001 R4)*
- **RM-P3-SIZING-06** — **Validation**: analytic golden vehicles, oracle/Sim Δv-closure cross-checks,
  SADF round-trip/instantiation in Sim, determinism gates. *(trace: sizing.md §10)*

**Dependencies:** Trajectory (`ManeuverBudget`), Fleet (templates + SADF emit), Core SADF propulsion
fields, Ledger (shared MDO graph), Sim (validation). **Exit criteria:** given a NEO-mission Δv +
throughput requirement, produce a **feasible, sized, instantiable** asset set Sim flies and Studio
trades. **Deferred:** physics-/Surrogate-backed subsystem fidelity tiers; community subsystem models.

---

## Ledger — open techno-economic value model (new)

> Architecture: [ledger.md](../architecture/ledger.md). The mission-level objective/value function.
> **Open framework; proprietary data is a plugin.**

**Scope & deliverables**

- **RM-P3-LEDGER-01** — **`ValueModel` / `CostModel` / `RevenueModel` / `RiskModel` contracts** —
  `evaluate(mission) → distribution over named objectives` (ROI/NPV/delivered-mass/expected-loss/
  makespan) with line-item breakdown. *(trace: ledger.md §3; `AST-FR-004`)*
- **RM-P3-LEDGER-02** — **Public parametric CERs** (launch, development, operations) with cited
  provenance + validity envelopes; **out-of-envelope queries widen, never narrow, uncertainty**. *(trace: ledger.md §2, §11)*
- **RM-P3-LEDGER-03** — **Monte-Carlo `UncertaintyEngine`** sampling cost × price × the
  [Prospect](../architecture/prospect.md) **belief** posterior **jointly** (correlation preserved;
  never average the resource field first). *(trace: ledger.md §5, §8, §11; `AST-FR-004`)*
- **RM-P3-LEDGER-04** — **OpenMDAO `LedgerComponent`** as the objective shared with Sizing (the tight
  vehicle⇄economics inner loop). *(trace: ledger.md §3, §11; RFC-0001 R4)*
- **RM-P3-LEDGER-05** — **Commons/commercial split (enforced)**: open framework + generic public
  models in-repo; **proprietary cost DBs / price feeds / ROI calibrations as access-gated Hub
  plugins**; a **no-proprietary-leak CI test** — a public-only build produces a complete, honestly-
  wide-error result. *(trace: ledger.md §2, §9, §10; charter §3; `AST-SR-004`)*
- **RM-P3-LEDGER-06** — **Ground-truth isolation inherited** (values against belief only; contract
  test asserts no `GroundTruthField` reach) + calibration/backtesting gates. *(trace: ledger.md §2, §9, §10)*

**Dependencies:** Sizing (drivers + shared MDO graph), Trajectory (Δv/ToF), Prospect (belief
posterior), Core objective schema (`RM-P1-CORE-03`). **Exit criteria:** ROI-rank candidate
asteroid-mining architectures on **public data**, feeding a Studio Pareto front + a Bench mission
metric (toward M3.1). **Deferred:** hierarchical-Bayesian CERs, EVPI-tied resource economics, a
maturing commercial-plugin ecosystem.

---

## Track A — flight integration (Bridge & Ops)

- **RM-P3-BRIDGE-30 — cFS / F´ adapters + CFDP / DTN-BP + full HIL.** Native cFS Software Bus app +
  F´ ground interface; CFDP/Bundle-Protocol as real delayed links demand; hardware-in-the-loop
  validation against flight units/engineering models behind the access-controlled boundary. *(trace: bridge.md §11, §12; `AST-SR-003`)*
- **RM-P3-BRIDGE-31 — Deep-space stacks (DSN), gated.** DSN telecommand/telemetry + extended CCSDS;
  **operational maneuver targeting stays partitioned and excluded**; the `operational_targeting` tag
  gates the registry/Session edge. *(trace: bridge.md §9, §12; RFC-0001 §6; `AST-SR-001,002`)*
- **RM-P3-OPS-30 — Real flight-asset & multi-phase mission operations.** Flight-asset operation via
  Bridge adapters (sensitive capability partitioned out of open core); the **phase executor** (mirrors
  Sim's sequencer mechanism, performs `PhaseTransition` handoffs, applies Studio-authored cross-phase
  policy), the **multi-regime shadow twin** (spans transit/proximity/surface, vets each phase),
  **regime-gated adjustable autonomy** (ratchet up for deep-space light-time). *(trace: ops.md §3, §11, §12; RFC-0001 R2; `AST-FR-001,006,007`)*

**Dependencies:** Phase-2 Ops/Bridge; Core mission hooks. **Exit criteria:** M3.3 (real flight-asset
op) and multi-phase Ops running a `MissionSpec` against the sim backend (toward M3.1).

---

## Track B — multi-regime extensions to existing components

Each is an **additive extension** consuming the Phase-1-reserved Core hooks — *extended, not
replaced* (RFC-0001 §4).

- **RM-P3-WORLDS-30 — Small / irregular bodies + microgravity regolith.** 3-D closed polyhedral shape
  models (not 2.5-D heightfields), polyhedral/mascon non-central gravity, body rotation/tumbling, and
  **cohesion-dominated microgravity regolith** fields for `surface`/`proximity_orbit`, as body packs.
  *(trace: worlds.md §11, §12; `AST-*` env)*
- **RM-P3-SIM-30 — Microgravity engine + multi-regime propagation + multi-phase sequencer.** A
  distinct cohesion-dominated low-g DEM contact domain (Project Chrono-class) behind the same waist;
  co-simulation coupling Transit free-space ↔ proximity ↔ surface; the thin **runtime sequencer**
  (mechanism only) over the episode loop; validates/propagates `TrajectoryRef` (never optimizes).
  *(trace: sim.md §3, §11, §12; `AST-FR-006`, `AST-TR-002`)*
- **RM-P3-SURR-30 — Microgravity contact/anchoring surrogate.** The lowest-data, hardest case — same
  bounded-error contract, **conservative trust regions + wider calibrated bounds**, strict validation
  gate. *(trace: surrogate.md §11, §12; `AST-TR-002`)*
- **RM-P3-FLEET-30 — Launch/return vehicles + propulsion content.** `launch_vehicle`/`return_vehicle`
  asset kinds + propulsive spacecraft authored against the additive Core SADF propulsion/return
  capabilities; reusable-LEO assets as fleet members with an initial in-orbit state. *(trace: fleet.md §12; mission-model §2.1; `AST-FR-012`)*
- **RM-P3-LINK-30 — Deep-space comms.** DSN contact scheduling (sparse Earth-link windows),
  minutes-to-tens-of-minutes light-time, **DTN/Bundle-Protocol** store-and-forward, small/irregular-
  body occultation; feeds the delay-tolerant posture. *(trace: link.md §11, §12; `AST-TR-004`)*
- **RM-P3-ALLOC-30 — Mission-level joint assignment.** The discrete **asset↔target↔window↔trajectory**
  assignment as added constraint families + a time-expanded graph over the existing CP-SAT/MILP +
  learned-warm-start backbone; window-feasibility as a hard orbital deadline. *(trace: allocate.md §3, §11, §12; `AST-FR-005`)*
- **RM-P3-MIND-30 — Window-gated cross-phase composition.** Per-phase decision stacks composed across
  `PhaseTransition` handoffs (delay-tolerant posture per regime); orbital-mechanics windows as hard
  constraints/replan triggers; outputs still Guard-wrapped; cross-phase *policy* in Studio/Ops (R2).
  *(trace: mind.md §11, §12; `AST-FR-007`)*
- **RM-P3-GUARD-30 — Deep-space one-shot assurance.** Per-phase `SafetySpec` profiles; worst-case-
  staleness margins at tens-of-minutes light-time; the autonomous **edge shield** carries no-recovery,
  window-gated events (proximity ops, landing/anchoring); embeddable Rust core behind Bridge. *(trace: guard.md §9.4, §11, §12; `AST-FR-007`)*
- **RM-P3-STUDIO-30 — Mission Architect mode.** A distinct workspace/persona authoring a `MissionSpec`
  and the outer **trajectory⇄fleet⇄swarm⇄economics** co-optimization (orchestrating Trajectory/Sizing/
  Ledger; Sizing+Ledger share one OpenMDAO graph); `MissionSpec` stays **declarative** (R4). *(trace: studio.md §3, §6, §12; RFC-0001 §5)*
- **RM-P3-VIEW-30 — Multi-body visualization.** Heliocentric/multi-body scene mode (transfer arcs,
  rendezvous geometry, porkchop plots), a **mission timeline across regimes**, cross-phase plan
  explanation; renders `TrajectoryRef`/Transit geometry only — no guidance synthesis. *(trace: view.md §3, §11, §12; `AST-UX-002,003,007`)*
- **RM-P3-HUB-30 — Mission-architecture artifact types.** Index/serve `MissionSpec`, `TrajectoryRef`/
  `ManeuverBudget` libraries, sized SADF designs, and open economics models — with
  `operational_targeting`-aware OPA gating + proprietary-cost-plugin access control. *(trace: hub.md §9, §12; `AST-SR-001,004`)*
- **RM-P3-CLOUD-30 — Mission-design sweep workload classes.** Porkchop/window scans + OpenMDAO sweeps
  on Argo; pygmo island-model on Ray — CPU-bound, spot + per-window/per-generation checkpointing; no
  new infra primitive. *(trace: cloud.md §3, §8, §12; `AST-TR-005`)*

**Dependencies (block):** the new mission-arch layer (Transit/Trajectory/Sizing/Ledger) + Core mission
hooks. **Exit criteria (block):** each extension is exercised by M3.1 (NEO sample-return) without
disturbing any single-`surface`-phase scenario.

---

## Mission scenarios (Bench)

- **RM-P3-BENCH-30 — NEO rendezvous + sample-return scenario** (the named R5 stepping-stone): a
  `ScenarioSpec` pinning the `MissionSpec`/`regime` schema and referencing small-body Worlds/Prospect,
  propulsive Fleet, and descriptive `TrajectoryRef`s by content hash. *(trace: bench.md §12; scenario 2; `AST-FR-001`)*
- **RM-P3-BENCH-31 — Multi-asteroid mining + ore return scenario** (capstone). *(trace: bench.md §12; scenario 2 §15)*
- **RM-P3-BENCH-32 — Mission-level metrics**: delivered sample/ore mass, mass-return ratio, Δv
  efficiency, schedule adherence, site coverage, sampler success rate, autonomy-under-light-time,
  anchoring/contact success, and **ROI-with-uncertainty via Ledger** — pluggable metrics on the same
  reproducibility harness. *(trace: bench.md §5, §12; scenario 2 §13; `AST-FR-009`)*

**Dependencies:** the full Track-B stack + Ledger. **Exit criteria:** M3.1 — the NEO sample-return
mission is architected, validated, scored, and reproducible end-to-end. The track is **opt-in and
must not gate the lunar MVP**.

---

← [Phase 2](phase-2-operations-bridge.md) · [Roadmap index](README.md)
