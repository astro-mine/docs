# RFC 0007: Put the units / frames / time vocabulary on the wire

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-08
- **Accepted:** 2026-07-09
- **Implemented in:** Phase 1 — `RM-P1-CORE-06/07/08` (Core), `RM-P1-VIEW-06` (View), with adopter
  deliverables in Worlds, Link, Prospect, Allocate, Guard, and Studio. Extends the Phase-0
  units waist (`RM-P0-CORE-06`) onto the wire, using the codegen and contract-test machinery
  `RM-P0-CORE-07` established.
- **Affects Core:** yes — one **additive** interface (`units`) realized on Core's three-part schema
  stack: a canonical `units.schema.json`, the existing Pydantic models, and a new
  `units.proto` (`ReferenceFrame`, `PlanetaryCRS`, `Epoch`, `EpochWindow`), plus **additive** typed
  fields on existing messages and two additive Cap'n Proto structs. **No existing field number,
  wire type, or meaning changes**, `buf breaking` gates it, and `CORE_INTERFACE_VERSIONS` stays at
  `0.1.0` for every interface ([VERSIONING.md §4](../VERSIONING.md)) with **no new entry** — `units`
  moves with the package rather than being independently negotiated. Touches the Core narrow waist,
  so it goes through the RFC process per
  [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

Core owns the platform's frame/CRS/time vocabulary — `ReferenceFrame`, `PlanetaryCRS`, `Epoch`,
`EpochWindow` — but owns it **as hand-written Pydantic only**. It has no canonical JSON Schema, so it
never reaches the layer `core.md §2` (principle 5) calls the source of truth, and from which every
language binding is generated. The consequence is visible on the wire: the Protobuf control-plane
schema carries a frame as a bare `string` and an epoch as a bare `double`, and has no `PlanetaryCRS`
at all.

This RFC gives `units` the same three-part schema stack every other Core interface has — canonical
JSON Schema → Pydantic → generated wire forms — threads the types into the message catalog as
**additive** fields, and ratifies the `require_frame` / `require_crs` guard semantics as a normative,
conformance-tested part of the contract. The goal is to make "frames and units are explicit, never
implicit" a property of the *contract* rather than of one language binding.

## Motivation

`conventions.md §5` is unambiguous:

> All spatial data is tagged with an explicit planetary CRS (body-fixed frame, datum, projection)
> resolved via SPICE/PROJ. No implicit Earth/WGS84 assumptions. […] [Core](../architecture/core.md)
> defines the frame/time **types** (`Epoch`, `ReferenceFrame`, `PlanetaryCRS`) and the
> `require_frame`/`require_crs` fail-loud guards […]

and `core.md §2` principle 8 restates it as a Core architecture principle: *"Every quantity has
explicit units (SI) and every spatial value an explicit reference frame. No implicit conventions."*

Core does define the types — in `astro_mine/core/units/model.py`, as Pydantic v2 models with
validators that reject a blank frame name, a non-positive reference radius, and a missing time
scale. What it does not have is the layer above them. `core.md §2` principle 5 is explicit:

> Each interface is a language-neutral spec (Protobuf / JSON Schema) from which all language
> bindings are generated. **The spec is the source of truth, not any one implementation.**

`units` has no such spec. Every other Core interface — `sadf`, `objective`, `messages`, `mission`,
`registry`, `policy`, `provenance` — ships a canonical `*.schema.json` that
`scripts/check_model_drift.py` pins its Pydantic model against and that
`scripts/build_schema_bundle.py` publishes. `units` ships neither, and it is absent from both
scripts' declared schema lists.

**Where the vocabulary did and did not reach the wire.** Core has two canonical wire formats
(`conventions.md §3`): Protobuf for the control plane, Cap'n Proto for the per-tick hot path. They
disagree.

- The **hot path already carries the types.** `observation.capnp` defines `struct ReferenceFrame` and
  `struct Epoch`, and `StateSample.frame` is a typed `ReferenceFrame`, not a string. It carries the
  closed vocabularies as text: `frameClass @1 :Text`, `scale @1 :Text`.
- The **control plane carries none of them.** In `schemas/proto/`:

  ```proto
  message Volume      { string frame = 1; … }           // any string. "moon"? "MOON_ME"? "WGS84"? ""?
  message GotoTask    { string target_frame = 1; … }
  message HaulTask    { string from_frame = 1; string to_frame = 2; … }
  message ContactPlan { optional double epoch_start_tdb_s = 4; … }   // scale by naming convention only
  message Maneuver    { double epoch_tdb_s = 1; … }
  message TrajectoryRef { string frame = 2; … }
  ```

  `grep -rn "message ReferenceFrame\|message PlanetaryCRS\|message Epoch" schemas/proto/` returns
  nothing.
- `PlanetaryCRS` and `EpochWindow` reach **neither** wire format, in any language.

So of the six types, two are on one of two wires, and the two that carry the actual anti-WGS84
guarantee are on neither.

**Consequences.**

1. **The fail-loud guarantee stops at the language boundary.** A Python producer that constructs a
   `ReferenceFrame` gets validation. The same value, serialized into a control-plane message and read
   by a TypeScript, C++, or Rust consumer, is an unvalidated `string`. Core's central safety property
   — *there is no implicit Earth/WGS84 anywhere* — is enforced in exactly one of the four languages
   Core generates bindings for (`core.md §4`: "Python, C++, Rust, TypeScript").
2. **Every non-Python consumer re-derives the vocabulary, and its guards.** This is not speculative.
   Standing up the View globe (`RM-P1-VIEW-02`, astro-mine-view#6) required writing a TypeScript
   mirror of `ReferenceFrame` / `PlanetaryCRS` / `Epoch` / `EpochWindow` / `FrameClass` / `TimeScale`
   (`lib/src/frames/types.ts`, 80 lines) **and** a TypeScript reimplementation of `require_frame` /
   `require_crs` (`guards.ts`, 139 lines), because Core publishes neither a JSON Schema View could
   generate types from nor an importable TS client. The mirror is pinned by a test asserting the
   anchor CRS's PROJ string byte-for-byte against the string Worlds emits — a test that exists solely
   to detect drift between two copies of a vocabulary that should have one source.
3. **The mirror has already drifted, and nothing caught it.** View's `requireCrs` rejects any
   PROJ/WKT/EPSG string containing an Earth marker (`wgs84`, `epsg:4326`, …); Core's `require_crs`
   does not — it only requires presence and well-formedness. The two guards named after the same
   contract enforce different rules today. Whether View's stricter rule is *right* is a separate
   question (see [Design §3](#3-guard-semantics-as-contract-not-generated-code)); that the divergence
   went unnoticed is the point.
4. **Nothing on the control-plane wire says what a `double` means.** `epoch_start_tdb_s` carries its
   scale in its *name*. A field renamed, or a new epoch field added without the `_tdb_s` suffix,
   silently loses the one thing `TimeScale` exists to make explicit. Core deliberately made
   `Epoch.scale` required with no default so "a scaleless epoch fails loudly" — and the hot-path
   schema honours that while the control-plane schema drops it.
5. **`PlanetaryCRS` is absent from every schema layer.** Worlds does not work around this with a
   private schema — `worlds/crs/__init__.py` imports and reuses Core's `PlanetaryCRS` model, exactly
   as intended — but it can only do so *because it is Python*. It serializes the CRS into `world.json`
   as an ad-hoc `model_dump()` with no schema behind it, and any component that wants to hand another
   component a georeferenced product over a Core message cannot express the CRS at all.

The cost of not doing it grows with every non-Python consumer. View is the first. `Ops` and `Bridge`
(C++/ROS 2, Phase 2) are next, alongside the Phase-2 **Earth-analog** field deployments — which make
the CRS rules load-bearing in the one setting where an Earth CRS is legitimate and must be
*explicit* rather than *assumed*. Each new consumer either re-derives the vocabulary or, more likely,
treats the `string` as opaque and lets an Earth-shaped value through.

**Why now.** Two forcing functions. First, `buf` already generates C++, Rust, and TypeScript clients
(`buf.gen.langs.yaml`), so the gap is observable rather than theoretical. Second, Phase 1 adds the
first real non-Python consumer of Core geometry (View) and Phase 2 adds two more. Fixing the schema
before those consumers harden their own mirrors is much cheaper than reconciling three later.

## Design

### 1. The three-part schema stack for `units`

The change starts at the layer Core calls the source of truth, not at the wire.

**1a. Canonical JSON Schema (new).** `src/astro_mine/core/units/schema/units.schema.json`, `$id`
`https://schemas.astro-mine.org/core/units/v0.1/units.schema.json`, defining `ReferenceFrame`,
`PlanetaryCRS`, `Epoch`, `EpochWindow`, `FrameClass`, `TimeScale`. It is added to `JSON_SCHEMAS` in
`scripts/build_schema_bundle.py` and brought under `scripts/check_model_drift.py`, which then pins
the existing hand-written Pydantic models against it exactly as it does for every other interface.
This is the layer a TypeScript consumer can generate types from today, without waiting on the
distribution question in §4 — and it is what actually retires View's mirror.

**1b. Pydantic (unchanged).** `astro_mine/core/units/model.py` and `enums.py` stay the public Python
surface, now drift-checked against 1a. No Python consumer changes.

**1c. Protobuf (new).** `schemas/proto/astro_mine/core/units/_proto/units.proto`, generating to
`src/astro_mine/core/units/_proto/units_pb2.py`. Package `astro_mine.core.units.v0`, matching the
`.v0` convention every other Core proto uses and the `v0.1` schema `$id`
(`buf.yaml` waives `PACKAGE_VERSION_SUFFIX` for exactly this reason).

```proto
syntax = "proto3";

package astro_mine.core.units.v0;

// A named reference frame. `name` is a SPICE frame name (e.g. "MOON_ME", "J2000"); `center` is the
// SPICE body it is centred on, absent for a centre-agnostic sky frame. Core names it;
// astro-mine-spice resolves it (RFC-0002).
//
// `frame_class` is a closed vocabulary carried as `string` (the SADF pattern; see below): the empty
// default is not a member, so an unset class is representable as invalid and fails the guard.
message ReferenceFrame {
  string name = 1;
  string frame_class = 2;  // FrameClass (closed vocab as string)
  optional string center = 3;
}

// An explicit planetary CRS: the minimum needed to place spatial data without guessing.
// `reference_radius_m` is the PROJ `+R`; its proto3 default of 0.0 is rejected by `require_crs`.
// `projection` carries a PROJ/WKT string for a projected CRS; absent means body-fixed geographic.
// No field has an Earth default.
message PlanetaryCRS {
  string body = 1;
  string body_fixed_frame = 2;
  double reference_radius_m = 3;
  optional string projection = 4;
  optional string datum = 5;
}

// An instant in TDB/ET: SI seconds past the J2000 TDB epoch. `scale` is required — an epoch whose
// scale is the empty default is invalid.
message Epoch {
  double tdb_seconds = 1;
  string scale = 2;  // TimeScale (closed vocab as string)
}

// A half-open interval [start, end); `end` strictly after `start`. Both fields are message-typed,
// so absence is detectable and rejected.
message EpochWindow {
  Epoch start = 1;
  Epoch end = 2;
}
```

**Closed vocabularies stay `string`, not proto enums.** This is deliberate and follows the rule every
existing Core `.proto` header states: *"Closed-vocabulary fields are carried as `string` (the SADF
pattern): the type authority is the JSON Schema / Pydantic, and string↔string keeps the round-trip
byte-exact and drift-free."* Three reasons it is the right call here specifically:

- `observation.capnp` already encodes these same two vocabularies as `Text`, and `hotpath.py` writes
  `rf.frame_class.value` / `e.scale.value` into them. A proto enum would give **one Core type two
  different wire encodings** — an int on the control plane, `"body_fixed"` on the hot path.
- The fail-loud property an `_UNSPECIFIED = 0` zero value buys is already had for free: proto3's
  string default is `""`, which is not a member of either `StrEnum` and which `_validate_token`
  rejects as not a non-empty, whitespace-free token.
- `FrameClass` and `TimeScale` are Python `StrEnum`s whose *values* (`"body_fixed"`, `"tdb"`) are the
  canonical JSON representation. Strings round-trip them byte-exact through every layer.

`TrajectoryRef.frame` and friends make `units.proto` the **first cross-file import** in Core's proto
set — `Vec3` and `Provenance` are deliberately duplicated per package today, so each file is
self-contained. Importing one shared vocabulary file is the point of this RFC and is what `buf`
exists to manage; it does not license a general relaxation of that per-file self-containment.

**1d. Cap'n Proto (additive).** `observation.capnp` gains `struct PlanetaryCRS` and
`struct EpochWindow` for parity; the existing `ReferenceFrame` / `Epoch` structs are unchanged.
Cap'n Proto field IDs are append-only, so this is additive. Adding new structs does not perturb the
existing ones' encoding.

### 2. Additive typed fields on existing messages

No existing field changes number, type, or meaning. Each message that carries a frame or epoch as a
primitive gains an optional typed sibling at the next free tag:

| Message (file) | Existing (kept) | Added |
|---|---|---|
| `Volume` (messages) | `string frame = 1` | `optional ReferenceFrame frame_ref` |
| `GotoTask` · `SampleTask` · `HopTask` · `DockTask` (messages) | `target_frame` / `site_frame` / `launch_frame` / `approach_frame` | `optional ReferenceFrame …_ref` |
| `HaulTask` (messages) | `string from_frame = 1`, `string to_frame = 2` | `optional ReferenceFrame from_frame_ref`, `to_frame_ref` |
| `ContactPlan` (messages) | `optional double epoch_start_tdb_s = 4`, `epoch_end_tdb_s = 5` | `optional EpochWindow window` |
| `ContactInterval` (messages) | `double start_tdb_s = 3`, `end_tdb_s = 4` | `optional EpochWindow window` |
| `Route` (messages) | `optional double earliest_delivery_tdb_s = 5` | `optional Epoch earliest_delivery` |
| `Maneuver` · `ReferenceState` (mission) | `double epoch_tdb_s = 1` | `optional Epoch epoch` |
| `TrajectorySegment` (mission) | `double start_epoch_tdb_s = 2`, `end_epoch_tdb_s = 3` | `optional EpochWindow window` |
| `TrajectoryRef` (mission) | `string frame = 2` | `optional ReferenceFrame frame_ref` |

`ExcavateTask` and `ProspectTask` carry their frame transitively through `Volume region` and need no
new field. Messages that carry a georeferenced product gain an `optional PlanetaryCRS crs` where one
is implied today by convention; the exact set is an implementation detail, and the rule is that no
existing field number or type moves.

**Each added proto field is matched by a field in the canonical JSON Schema and the Pydantic model.**
The proto is a mirror (`core.md §2` principle 5); adding a wire field with no counterpart in the
authority layer would invert the stack and is not proposed.

**RFC-0001 dual-use (R3).** Two of these rows touch `mission.proto`, whose header states that
`TrajectoryRef` / `Maneuver` "OMIT — by schema, not convention — actuator/thruster command channels,
control gains, closed-loop guidance laws, and any onboard-flight-clock binding." An `optional Epoch
epoch` on `Maneuver` is **information-preserving**: it carries the same design-time TDB instant as
the existing `epoch_tdb_s`, in the same scale, with no binding to an onboard clock. It adds no
guidance capability and does not touch the `operational_targeting` capability gate.

Producers SHOULD populate the typed field; consumers MUST prefer it when present and MAY fall back to
the primitive. A follow-up RFC, once every producer populates the typed field, may deprecate the
primitives — that is a **separate** decision and explicitly not proposed here.

### 3. Guard semantics as contract, not generated code

Types alone move the problem. `require_frame` / `require_crs` are what make the vocabulary safe, and
today they exist only in `astro_mine/core/units/validate.py`. This RFC proposes that Core ratify the
guard **semantics** as a normative part of the contract, and ship the means to test them — but **not**
that Core ship four hand-written guard implementations.

- The validation rules are specified as MUST requirements on any Core binding. They belong in
  `conventions.md §5`, which already describes the guards normatively; `core.md §2` is a flat list of
  architecture principles with no subsections and is the wrong home for a rule of this granularity.
- Core's Python `validate.py` is the **reference implementation** (`core.md §8`: "the Rust validator
  is the recommended fast path; Python is the reference").
- Core ships a shared vector file, `src/astro_mine/core/units/schema/conformance.json`, alongside the
  JSON Schema and included in the schema bundle. This is the data form of the **contract tests**
  `conventions.md §11` already requires and the "contract-test utilities" `core.md §10` already says
  Core ships — not a new concept, and not new behaviour in Core.
- Implementing the guards in each binding's language is the **consumer's** obligation, discharged by
  running the vectors in its own CI. Core's `codegen/{cpp,rust,ts}` trees are build artifacts,
  generated fresh and never checked in (`buf.gen.langs.yaml`); a hand-maintained guard module cannot
  live there, and putting one in Core in four languages would contradict `core.md §2` principle 3 and
  this RFC's own claim to add no behaviour.

The normative rules:

1. A frame is present, and `name` / `center` are non-empty, whitespace-free tokens.
2. `frame_class` is a member of `FrameClass`; `scale` is a member of `TimeScale`.
3. `TimeScale.ET` and `TimeScale.TDB` denote the **same** scale (SPICE ET ≡ TDB). A consumer MUST NOT
   reject or reinterpret an epoch on the grounds that its scale is spelled `et` rather than `tdb`.
   Neither Core nor View states this today, and a naive `scale == TDB` comparison is a latent bug.
4. A CRS is present; `body` / `body_fixed_frame` are tokens; `reference_radius_m` is finite and `> 0`.
5. `EpochWindow.start` and `.end` are both present and `end.tdb_seconds > start.tdb_seconds`.
6. **An Earth CRS is not forbidden; an *implicit* one is.** `conventions.md §5` says "no implicit
   Earth/WGS84 assumptions", and Core's own `units.model` exports `EARTH` as a canonical NAIF body.
   Phase-2 Earth-analog deployments need Earth CRSs to be *expressible*. The MUST is therefore a
   **consistency** rule, not a blanket ban: an Earth datum or projection marker (`WGS84`,
   `EPSG:4326`, `urn:ogc:def:crs:OGC`) MUST be rejected when `body` is not `EARTH`, because that
   combination can only be a defaulting bug. A component MAY additionally refuse Earth CRSs outright
   as a local policy — View does, correctly, because it renders planetary bodies only — but that is
   **View's** rule, not Core's, and the conformance vectors MUST NOT conflate them: they assert
   `body="EARTH"` + a WGS84 datum is *valid at the waist*, and a component-local refusal is out of
   their scope.

Rule 6 is the whole argument for this section in miniature: the two implementations of "the same"
guard disagree on it today, and a proto file alone would not have surfaced that. The vectors are the
deliverable that actually prevents drift.

### 4. Distribution

Generating types nobody can import solves nothing.

The **JSON Schema** (§1a) needs no distribution decision: it ships in-package, in the schema bundle,
and any language can generate types from it. This matters because **View's ingest boundary is JSON,
not Protobuf** — `requireCrs` parses the `PlanetaryCRS.model_dump()` that Worlds writes into
`world.json`, accepting both camelCase and snake_case. A proto-only change would not have let View
drop a single line of its mirror. §1a is what does.

The **generated TS client** is a separate matter: `codegen/ts/package.json` is `private: true`,
`version: 0.0.0`, and unpublished. This RFC does **not** decide the registry question — see
*Unresolved questions* — but it records that the Protobuf half of the change is only load-bearing for
a non-Python consumer once that consumer can depend on the output.

## Impact on Core

**Does this widen the narrow waist?** It widens the *schema* and narrows the *semantics*. Six small,
dependency-free value types gain a canonical spec and a wire form — no new heavy dependency, no SPICE
resolution (`core.md §2` principle 3 still forbids that; name→geometry stays in `astro-mine-spice`,
RFC-0002). What is gained is that the waist now expresses, rather than merely documents, the
frame/CRS/time contract.

The capability cannot live in a plugin: it *is* the vocabulary plugins are written against. A plugin
defining `PlanetaryCRS` would be exactly the "private side-channel that bypasses Core contracts"
`conventions.md §1` tenet 1 forbids.

**New behaviour in Core:** none. The guards already exist in `validate.py`; §3 ratifies their
semantics and adds a test-vector data file. No per-language guard code is added to Core.

**Breaking changes:** none on the wire. All additions are new message types and new optional fields;
existing fields keep their numbers and types; `buf breaking` (configured `use: FILE`) gates this in
CI, which is precisely the mechanism `VERSIONING.md §4` names as one of the three that make the
frozen interface version safe.

**`CORE_INTERFACE_VERSIONS`:** stays at `0.1.0` for every interface, and gains **no `units` entry**.
Per `compat/__init__.py`, that dict lists only "the swappable-edge interfaces a consumer declares a
built-against version for"; the units types are embedded in the `messages` and `mission` interfaces
and move with the package. Adding new optional fields to those interfaces is additive and, per
`VERSIONING.md §4`, does not bump them.

**`schema_digest` changes.** `build_schema_bundle.py` hashes every `.proto` under `schemas/proto/`
(via `rglob`) plus the declared JSON Schemas. Adding `units.proto` and `units.schema.json` therefore
produces a **new `schema_digest`**. That is not a wire break — a `ScenarioSpec` pinned to the old
digest still resolves the old, immutable bundle by content address — but any scenario that re-pins to
the current Core will record a different digest, and `units.schema.json` MUST be added to the
`JSON_SCHEMAS` list (an undeclared schema is silently omitted from the bundle; a declared-but-missing
one raises).

**Migration path:** producers populate typed fields opportunistically; consumers prefer typed and fall
back to primitive. The Python `units` package gains a `wire.py` with free `*_to_proto` /
`*_from_proto` functions, matching the module pattern `messages` / `mission` / `objective` / `sadf`
already use — not `.to_proto()` methods on the models. `astro-mine-view`'s `frames/types.ts` and
`guards.ts` become generated types plus a vector-tested guard; its `projection.ts` / `coords.ts` /
`time.ts` are Cesium-side math and stay. Its PROJ-string drift test is retired in favour of the
conformance vectors.

## Documentation impact

Accepting this RFC obliges three doc changes, tracked with the implementation:

- **`conventions.md §5`** gains the six normative guard rules of [Design §3](#3-guard-semantics-as-contract-not-generated-code)
  as MUST requirements on any Core binding. §5 already describes `require_frame`/`require_crs`
  normatively; today it describes them without saying what they check. The rules must live there, not
  only in this RFC — a normative contract that lives only in an RFC is how `require_crs` and
  `guards.ts` diverged in the first place.
- **`core.md §3`** notes that the `units/` module now ships a canonical JSON Schema and a proto wire
  form, like every other Core interface; **§4** is unchanged (the codegen already covers it).
- **`architecture/view.md`** drops the "structural mirror rather than a private schema" caveat once
  View consumes generated types.

`core.md §2` is a flat list of architecture principles with no subsections and is deliberately *not*
the home for the guard rules — principle 8 ("frame- and unit-explicit") states the intent, and §5 of
`conventions.md` states the mechanism.

## Alternatives considered

**Do nothing; let each binding mirror.** The status quo. It costs nothing today, and View's mirror is
only ~220 lines. It fails at N > 1 consumers, and it leaves Core's headline safety property (no
implicit WGS84) unenforced on the wire, where it matters most. Rejected because the drift it invites
is silent — as guard rule 6 above demonstrates, it has *already happened* — and the failure mode is a
plausibly-rendered wrong body.

**Add the proto but not the JSON Schema.** The original shape of this RFC. Rejected: it inverts
Core's own layering (`core.md §2` principle 5 — the language-neutral spec is the source of truth, and
the proto is a mirror of it), leaves `check_model_drift.py` unable to pin the Pydantic models, and —
decisively — does not serve the motivating consumer, whose ingest boundary is JSON.

**Model `FrameClass` / `TimeScale` as proto enums with `_UNSPECIFIED = 0`.** Superficially the more
"typed" answer, and the zero value makes an unset vocabulary member representable as invalid.
Rejected: it contradicts the closed-vocab-as-string rule every existing Core `.proto` states, gives
one Core type two different wire encodings (proto int vs. Cap'n Proto `Text`), breaks byte-exact
round-tripping with the Python `StrEnum` values, and buys a fail-loud property the empty string
already provides.

**Ship the types but not the guards.** Cheaper, and superficially sufficient. Rejected: a
`PlanetaryCRS` message with a `projection` field happily carries `+proj=longlat +datum=WGS84`. The
guards, not the types, are what `conventions.md §5` actually promises, and the vectors are what
detect a divergence like View's.

**Replace the primitives outright (`string frame` → `ReferenceFrame frame`).** Cleanest end state.
Rejected for now: it is a breaking wire change, and `CORE_INTERFACE_VERSIONS` is deliberately frozen
until Phase 3. Deferred to a follow-up RFC once producers have populated the typed fields.

**Let each producer serialize the CRS its own way (status quo).** Worlds does not define a private
CRS schema — it imports Core's `PlanetaryCRS` — but it can only do that because it is Python, and it
writes the result into `world.json` as an unschema'd `model_dump()`. Generalized, this means every
producer/consumer pair negotiates geometry bilaterally against an undocumented JSON shape, which is
precisely the private side-channel the narrow waist exists to prevent.

## Resolved decisions

- **Guard rule 6 stays in Core, as a consistency rule.** Decided at acceptance. `require_crs` MUST
  reject an Earth datum/projection marker when `body != EARTH`, and MUST accept one when
  `body == EARTH`. The two rejected options were dropping the rule from Core entirely (leaving the
  conformance vectors blind to the exact failure mode that motivated this RFC, and View/Core
  divergent by design) and promoting View's blanket ban to the contract (which would make Earth CRSs
  unrepresentable, colliding with Core's own `EARTH` NAIF-body constant and the Phase-2 Earth-analog
  deployments). The consistency rule catches the defaulting bug — a lunar product carrying a WGS84
  datum — without forbidding the legitimate case.

## Unresolved questions

- **Distribution of the generated TypeScript client.** Un-private `codegen/ts` and publish to a
  private registry (GitHub Packages), vendor the generated file into consumers, or expose it as a
  git dependency? This blocks the Protobuf half's practical benefit but not this RFC's acceptance
  (§1a lands independently of it), and it is entangled with the same decision pending for
  `@astro-mine/view`. Deferrable to implementation.
- **Where the conformance vectors live.** Proposed: in Core, next to the JSON Schema
  (`units/schema/conformance.json`) and in the schema bundle, since they are part of the contract.
  The alternative is `astro-mine-seal`-style shared tooling (RFC-0005).
- **Should `SiUnit` also go on the wire?** Core's `unit` fields are already validated strings against
  `KNOWN_UNITS`. Composite units (`kg·m⁻³`) are deliberately not enumerated (`enums.py`), so an enum
  would be wrong. Proposed: leave `unit` a string, define it in `units.schema.json`, and cover
  `require_si_unit` in the conformance vectors. Not blocking.
- **Deprecation timeline for the primitive fields.** Explicitly out of scope; a follow-up RFC once
  every producer populates the typed fields.
