# RFC 0003: Append-only Core vocabulary additions for Phase-1 Wave-10 consumers

- **Status:** proposed
- **Author(s):** djankov
- **Created:** 2026-07-03
- **Affects Core:** yes — two **append-only** members: one added to the SADF `SensorKind`
  vocabulary, one to the `CapabilityTag` vocabulary (the latter also added to
  `GATED_CAPABILITY_TAGS`). Both are string-enum additions with **no wire change**;
  `CORE_INTERFACE_VERSIONS` stays frozen at `0.1.0` ([VERSIONING.md §4](../VERSIONING.md)). Goes
  through the RFC process because it touches the Core narrow waist
  ([GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)).

## Summary

Two independent, additive Phase-1 (Wave-10) touches to Core's closed vocabularies, batched into
one RFC because they are the same *kind* of change (append a string-enum member; no schema/wire
break) and land together:

1. **`SensorKind.RESOURCE_STORAGE = "resource_storage"`** — an **ISRU stored-mass gauge** that
   reports the *cumulative extracted/stored resource* a swarm asset holds (for the anchor
   scenario, water in kg). The Core half of **RM-P1-SIM-02** (astro-mine-sim#21): it lets
   `Astro-Mine-Sim` render stored-water as a first-class `SensorReading` in the Core
   `Observation` / MCAP stream that `Astro-Mine-Bench` scores.
2. **`CapabilityTag.COMMS_LIVE_MISSION_LINK_PREDICTION = "comms.live_mission_link_prediction"`**,
   added to `GATED_CAPABILITY_TAGS` — a **reserved, dual-use-gated** capability so that
   high-fidelity link prediction *tied to a live mission* can be OPA-gated out of the open
   commons. The Core half of **RM-P1-LINK-13** (astro-mine-link#20): Link's default open path
   predicts contacts from public ephemerides + parametric antenna models, and this tag marks the
   partitioned operational path.

Both are one-line additions to `sadf/enums.py` and the two JSON Schemas that enumerate these
vocabularies (`sadf.schema.json`, `registry/manifest.schema.json`).

## Motivation

The anchor scenario is lunar polar **water-ice prospecting and extraction**. Bench defines
`water_mass` (kg of water stored over a campaign) and `energy_per_kg` (its energy cost) as
first-class metrics (bench.md §3), and the roadmap's Phase-1 Sim scope (RM-P1-SIM-02) calls for a
reduced-order ISRU extraction/storage process model that emits stored mass.

But there is no way to *observe* stored mass through the narrow waist. `SensorKind` (sim.md §1/§3;
prospect.md §3) enumerates imaging, spectrometers, contact, comms-link-state, and so on — every
one a sensor that renders an observation *of the environment*. None names a **self-state mass
gauge** reporting an accumulating on-board quantity. Without it, a Sim ISRU sensor would have to
either (a) mislabel stored mass under an unrelated kind, or (b) smuggle it through a private
side-channel that bypasses the Core `Observation` contract — the exact edge→edge coupling
`conventions.md §1.1` forbids, and which would leave Bench unable to score productivity from the
standard MCAP.

**Why now, and why via RFC.** Phase-0 Sim (RM-P0-SIM-11, astro-mine-sim#19) deliberately deferred
the ISRU sensor: Core v0.1 was frozen for Phase 0, and adding a `SensorKind` member is a Core
narrow-waist change that must go through governance. Phase 1 is the reserved window for additive
Core evolution (phase-1 roadmap, Core section), so the addition is made properly here. The cost of
*not* doing it is that the flagship metric of the anchor benchmark (`water_mass`) cannot be
computed from a standard run — i.e., the Phase-1 "the flywheel turns" milestone has no productivity
signal to rank on.

## Design

### The change

One member, append-only, at the end of the enum:

```python
class SensorKind(StrEnum):
    ...
    COMMS_LINK_STATE = "comms_link_state"
    # ISRU stored-mass gauge: cumulative extracted/stored resource (e.g. water, kg).
    RESOURCE_STORAGE = "resource_storage"
```

and the mirrored value `"resource_storage"` appended to `$defs/SensorKind.enum` in
`sadf/schema/sadf.schema.json` (the JSON Schema is the canonical source of truth; the Pydantic
enum mirrors it — the `check_model_drift.py` guard and the `test_schema_enum_matches_python_enum`
parity test enforce that they agree).

### How it is used (Sim / Bench, out of scope for Core)

- A Fleet **SADF** asset that does ISRU declares a sensor with `kind: resource_storage`.
- **Sim** (RM-P1-SIM-02) runs a reduced-order extraction/storage process model and its ISRU
  sensor forward-model renders the **cumulative stored mass** as an ordinary
  `messages.SensorReading` — reusing the *existing* message fields, no message-schema change:

  ```
  SensorReading(sensor="isru_tank", values=[stored_kg], unit="kg", resource_species="water")
  ```

  This rides in the per-tick `Observation.sensors` list / MCAP exactly like every other reading.
- **Bench** reads the channel from the standard MCAP and computes `water_mass` / `energy_per_kg`.
  Bench never imports Sim and Sim never imports Bench — the `Observation` stream is the only seam.

Crucially, `SensorReading` **already** carries `values`, `unit`, and `resource_species`, so **no
message schema changes** — only the `SensorKind` vocabulary gains the term that lets an asset
*declare* such a sensor and lets consumers *route* the channel by kind.

### Semantics

`RESOURCE_STORAGE` reports a **self-state accumulator** (a monotonic-under-extraction on-board
quantity), distinct from the environment-sensing kinds. It is uncertainty-honest like any reading
(the `SensorReading` noise/validity fields apply); it is **not** a ground-truth resource-field
probe — Sim still renders resource *observations* of a Prospect field through the existing
spectrometer/assay kinds, never a point guess (prospect.md §6).

### The second change: `comms.live_mission_link_prediction` (gated)

```python
class CapabilityTag(StrEnum):
    ...
    GROUND_TRUTH_ACCESS = "ground_truth_access"          # existing gated tag
    COMMS_LIVE_MISSION_LINK_PREDICTION = "comms.live_mission_link_prediction"  # new, gated

GATED_CAPABILITY_TAGS = frozenset({
    CapabilityTag.OPERATIONAL_TARGETING,
    CapabilityTag.GROUND_TRUTH_ACCESS,
    CapabilityTag.COMMS_LIVE_MISSION_LINK_PREDICTION,   # added
})
```

with the mirrored value appended to the `$defs/CapabilityTag` enum in **both** schemas that carry
that vocabulary (`sadf.schema.json` and `registry/manifest.schema.json`).

**Why gated.** `Astro-Mine-Link` (link.md §9) draws a hard line: generic comms geometry, link
budgets, and DTN modeling for *science/simulation* are open commons, but *precise, real-asset
link prediction tied to a live mission* becomes operational availability intelligence. Adding the
tag to `GATED_CAPABILITY_TAGS` makes the SADF loader reject any open-commons asset/plugin that
declares it (exactly like `operational_targeting`), which is the Core-level substrate the Hub OPA
download gate (RM-P1-HUB-05) enforces. **RM-P1-LINK-13's** open deliverable — forward-looking
Earth-link windows from public ephemerides — needs *no* gated capability; the tag simply reserves
the name for the P2 live-prediction path that is out of scope today (link.md §12).

## Impact on Core

**Additive, append-only, non-breaking — the narrow waist does not widen.** `SensorKind` is a
closed vocabulary that already grows by append under the platform's never-break rule
(`core.md`; `conventions.md §6`):

- **No wire/proto change.** `SensorKind` is a *string* enum surfaced only in `sadf.schema.json`;
  it is **not** a protobuf enum, so `buf breaking` is unaffected and old wire payloads decode
  unchanged.
- **Interface version frozen.** Per VERSIONING §4, `CORE_INTERFACE_VERSIONS` stays `0.1.0`; an
  older consumer that has never heard of `resource_storage` simply doesn't route that channel.
  Reproducibility is held by tag-pin + content hashes, not the version number.
- **No new message type, no new API surface.** Consumers that don't care are unaffected; the
  mechanism (the extraction/storage model, the forward-model) lives entirely in Sim, above the
  waist — Core only gains the *name*.

The **package** version of `astro-mine-core` bumps a minor at the next milestone cut (a Git tag,
per VERSIONING §2.1), and downstreams re-pin to it — during incubation a consumer may pin the
commit `rev` directly.

## Alternatives considered

1. **Reuse an existing `SensorKind` (e.g. `MASS_SPECTROMETER` or `CONTACT`).** Rejected:
   semantically wrong (those sense the environment; this reports on-board accumulated mass),
   which would make Bench's routing-by-kind and any downstream analysis misleading. A benchmark
   metric should not be inferred from a mislabeled channel.
2. **A dedicated `StoredMass` / telemetry message instead of a `SensorReading`.** Rejected: it
   would add a *new message type* to the hot path (a bigger Core change) for something the
   existing `SensorReading(values, unit, resource_species)` already expresses exactly. Prefer the
   smaller, append-only enum addition over new schema.
3. **Keep it in Sim as a private channel / MCAP side-topic.** Rejected: bypasses the Core
   `Observation` contract (`conventions.md §1.1`) and leaves Bench unable to score productivity
   from the standard run — defeating the purpose.
4. **Names considered:** `ISRU_TANK`, `MASS_GAUGE`, `RESOURCE_STORAGE`. Chose `RESOURCE_STORAGE`
   as the most generic (not water- or tank-specific) — the same gauge kind serves future stored
   species and body-agnostic ISRU, consistent with the platform's "extend, don't specialize"
   posture.

## Documentation impact

Minimal. The Phase-1 roadmap already names both additions (RM-P1-SIM-02: *"a new
`RESOURCE_STORAGE` `SensorKind` via RFC"*; RM-P1-LINK-13: *"tag `live-mission-link-prediction`…
via the Core capability vocabulary"*), so no roadmap edit is required. On acceptance, Sim
(RM-P1-SIM-02) + Bench consume the SensorKind, and Link (RM-P1-LINK-13) + the Hub OPA gate consume
the capability tag; no other architecture doc changes.

## Unresolved questions

- **Multi-species storage.** The anchor needs only water. If future scenarios store multiple
  species per asset, whether that is N readings (one per `resource_species`) or a structured
  payload is deferred to the Sim implementation — it does **not** affect this enum member.
- **Acceptance.** Pending steering-group (Phase-0 founding team) sign-off, tracked with the Core
  implementation PR (astro-mine-core#36) and its Wave-10 consumers — the Sim ISRU sensor
  (astro-mine-sim#21) and the Link Earth-link-window product (astro-mine-link#20).
