# RFC 0007: Put the units / frames / time vocabulary on the wire

- **Status:** draft
- **Author(s):** djankov
- **Created:** 2026-07-08
- **Affects Core:** yes — one **additive** schema file (`units.proto`: `ReferenceFrame`,
  `PlanetaryCRS`, `Epoch`, `EpochWindow`, `FrameClass`, `TimeScale`) plus **additive** typed fields
  on existing messages, with **no change to any existing field, enum, or wire type**;
  `CORE_INTERFACE_VERSIONS` stays frozen at `0.1.0` ([VERSIONING.md §4](../VERSIONING.md)). Touches
  the Core narrow waist, so it goes through the RFC process per
  [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

Core owns the platform's frame/CRS/time vocabulary — `ReferenceFrame`, `PlanetaryCRS`, `Epoch`,
`EpochWindow` — but owns it **only in Python**. On the wire, in the Protobuf schema that every
non-Python component consumes, a frame is a bare `string` and an epoch is a bare `double`. This RFC
adds `astro_mine/core/units/_proto/units.proto` carrying those types and their closed vocabularies,
threads them into the message catalog as **additive** typed fields, and thereby makes the
"frames and units are explicit, never implicit" guarantee a property of the *contract* rather than
of one language binding.

## Motivation

`conventions.md §5` and `core.md §2` are unambiguous:

> All spatial data is tagged with an explicit planetary CRS … No implicit Earth/WGS84 assumptions.
> [Core](core.md) defines the frame/time **types** (`Epoch`, `ReferenceFrame`, `PlanetaryCRS`) and
> the `require_frame`/`require_crs` fail-loud guards.

Core does define them — in `astro_mine/core/units/model.py`, as Pydantic v2 models with validators
that reject a blank frame name, a non-positive reference radius, and a missing time scale.

The Protobuf schema does not. Today:

```proto
message Volume      { string frame = 1; … }           // any string. "moon"? "MOON_ME"? "WGS84"? ""?
message GotoTask    { string target_frame = 1; … }
message HaulTask    { string from_frame = 1; string to_frame = 2; … }
message ContactPlan { optional double epoch_start_tdb_s = 4; … }   // scale by naming convention only
message Maneuver    { double epoch_tdb_s = 1; … }
```

`grep -rn "message ReferenceFrame\|message PlanetaryCRS\|message Epoch" schemas/proto/` returns
nothing. There is no `PlanetaryCRS` on the wire at all.

**Consequences.**

1. **The fail-loud guarantee stops at the language boundary.** A Python producer that constructs a
   `ReferenceFrame` gets validation. The same value, serialized and read by a TypeScript or C++
   consumer, is an unvalidated `string`. Core's central safety property — *there is no implicit
   Earth/WGS84 anywhere* — is enforced in exactly one of the three languages Core generates code for.
2. **Every non-Python consumer re-derives the vocabulary, and its guards.** This is not speculative.
   Standing up the View globe (`RM-P1-VIEW-02`, astro-mine-view#6) required writing a TypeScript
   mirror of `ReferenceFrame` / `PlanetaryCRS` / `Epoch` / `EpochWindow` / `FrameClass` / `TimeScale`
   **and** a TypeScript reimplementation of `require_frame` / `require_crs`, because Core's generated
   TS client contains none of them. The mirror is pinned by a test that asserts the anchor CRS's PROJ
   string byte-for-byte against the string Worlds emits — a test that exists solely to detect drift
   between two copies of a vocabulary that should have one source.
3. **Nothing on the wire says what a `double` means.** `epoch_start_tdb_s` carries its scale in its
   *name*. A field renamed, or a new epoch field added without the `_tdb_s` suffix, silently loses
   the one thing `TimeScale` exists to make explicit. Core deliberately made `Epoch.scale` required
   with no default so "a scaleless epoch fails loudly" — the wire schema then drops the scale.
4. **`PlanetaryCRS` is absent entirely.** The world bundle carries a CRS (Worlds' own JSON Schema);
   the Core message catalog cannot express one. Any component that wants to hand another component a
   georeferenced product must pass the CRS out of band or by convention.

The cost of not doing it grows with every non-Python consumer. View is the first. `Bridge` (ROS 2/DDS,
C++), the `Ops`/`View` browser clients, and any external plugin author are next. Each one either
re-derives the vocabulary or, more likely, treats the `string` as opaque and lets an Earth-shaped
value through.

**Why now.** Two forcing functions. First, the C++ and TypeScript codegen already exist
(`codegen/cpp`, `codegen/ts`), so the gap is now observable rather than theoretical. Second, Phase 1
adds the first real non-Python consumer of Core geometry (View) and Phase 2 adds two more
(`Ops`, `Bridge`). Fixing the schema before those consumers harden their own mirrors is much cheaper
than reconciling three mirrors later.

## Design

### 1. A new schema file: `astro_mine/core/units/_proto/units.proto`

Mirrors `astro_mine/core/units/model.py` and `enums.py` field-for-field. Closed vocabularies become
proto enums with an explicit `_UNSPECIFIED = 0` zero value, so an unset scale or frame class is
*representable as invalid* and fails the guard rather than defaulting.

```proto
syntax = "proto3";
package astro_mine.core.units;

// Admissible epoch time scale. Only the SI-second SPICE ephemeris scales exist at the waist;
// a civil/atomic scale (UTC/TAI) is unrepresentable by construction (conventions.md §5).
enum TimeScale {
  TIME_SCALE_UNSPECIFIED = 0;   // invalid: a scaleless epoch must fail loudly
  TIME_SCALE_TDB = 1;
  TIME_SCALE_ET = 2;            // SPICE alias; identical to TDB
}

enum FrameClass {
  FRAME_CLASS_UNSPECIFIED = 0;
  FRAME_CLASS_BODY_FIXED = 1;
  FRAME_CLASS_INERTIAL = 2;
  FRAME_CLASS_TOPOCENTRIC = 3;
}

// A named reference frame. `name` is a SPICE frame name (e.g. "MOON_ME", "J2000"); `center` is the
// SPICE body it is centred on, absent for a centre-agnostic sky frame. Core names it;
// astro-mine-spice resolves it (RFC-0002).
message ReferenceFrame {
  string name = 1;
  FrameClass frame_class = 2;
  optional string center = 3;
}

// An explicit planetary CRS: the minimum needed to place spatial data without guessing.
// `reference_radius_m` is the PROJ `+R`. `projection` carries a PROJ/WKT string for a projected
// CRS; absent means body-fixed geographic. No field has an Earth default.
message PlanetaryCRS {
  string body = 1;
  string body_fixed_frame = 2;
  double reference_radius_m = 3;
  optional string projection = 4;
  optional string datum = 5;
}

// An instant in TDB/ET: SI seconds past the J2000 TDB epoch. `scale` is required — an epoch whose
// scale is TIME_SCALE_UNSPECIFIED is invalid.
message Epoch {
  double tdb_seconds = 1;
  TimeScale scale = 2;
}

// A half-open interval [start, end); `end` strictly after `start`.
message EpochWindow {
  Epoch start = 1;
  Epoch end = 2;
}
```

### 2. Additive typed fields on existing messages

No existing field changes number, type, or meaning. Each message that carries a frame or epoch as a
primitive gains an optional typed sibling:

| Message | Existing (kept) | Added |
|---|---|---|
| `Volume` | `string frame = 1` | `optional ReferenceFrame frame_ref = N` |
| `GotoTask` · `SampleTask` · `HopTask` · `DockTask` | `string target_frame` / `site_frame` / `launch_frame` / `approach_frame` | `optional ReferenceFrame …_ref = N` |
| `HaulTask` | `string from_frame = 1`, `string to_frame = 2` | `optional ReferenceFrame from_frame_ref`, `to_frame_ref` |
| `ContactPlan` | `optional double epoch_start_tdb_s = 4`, `epoch_end_tdb_s = 5` | `optional EpochWindow window = N` |
| `ContactInterval` | `double start_tdb_s = 3`, `end_tdb_s = 4` | `optional EpochWindow window = N` |
| `Maneuver` · `ReferenceState` (`mission.proto`) | `double epoch_tdb_s = 1` | `optional Epoch epoch = N` |

Messages that carry a georeferenced product gain an `optional PlanetaryCRS crs` where one is implied
today by convention. The exact field set is an implementation detail; the rule is that no existing
field number or type moves.

Producers SHOULD populate the typed field; consumers MUST prefer it when present and MAY fall back to
the primitive. A follow-up RFC, once every producer populates the typed field, may deprecate the
primitives — that is a **separate** decision and explicitly not proposed here.

### 3. Generated guards, not just generated types

Types alone move the problem. `require_frame` / `require_crs` are what make the vocabulary safe, and
today they exist only in `astro_mine/core/units/validate.py`. This RFC proposes that Core ship the
guard **semantics** as a normative part of the contract:

- The validation rules (non-empty whitespace-free tokens; `reference_radius_m > 0`;
  `scale != UNSPECIFIED`; `EpochWindow.end > start`; **rejection of any Earth CRS marker** —
  `WGS84`, `EPSG:4326`) are specified in `core.md §2` as MUST requirements on *any* Core binding.
- Core's Python `validate.py` becomes the reference implementation.
- Each generated binding carries a hand-written guard module implementing them, with a shared
  conformance-test vector file (`schemas/conformance/units.json`) that every binding runs.

The conformance vectors are the deliverable that actually prevents drift; the proto file alone would
not have caught the View mirror's divergence.

### 4. Distribution

Generating TS types nobody can import solves nothing. `codegen/ts/package.json` is
`private: true`, `version: 0.0.0`, and unpublished, which is why View mirrors rather than depends.
This RFC does **not** decide the registry question — see *Unresolved questions* — but it records that
the schema change is only load-bearing once a consumer can depend on the output.

## Impact on Core

**Does this widen the narrow waist?** It widens the *schema* and narrows the *semantics*. Six small,
dependency-free value types are added — no behaviour, no heavy dependency, no SPICE resolution
(`core.md §2.3` still forbids that; name→geometry stays in `astro-mine-spice`, RFC-0002). What is
gained is that the waist now expresses, rather than merely documents, the frame/CRS/time contract.

The capability cannot live in a plugin: it *is* the vocabulary plugins are written against. A plugin
defining `PlanetaryCRS` would be a private schema, which `conventions.md §1.1` forbids.

**Breaking changes:** none. All additions are new message types and new optional fields; existing
fields keep their numbers and types. `CORE_INTERFACE_VERSIONS` stays at `0.1.0`.

**Migration path:** producers populate typed fields opportunistically; consumers prefer typed and fall
back to primitive. The Python `units` models gain `.to_proto()` / `.from_proto()` and remain the
public Python surface, so no Python consumer changes. `astro-mine-view`'s `frames/` mirror becomes a
re-export once distribution is settled, and its drift-detection test is retired.

## Alternatives considered

**Do nothing; let each binding mirror.** The status quo. It works — View's mirror is 130 lines and
test-pinned — and it costs nothing today. It fails at N > 1 consumers, and it leaves Core's headline
safety property (no implicit WGS84) unenforced on the wire, where it matters most. Rejected because
the drift it invites is silent and the failure mode is a plausibly-rendered wrong body.

**Ship the types but not the guards.** Cheaper, and superficially sufficient. Rejected: a
`PlanetaryCRS` message with a `projection` field happily carries `+proj=longlat +datum=WGS84`. The
guards, not the types, are what `conventions.md §5` actually promises. Types without conformance
vectors would have let the View mirror drift undetected.

**Replace the primitives outright (`string frame` → `ReferenceFrame frame`).** Cleanest end state.
Rejected for now: it is a breaking wire change, and `CORE_INTERFACE_VERSIONS` is deliberately frozen
at `0.1.0` until Phase 3. Deferred to a follow-up RFC once producers have populated the typed fields.

**Put the CRS in each producer's own schema (status quo for Worlds).** Worlds already validates its
bundle CRS. Rejected as a general answer: it means every producer/consumer pair negotiates geometry
bilaterally, which is precisely the private side-channel the narrow waist exists to prevent.

## Unresolved questions

- **Distribution of the generated TypeScript client.** Un-private `codegen/ts` and publish to a
  private registry (GitHub Packages), vendor the generated file into consumers, or expose it as a
  git dependency? This blocks the RFC's practical benefit but not its acceptance, and it is entangled
  with the same decision pending for `@astro-mine/view`. Deferrable to implementation.
- **Do the conformance vectors live in Core or in `astro-mine-seal`-style shared tooling?** Proposed:
  Core, as `schemas/conformance/`, since they are part of the contract.
- **Should `SiUnit` also go on the wire?** Core's `unit` fields are already validated strings against
  `KNOWN_UNITS`. Composite units (`kg·m⁻³`) are deliberately not enumerated (`enums.py`), so an enum
  would be wrong. Proposed: leave `unit` a string, and specify `require_si_unit` in the conformance
  vectors instead. Not blocking.
- **Deprecation timeline for the primitive fields.** Explicitly out of scope; a follow-up RFC once
  every producer populates the typed fields.
