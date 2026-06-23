# Mission / Phase / Regime Model — Core Schema Sketch

> Status: **Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) — implementation Phase 3.
> Layer: **Commons backbone** (extends [Core](core.md)) · Phase: schema hooks in **1**, implementation **3**.
> Cross-cutting standards: see [conventions.md](conventions.md).

This document sketches the one conceptual change that lets Astro-Mine support end-to-end
interplanetary resource missions (asteroid mining, NEO sample-return, cislunar logistics)
without becoming a different platform: generalize **"a swarm campaign on a world"** into a
**Mission** — an ordered set of **Phases**, each in a **Regime**. It is the foundation the new
[Transit](transit.md), [Trajectory](trajectory.md), [Sizing](sizing.md), and [Ledger](ledger.md)
components build on, and the only part of the extension that touches the narrow waist.

**Design intent:** this is purely *additive* to [Core](core.md). Every existing single-body
scenario is the degenerate one-phase mission, so nothing already built changes behavior.

---

## 1. The model

```
Mission
├── objective        → value/score model (Astro-Mine-Ledger)
├── fleet            → SADF assets (Astro-Mine-Fleet), incl. reusable LEO inventory
├── constraints      → global limits (budget, schedule, launch capacity, export gating)
├── phases[]         → ordered, each in one Regime
│   └── Phase
│       ├── regime           → enum (see §1.2)
│       ├── environment      → Worlds (a body) | Transit (free space)
│       ├── entry / exit      → conditions + state handoff to the next phase
│       ├── assets_active     → subset of the fleet present in this phase
│       ├── campaign?         → per-phase swarm ops (existing Studio/Ops "campaign")
│       └── legs[]            → trajectory/maneuver budgets between phases (Trajectory)
└── provenance       → inputs, code versions, seeds (conventions.md §5)
```

- A **Mission** is the new top-level authored object. A lunar-polar prospecting run is a Mission
  with a single `surface` Phase whose `campaign` is exactly today's swarm campaign.
