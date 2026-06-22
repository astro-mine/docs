# Astro-Mine-Fleet — Technology Architecture

> Layer: **Asset & agent models** · Phase: **0**
> The content library of concrete, parameterizable robot/asset models authored *in* SADF.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Fleet` is the **asset content library** for the platform: a curated, versioned
collection of concrete vehicle and plant models — orbiters, landers, rovers, hoppers/flyers,
excavators, haulers, manipulators, and ISRU plants — each authored in the **Swarm Asset
Description Format (SADF)**. Where [Core](core.md) *owns and defines* SADF as a schema, Fleet
*authors content against it*. Fleet provides:

- a **reference vehicle library** of complete, validated assets covering every regime the
  charter spans (orbital → surface → manipulation → ISRU, charter §5.2);
- **parametric asset families** — templated models whose dimensions, masses, power budgets,
  sensor fits, and capability sets are exposed as validated parameters;
- **authoring, validation, linting, and import/export tooling** that turns CAD/URDF/USD inputs
  into well-formed SADF and checks it against the Core schema and physical-plausibility rules;
- **asset packaging** as signed OCI artifacts published and discovered through [Hub](hub.md).

**What Fleet explicitly does NOT do:**

- It does **not define the SADF schema** — that is [Core](core.md)'s job. Fleet consumes the
  schema and fails loudly when an asset violates it.
- It contains **no physics engine, no solvers, no rendering**. It describes assets; [Sim](sim.md)
  instantiates and simulates them. Fleet declares *what* a wheel/actuator/sensor is, never *how*
  contact or dynamics are integrated.
- It contains **no autonomy logic**. It *declares* capability tags; [Mind](mind.md) and
  [Allocate](allocate.md) reason over those declarations.
- It is **not a registry/distribution service** — it produces artifacts; [Hub](hub.md) indexes
  and serves them.

**Primary users:** roboticists and mission designers assembling the menu of available robots for
a campaign, and contributors publishing new vehicle types as self-contained packages.

**Charter alignment:** §5.2 (the asset & agent models layer), §6 (Fleet describes the robots in
the design/training loop), §9 ("heterogeneity without abstraction collapse"; "a durable
abstraction across orbital, surface, manipulation, and ISRU"), §10.2 (every robot type is a
plugin; reference vehicles are replaceable examples), §11 (Phase-0 deliverable alongside Core,
Sim, Worlds, Bench).

---

## 2. Architecture principles

1. **Consume the waist, never widen it.** Fleet authors *content* against the SADF contract from
   [Core](core.md). If an asset cannot be expressed in current SADF, the response is an RFC to
   Core (conventions.md §3), never a private Fleet extension or side-channel.
2. **Declarative assets, no executable behavior.** A SADF document is pure data — geometry refs,
   parameters, budgets, sensor/comms specs, capability tags. Behavior lives in
   [Mind](mind.md)/[Learn](learn.md); physics lives in [Sim](sim.md). Fleet ships no policy code.
3. **Parametric over copy-paste.** Vehicles are authored as *families* with a typed, range-checked
   parameter schema, not as N hand-edited duplicates. A "10–500 kg rover" is one template, not
   fifty files.
4. **Fidelity tiers per asset, one identity.** A single asset declares multiple representations
   (low-fi mass/power model → high-fi articulated model) under one stable asset identity, so the
   [Sim](sim.md) multi-fidelity scheduler (conventions.md §8) can pick the right one without the
   asset changing identity.
5. **Capabilities are declared, gated, and negotiated.** Every asset carries Core capability tags
   that drive autonomy negotiation ([Mind](mind.md)/[Allocate](allocate.md)) *and* export-control
   gating (conventions.md §12, charter §10.5). Capability vocabulary is owned by Core; Fleet only
   applies it.
6. **Engine-neutral content.** SADF assets reference [Sim](sim.md) physics by capability, not by
   engine. The same asset must instantiate in MuJoCo, Drake, or Isaac without rewriting the asset
   (charter §7 interop-first).
7. **Validate at author time, not run time.** Linting and schema/physical-plausibility checks run
   in CI on every asset and parameter combination, so [Sim](sim.md) never spawns a malformed or
   physically nonsensical vehicle (mirrors core.md principle "fail validation early and loudly").
8. **Frame- and unit-explicit, provenance-tracked.** Every quantity is SI with an explicit frame
   (conventions.md §5); every asset records the CAD/URDF/USD source, converter version, and
   content hashes it was derived from.
9. **Reference assets are replaceable examples.** The shipped library is exemplary, not
   privileged. Third-party assets discovered via [Hub](hub.md) are first-class equals
   (charter §10.2).

---

## 3. Application architecture

Fleet is **library-first** (conventions.md §1): an importable Python package plus a CLI for
authoring/validation/packaging, and a content tree of assets. It exposes no long-running service
of its own; publication is a CI step into [Hub](hub.md).

```
astro_mine.fleet
├── library/         # the reference vehicle catalog (SADF docs + parameter schemas + geometry refs)
│   ├── orbital/     #   relay/comm orbiters, landers (descent stage)
│   ├── surface/     #   rovers, hoppers/flyers
│   ├── manipulation/#   manipulators, excavators
│   ├── logistics/   #   haulers
│   └── isru/        #   ISRU plants (process-bearing assets)
├── templates/       # parametric asset families: base template + parameter JSON Schema + range constraints
├── params/          # parameter-resolution engine: bind values → emit a concrete, validated SADF doc
├── authoring/       # programmatic SADF builders / helpers atop Core's SADF types
├── importers/       # URDF/SDF → SADF, USD-stage → SADF geometry binding, CAD/glTF mesh ingest
├── exporters/       # SADF → URDF/SDF (ROS-ecosystem interop), SADF → USD stage (Sim/Studio)
├── lint/            # schema validation + physical-plausibility & capability-consistency rules
├── geometry/        # USD/glTF asset management, LOD/collision-mesh handling, unit/frame normalization
├── capabilities/    # helpers to attach/validate Core capability tags (autonomy + export-control)
├── package/         # build SADF + geometry + provenance into a signed OCI asset bundle
└── cli/             # `fleet new|lint|validate|render|import|export|resolve|package|publish`
```

### Key abstractions exposed

- **Asset package** — the unit of distribution: a SADF document (or parametric template + its
  parameter schema), referenced geometry (USD/glTF), a Core plugin manifest, and provenance,
  bundled as a content-addressed OCI artifact.
- **Asset template** — a parametric family: a base SADF skeleton plus a parameter JSON Schema
  with validated ranges and derived-quantity rules (e.g., mass scales drive inertia, motor
  torque, and power-draw fields).
- **Fidelity profile** — a named representation tier (`massmodel`, `kinematic`, `articulated`)
  under one asset identity, each pointing at the appropriate geometry/dynamics detail.
- **Capability declaration** — the Core-defined capability tags an asset advertises (e.g.
  `mobility.wheeled`, `excavation.bucket`, `comms.relay.s_band`, `isru.electrolysis`).

### Key abstractions consumed (all from [Core](core.md))

- the **SADF schema** (JSON Schema + canonical Protobuf wire form) and its loader/validator;
- the **capability-tag vocabulary** (autonomy negotiation + export-control gating);
- the **plugin manifest schema** (so each asset is a discoverable plugin);
- the **units/frames/time** conventions (SI, SPICE-backed frames).

### Extension / plugin points

- A **new vehicle type** is a new asset package (charter §10.2) — author SADF, lint, package,
  publish to [Hub](hub.md). No Fleet code change required.
- **Custom importers/exporters and lint rules** register via Python entry points so a
  contributor can support a niche CAD pipeline or a domain-specific plausibility check.
- **Parameter resolvers / derived-quantity functions** are pluggable for advanced templates
  (e.g. a procedural appendage generator) without touching the core resolver.

### Interaction patterns

Consumed **in-process as a library** at author time (Python builders/validators) and at
spawn time ([Sim](sim.md) loads SADF via Core types). Distribution is asynchronous: assets are
packaged in CI and pushed to [Hub](hub.md); consumers pull by content hash. Fleet never sits on
a per-tick hot path.

---

## 4. Application programming & runtime platforms

- **Languages.** **Python 3.11+** for authoring helpers, importers/exporters, the parameter
  engine, lint, and CLI (conventions.md §2). A **Rust** path is recommended for the hot
  validation/linting kernel reused from Core's Rust validator (conventions.md §2) so that
  validating the full library and large parameter sweeps in CI is fast. No C++ is required —
  Fleet runs no physics.
- **Frameworks & libraries.**
  - **Pydantic v2** typed models generated from the Core SADF JSON Schema
    (`datamodel-code-generator`); `jsonschema` for boundary validation (conventions.md §3).
  - **OpenUSD (`usd-core`/`pxr`)** for USD stage authoring/inspection; **`pygltflib`/`trimesh`**
    for glTF and mesh handling (decimation, LOD, collision-hull generation); **GDAL/PROJ/SPICE**
    only where an asset references body-fixed frames (conventions.md §5).
  - **`urdfpy`/`yourdfpy`** and an SDF parser for ROS-ecosystem import/export.
  - **`typer`/`click`** for the CLI; **`rich`** for diagnostics.
- **Runtime model.** A pure library + CLI; "library first, service second" (conventions.md §1).
  The only "service-like" behavior is a CI publish step that authenticates to [Hub](hub.md).
- **Build/packaging.** Python wheel `astro-mine-fleet` (import `astro_mine.fleet`,
  conventions.md §13); **SemVer**. The asset *content* is versioned and distributed
  independently of the toolchain, as **OCI artifacts** (conventions.md §7) — the library wheel
  ships only tooling and may bundle a thin "starter" set by reference.

---

## 5. Data architecture

Fleet **owns and produces asset content**; it does not own any schema (that is [Core](core.md)).

| Data | Role | Format / store |
|---|---|---|
| Concrete asset definitions | Produced | **SADF** documents in **YAML/JSON** (authored), Core **Protobuf** wire form (canonical), validated by the Core JSON Schema (conventions.md §3) |
| Parametric templates | Produced | SADF skeleton + a **parameter JSON Schema** with range/constraint rules |
| Geometry / visual assets | Produced / referenced | **USD** (preferred for [Sim](sim.md)/[Studio](studio.md)) and **glTF** (web/[View](view.md)); meshes in standard formats with explicit units/frames (conventions.md §3) |
| Capability declarations | Produced | Core capability tags embedded in SADF (autonomy + export-control) |
| Import sources | Consumed | **URDF/SDF** (ROS ecosystem), **CAD/STEP→mesh**, USD/glTF |
| Asset bundles | Produced / published | **content-addressed OCI artifacts** in an S3-backed registry (conventions.md §5, §7), served via [Hub](hub.md) |
| Asset catalog metadata | Produced | indexed by [Hub](hub.md) in **PostgreSQL** (conventions.md §5); Fleet emits the records, Hub stores them |

**Schemas.** Fleet authors *against* Core's SADF JSON Schema and embeds the Core schema version
each asset targets, so Sim/Studio can negotiate compatibility (conventions.md §3 schema
evolution; core.md §6 version negotiation).

**Lifecycle.** author (template or hand-authored) → lint/validate (CI) → resolve parameters to a
concrete doc → bind/normalize geometry → package as OCI bundle → publish to [Hub](hub.md) →
discovered/pulled by [Sim](sim.md)/[Studio](studio.md). Deprecation follows SemVer; a superseded
asset version remains pullable by content hash for reproducibility.

**Provenance & versioning.** Every asset bundle records (conventions.md §5): the CAD/URDF/USD
**source content hashes**, the **importer/converter version**, the **Core SADF schema version**,
the toolchain version, and a signature. This makes any [Bench](bench.md) result that used an
asset reproducible down to the exact geometry and parameter values.

---

## 6. Integration architecture

Fleet sits at the upstream edge of the design/training loop (charter §6: "Astro-Mine-Fleet
describes the robots"). Every integration crosses a [Core](core.md) contract — no private
side-channels (conventions.md §1).

- **[Core](core.md):** Fleet's foundational dependency. It consumes the SADF schema, capability
  vocabulary, plugin manifest schema, and units/frames. Each asset ships a **Core plugin
  manifest** (kind = asset; declared SADF/Core interface versions; capability tags; provenance;
  signature) so it is a discoverable plugin (core.md §3 plugin manifest).
- **[Sim](sim.md):** the primary consumer. Sim loads SADF and **instantiates** geometry,
  kinematics/dynamics, sensors, comms, and power/thermal budgets. The **SADF↔engine boundary**
  is the key design seam (see §11): SADF declares engine-neutral physical *parameters and
  fidelity profiles*; Sim maps them to engine-specific config (MuJoCo/Drake/Isaac).
- **[Mind](mind.md) & [Allocate](allocate.md):** consume **capability declarations** — what each
  asset can do — to negotiate roles and solve heterogeneous task allocation (charter §5.4).
  Capability tags are the contract; Fleet never embeds planner logic.
- **[Studio](studio.md):** presents the Fleet/[Hub](hub.md) catalog as the **selectable robot
  menu** for assembling a campaign (charter §5.2), using glTF/USD geometry for preview.
- **[Hub](hub.md):** Fleet **publishes** signed OCI asset bundles and emits catalog metadata;
  Hub indexes and serves them for discovery/reuse (charter §5.7).
- **[Bridge](bridge.md):** an asset's SADF (and its URDF/SDF export) is the description that may
  **map to real hardware** through ROS 2/cFS/F´ adapters, so the same asset identity spans sim
  and flight (charter §5.6; conventions.md §4 ROS 2/DDS data plane). Fleet provides the
  description; Bridge owns the binding and its export-control posture.
- **[Worlds](worlds.md)/[Prospect](prospect.md):** indirect — assets are instantiated *into* a
  world by [Sim](sim.md); Fleet shares the conventions.md §5 CRS/frame rules so an asset placed
  on a body uses a consistent body-fixed frame.
- **[Bench](bench.md):** scenarios pin exact asset versions (by content hash) so a benchmark's
  robot menu is reproducible (conventions.md §11; core.md §6).

---

## 7. Infrastructure & deployment

- **Deployment tier:** primarily **local/dev** (conventions.md §7 tier 1) — a roboticist clones,
  authors, lints, renders, and packages an asset on a workstation; this tier MUST always work.
  The only networked operation is publishing to [Hub](hub.md).
- **Compute:** **CPU-bound and modest.** Authoring, validation, import/export, and parameter
  resolution need no GPU. A **GPU is optional** only for offline geometry preview/thumbnail
  rendering of USD/glTF; CI does this headless. Memory is dominated by the largest mesh being
  processed — bounded by streaming/decimation in the geometry module.
- **Containerization:** an OCI **toolchain image** (Python + USD/glTF + URDF/GDAL deps) for
  reproducible CI authoring/linting (conventions.md §7). Asset *content* ships as separate,
  content-addressed OCI **artifacts**, not code images.
- **Orchestration:** none at runtime (no service). CI is **GitHub Actions** (conventions.md §11);
  large library-wide validation/parameter sweeps can fan out as an **Argo Workflows** batch
  (conventions.md §7) when the library grows.
- **Scaling:** scaling is about **catalog size and CI throughput**, not request load —
  parallelize lint/validate across assets and parameter samples; cache by content hash.

---

## 8. Performance & scalability

- **Targets.**
  - Spawn-path overhead: SADF parse + validate per asset should be **negligible** relative to
    [Sim](sim.md) instantiation, so spawning hundreds of assets at scenario start is not
    bottlenecked by Fleet (mirrors core.md §8 validation-throughput concern).
  - CI: lint + schema-validate the entire reference library on every PR in **minutes**.
  - Parameter resolution: bind + validate a concrete asset from a template in well under a
    second so [Studio](studio.md) trade studies stay interactive.
- **Bottlenecks.** (1) JSON-Schema validation over many assets/parameter combinations;
  (2) mesh/geometry processing (decimation, collision-hull generation) for high-fi assets;
  (3) USD/URDF/CAD imports of large stages.
- **Mitigations.**
  - Use the **Rust validation kernel** (shared with Core, conventions.md §2) for the hot CI
    path; Python remains the reference.
  - **Content-address and cache** geometry artifacts so unchanged meshes are never reprocessed
    (conventions.md §5).
  - **Multi-fidelity by construction** (conventions.md §8): cheap mass models for large sweeps,
    articulated models only when fidelity demands — Fleet *declares* the tiers, [Sim](sim.md)
    *chooses* them.
  - **Stream/range-read** large geometry from object storage (conventions.md §8) rather than
    materializing whole stages.
- **Scaling strategy:** horizontal across assets/parameter samples in CI (Argo); the library
  itself scales by adding content, with no central runtime to saturate.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** Fleet itself is a library; access control lives at the **publish boundary** to
  [Hub](hub.md) (OIDC + OPA RBAC, conventions.md §9). Who may publish/overwrite an asset
  namespace is a Hub/OPA policy.
- **Supply chain:** asset bundles are **signed (Sigstore/cosign)** with **SLSA provenance** and
  an **SBOM-equivalent** content manifest (geometry hashes, source lineage), per
  conventions.md §9; [Hub](hub.md)/[Core](core.md) verify signatures before load (core.md §9
  manifest signing).
- **Validation-as-security:** strict boundary validation (the lint module) prevents
  malformed/hostile SADF and untrusted geometry from propagating into [Sim](sim.md)
  (mirrors core.md §9). Imported meshes are size-/complexity-bounded and sanitized.
- **Plugin isolation:** assets are *data*, not code — they carry no executable behavior, which
  sharply limits the threat surface. Pluggable importers/lint rules that run third-party code
  follow conventions.md §9 (entry points for trusted; sandboxed out-of-process for untrusted).
- **Export-control / dual-use (conventions.md §12, charter §10.5):** capability tags are
  **first-class gating metadata**. Sensitive vehicle classes or capabilities (e.g. certain
  comms/RF, precision-targeting-adjacent payloads, anything that maps to controlled flight
  hardware via [Bridge](bridge.md)) are **tagged at the asset level** so OPA policy can gate
  publication, discovery, and download. Genuinely sensitive assets are partitioned into
  access-controlled repos; the open library stays default-open science/simulation content.
- **Safety:** Fleet declares physical limits (mass/power floors, joint/torque/keep-out
  envelopes) that downstream **[Guard](guard.md)** enforces as hard constraints; Fleet does not
  itself enforce runtime safety but provides the *authoritative limit data* the assurance layer
  relies on.

---

## 10. Observability & operability

- **Diagnostics:** the lint/validation pipeline emits **structured JSON** diagnostics
  (file, JSON-Pointer path, rule id, severity, fix hint) via the standard logging/OpenTelemetry
  conventions (conventions.md §10), so authoring failures are precise and machine-readable
  (mirrors core.md §10).
- **Metrics:** CI publishes catalog-health metrics (Prometheus, conventions.md §10): asset
  count by class, lint pass/fail rates, schema-version drift, mesh-size distribution.
- **Testing & validation strategy:**
  - **Schema conformance:** every asset and a sampled grid of every template's parameter space
    validates against the pinned Core SADF schema (`pytest`; **Hypothesis** property-based tests
    over parameter ranges, conventions.md §11).
  - **Physical-plausibility lint:** mass/inertia/power/thermal/sensor budgets are internally
    consistent and within declared envelopes (e.g. positive-definite inertia, power balance,
    sensor FOV/range sanity).
  - **Round-trip tests:** URDF→SADF→URDF and USD→SADF→USD preserve invariants (kinematic tree,
    masses, frames) within tolerance.
  - **Golden/determinism gates:** parameter resolution is deterministic — same inputs ⇒ same
    canonical SADF bytes (conventions.md §11; charter determinism default).
  - **Contract tests:** every asset proves it honors the Core SADF/interface version it claims
    (consumer-driven contract tests against [Core](core.md), conventions.md §11; core.md §10).
  - **Instantiation smoke test:** a representative asset spawns and steps in [Sim](sim.md) in CI,
    catching SADF that validates but cannot be realized by an engine.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Physics/dynamics parameterization split | All physics in SADF; minimal SADF + most config in [Sim](sim.md); **engine-neutral physical params in SADF, engine-specific config in Sim** | **Engine-neutral physical params (mass, inertia, joint limits, motor/torque, friction priors, sensor specs, power/thermal budgets) in SADF; numerical/solver/engine knobs in [Sim](sim.md)** — keeps assets engine-portable (charter §7) and the waist neutral (core.md §11 SADF base) |
| Geometry pipeline | Author natively in USD; convert from CAD/STEP; convert from URDF/SDF; support all | **Support all via importers, store USD (sim) + glTF (web) as the two canonical refs** (conventions.md §3 "USD preferred, glTF for web") |
| Parametric modeling approach | Hand-authored variants; **template + parameter JSON Schema**; full procedural generators | **Template + validated parameter schema as the default; pluggable procedural generators for advanced families** — matches "plugins over patches" (conventions.md §1) and keeps the common case diff-friendly |
| Fidelity tiers for one asset | Single high-fi model; single low-fi model; **multiple profiles under one identity** | **Multiple fidelity profiles (`massmodel`/`kinematic`/`articulated`) under one stable asset identity** — feeds Sim's multi-fidelity scheduler (conventions.md §8) |
| ROS-ecosystem interop | Native URDF/SDF; SADF only; **bidirectional URDF/SDF ↔ SADF converters** | **Bidirectional URDF/SDF converters** (lossy-but-documented), with SADF authoritative — interop-first without coupling the waist to robot-arm-centric URDF (core.md §11) |
| Validation engine | Python only; **Python reference + Rust fast path** | **Python reference + Rust fast path** reused from Core's validator (conventions.md §2; core.md §11) |
| Asset distribution | Bundle in the wheel; git-LFS; **content-addressed OCI artifacts via [Hub](hub.md)** | **Content-addressed OCI artifacts via [Hub](hub.md)** (conventions.md §7) — decouples heavy content from the toolchain wheel |
| Capability taxonomy ownership | Define in Fleet; **own in [Core](core.md), apply in Fleet** | **Own the vocabulary in [Core](core.md); Fleet only applies/validates tags** (autonomy + export-control gating) |

**Open questions / research dependencies:**

- **How much physics belongs in SADF before it becomes a leaky god-schema** (charter §9 "durable
  abstraction"; core.md open question)? Resolve empirically as the reference assets span
  orbiter → excavator; escalate gaps to a Core RFC rather than widening SADF unilaterally.
- **Granular/excavation asset parameterization.** Excavators and ISRU intake are the charter's
  hardest physics (charter §9); the *asset-side* parameters needed to drive granular contact in
  [Sim](sim.md)/[Surrogate](surrogate.md) are unsettled — co-design with both.
- **Lossy URDF/SDF/USD round-trips.** Exactly which fields survive conversion, and how to flag
  loss, needs a documented fidelity contract per converter.
- **Procedural vs template families** for highly variable assets (e.g. articulated arms, modular
  haulers): when does a generator earn its complexity over a parameter schema?
- **Sensor/comms model depth in SADF** vs deferring to [Sim](sim.md)/[Link](link.md) — how much
  of a sensor's noise/range model is asset-intrinsic vs environment-coupled.

---

## 12. Roadmap alignment

- **Phase 0 (now):** Fleet is a **Phase-0 deliverable** alongside Core/Sim/Worlds/Bench
  (charter §11). MVP ships:
  - the SADF authoring/validation/lint toolchain and CLI;
  - URDF/SDF importers and USD/glTF geometry handling;
  - a **minimal reference library sufficient for the anchor scenario** (lunar polar water-ice
    prospecting): at least a relay **orbiter**, a **lander**, a prospecting **rover**, and an
    **excavator/hauler** plus a basic **ISRU plant**, each with low-fi and at least one
    higher-fi profile;
  - packaging of assets as signed OCI artifacts (pre-[Hub](hub.md): a local/object-store path,
    upgraded to Hub publish when Hub lands in Phase 1).
  - **Goal:** a researcher can clone, pick robots, and run/score the reference scenario in an
    afternoon (charter §13), with assets that [Sim](sim.md) instantiates and [Bench](bench.md)
    pins by hash.
- **Phase 1:** broaden the parametric families and capability taxonomy; integrate publish/discover
  through [Hub](hub.md); expose the asset menu in [Studio](studio.md); feed capability
  declarations to [Mind](mind.md)/[Allocate](allocate.md) as autonomy lands.
- **Phase 2:** asset descriptions back **[Bridge](bridge.md)** hardware mapping for terrestrial
  analog rover-swarm field tests; tighten export-control gating on hardware-mappable assets.
- **Phase 3:** community-contributed vehicle types and new-body assets (asteroid/icy-moon
  platforms) as plugins; third-party commercial asset packages atop the open library
  (charter §11). The measure of success: new vehicle types arrive as packages, never as Fleet
  code changes.
