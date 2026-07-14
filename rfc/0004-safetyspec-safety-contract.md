# RFC 0004: `SafetySpec` — a Guard-owned, Core-catalogued safety contract

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-05
- **Accepted:** 2026-07-05
- **Amended:** 2026-07-06 — Amendment 1 (`safe_pose` retreat target + distinct verified backup
  behaviors; RM-P1-GUARD-04), accepted; see [Amendment 1](#amendment-1--safe_pose-retreat-target--distinct-verified-backup-behaviors-accepted-2026-07-06) below.
  · 2026-07-13 — Amendment 2 (`admissible_directives` — the MODE/TASK allowlist moves into the
  reviewed contract; configuration may only narrow it), accepted; see [Amendment 2](#amendment-2--admissible_directives-the-modetask-allowlist-belongs-to-the-contract-accepted-2026-07-13) below.
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
state). *([Amendment 1](#amendment-1--safe_pose-retreat-target--distinct-verified-backup-behaviors-accepted-2026-07-06) adds the authored `safe_pose` retreat target and gives these three selectors distinct, individually-verified backup control laws; [Amendment 2](#amendment-2--admissible_directives-the-modetask-allowlist-belongs-to-the-contract-accepted-2026-07-13) closes the one place a passthrough had become expressible again — an unreviewed **configuration** grant on the discrete-directive gate.)* "Let the policy's action through unchecked" is *not expressible* in the schema. The loader
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

**Accepted 2026-07-05** by the steering group (the Phase-0 founding team), as specified in
*Design*: the constraint vocabulary (`keep_out` · `power_floor` / `energy_floor` ·
`thermal_ceiling` / `thermal_floor` · `torque_ceiling` · `kinematic_limit` · `temporal`), the
structured STL/MTL AST, the fail-safe `OnUncertain` posture (no `passthrough` member),
content-addressing via canonical JSON, and the **additive-only / RFC-gated** evolution rule for the
`SafetySpec` vocabulary. Implementation is tracked as **RM-P1-GUARD-01**
([astro-mine-guard#1](https://github.com/astro-mine/astro-mine-guard/pull/10)); the `SafetySpec`
schema stays **Guard-owned** and catalogued through the Core plugin registry, and the Core
interfaces the manifest negotiates against stay frozen at `0.1.0` — **no `astro-mine-core`
change**.

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

---

## Amendment 1 — `safe_pose` retreat target + distinct verified backup behaviors (accepted 2026-07-06)

- **Status:** accepted
- **Accepted:** 2026-07-06
- **Affects Core:** no (unchanged from the base RFC — no `astro-mine-core` change,
  `CORE_INTERFACE_VERSIONS` stays `0.1.0`, `safety_version` stays `"0.1"`)
- **Implementation:** **RM-P1-GUARD-04**
  ([astro-mine-guard#4](https://github.com/astro-mine/astro-mine-guard/pull/14))

### What changed

The base RFC's fail-safe posture named three `OnUncertain` selectors — `fallback`, `hold`,
`safe_state` — and defined `safe_state` as *"retreat to a **named** safe state,"* but v0.1 shipped
no target for that retreat, and the initial trusted core (RM-P1-GUARD-02) conservatively collapsed
all three selectors to the verified brake-to-stop. RM-P1-GUARD-04 realizes the distinction with two
**additive** changes.

**1. `safe_pose` — an additive `SafetySpec` field (the retreat target).** A new *optional*
`SafePose{ frame, position_m }` on `SafetySpec` (`safe_pose: SafePose | None`): a body-fixed
position in an explicitly named `frame` (SI metres; `conventions.md §5`, LUNAR-TR-001 — **no
implicit Earth/WGS84 frame**), lowered by the compiler into the keep-out spatial frame as a
`CompiledSafePose` on `CompiledSafetyModel`. The loader **rejects** a `safe_pose` whose frame is
empty or does not match the keep-out geometry frame(s) — *the retreat target and the certified safe
set must share a frame* — and the trusted-core decode is fail-closed (a non-finite coordinate or an
arity below the model's spatial dimension rejects the whole model). This is an **append-only** schema
addition under the base RFC's additive-only rule: no member is removed or changed, no required field
is added to an existing kind, `safety_version` stays `"0.1"`, and the `buf breaking` /
`check_model_drift` / append-only schema-compat CI guards stay green.

**2. Three distinct, individually-verified backup control laws (in the trusted Rust core).** The
`OnUncertain` selectors now map to three provably-fail-safe behaviors in the TCB (the RM-P1-GUARD-02
arbiter + simplex library), replacing the collapse-to-brake placeholder:

| selector | backup behavior | law |
|---|---|---|
| `fallback` | **BrakeToStop** — the ever-present safety floor | `u = −clamp(k_brake·v, u_max)`, anti-parallel to velocity ⇒ `d/dt‖v‖² ≤ 0`; dt-free, always available |
| `hold` | **Hold** (station-keep / hold-attitude) | return to and hold the pose latched when the hold behavior engaged |
| `safe_state` | **SafeState** (retreat-to-charging-pose) | steer toward the authored `safe_pose` (the lunar-night survival target) |

**Fail-safe composition (the load-bearing invariant).** Hold and SafeState are *guarded* saturated-PD
move-toward-target laws: each emits its command **only if** (a) the action is inside the control box
(`|u| ≤ u_max`), (b) it does not increase the target Lyapunov energy
`V = ½·k_p‖p − g‖² + ½‖v‖²`, and (c) the one-step-predicted position stays inside the **same**
certified safe set the shield enforces (the shared keep-out barriers). If no such bounded action
exists — the target is unreachable safely, the step would exit the safe set, no `safe_pose` is
authored, or the model is non-spatial — the behavior **degrades to BrakeToStop**. There is
deliberately no path that emits the untrusted proposal: the base RFC's *"absence of a positive
certificate can only resolve to a verified safe action"* is preserved, now discharged by three
distinct verified behaviors rather than one. (The per-step one-step-prediction in-set check is a
documented, conservative first slice; an exact reach-avoid retreat filter is deferred — below.)

### Why via (this) RFC

Amendment 1 touches the **safety contract's authored surface** (a new `SafetySpec` field) and the
**operational meaning of a fail-safe selector** (`safe_state` now carries a target and a distinct
verified control law). The base RFC makes vocabulary evolution *"additive-only, RFC-gated"* precisely
so a safety-relevant addition is reviewed rather than slipped in by commit. It remains a
**Guard-owned, no-Core-change** amendment.

### Impact on Core

**None**, as in the base RFC. No enum member, message type, schema, or wire form changes on
`astro-mine-core`; `CORE_INTERFACE_VERSIONS` stays `0.1.0`; the `PluginManifest` still negotiates
`messages` / `sadf` / `registry` at `0.1.0`.

### Deferred (updated)

- The base RFC's open item *"retreat to a **named** safe state"* is now **resolved** — the retreat
  target is the authored, shared-frame `safe_pose`.
- An **exact reach-avoid retreat filter** (replacing the conservative one-step-prediction in-set
  check) is deferred (P1-late/P2), alongside the HJ-reachability shields already deferred in the base
  RFC.
- A **multi-target / per-regime `safe_pose`** (e.g. the nearest charging pose from a set; RFC-0001
  regime-scoped profiles) remains an additive future extension (P3).

### Decision

**Accepted 2026-07-06.** The additive `safe_pose` field and the three distinct verified backup
behaviors (BrakeToStop / Hold / SafeState) with the guarded-move fail-safe composition are ratified
as an **additive, Guard-owned** extension of the `SafetySpec` safety contract; `safety_version` stays
`"0.1"` and there is **no `astro-mine-core` change**. Implemented and merged as **RM-P1-GUARD-04**.

---

## Amendment 2 — `admissible_directives`: the MODE/TASK allowlist belongs to the contract (accepted 2026-07-13)

- **Status:** accepted
- **Accepted:** 2026-07-13
- **Affects Core:** no (unchanged from the base RFC — no `astro-mine-core` change,
  `CORE_INTERFACE_VERSIONS` stays `0.1.0`, `safety_version` stays `"0.1"`)
- **Implementation:** **RM-P1-GUARD-03** (the action gate)
  ([astro-mine-guard#25](https://github.com/astro-mine/astro-mine-guard/issues/25); raised by
  astro-mine-guard#24)

### What changed

RM-P1-GUARD-03 gave the trusted core an **action gate**: a `MODE` or `TASK` proposal carries no
continuous quantity to project, so the shield cannot *correct* it — it can only certify it by
**enumeration** against an allowlist. That allowlist shipped in `CoreConfig.action_policy`
(`certified_modes` / `certified_tasks`): local, unsigned deployment configuration. Amendment 2 moves
the **grant** into the reviewed contract and demotes the configuration to a **narrowing-only** knob.

**1. `admissible_directives` — an additive, optional `SafetySpec` field (the reviewed grant).**

```yaml
safety:
  admissible_directives:          # optional; absent ⇒ the spec grants NOTHING
    modes: [safe_hold]            # ModeCommand.mode names (free strings; SADF loads_by_mode)
    tasks: [standby, charge]      # Core TaskKind values (closed vocabulary)
```

`AdmissibleDirectives{ modes: [str], tasks: [TaskKind] }` is a top-level optional field on
`SafetySpec` — the same shape Amendment 1 established for `safe_pose`, and for the same reason (see
*Alternatives*). The compiler lowers it to `CompiledSafetyModel.admissible_directives`; the trusted
core decodes it fail-closed and rejects a malformed grant rather than enforcing against a bad one.
`tasks` is typed as Core's `TaskKind`, so an unknown task is refused at authoring time.

**2. The gate's effective allowlist is now `spec ∩ config`.** A directive is certifiable **iff the
reviewed spec admits it *and* the configuration admits it**. `CoreConfig.action_policy` survives, but
it can only ever **narrow** the reviewed grant — the legitimate "run this deployment stricter than
the contract allows" case. It can no longer *create* a permission.

Both changes are **append-only** under the base RFC's additive-only rule: no member is removed or
changed, no required field is added to an existing kind, `safety_version` stays `"0.1"`, and the
`buf breaking` / `check_model_drift` / append-only schema-compat CI guards stay green. An
existing spec that authors no `admissible_directives` still loads — it now simply certifies **no**
directive, which is the fail-closed reading and was already the default posture of an unconfigured
Guard.

### Merge semantics (load-bearing)

```
effective_modes = config.certified_modes ∩ spec.admissible_directives.modes
effective_tasks = config.certified_tasks ∩ spec.admissible_directives.tasks

spec silent (field absent)      ⇒ effective = ∅        (NOT "whatever config says")
spec authors ∅                  ⇒ effective = ∅
config silent (empty allowlist) ⇒ effective = ∅
```

The intersection is computed **once**, at trusted-core construction, so the hot path stays
allocation-free (guard.md §2 principle 6).

**The deliberate asymmetry with `tighten()`.** Amendment 2 introduces the *second* place where a
reviewed spec value and a configured value must be merged, and it merges them the **other way round
on silence**. That is not an inconsistency; it is the lattice being honest:

| merged thing | greatest lower bound | identity ("no opinion") | spec silent ⇒ |
|---|---|---|---|
| a scalar **ceiling** (`kinematic_limit` → `ActionLimits`) | `min(config, authored)` | `+∞` | **config stands** |
| a **permission set** (`admissible_directives`) | `config ∩ authored` | `∅` | **nothing is admitted** |

Both are the greatest-lower-bound of the two inputs — "configuration may only tighten the reviewed
contract" is one rule, not two. Only the *identity element* of the meet differs. For a ceiling, an
unstated limit is `+∞` (no constraint), so `min(config, absent) = config` and the configured ceiling
is safe to keep. For a permission set, an unstated grant is `∅` (no authority), so
`config ∩ absent = ∅` — **silence must grant nothing**. Reading a silent spec as "config stands"
would make the permission set fail *open* by silence, which is exactly the property this amendment
exists to remove. This asymmetry is stated here explicitly because it is the load-bearing rule and
must not be re-derived by analogy to `tighten()` at a later review.

### Why via (this) RFC

Amendment 2 touches the safety contract's authored surface and the operational meaning of the gate,
so it is RFC-gated by the base RFC's own rule. The substantive arguments:

**1. A config-granted MODE is an expressible `passthrough` — the one thing this RFC designed out of
the schema.** The base RFC states that `OnUncertain` has no `passthrough` member and that "let the
policy's action through unchecked" is *not expressible*. But an allowlisted directive resolves in the
arbiter to `Intervention::None` / `Reason::Certified` with an **empty** `certified_action`, and the
Python marshal layer then re-emits the wrapped policy's proposal **byte-for-byte, uncertified**. That
is a passthrough by any operational definition, and the only thing standing between an untrusted
policy and it is a dict of plugin `params`. The schema kept the door shut; configuration had cut a
new one next to it.

**2. A MODE transition is an actuation path with direct safety semantics.** `ModeCommand.mode` names
a SADF `loads_by_mode` mode, and the simulator's engines switch behavior on it. `loads_by_mode` **is**
the power/thermal load profile the anchor spec's survival floors are stated against — so a MODE
switch is the most direct available way to invalidate the very constraints Guard is enforcing (e.g.
leaving a survival-heater profile during lunar night). It is also the only *prospective* control on
that path: the monitors are `ScalarBound`s over **measured** signals and observe the consequence one
or more ticks *after* the load profile has already changed. A permission with that reach is a safety
decision, and safety decisions belong in the reviewed, content-addressed artifact.

**3. The hole was already open, with a wrong answer in it.** The Mind reference stack
(`lunar_prospecting_anchor.yaml`) shipped `certified_modes: ["velocity"]`, justified in-file with
"Sim's engine actuates VELOCITY setpoints, so VELOCITY is the mode this stack certifies." That
rationale is **factually wrong**: `certified_modes` gates `ModeCommand.mode` *names*, not
`ControlMode` values; an `ACTUATOR`/`VELOCITY` action is classified as a **numeric** command and is
routed to the shield, where the allowlist is never consulted. So the entry was (a) inert for the
actions the stack actually emits, and (b) a standing grant that *any* `MODE` directive happening to be
named `"velocity"` would cross the TCB untouched. A safety-relevant permission, granted in a YAML, in
a different repo, on a mistaken premise, caught by nothing. That is the failure mode the contract/config
split exists to prevent, and it had already happened.

**4. `SafetySpec` is the only artifact on this path with an integrity story.** It is
content-addressed (`content_hash_json`), signed and fail-closed-verified before the trusted core sees
it, re-derived *inside* the core, and stamped into every `SafetyVerdict` as `spec_content_hash`.
`CoreConfig` has none of that: it is an unsigned `params` dict from a stack YAML and appears nowhere
in the verdict record. Today, two runs can report the **same** `spec_content_hash` and enforce
**different** action gates — which breaks the guarantee `guard.md` §5 and §9.3 are built on ("the
property enforced is exactly the property reviewed", and an auditable record that says which). After
this amendment the verdict's `spec_content_hash` bounds the grant: config can only have narrowed it.

### Impact on Core

**None**, as in the base RFC and Amendment 1. No enum member, message type, schema, or wire form
changes on `astro-mine-core`; `CORE_INTERFACE_VERSIONS` stays `0.1.0`; the `PluginManifest` still
negotiates `messages` / `sadf` / `registry` at `0.1.0`. Guard's schema `$ref`s Core's existing
`TaskKind` by its published `$id` (RFC-0009 §1) — a *read* of Core's public vocabulary, not a change
to it.

### Alternatives considered

- **(i) A new `ConstraintKind.directive_allowlist` member.** *Rejected.* A `Constraint` in this
  vocabulary is a **predicate over a declared signal**, carrying an `on_uncertain` selector that names
  the verified backup to run when it fires. A directive allowlist has no signal, no predicate, and no
  meaningful `on_uncertain` (a rejected directive is not a fired constraint — it is an *absent*
  certificate). Forcing it into the tagged union would pollute the constraint vocabulary and every
  compiler/monitor path that consumes it with a member that is not a constraint. `safe_pose` faced the
  identical question in Amendment 1 and answered it the same way: a spec-level fact that is neither a
  predicate nor a geometry is a **top-level optional field**, not a constraint kind.
- **(ii) Leave it in `CoreConfig`.** *Rejected* — that is the status quo whose four defects are
  enumerated above. The honest counter-argument for it is recorded below.
- **(iii) Keep the field, but read spec-silence as "config stands"** (i.e. mirror `tighten()`'s
  absent-⇒-config default). *Rejected* as **fail-open-by-silence**: every spec authored before this
  amendment is silent, so the rule would preserve exactly the unreviewed grant the amendment exists to
  revoke, and would make "add a permission" achievable by *deleting* a line from the contract. See the
  lattice argument above.

**The counter-position, recorded honestly.** The MODE vocabulary is **open** — mode names are free
strings drawn from a SADF asset's `loads_by_mode` — so an allowlist over them is asset- and
deployment-specific, and pinning it inside a content-addressed spec means a **new spec hash and a
re-sign for every fleet variant**. That is a real ergonomic cost and it is the strongest argument for
leaving the allowlist in configuration. It does not carry: `SafetySpec` **already** carries
fleet-specific content (the torque ceiling, the keep-out geometry, the `safe_pose`), `scenario_ref`
exists precisely to bind a spec to the scenario it is stated against, and the narrowing-only knob
preserves the legitimate "run stricter than the contract" use-case without a re-sign. The friction
lands only on the operation that *should* be expensive: **granting a robot new authority**.

### Deferred

- **Validating MODE names against a SADF asset's `loads_by_mode`.** The spec would then reject a
  grant for a mode the asset cannot enter. This needs a spec↔asset binding the loader does not have
  today (the spec references signals abstractly by key); deferred, and not required for the
  fail-closed property this amendment establishes.
- **Per-regime directive profiles.** RFC-0001 multi-regime missions will want a grant scoped to a
  `Phase`'s `regime` (a `MODE` admissible on the surface need not be admissible during transit);
  deferred to **P3** as an additive, document-level extension, alongside the per-regime `SafetySpec`
  profiles already deferred in the base RFC and Amendment 1.
- **Whether `fallback_control_mode` / `fallback_target` should also move into the spec.**
  **Recommendation: no.** They are not a *permission* — they name the actuation **channel** a rejected
  proposal is answered in (a velocity-tracking plant must be answered with a velocity command, not an
  `EFFORT` brake its actuator would ignore). That is a property of the plant and its wiring, not of the
  safety contract, and it is already constrained to the control modes the TCB has a plant model for
  (rejected at construction time otherwise). No configuration of it can widen what is certifiable —
  the property this amendment is about — so it stays where it is.

### Decision

**Accepted 2026-07-13.** The additive, optional `SafetySpec.admissible_directives` field and the
`effective = spec ∩ config` gate semantics — with **spec-silence granting nothing** — are ratified as
an **additive, Guard-owned** extension of the `SafetySpec` safety contract. `CoreConfig.action_policy`
is retained as a **narrowing-only** deployment knob and may never create a permission the reviewed
contract does not already grant. `safety_version` stays `"0.1"` and there is **no `astro-mine-core`
change**. Implemented under **RM-P1-GUARD-03** (astro-mine-guard#25).