- A **Phase** is a span of the mission in one dynamical/operational regime, bound to one
  environment, with explicit **entry/exit conditions** and **state handoff** to its successor
  (e.g., the proximity phase begins when the approach leg's terminal state is reached).
- A **Leg** is a trajectory/maneuver budget connecting phases (design-time only — see §4).

### 1.1 Why phases, not one flat scenario

Different regimes have different dynamics, time constants, comms, and autonomy postures. Making
the phase boundary explicit is what lets the **multi-fidelity scheduler** ([Sim](sim.md)),
**assurance posture** ([Guard](guard.md)), and **operator autonomy model** ([Ops](ops.md)) all
switch per phase — without any of them needing to know about regimes they don't run.

### 1.2 The Regime enumeration

A **small, closed, RFC-governed enum** — deliberately not an open type, to protect the waist:

| Regime | Environment | Example |
|---|---|---|
| `launch_ascent` | Earth → orbit (boundary) | injection to LEO/escape |
| `interplanetary_transit` | [Transit](transit.md) | heliocentric cruise to a NEO |
| `proximity_orbit` | [Worlds](worlds.md) (small body) + [Transit](transit.md) | station-keeping, approach, characterization |
| `surface` | [Worlds](worlds.md) | prospecting, mining, ISRU (today's case) |
| `ascent_return` | body → transit (boundary) | departure with mined mass |
| `earth_interface` | boundary event | delivery/recovery (modeled as an event, **not** a guided-EDL simulator — see §4) |

Adding a regime is an RFC. The expectation is that this list is near-complete for cislunar and
small-body missions; growth should be rare.

---

## 2. Core schema extensions (additive)

All of the following are **append-only** additions under new, versioned Core interface minors;
none renumber or repurpose existing fields (conventions.md §3).

### 2.1 SADF — propulsion & cross-regime mobility

Today SADF declares geometry, dynamics, power/thermal, sensors, comms, and autonomy
capabilities. Add (as *declared capabilities*, consumed by negotiation — not new asset types):

```yaml
# additive SADF block (illustrative)
propulsion:
  systems:
    - kind: chemical_biprop        # | electric_ion | cold_gas | solar_sail | none
      thrust_N: 440
      isp_s: 321
      propellant: { type: MMH_NTO, mass_kg: 1200 }
  delta_v_budget_mps: 2950
  staging: [ { dry_kg: 800, prop_kg: 1200 }, ... ]
mobility_regimes: [ interplanetary_transit, proximity_orbit, surface ]   # capability tags
return:
  capability: sample_canister      # | bulk_hauler | none
  earth_interface: ballistic_capsule   # delivery mode (not a guided-EDL spec)
```

`launch_vehicle` and `return_vehicle` are **asset kinds in [Fleet](fleet.md)**, described in the
same SADF — not a new component. Reusable LEO assets are just fleet members with an initial
in-orbit state in the Mission.

### 2.2 Environment API — a bounded `regime` dimension

The environment contract gains:
- a **`regime` descriptor** on observations/actions (so a consumer can branch or refuse);
- **free-space / no-surface** observations (the [Transit](transit.md) case — no terrain, n-body
  frame context);
- **phase-transition events** carrying the terminal state of one phase as the initial state of
  the next (the handoff).

It does **not** gain per-regime interfaces. One contract, a small enum, transition events.

### 2.3 New schemas

- **`MissionSpec`** — the top-level document above: phases, regimes, fleet, objective ref,
  constraints, provenance. (JSON Schema authored + Protobuf wire, per conventions.md §3.)
- **`TrajectoryRef` / `ManeuverBudget`** — *design-time* reference trajectories and Δv/time-of-
  flight budgets (descriptive artifacts, **not** executable guidance — see §4). Produced by
  [Trajectory](trajectory.md), consumed by [Allocate](allocate.md)/[Sizing](sizing.md)/
  [Studio](studio.md).
- **`PhaseTransition`** message — the typed handoff event on the Environment API.

### 2.4 Capability taxonomy — including a dual-use gate

The capability-tag vocabulary (the substrate for export-control gating, [Core](core.md) §9) gains
mobility-regime, propulsion, and return tags, **plus** a reserved sensitive tag class
`operational_targeting` that is policy-gated (OPA) and **partitioned out of the open commons** by
default (see §4 and [conventions.md §12](conventions.md)).

---

## 3. Staying narrow-waisted (the three rules)

The charter's whole thesis is a small core guarded jealously. This extension obeys it:

1. **Regimes are a bounded enum behind one contract** — not N new interfaces.
2. **Mission/Phase sequencing lives *above* [Sim](sim.md)** (in the runtime / [Studio](studio.md)
   / [Ops](ops.md) layers). Core learns the *schema* of a Mission, never how to fly one.
3. **SADF grows by capability declaration, not type explosion.** Propulsion/return are declared
   capabilities consumed by negotiation, exactly like sensors and autonomy today.

**Sequencing rule (important):** the `MissionSpec`/`regime`/`PhaseTransition` **schema hooks
should land in Core v0.x during Phase 1** (when Core is already being extended for autonomy),
even though the implementations land in Phase 3. Retrofitting multi-regime into a frozen waist
later is precisely the leaky-god-interface failure the charter warns about (§9).

---

## 4. The dual-use boundary (load-bearing)

Trajectory work is the most export-sensitive addition, so the boundary is drawn in the schema
itself:

- **In the open commons:** `TrajectoryRef`/`ManeuverBudget` are **descriptive design-time
  artifacts** — reference arcs, Δv/ToF, window feasibility — for trade studies. They are not a
  command format and carry no guidance/closed-loop targeting.
- **Out / partitioned:** turning a reference trajectory into **executable maneuver guidance for
  real flight hardware** (operational targeting) and **guided atmospheric EDL** remain excluded,
  per [EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md) and
  charter §10.5. `earth_interface` is modeled as a **delivery/recovery event with a mass/▵v
  accounting**, not a guided re-entry simulator. The `operational_targeting` capability tag gates
  anything that crosses this line at the registry/Bridge boundary.

---

## 5. Backward compatibility & migration

- Existing scenarios are valid Missions with one `surface` Phase; no author action required.
- Consumers that predate the `regime` field ignore it (proto3 unknown-field tolerance) and
  continue to operate on single-phase, single-regime missions.
- Bench scenarios pin the Core interface minor; adding the mission schema is a minor bump with a
  deprecation-free additive path (conventions.md §3, §11).

---

## 6. Open questions (deferred to the RFC / implementation)

- **Regime completeness:** is the §1.2 enum sufficient for icy-moon and multi-target tours, or do
  we need `aerobraking` / `formation` regimes? (Resolve via reference scenarios, not speculation.)
- **Where phase-sequencing logic lives:** a thin sequencer in the scenario runtime ([Sim](sim.md))
  vs. an orchestration concern in [Studio](studio.md)/[Ops](ops.md). Leaning runtime for the
  mechanism, orchestration for the policy.
- **Trajectory representation:** how much structure `TrajectoryRef` carries (waypoints + budgets
  vs. full state history) without becoming a back-door command format.
- **Co-optimization coupling:** how tightly `MissionSpec` encodes the trajectory ⇄ fleet ⇄ swarm
  ⇄ economics coupling vs. leaving it to [Studio](studio.md)'s trade-study engine.
