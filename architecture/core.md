# Astro-Mine-Core — Technology Architecture

> Layer: **Commons backbone** · Phase: **0** (interfaces v0.1) · Ships in: [`astro-mine-platform`](platform.md)
> Mission/Phase/Regime hooks reserved in Phase 1 ([multi-regime missions](mission-model.md))
> The narrow waist. The single most important package to design well.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Core` is the **contract layer** — the thin, stable "narrow waist" that every other
package and every third-party plugin speaks to. It defines, and only defines:

- the **Swarm Asset Description Format (SADF)** — how robots/assets are described;
- the **Environment API** — how a simulatable world is observed and acted upon;
- the **Policy / Planner API** — how decisions are computed and composed;
- the **message schemas** — the typed vocabulary exchanged across the platform;
- the **plugin registry & manifest** — how content is discovered, versioned, and loaded.

**Explicitly out of scope:** Core contains *no* physics, *no* solvers, *no* learning, *no* UI,
and *no* heavy dependencies. If something can live in a plugin, it MUST NOT live in Core. Core
ships reference *types and validators*, not reference *implementations* (those are separate
packages that depend on Core).

**Multi-regime missions.** Core additively absorbs the Mission/Phase/Regime model —
the `MissionSpec` schema, a bounded `regime` dimension and `PhaseTransition` events on the
Environment API, propulsion/staging/return SADF capability declarations, the descriptive
design-time `TrajectoryRef`/`ManeuverBudget` message schemas, and an `operational_targeting`
capability tag that gates dual-use. These are append-only additions, reserved in **Phase 1**; the
full sketch is in [mission-model.md](mission-model.md). They obey the same rule as everything else
in Core — **schema only**: the phase-sequencing *mechanism* lives in the [Sim](sim.md)/[Ops](ops.md)
runtime and the *policy* in [Studio](studio.md)/Ops, never in Core.

**Mission objectives.** Core additively owns the **`ObjectiveSpec`** schema and the
**objective→metric binding** — the shared contract by which [Studio](studio.md) states a goal,
[Bench](bench.md) measures it, [Ledger](ledger.md) values it, and [Ops](ops.md)/[View](view.md)
track progress against it in both design and operations. Like everything in Core it is **schema
only**: the optimization (Studio's trade-study engine) and the evaluation (Bench/Ops) live above
Core. Part of the Core v0.1 baseline (**Phase 0**, RM-P0-CORE-04); append-only thereafter.

**Primary users:** all developers and every other component. Core is a dependency of everything
and depends on (almost) nothing.

**Charter alignment:** §4 ("narrow waist"), §5.7, §10.1. "If only one thing is designed
superbly, it must be Astro-Mine-Core."

---

## 2. Architecture principles

1. **Guard the waist jealously.** Every addition to Core is a permanent liability. The default
   answer to "should this go in Core?" is **no**. A change to the waist is a deliberate change with
   a named consumer, not a convenience.
2. **Mechanism, not policy.** Core defines *how* to describe and exchange; it never decides
   *what* is correct physics, good planning, or the right robot. No domain opinions baked in.
3. **Zero heavy dependencies.** Core depends only on schema/serialization runtimes (protobuf,
   pydantic, jsonschema). No numpy-heavy, no torch, no sim engines. This keeps Core importable
   anywhere, including flight-adjacent and constrained environments.
4. **Versioned, append-only, never-break.** Interfaces evolve by addition and explicit
   versioning. Field tags are never reused; removals go through deprecation windows.
5. **Spec before code.** Each interface is a language-neutral spec (Protobuf / JSON Schema)
   from which all language bindings are generated. The spec is the source of truth, not any one
   implementation.
6. **Capabilities are declared, not assumed.** Assets and plugins declare what they can do;
   consumers negotiate against declarations rather than hard-coding types.
7. **Fail validation early and loudly.** Invalid SADF, manifests, or messages are rejected at
   the boundary with precise, actionable errors — never silently coerced.
8. **Frame- and unit-explicit.** Every quantity has explicit units (SI) and every spatial
   value an explicit reference frame. No implicit conventions.

---

## 3. Application architecture

Core is primarily a set of **schemas + generated bindings + lightweight runtime helpers**,
not a running service. Its modules:

```
astro_mine.core
├── sadf/           # Swarm Asset Description Format: schema, loader, validator, converters
├── env/            # Environment API: abstract observation/action/step contracts
├── policy/         # Policy & Planner API: decision interfaces, composition contracts
├── messages/       # Canonical message schemas (proto + generated types)
├── objective/      # ObjectiveSpec + objective→metric binding (the shared objective contract)
├── registry/       # Plugin manifest schema, discovery, resolution, version negotiation
├── units/          # SI units, frames, time (SPICE-backed): types + canonical JSON Schema + proto/Cap'n Proto wire form
└── compat/         # Interface version negotiation & contract-test utilities
```

### Key abstractions

- **SADF document** — declarative description of an asset: identity, geometry references
  (USD/glTF), kinematics/dynamics, power & thermal budgets, sensor suite, comms capabilities,
  and **declared autonomy capabilities**. Composable (sub-assemblies, payload slots).
- **Environment contract** — `reset()/step(action) -> observation, reward?, info` generalized
  for multi-agent, partial observability, variable timesteps, and explicit comms/observation
  masks. Maps cleanly onto Gymnasium/PettingZoo without being limited to them.
- **Policy/Planner contract** — a uniform interface for "given observations + context, produce
  actions/assignments," with sub-interfaces for mission planners, task-and-motion planners,
  allocators, and controllers, so layers compose (charter §4.4).
- **Plugin manifest** — declares a plugin's kind, the Core interface versions it implements,
  its inputs/outputs, resource needs, capability tags, and provenance/signature. The manifest is
  `extra="forbid"` and is not subclassable; `attributes` is the sanctioned extension point for
  component-specific facets.
- **`PluginKind`** — the **closed, Core-owned vocabulary** of content kinds resolved through the
  registry, and the single answer to *"what interface does this implement?"*. Members map to the
  extension surfaces named across the component backlogs: [Sim](sim.md)
  (`regime_engine`/`sensor_model`/`coupling_scheme`), [Worlds](worlds.md)
  (`world_provider`/`body_pack`/`field_model`), [Prospect](prospect.md)
  (`resource_field_backend`/`observation_model`/`prior_recipe`/`info_gain_objective`),
  [Link](link.md) (`comms_model`), [Fleet](fleet.md) (`asset`), [Bench](bench.md)
  (`policy`/`metric`), and [Studio](studio.md) (`design`/`campaign`).

  Some members are **packaging metadata** for content nobody loads as code — an `asset` manifest
  describes a SADF document instantiated by Sim's loader, and `design`/`campaign` describe frozen
  Studio artifacts whose bytes Core never parses ([core.md](core.md)).
  The vocabulary names what Core *describes for discovery*, not only what it executes.

  It is **published as a schema** at `$defs/PluginKind` under the manifest's absolute `$id`, so
  cross-language consumers resolve it rather than transcribe it (conventions.md §3.1). It is
  **append-only, and widening it is a deliberate Core change** — the rule that makes it safe for
  other components to key on, and three decisions turn on it: [Guard](guard.md) reuses `POLICY`
  rather than adding a kind, `design`/`campaign` were *appended* for Studio's frozen artifacts
  rather than folded into an existing member, and the front end keys its artifact inspector
  registry on the vocabulary without changing it at all ([ui.md](ui.md) §6).

  **What a kind does *not* answer is "what am I looking at."** A [Worlds](worlds.md) illumination
  field model and a [Surrogate](surrogate.md) excavation model both carry `field_model`; the kind is
  the interface, not the subject. Consumers that need to distinguish the *thing* — an artifact
  browser, an inspector — must discriminate on a second facet, which is why [Hub](hub.md) §2
  principle 2 carries its container kind as a separate queryable field and never folds the two
  vocabularies into one. Leaving this implicit is how the question got answered wrongly twice before
  the console's design settled it.
- **Objective contract** — `ObjectiveSpec` (objective + success criteria + their **binding** to
  [Bench](bench.md) metrics and the [Ledger](ledger.md) value model); authored by
  [Studio](studio.md), consumed by Bench/Ledger/[Ops](ops.md)/[View](view.md). Schema only — the
  optimization and evaluation live above Core.

### Extension points

Core *is* the extension mechanism. Everything else extends the platform by implementing a Core
interface and registering a manifest. Core itself has no plugins.

### Interaction patterns

Core is consumed **in-process as a library** (generated types, validators, helpers). It also
publishes the `.proto`/`.json` schema artifacts that services use to generate their own gRPC
stubs. Core exposes no network service of its own.

---

## 4. Application programming & runtime platforms

- **Spec authoring:** Protocol Buffers (proto3) for messages/service contracts; JSON Schema for
  SADF and config; both are the canonical sources.
- **Codegen:** `buf` for Protobuf (lint, breaking-change detection, multi-language generation:
  Python, C++, Rust, TypeScript); `datamodel-code-generator` for Pydantic models from JSON
  Schema.
- **Runtime helpers:** Python 3.12+ (Pydantic v2 validators, loaders). A **Rust** core
  validation/codegen library is recommended for performance and for embedding in non-Python
  contexts (see conventions.md §2).
- **Packaging:** ships in the [`astro-mine-platform`](platform.md) wheel; generated client libs per
  language published alongside; schemas also published as a versioned schema bundle (an OCI artifact)
  so any tool can fetch them — which is how a non-Python consumer resolves a Core `$id` without a
  Python import (conventions.md §3.1).

---

## 5. Data architecture

Core defines **schemas**, it does not store data. It owns:

- the **SADF schema** and its versioned JSON Schema / Protobuf definitions;
- the **message schema catalog** (every cross-component message type);
- the **plugin manifest schema**;
- the **units, frames, and time conventions** (SI; SPICE-backed frames/epochs).

All Core schemas are themselves **content-addressed and versioned**; downstream artifacts
record which Core schema versions they were produced against (provenance, conventions.md §5).

---

## 6. Integration architecture

Core is the integration substrate; it doesn't integrate *with* others so much as it *is* what
others integrate through:

- **Every component** depends on `astro_mine.core` and generates its gRPC/data bindings from
  Core schemas.
- **Fleet** authors assets in SADF; **Worlds/Prospect/Link** expose worlds via the Environment
  API; **Sim** implements the Environment API; **Mind/Learn/Allocate/Guard** implement the
  Policy/Planner API; **Hub** indexes plugins by their Core manifests; **Bench** pins Core
  interface versions per scenario.
- **Version negotiation:** at load time, the `registry`/`compat` modules check that a plugin's
  declared Core interface major versions are satisfied by the host, refusing incompatible loads
  with a clear error.

---

## 7. Infrastructure & deployment

- **Runs:** in-process, everywhere — workstation, cloud worker, ops console, flight-adjacent
  ground tools. No servers, no databases.
- **Footprint:** minimal; importable in constrained environments. This is why Core forbids
  heavy dependencies.
- **Distribution:** language packages + a published schema bundle (OCI artifact) consumed by
  `buf`/codegen in each repo's CI.

---

## 8. Performance & scalability

- **Validation throughput** matters: SADF/message validation sits on hot load paths (e.g.,
  spawning hundreds of assets, ingesting bench submissions). The Rust validator is the
  recommended fast path; Python is the reference.
- **Zero-copy where it counts:** message schemas intended for per-tick telemetry use the
  FlatBuffers/Cap'n Proto encodings (conventions.md §3) rather than Protobuf to avoid
  decode overhead at swarm scale.
- Core itself does not scale out (it's a library); it must impose negligible overhead on the
  components that do.

---

## 9. Security, safety & compliance

- **Manifest signing:** plugin manifests are signed (Sigstore/cosign); `registry` verifies
  signatures and records provenance before load.
- **Capability declarations** in manifests are the substrate for export-control gating:
  sensitive capabilities are tagged and can be policy-gated (OPA) at load/registry time.
- **Validation-as-security:** strict boundary validation prevents malformed/hostile SADF or
  messages from propagating.
- **No execution in Core:** Core never executes plugin code; it only describes, validates, and
  resolves. Execution/sandboxing is the host component's responsibility (conventions.md §9).
- **Export control:** Core's capability-tag vocabulary is the mechanism the rest of the
  platform uses to partition dual-use functionality (charter §9.5).

---

## 10. Observability & operability

- Core emits structured validation diagnostics and version-negotiation decisions via the
  standard logging/OpenTelemetry conventions, so load failures are debuggable across
  components.
- Ships **contract-test utilities** so any component can assert, in its own CI, that it honors
  the Core interface versions it claims.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Message IDL | Protobuf; FlatBuffers; Cap'n Proto; Avro | **Protobuf default**; FlatBuffers/Cap'n Proto for per-tick hot paths |
| SADF base | Pure USD; URDF/SDF extension; custom YAML+JSON Schema (+proto wire) | **Custom YAML + JSON Schema** with USD/URDF/SDF *converters* — keeps the waist engine-neutral |
| SADF geometry refs | USD; glTF; both | **Both**, USD preferred for sim, glTF for web/View |
| Validator implementation | Python only; Python + Rust | **Python reference + Rust fast path** |
| Codegen toolchain | `protoc` scripts; **`buf`**; Bazel | **`buf`** (lint + breaking-change CI + multi-lang) |
| Versioning model | Single platform version; per-interface versions | **Per-interface semantic versions**, decoupled from impl versions |

**Open questions / research dependencies:**

- How expressive must SADF be to span orbiters → excavators *without* becoming a leaky
  god-schema (charter §8 "durable abstraction")? Resolve via reference assets in `Fleet`.
- Exact boundary of the Environment API for variable-fidelity and comms-masked observation —
  co-designed with `Sim` and `Learn`.
- Capability-tag taxonomy for dual-use gating — co-designed with governance/export-control.

---

## 12. Roadmap alignment

- **Phase 0:** ship **interfaces v0.1** — SADF, Environment API, Policy/Planner API, message
  schemas, plugin manifest/registry — sufficient for `Sim + Worlds + Fleet + Bench` to run one
  reference scenario end-to-end. Stability over completeness.
- **Phase 1+:** extend (additively) for autonomy composition, hub indexing, and studio intent;
  every change additive, machine-checked for wire compatibility, and carrying a deprecation window
  where it removes anything. The measure of success is how *little* Core
  has to change as the edges grow.
