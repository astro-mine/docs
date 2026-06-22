# RFC 0001: Multi-regime missions (interplanetary resource campaigns)

- **Status:** draft
- **Author(s):** djankov (https://github.com/djankov)
- **Created:** 2026-06-22
- **Affects Core:** yes

## Summary

Generalize Astro-Mine's central abstraction from *"a swarm campaign on one world"* to a
**Mission** — an ordered set of **Phases**, each in a **Regime** (launch, interplanetary
transit, body-proximity, surface, ascent/return, Earth-interface). This single, additive change
lets the platform plan and operate end-to-end interplanetary resource missions (asteroid mining,
near-Earth-object sample-return, cislunar logistics) while leaving every existing single-body
scenario unchanged as the degenerate one-phase mission. The RFC adds one new component layer
(**Mission architecture & logistics**) with three components — **Astro-Mine-Trajectory**,
**Astro-Mine-Sizing**, **Astro-Mine-Ledger** — plus one new environment component
(**Astro-Mine-Transit**), a "Mission Architect" mode in **Studio**, and bounded, append-only
extensions to Core (SADF, the Environment API, message schemas, and the capability taxonomy).
The most export-sensitive addition — trajectory work — is held strictly to *design-time
exploration*; operational maneuver targeting and guided Earth re-entry remain out of scope.

## Motivation

**The problem.** A user who wants to plan, say, an asteroid-mining mission — launch assets from
Earth (or reuse what is already in LEO), transit to a near-Earth object, characterize and mine
it, and return ore — cannot do so end-to-end in Astro-Mine as chartered. A gap analysis found
that the *swarm-on-and-around-the-body* core (prospecting, heterogeneous task allocation,
comms-window-constrained coordination, ISRU) is squarely in scope, but several mission-critical
pieces are missing:

1. **No interplanetary trajectory design/optimization.** [Sim](../architecture/sim.md)
   can *propagate and validate* a trajectory, but nothing *optimizes* launch windows, transfers,
   rendezvous, or return — and the discrete/continuous joint problem (which asset → which target
   → which window → which trajectory) sits between
   [Allocate](../architecture/allocate.md) and Sim with
   no owner.
2. **No spacecraft/payload sizing.** [Fleet](../architecture/fleet.md)
   parameterizes assets; it is not a mass/power/propellant systems-engineering tool, so "what
   spacecraft, what payload, reuse what's in LEO" cannot be answered.
3. **No mission-level value model.** Trade studies need an objective spanning trajectory + fleet +
   swarm ops + delivered value; today there is none.
4. **The lifecycle spans regimes the loops were not shaped for.** The design and operations loops
   assume a single-body surface campaign; a mission is a *sequence* of regimes with different
   dynamics, comms, latency, and autonomy postures.
5. **The deep-space environment is unmodeled.** There is no representation of the interplanetary
   medium (n-body dynamics, radiation, thermal, micrometeoroid) between bodies.

**Why now.** The charter already names small bodies as in-scope and asteroids as a Phase-3 plugin
environment, but only vaguely ("new environments as plugins"). The cost of not acting is
architectural, not schedule-driven: the **Mission/Phase/Regime hooks must be designed into Core
early** (Phase 1, while Core is already being extended for autonomy). Retrofitting multi-regime
into a frozen narrow waist later is exactly the leaky-god-interface failure the charter warns
about (§9). We can defer the *implementations* to Phase 3; we cannot cheaply defer the *schema*.

**Who is affected.** A new audience — mission/systems engineers, astrodynamicists, and resource-
economics analysts — joins the existing robotics/RL/planetary-science base. The change is gated
behind the lunar MVP and is opt-in, so the existing base is not disrupted.

## Design

The full per-component technology architecture lives in the `docs` repo under `architecture/`;
this section gives the design at RFC altitude. See the
[Mission/Phase/Regime model](../architecture/mission-model.md)
for the schema sketch.

### 1. The Mission / Phase / Regime model

- **Mission** — the new top-level authored object: an objective (value model), a fleet (SADF
  assets including reusable LEO inventory), global constraints, and an ordered list of phases.
- **Phase** — a span of the mission in one regime, bound to one environment, with explicit
  entry/exit conditions and **state handoff** to its successor, optionally containing a per-phase
  **swarm campaign** (today's campaign concept).
- **Regime** — a **small, closed, RFC-governed enum**:
  `launch_ascent · interplanetary_transit · proximity_orbit · surface · ascent_return ·
  earth_interface`.

A lunar-polar prospecting run is a Mission with one `surface` phase whose campaign is exactly
what the platform runs today. This backward-compatibility is the crux of the proposal.

### 2. New component layer: Mission architecture & logistics

| Component | Role | Leverages |
|---|---|---|
| **Astro-Mine-Trajectory** | *Design-time* trajectory & maneuver optimization across regimes (launch injection, transfers, rendezvous, proximity, return; window scans; Δv/ToF trades). Produces **descriptive** `TrajectoryRef`/`ManeuverBudget` artifacts for trade studies — **not** executable guidance. | pykep/pygmo, poliastro, Orekit, Basilisk; GMAT/STK as oracles |
| **Astro-Mine-Sizing** | Spacecraft & payload systems-engineering sizing: mass/power/propellant/staging budgets, payload packing, launch manifesting, reusable-LEO accounting. Emits sized SADF configs. | OpenMDAO |
| **Astro-Mine-Ledger** | *Open, generic* techno-economic & logistics modeling (cost/value/risk **with uncertainty**) — the mission-level objective/value function. Proprietary cost data stays a commercial plugin. | OpenMDAO, parametric cost models, Monte Carlo |

### 3. New environment component

- **Astro-Mine-Transit** — the interplanetary / free-space dynamical and hazard environment
  (n-body ephemerides & gravity, radiation, thermal/eclipse, micrometeoroid) for the
  `interplanetary_transit` regime and proximity station-keeping. Complements
  [Worlds](../architecture/worlds.md) (on a body) and
  [Link](../architecture/link.md) (comms).

### 4. Extensions to existing components

Worlds → small/irregular bodies (3-D shape, polyhedral/mascon gravity, rotation, microgravity
regolith); Sim → microgravity contact/anchoring + multi-regime propagation + a multi-phase
runtime; Surrogate → microgravity-contact surrogates; Link → deep-space comms (DSN, light-time,
DTN); Fleet/SADF → propulsion/staging/return capabilities and launch/return vehicle kinds;
Mind/Allocate → window-gated, multi-regime planning and the joint asset↔target↔window↔trajectory
assignment; Guard → no-recovery, window-gated, high-latency assurance; Studio → a **Mission
Architect** mode; Ops → multi-phase operations across regimes; Bridge → deep-space stacks (with
operational targeting still partitioned); View → multi-body trajectory + mission-timeline
visualization; Bench → asteroid-mining and NEO-sample-return reference scenarios with mission-
level metrics; Hub → mission/trajectory/spacecraft/economics artifact types.

### 5. The "Mission Architect" surface

Mission architecture and swarm design are co-dependent — the trajectory depends on the swarm's
mass, the swarm depends on the Δv budget — so they must co-optimize in one loop. Therefore the
Mission Architect is a **new mode/stage inside Studio**, orchestrating the new engines exactly as
Studio already orchestrates Sim/Learn/Mind/Allocate — **not** a separate application. The distinct
*persona* (mission/systems engineer vs. swarm/autonomy designer) is honored with a distinct
workspace in the UI (optionally a separately deployable front-end module), but the backend and
trade-study loop are one.

### 6. Dual-use boundary (load-bearing)

Trajectory work is the most export-sensitive addition. The boundary is drawn **in the schema**:

- **Open commons:** `TrajectoryRef`/`ManeuverBudget` are *descriptive design-time artifacts*
  (reference arcs, Δv/ToF, window feasibility) for trade studies. No guidance, no closed-loop
  targeting, no command format.
- **Out / partitioned:** converting a reference trajectory into **executable maneuver guidance
  for real flight hardware** (operational targeting) and **guided atmospheric EDL** remain
  excluded per [EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md) and charter §10.5. `earth_interface` is a
  **delivery/recovery event with mass/Δv accounting**, not a guided re-entry simulator. A reserved
  `operational_targeting` capability tag gates anything that crosses this line at the registry and
  [Bridge](../architecture/bridge.md) boundary.

`EXPORT_CONTROL.md` should gain a sentence making the design-time-exploration vs. operational-
targeting line explicit for trajectory capabilities.

## Impact on Core

**Does this widen the narrow waist?** Yes, but minimally and additively, and the alternative
(no Core hooks, retrofit later) is worse. The additions are:

1. **SADF** gains propulsion / staging / return / mobility-regime **capability declarations** —
   consumed by negotiation, like today's sensor/autonomy capabilities. No new asset *types* in
   Core (`launch_vehicle`/`return_vehicle` are Fleet content).
2. **Environment API** gains a bounded **`regime` descriptor**, **free-space (no-terrain)
   observations**, and **`PhaseTransition`** handoff events — *one* contract with a small enum,
   not per-regime interfaces.
3. **New schemas:** `MissionSpec`, `TrajectoryRef`/`ManeuverBudget` (descriptive), `PhaseTransition`.
4. **Capability taxonomy** gains mobility/propulsion/return tags and the gated
   `operational_targeting` tag.

**Why it cannot live entirely in a plugin.** The *Mission/Phase/Regime vocabulary* and the
`regime`/`PhaseTransition` additions to the Environment API are interoperability contracts —
they are how Trajectory, Sizing, Sim, Allocate, Ops, and Bench agree on what a mission *is*. A
plugin cannot define a shared contract; that is by definition Core's job. Everything *built on*
the vocabulary (engines, models, scenarios) remains a plugin.

**Breaking changes / migration.** None. All additions are append-only minors (proto3 unknown-
field tolerance; existing consumers ignore `regime` and operate as single-phase). Existing
scenarios are valid one-phase Missions with no author action. Bench scenarios pin the Core minor.

**Narrow-waist discipline (the three rules enforced):** (a) regimes are a closed enum; (b)
phase-sequencing logic lives *above* Sim, never in Core; (c) SADF grows by capability declaration,
not type explosion.

## Alternatives considered

1. **A separate "Mission Architect" application instead of a Studio mode.** Rejected: it would
   duplicate Studio's orchestration and fracture the trajectory⇄fleet⇄swarm co-design, which must
   be a single loop. Persona separation is handled with a workspace, not a separate app.
2. **A standalone trajectory-optimization service with no Core schema change.** Rejected: without
   `MissionSpec`/`regime` in Core, every consumer would invent its own mission representation —
   the fragmentation the narrow waist exists to prevent.
3. **Extend Worlds to represent free space rather than add Transit.** Rejected (documented as the
   runner-up): Worlds is surface/terrain-centric; stretching it to no-terrain free space strains
   the abstraction. A dedicated, lightweight Transit component keeps each environment coherent.
4. **Fold trajectory + sizing into Sim/Studio without new components.** Rejected: these are
   distinct engines (continuous astrodynamics optimization; multidisciplinary systems-engineering
   sizing) with their own toolchains; burying them inside Sim/Studio would bloat both and hide the
   dual-use boundary that Trajectory must isolate.
5. **Build trajectory optimization from scratch.** Rejected per the charter's "integrate
   aggressively, reinvent little" mandate — bridge to pykep/pygmo/Orekit/GMAT instead.
6. **Open techno-economics fully (data included) vs. keep it commercial.** Resolved by splitting:
   an open parametric *framework* in Ledger; proprietary cost/pricing as commercial plugins —
   consistent with the charter's commons/commercial positioning (§3).
7. **Do nothing; keep asteroids as undefined "plugins."** Rejected: the Core schema hooks are the
   one thing that genuinely cannot be deferred without future pain.

## Unresolved questions

- **Regime-enum completeness:** is `{launch_ascent, interplanetary_transit, proximity_orbit,
  surface, ascent_return, earth_interface}` sufficient for icy-moon and multi-target tours, or are
  `aerobraking` / `formation` regimes needed? Resolve via reference scenarios, not speculation.
- **Where phase-sequencing logic lives:** a thin sequencer in the Sim scenario runtime (mechanism)
  vs. orchestration in Studio/Ops (policy). Current lean: runtime mechanism, orchestration policy.
- **`TrajectoryRef` expressiveness:** how much structure it carries (waypoints + budgets vs. full
  state history) without becoming a back-door command format — the crux of keeping the dual-use
  line clean.
- **Co-optimization coupling:** how tightly `MissionSpec` encodes the trajectory⇄fleet⇄swarm⇄
  economics coupling vs. leaving it to Studio's trade-study engine.
- **Roadmap placement:** confirm Core schema hooks in Phase 1 with implementations in Phase 3, and
  whether the NEO sample-return stepping-stone scenario should be promoted to a named Phase-2/3
  Bench benchmark.
- **Scope governance:** this roughly doubles platform surface area; the steering group should
  decide the opt-in track's resourcing so it does not compete with the lunar MVP.
