# RFC 0006: `Plan` / `ContingentPlan` — Core-owned delay-tolerant plan artifacts

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-07
- **Accepted:** 2026-07-07
- **Affects Core:** yes — two **additive** message schemas (`Plan`, `ContingentPlan`, and their
  supporting value types) added under the Core `messages` interface, with **no change to any
  existing message, enum, or wire type**; `CORE_INTERFACE_VERSIONS` stays frozen at `0.1.0`
  ([VERSIONING.md §4](../VERSIONING.md)). Goes through the RFC process because it touches the Core
  narrow waist ([GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)).

## Summary

Ratify **`Plan`** and **`ContingentPlan`** — the time-stamped, validity-horizoned plan artifacts
Mind's degrade-not-collapse work (RM-P1-MIND-06) acts on — as **Core-owned message schemas**, so
every autonomy component (Mind, Ops, View, Bench) reads the *same* plan vocabulary rather than
re-deriving it per package. [mind.md §5](../architecture/mind.md) already designates `Plan` and
`ContingentPlan` as Core-owned message schemas that "Mind generates bindings for, never forks";
this RFC makes that designation concrete and disciplined, on the same three-part schema stack Core
uses for `ObjectiveSpec` (canonical JSON Schema + Pydantic v2 model; the Protobuf wire form lands
with the first cross-process consumer — see [Unresolved questions](#unresolved-questions)).

It also records the **binding convention** by which the real `Astro-Mine-Guard` `PolicyShield`
(RM-P1-GUARD-03) and `Astro-Mine-Allocate` `AllocationPlanner` (RM-P1-ALLOC-01) plug into a Mind
stack — through the Core plugin registry and Mind's `astro_mine.mind.tier_plugins` entry-point
group — with **no `mind → guard` / `mind → allocate` dependency**, closing the loop RM-P1-MIND-04
and RM-P1-MIND-05 opened.

## Motivation

**Why a Core-owned plan schema.** Phase 1 is the reserved window for the autonomy stack. Mind
composes plans; Ops replays and supervises them; View renders them; Bench scores them. If each
package defines its own plan type, "a plan" becomes per-package tribal knowledge: two components
claiming to exchange a plan could disagree on whether it carries a validity horizon or its
assumptions, and a decision trace (RM-P1-MIND-07) could not be replayed against a stable schema.
A delay-tolerant plan is the linchpin of principle 5 (*delay-tolerant by construction*) and of the
degrade-not-collapse safety property (LUNAR-FR-005) — it must be as auditable and versioned as the
`ObjectiveSpec` it serves.

**Why now, and the interim.** RM-P1-MIND-06 needs the artifact today. Following the precedent
RM-P1-MIND-01 set for `ReplanTrigger` and `BeliefView` — Core-owned *concepts* realized
Mind-locally while the waist was still settling — the Mind PR (astro-mine-mind#12) ships
`astro_mine.mind.plan.{Plan,ContingentPlan}` as Mind-local dataclasses, **documented to migrate to
this Core schema**. This RFC ratifies the target so the migration is a mechanical re-point at a
tagged Core release, not a redesign.

**Why via RFC even though the change is additive.** Adding a message family to Core touches the
narrow waist. [conventions.md §3](../architecture/conventions.md) and GOVERNANCE.md require that
the Core vocabulary grow only by reviewed, additive change — exactly what this process is for.

## Design

### The schema

A `PlanDocument{ plan_version: "0.1", plan: Plan | ContingentPlan }`, authored/serialized in
JSON, validated by a canonical **JSON Schema** (`plan.schema.json`, the source of truth) mirrored
by a **Pydantic v2** model. Every model sets `extra="forbid"`; all durations are SI seconds; all
geometry is frame-explicit (via existing `messages` types).

```
PlanValidity   { issued_at_s: float, horizon_s: float | null }          # null = standing plan
Assumption     { key: str, description: str, holds: bool | null }        # a violated assumption -> branch
ContingencyBranch { trigger: str, action: str, description: str }        # what to do when `trigger` fires
Plan           { plan_id: str, tier: str, validity: PlanValidity,
                 actions: ActionBatch, assumptions: Assumption[],
                 provenance: Provenance | null }
ContingentPlan { base: Plan, branches: ContingencyBranch[] }
```

- **`Plan`** is the time-stamped, validity-horizoned unit: which tier issued it, the `ActionBatch`
  it proposes (an existing Core message), how long it stays valid, and the assumptions it rests on.
- **`ContingentPlan`** wraps a `Plan` with explicit `ContingencyBranch` points — the
  degrade-not-collapse artifact: act on `base` while valid, take a branch when a trigger fires
  (`comms_lost → hold_cached`, `plan_expired → reconcile`), reconcile on recovery. It is idempotent
  and safe to act on while stale.
- `trigger` strings align with the Mind stack-spec `ReplanTriggerKind` vocabulary
  (`plan_expired`, `periodic`, `on_fallback`, `comms_lost`); `action` strings are a small,
  append-only set (`hold_cached`, `reconcile`, `safe_idle`, `coordinate`).
- `provenance` reuses the existing Core `Provenance` block (input content hashes, code version,
  lockfile, seed), so a plan is content-addressable and reproducible (conventions.md §5).

`Plan` lands as a new `astro_mine.core.plan` module under the **`messages`** interface — an
additive sibling to `ObjectiveSpec`, **not** a new `CORE_INTERFACE_VERSIONS` key. No existing
schema, enum, or wire type changes.

### The sibling-binding convention (Guard / Allocate)

Mind's registry discovers tier/shield plugins through the `astro_mine.mind.tier_plugins` Python
entry-point group (conventions.md §7); each entry point is a provider returning a
`TierPlugin{ manifest, factory }`. The real siblings bind here — through the Core registry, with
no Mind dependency in their base package:

- **Guard.** An `astro-mine-guard` `[mind]` optional extra ships a provider that wraps Guard's
  `PolicyShield` (RM-P1-GUARD-03) as a Mind shield plugin. Because Mind's shield stage shields the
  already-composed proposal (threaded via `DecisionContext.upstream`), the adapter constructs
  `PolicyShield(wrapped=<identity-over-upstream>, compiled=compile_spec(safety_spec))` and
  implements Mind's `ReportingShield` seam (RM-P1-MIND-05) by draining Guard's `SafetyVerdict`
  stream (RM-P1-GUARD-06) into a `ShieldReport{ intervened, kind, clauses, certificate }`. The
  `mind → guard` edge exists **only** inside guard's optional extra; base Mind ships the reference
  `ConstraintShield` stand-in.
- **Allocate.** An `astro-mine-allocate` `[mind]` optional extra registers a provider on the
  `astro_mine.mind.tier_plugins` entry point that binds the CP-SAT solver as the `allocator`-role
  tier plugin behind Mind's `AllocationAdapter` (RM-P1-MIND-04). The adapter publishes a
  **Mind-owned** request DTO under the shared `allocation.request` `DecisionContext.extras` key — Mind
  owns that type so it need not depend on Allocate's rich request. `AllocationPlanner.decide` itself
  requires an Allocate-native `AllocationRequest` and **raises `TypeError`** on the Mind DTO, so the
  real planner cannot be dropped in unmediated. The `[mind]` provider therefore ships a small
  translation shim — `astro_mine.allocate.mind.MindAllocationSolver` (with `_as_allocation_request`) —
  which reads the `allocation.request` key, translates the Mind DTO into Allocate's `AllocationRequest`,
  solves, and maps the plan back to per-agent directives. The both-vocabulary knowledge lives only on
  Allocate's side of the waist — the only side permitted to know both — so there is still no
  `mind → allocate` dependency in either base package (astro-mine-allocate#21).

This is the same "reference stand-in now, real sibling via the registry later" pattern the spine
used for Sim (the toy env) and Guard (the pass-through shield) — the framework commits to the Core
contract, not the backend (mind.md §2, principle 2).

## Impact on Core

Additive only. Two new message schemas + their value types under the existing `messages`
interface; **no** new enum member, no change to an existing message or wire type, and
`CORE_INTERFACE_VERSIONS` stays `0.1.0` (additive schema growth, VERSIONING.md §4). The narrow
waist widens by exactly the plan vocabulary mind.md §5 already promised it would host, and by
nothing else — allocation request/response types stay **Allocate-owned** (they are not part of
this RFC), and the `SafetySpec` stays **Guard-owned** (RFC-0004). No breaking change; the
migration path for Mind is a re-point from `astro_mine.mind.plan` to `astro_mine.core.plan` at the
next tagged Core release.

## Alternatives considered

- **Keep `Plan`/`ContingentPlan` Mind-local permanently.** Rejected: Ops/View/Bench would each
  re-derive the plan vocabulary, defeating the narrow waist and making cross-component plan replay
  and scoring unverifiable — the exact failure mind.md §5 designates a Core schema to prevent.
- **Put allocation request/response in Core too.** Rejected for this RFC: Allocate already owns a
  rich, battle-tested `AllocationRequest`/`Allocation` (RM-P1-ALLOC-01); duplicating a thinner copy
  into Core would fork a safety-adjacent contract. Mind delegates over the Core `Allocator`
  *protocol* (which already exists) instead. A future Core-owned allocation *message* remains open
  if a second consumer appears.
- **Protobuf wire form now.** Deferred: no cross-process consumer of `Plan` exists in Phase 1
  (Mind hosts it in-process); the JSON-Schema + Pydantic pair is sufficient and matches how
  `ObjectiveSpec` began. The wire form lands with the first Ops/Bridge consumer (P2).

## Unresolved questions

- The Protobuf wire schema for `Plan`/`ContingentPlan` (deferred to the first cross-process
  consumer, P2). The JSON-Schema is the source of truth until then.
- Whether `ContingencyBranch.action` should become a closed `StrEnum` in Core once its members
  stabilize (currently an append-only string set shared by convention with Mind).
- Cross-phase plan provenance for multi-regime missions (RFC-0001) — out of scope until Phase 3.
