# RFC 0004: `SafetySpec` — a Guard-owned, Core-catalogued safety contract

- **Status:** proposed
- **Author(s):** djankov
- **Created:** 2026-07-05
- **Affects Core:** no — the `SafetySpec` schema is **Guard-owned** and catalogued *through*
  the Core plugin registry (`astro_mine.core.registry.PluginManifest`); it makes **no** change to
  the `astro-mine-core` package — no new enum member, message, schema, or wire type, and
  `CORE_INTERFACE_VERSIONS` stays frozen at `0.1.0` ([VERSIONING.md §4](../VERSIONING.md)). It goes
  through the RFC process because it establishes a **safety contract** whose evolution is
  RFC-gated ([guard.md §5](../architecture/guard.md);
  [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)).

## Summary

Ratify `SafetySpec` — the declarative contract of *hard* safety constraints that every
`Astro-Mine-Guard` layer compiles from — as a recognized, versioned, **content-addressed** safety
artifact of the commons, with an **additive-only, RFC-gated** evolution rule for its constraint
vocabulary. The schema is authored and owned by Guard (a Pydantic v2 model with a canonical JSON
Schema and a byte-stable Protobuf wire form), and is made discoverable "through Core" by
registering it in the Core plugin registry as a `PluginManifest` — **not** by widening the Core
narrow waist. This RFC records the contract, its constraint kinds, its fail-safe-by-construction
posture, and the governance rule that new constraint *kinds* are append-only schema changes that
land via this process. It is the governance half of **RM-P1-GUARD-01**
([astro-mine-guard#1](https://github.com/astro-mine/astro-mine-guard/pull/10)).

## Motivation

Guard is safety-critical, and its guarantee is only as trustworthy as the specification it
enforces. [guard.md §2](../architecture/guard.md) makes the spec the linchpin of three
principles: **"what is safe" is authored once and reused** across design-time training, sim
validation, and operations (principle 3); **the property enforced is exactly the property
reviewed** (§9.3); and the guarantee derives from the spec, never from the wrapped policy's
internals (§9.1, independence). For those to hold, the spec must be a *reviewed artifact* with a
stable identity and a disciplined evolution rule — not an ad-hoc config file that drifts.

**Why a contract, and why now.** Phase 1 is the reserved window for landing the autonomy stack
(Mind / Learn / Allocate / Guard). Guard's `PolicyShield` wraps outputs from all of them, and a
learned policy published to Hub and scored on the public Bench leaderboard (the M1.2 flywheel) is
only safe to run if the safety envelope it runs inside is itself a versioned, content-addressed,
signable object. The cost of *not* formalizing this is that "safe" becomes per-deployment tribal
knowledge: two runs claiming the same safety could enforce different constraints, a spec could be
edited in a way that silently weakens a bound, and there would be no governance gate on adding a
new constraint *kind* to a safety-critical vocabulary. A safety contract must be as auditable as
the code that honors it.

**Why via RFC even though Core does not change.** The schema lives in the Guard package, so this
is not a Core narrow-waist change (contrast [RFC-0003](0003-resource-storage-sensorkind.md), which
appended Core enum members). But [guard.md §5](../architecture/guard.md) states that new
constraint kinds are *"additive, RFC-gated"* — the same discipline the platform applies to its
closed vocabularies (`conventions.md §3`). Recording that rule, and the contract it governs, is
exactly what the RFC process is for: a safety vocabulary should not grow by an unreviewed commit.

## Design

### What `SafetySpec` is

A `SafetyDocument{ safety_version: "0.1", safety: SafetySpec }` where
`SafetySpec{ id, name, description?, scenario_ref?, signals[], constraints[], provenance? }`.
Authored in YAML/JSON, validated by a canonical **JSON Schema** (`safety_spec.schema.json`, the
source of truth) mirrored by a **Pydantic v2** model, and serialized to a byte-stable **Protobuf**
wire form — the same three-part schema stack Core uses for `ObjectiveSpec` (`conventions.md §3`).
Every model sets `extra="forbid"`; all quantities are SI; all geometry is frame-explicit.

### Signals — the abstract constraint-source binding

Constraints do not reach into sibling packages. A `SignalRef{ key, unit, source }` names a runtime
channel by key; `source` is a `SignalSource` tag — `observation` (a Core Environment observation
channel), `sadf` (a Fleet SADF budget path, e.g. `power.floor_w`), `worlds` (a Worlds keep-out /
terrain field), or `derived` (computed from other signals). Only the *name and origin* are
recorded here; resolving the actual Worlds raster or Fleet budget value is deferred to
**RM-P1-GUARD-04**. This is how "constraint sources are Core-typed references, never sibling
imports" is realized.

### Constraint kinds — the safety vocabulary

`Constraint` is a tagged union discriminated by `ConstraintKind`, with exactly one typed payload
per member (the loader enforces exactly-one-set, the `TaskDirective`/`Action` idiom). The v0.1
members:

| `ConstraintKind` | payload | family |
|---|---|---|
| `keep_out` | `KeepOutVolume` (geometry) + `margin_m` + optional `collision_pair` | geometric |
| `power_floor` | `signal` + `floor_w` | budget |
| `energy_floor` | `signal` + `floor_j` | budget |
| `thermal_ceiling` | `signal` + `limit_k` | budget |
| `thermal_floor` | `signal` + `limit_k` | budget |
| `torque_ceiling` | `signal` + `max_nm` | budget |
| `kinematic_limit` | `signal` + `max_velocity?` / `max_accel?` | kinematic |
| `temporal` | `STLFormula` | STL/MTL temporal |

**Keep-out geometry** is a `KeepOutVolume` tagged union over `GeometryKind`: `box` (anchored on the
Core `messages.Volume` — axis-aligned, frame-explicit), `sphere`, and `half_space` (Guard-local
barrier primitives). Each constraint carries an `id` and an `on_uncertain` selector.

**STL/MTL temporal clauses are a structured AST, not a string DSL.** An `STLFormula` is a recursive
node discriminated by `TemporalOp` — `predicate` (the atomic leaf `signal <op> threshold`, with
`op ∈ PredicateOp {lt, le, gt, ge}`), the boolean combinators `not` / `and` / `or`, and the
bounded temporal operators `always` / `eventually` / `until`. Every temporal operator carries a
**finite** interval `[lo, hi]` seconds. This makes a clause reviewable and analyzable *now*, with
no parser dependency and no Rust core — it expresses "SoC ≥ floor **until** a charging window" and
"**always**: chassis ≥ survival floor over the night horizon" directly (see the anchor spec below).

### Fail-safe, baked into the vocabulary

`on_uncertain` is an `OnUncertain` selector with **no `passthrough` member** — `fallback` (default;
hand control to the simplex backup), `hold` (freeze/brake), or `safe_state` (retreat to a named safe
state). "Let the policy's action through unchecked" is *not expressible* in the schema. The loader
additionally **rejects any temporal operator lacking a finite interval**: an unbounded operator has
no statically-bounded history window, so it cannot be certified and is refused at authoring time
(guard.md §2 principle 4; §9.1). Absence of a positive certificate can only resolve to a verified
safe action.

### The constraint compiler → a statically-bounded IR

`compile_spec(document) → CompiledSafetyModel` lowers a *validated* spec into a flat,
integer-indexed, serializable IR that the future Rust safety core (**RM-P1-GUARD-02**) will load:

- **`PredicateTable`** — deduplicated atoms `{op, signal_index, threshold}`; signal *keys* are
  resolved to integer *indices* at compile time (no runtime string lookup).
- **`ScalarBound`** — the budget/kinematic one-sided bounds.
- **`KeepOutTerm`** — keep-out/collision lowered to box/sphere/half-space barrier terms with
  precomputed coefficients (normalized half-space normals) and margin.
- **`MonitorAutomaton`** — each temporal clause lowered to a resolved `CompiledNode` tree with a
  compile-time **`history_window_len`** derived from the interval bounds.
- **`ResourceBounds`** — the static pre-allocation budget (max history-buffer length, predicate-slot
  count, monitor count, worst-case term count).

A static-analysis pass computes those bounds and **rejects any construct that cannot be statically
bounded** — this is how GUARD-01 discharges "no hot-path allocation *implied* by the lowering"
before the Rust core (which enforces it at runtime) exists. The lowering is deterministic:
everything is sorted and integer-keyed, so the same spec compiles to identical bytes.

### Content-addressing and "Core-catalogued"

A `SafetyDocument`'s identity is `content_hash()` = `sha256:<hex>` of its canonical JSON, via the
one platform primitive `astro_mine.core.hashing.content_hash_json`; `CompiledSafetyModel` is
content-addressed the same way. "Core-catalogued" is realized by registering the **Guard-owned**
schema through the Core plugin registry: `build_safety_manifest(...)` produces a Core
`PluginManifest` that

- declares the Core interfaces the spec is built against —
  `{ "messages": "0.1.0", "sadf": "0.1.0", "registry": "0.1.0" }` (the registry negotiates them at
  load via `assert_core_compatible`);
- names the Guard-owned output types (`astro_mine.guard.spec.SafetySpec`,
  `…CompiledSafetyModel`) and the embedded Core input (`astro_mine.core.messages.Volume`);
- reuses the existing `PluginKind.POLICY` (Guard's headline `PolicyShield` *is* a Core
  Policy/Planner) — **no new `PluginKind`, no Core change** (the `astro-mine-surrogate`
  `build_surrogate_manifest` precedent); and
- carries the spec's content hash as `provenance.digest` — the identity a cosign signature will
  bind to under **RM-P1-GUARD-05** (signed loading; out of scope here, so registration defaults to
  `require_signature=False` for local/dev use).

### Additive-only, RFC-gated evolution

New constraint *kinds* (a `ConstraintKind` member + its payload), new keep-out geometries, and new
signal sources are **append-only** schema changes that land via this RFC process. Enforcement is
mechanical, mirroring Core: `buf breaking --against origin/main` over the Guard `.proto`, a
`check_model_drift.py` regenerate-and-compare guard, and a `test_schema_compat.py` that asserts the
enums are append-only versus a checked-in baseline and that no required field is added to an
existing kind. A non-additive edit turns CI red.

### Worked example — the anchor SafetySpec

The flagship lunar-polar water-ice prospecting rover ships as
`examples/safety_specs/anchor.safety.yaml`, exercising every constraint kind and all three keep-out
geometries: a `power_floor` (15 W survival-heater floor) and `energy_floor` (180 kJ night-survival
floor); `thermal_ceiling` (320 K) and `thermal_floor` (120 K survival); a `torque_ceiling` (40 N·m
anchoring drill) and a `kinematic_limit` (0.1 m/s traverse cap, `on_uncertain: hold`); three
`keep_out` volumes (a PSR-crater `box`, a lander-safety `sphere`, a steep-slope `half_space`); and
two `temporal` clauses over a finite lunar-night horizon — `until(SoC ≥ 180 kJ, charging_window)`
(`on_uncertain: safe_state`) and `always(chassis ≥ 120 K)`. It validates, compiles to monitor +
barrier artifacts, and is pinned by a golden/determinism test.

## Impact on Core

**None to the `astro-mine-core` package.** No enum member, message type, schema, or wire form
changes; `buf breaking` on Core is untouched; `CORE_INTERFACE_VERSIONS` stays `0.1.0`
([VERSIONING.md §4](../VERSIONING.md)). The narrow waist does not widen — `SafetySpec` is a
Guard-owned plugin artifact that becomes *discoverable* through the existing Core plugin registry,
exactly as the shared-SPICE foundation ([RFC-0002](0002-shared-spice-foundation.md)) added a
companion package rather than Core surface. The only Core types the contract *depends on* are the
already-frozen `messages.Volume` (embedded in the `box` keep-out) and the `registry` / `sadf` /
`messages` interfaces the manifest negotiates against.

The governance commitment this RFC adds is process, not code: the Guard `SafetySpec` vocabulary
now evolves append-only and via RFC, on par with Core's closed vocabularies.

## Alternatives considered

1. **Make `SafetySpec` a Core message (edit `astro_mine.core.messages`).** Rejected: it would widen
   the narrow waist with a large, safety-domain-specific schema (keep-out geometry, STL AST,
   compiled monitor automata) that only Guard produces and consumes. [guard.md §5](../architecture/guard.md)
   deliberately keeps the schema Guard-owned and merely *catalogued* through Core — the smaller,
   plugin-shaped change. The Core registry already provides discovery and version negotiation.
2. **A string surface syntax for STL/MTL** (e.g. `always[0,T](soc >= floor)`). Rejected for v0.1: a
   string DSL needs a trusted parser on the path to a safety artifact and is harder to diff and
   review. The structured AST is analyzable and reviewable directly; a surface syntax can be added
   **additively** later as sugar that lowers to the same AST.
3. **No RFC — just ship the schema in the Guard repo.** Rejected: a safety vocabulary that can gain
   new *hard-constraint kinds* by an unreviewed commit defeats "the property enforced is exactly the
   property reviewed." The append-only + RFC-gate rule is itself part of the safety case.
4. **Hash over the Protobuf wire form rather than canonical JSON.** Considered; the implementation
   content-addresses over canonical JSON (`content_hash_json`) to keep identity independent of the
   optional generated proto bindings and consistent with the platform's documented canonical form.
   The Protobuf wire form is separately proven byte-stable and round-trip-exact.

## Documentation impact

Minimal. [guard.md §3/§5/§9](../architecture/guard.md) already describe the `SafetySpec`, its
Guard ownership, content-addressing, and the additive-only rule; the Phase-1 roadmap names
RM-P1-GUARD-01 as *"`SafetySpec` schema + constraint compiler … RFC-gated as a safety contract."*
This RFC records the ratified contract and vocabulary; no architecture-doc edit is required. On
acceptance, GUARD-02 (Rust core) consumes the `CompiledSafetyModel`, GUARD-04 resolves the abstract
signal sources against Worlds/Fleet, and GUARD-05 adds signed loading.

## Decision

**Proposed — pending ratification** by the steering group (the Phase-0 founding team). The
constraint vocabulary, the fail-safe `OnUncertain` posture (no `passthrough`), the
content-addressing primitive, and the additive-only / RFC-gated evolution rule are as specified in
*Design*. Implementation is tracked as **RM-P1-GUARD-01**
([astro-mine-guard#1](https://github.com/astro-mine/astro-mine-guard/pull/10)); the Core
interfaces the manifest negotiates against stay frozen at `0.1.0`.

## Unresolved questions

- **Multi-agent / `coord` constraint kinds.** Latency-aware separation and responsibility
  partitioning for multi-agent shielding are deferred (P1-late/P2); they will append new
  `ConstraintKind` members via a future RFC and do not affect the v0.1 vocabulary.
- **Per-phase / per-regime `SafetySpec` profiles.** RFC-0001 multi-regime missions will want
  regime-scoped safety profiles (deep-space one-shot clauses, EDL); deferred to P3 as an additive
  document-level extension.
- **Signature algorithm + trust roots** for signed loading (GUARD-05) — which cosign identities a
  signature-requiring registry trusts — is out of scope here and decided with Hub's verify-twice
  supply chain (RM-P1-HUB-03).
- **Surface syntax for STL/MTL** (sugar over the AST) — whether to add one, and which grammar, is
  deferred; if added it must lower to the ratified AST with no new expressive power.
