# Cross-Cutting Technology Conventions

> **Status:** Normative for every Astro-Mine component and every distribution that ships one.
> Changes land as ordinary pull requests against this document. What protects a published
> interface is not a process gate but the machinery of §3 and §11 — append-only schemas,
> machine-checked wire compatibility, a pinnable contract digest, and layering tests that fail
> the build.

This document defines the technology decisions that are shared across **every** Astro-Mine
component. Component architecture docs in this directory **reference** these decisions rather
than restating them; a component only documents where it *deviates* and *why*. The goal is a
**thin, stable core with thick, swappable edges**: the narrow-waist contracts here change
slowly and deliberately; everything else can evolve independently.

When this document says **MUST / SHOULD / MAY**, read them in the RFC-2119 sense.

**Component vs. distribution.** A *component* is a unit of design — `Core`, `Sim`, `Worlds` — and
is a subpackage, `astro_mine.<name>`. A *distribution* is a unit of release. There are four
(§7): the platform library, the CLI, the REST tier, and the front end. This document is normative
for both, and says which it means whenever the difference matters.

---

## 1. Architecture tenets (apply to all components)

1. **Narrow waist.** Everything integrates through a small set of stable contracts owned by
   `Astro-Mine-Core` (SADF, environment API, policy/planner API, message schemas, plugin
   registry). Components MUST NOT create private side-channels that bypass Core contracts.
   Sharing one distribution is not permission to couple: a component MUST NOT import another
   component's underscore-private modules, and MUST NOT depend on a name absent from the other's
   `__all__` (§13). Which dependencies between components are *allowed* is §3.2; how a component
   gets a collaborator without depending on it is §3.3.
2. **Contribute once, use everywhere.** A world, asset, planner, policy, or ISRU process is
   authored against Core interfaces and is then usable in design, training, operations, and
   benchmarks without modification.
3. **Plugins over patches.** New content (bodies, robots, sensors, planners, processes) is a
   plugin discovered through the registry — never a core code change. Reference
   implementations ship as *replaceable examples*, not privileged internals.
4. **Library first, service second.** Every component is usable as an importable library on a
   single workstation before it is a network service. The service is a deployment of the
   library, not a separate codebase — which is why the REST tier is its own distribution over an
   unchanged library rather than routes woven through it (§7).
5. **Determinism & reproducibility by default.** Same inputs + same seed + same pinned
   environment ⇒ same result. This is a hard requirement for `Bench` and a strong default
   everywhere.
6. **Uncertainty is first-class.** Resource fields, surrogate outputs, state estimates, and
   sim-to-real claims carry explicit uncertainty. "A single guess" is an anti-pattern.
7. **Interop, don't reinvent.** Bridge to ROS 2, cFS, F´, SPICE, OpenMCT, STK/GMAT, USD,
   ONNX. Build the planetary-swarm layer on mature foundations.
8. **Honest about dual use.** The scientific, simulation, and coordination commons is open;
   genuinely sensitive operational targeting is partitioned and access-controlled. See §12.

---

## 2. Languages & runtimes

| Use | Standard | Notes |
|---|---|---|
| Control plane, APIs, ML, orchestration glue, most component logic | **Python 3.12+** | The research community's lingua franca; PyTorch/JAX/Gymnasium ecosystem. Type-hinted, checked with `mypy`/`pyright`. |
| Performance-critical kernels (physics, contact, granular, hot inner loops) | **C++20** | Pybind11 bindings exposed to Python. Integrates with Drake / MuJoCo / Isaac / BehaviorTree.CPP. |
| High-assurance & safety-critical logic, schema/codegen tooling | **Rust** | Recommended where memory safety + performance matter most: `Guard`'s runtime monitors (a PyO3 extension the platform wheel bundles), `Core` schema validation/codegen, content-addressed registry tooling. Optional elsewhere. |
| GPU kernels | **CUDA** (+ vendor-neutral fallback) | Used inside Sim/Surrogate; abstracted behind device-agnostic interfaces where feasible. |
| Web front-ends | **TypeScript + React** | The console shell, the design system, the visualization library, and every per-component surface. The full baseline is §2.1. |

**Rule:** the *public* API surface of any component MUST be reachable from Python. Native code
sits behind Python bindings or a gRPC service.

**Scope of that rule.** It binds *components* — the Python packages that own platform capability.
It does **not** bind the **front-end packages** of §2.1 (`@astro-mine/surface`, `@astro-mine/ui`,
`@astro-mine/console`, `@astro-mine/view`, and the per-component surfaces), which are TypeScript
and have no Python surface at all. That is not an exemption from the rule but a consequence of it:
a front-end package renders capability that a component already exposes from Python, and adds none
of its own. A front-end package that needed its own Python API would be a component wearing the
wrong clothes.

**The library ships no commands.** The platform distribution declares **no** console scripts. Every
command lives in the CLI distribution (§7, §13), which is a thin wrapper over library functions: a
command module MAY declare arguments, read a namespace, call a platform function, format output,
and map a result to an exit status — and MUST NOT implement platform behaviour of its own. A
capability reachable only by running a command is a capability the library failed to export.

### 2.1 The front-end baseline

Normative for every front-end package. This is the **only** place it is stated; a component doc
cites it rather than restating it, and documents only where it deviates and why (§13).

| Concern | Standard |
|---|---|
| Language / framework | **TypeScript 5.5** · **React 18.3** |
| Runtime | **Node >= 20.19** (Vite 8 and Vitest 4 require it) |
| Package manager | **pnpm 11.10.0**, pinned in the workspace root's `package.json` `packageManager` |
| Build | **Vite 8** — library mode for published packages, app mode for the console |
| Unit tests | **Vitest 4** + Testing Library, `jsdom` environment |
| Browser tests | **Playwright** against the built artifact, not the dev server |
| Lint / format | **ESLint 8** (classic config) + `typescript-eslint` 7 · **Prettier 3** |
| Routing | **react-router** — nested routes map onto the console's surface namespaces |
| Server state | **None.** `fetch` plus the design system's `AsyncState` primitive |
| Charts | **visx** + `d3-scale` |

**On the package manager.** One pinned version, everywhere. Three managers across four trees is how
a cold clone acquires three ways to fail, and `--frozen-lockfile` turns any drift into a red build
rather than a silent one — which is the point. The pin is a floor for reproducibility, not a
statement that newer is unusable; move it deliberately, in one sweep.

**On server state.** The platform deliberately ships **no** data-fetching or client-cache library.
Every front end already uses bare `fetch`, and the loading / error / empty discipline lives in a
shared `AsyncState` component instead — which is where it belongs, because the discipline is about
what the user is shown when a request is in flight or has failed, not about how the request was
made. Adding a cache layer is a real dependency in every surface and buys little for screens that
are read-mostly and human-paced. Revisit it when a surface has a concrete need (optimistic writes,
polling, cross-surface cache invalidation) — as a deliberate, documented change to this baseline,
not as an import in one surface.

**On charts.** `visx` composes D3 primitives as React components, so the chart discipline is
enforced by the API rather than by care: `@astro-mine/ui` owns the chart layer, a second y-axis is
unrepresentable, and a value with no uncertainty bound renders as an open mark by construction
rather than as a zero-length error bar. Parallel coordinates is the one form `visx` does not
provide and is hand-built.

---

## 3. Interfaces, schemas & APIs (the narrow waist)

| Concern | Standard | Rationale | Alternatives considered |
|---|---|---|---|
| **Messages & service contracts (IDL)** | **Protocol Buffers (proto3)** + gRPC | Language-neutral, codegen for Py/C++/Rust/TS, disciplined backward-compat rules | FlatBuffers/Cap'n Proto (see hot-path note) |
| **High-rate / zero-copy telemetry payloads** | **FlatBuffers or Cap'n Proto** | Zero-copy decode for per-tick sensor/telemetry streams | Protobuf (default for everything else) |
| **SADF — Swarm Asset Description Format** | Human-authored **YAML/JSON** validated by **JSON Schema**, with a canonical **Protobuf** wire form | Engine-neutral, diff-friendly, reviewable; converters bridge URDF/SDF/USD | Pure USD (too engine-coupled for the waist); pure URDF (too robot-arm-centric) |
| **Geometry / visual assets referenced by SADF** | **USD** (preferred) and **glTF**; meshes via standard formats | Aligns with Isaac/Omniverse; USD is the graphics-interchange standard | — |
| **Config & scenario specs** | **JSON Schema** + **Pydantic v2** (Python) | One schema validates files and generates typed models | — |
| **RL environment view** | **Gymnasium** (single-agent) / **PettingZoo** (multi-agent) APIs | Community standard; instant familiarity | — |
| **External / web-facing APIs** | **REST + OpenAPI 3.1** via **FastAPI**, in the API distribution (§7) | Browser- and tool-friendly, self-documenting | GraphQL only where a UI's query shape demands it |
| **Internal service-to-service** | **gRPC** over HTTP/2, shipped with the component that serves it | Streaming, typed, efficient | — |

**Schema evolution:** Protobuf fields are append-only; never renumber or repurpose tags.
Breaking a Core contract requires a new major interface version and a deprecation window. All
schemas are versioned with the component that owns them and published as generated client
libraries.

**Where the REST layer lives (normative).** A component MUST NOT ship its own FastAPI application.
Every REST surface is a route module in the API distribution, built over the owning component's
public library API — so the component stays importable without a web framework, one set of REST
conventions applies platform-wide, and the routes cannot become the only place a behaviour exists
(§2, §7). gRPC services are different and stay with their component: they serve the component's own
contract at high rate, are not a web edge, and have no cross-component conventions to unify.

### 3.1 Referencing a Core schema from another component

Core owns schemas that other components `$ref` across files — above all the shared units vocabulary
(§5). Left unstated, this went wrong in a specific and instructive way: six components once invented
five different techniques to name one schema — path arithmetic reconstructing Core's directory
layout, `$id` squatting inside Core's namespace, a hardcoded copy of a private URI, runtime
derivation, and a vendored byte-copy. Only one was correct. These rules are what was missing, and
they hold whether or not the referencing code ships in the same distribution.

**One name.**

- A Core schema is referenced by its absolute **`$id`**. A schema **MUST** `$ref` it that
  way — never by a relative path, never by a URI derived from Core's directory layout. A path that
  happens to resolve inside one repository is not a name; it is a coincidence that breaks the first
  time the layout moves.

  ```json
  { "$ref": "https://schemas.astro-mine.org/core/units/v0.1/units.schema.json#/$defs/ReferenceFrame" }
  ```

- A published `$id` is **public, append-only API**. It **MUST NOT** be repurposed or removed; a new
  schema minor takes a new `$id` (`…/v0.2/…`). Changing a Core schema's `$id`, or the set of URIs
  its `$ref` graph resolves to, is a **breaking change**.

**`$id` namespaces are owned.**

- A component **MUST** declare `$id`s only under its own namespace
  (`https://schemas.astro-mine.org/<component>/…`). It **MUST NOT** publish an `$id` under another
  component's namespace, and two components **MUST NOT** publish the same `$id`. A colliding or
  squatted `$id` is a silent wrong-schema resolution.

**One mechanism.**

- These URIs are **nominal**: nothing serves them, and resolution **MUST** work offline (§11).
  Resolution is therefore always by registry, **never over the network**.
- A validator **MUST** be built with `astro_mine.core.schema_registry()`, which resolves every Core
  schema by `$id`:

  ```python
  Draft202012Validator(my_schema, registry=schema_registry(my_schema))
  ```

- A component **MUST NOT** import Core modules that are underscore-private or absent from Core's
  `__all__`. Correspondingly, **Core MUST provide a public, documented equivalent** for any
  capability a consumer legitimately needs — the absence of one is what produced all five
  workarounds, and a private API with five importers is a Core defect, not a consumer defect.
  Consolidation makes this rule *more* load-bearing, not less: reaching into Core's internals is now
  a plain import with nothing to declare and nothing to notice.

**Cross-language and vendored consumers.**

- A consumer that cannot import Core (a non-Python binding) **MUST** resolve Core schemas from the
  **published bundle**, using its `schema_index` (`$id` → path).
- A consumer that nonetheless **vendors** a copy of a Core schema **MUST** guard it against drift by
  pinning `astro_mine.core.SCHEMA_DIGEST` (or the bundle's `schema_digest`) and **failing** CI when
  the copy no longer matches. A hand-resynced copy guarded by a comment is drift with extra steps.

**Compatibility is verified, not assumed.** Within the platform distribution, a change to Core runs
every component's schema tests in the same CI job, so breaking a consumer fails the pull request
that breaks it — the property that used to require a cross-repo canary, now structural. Across
distributions it still requires a check: the CLI, API, and front-end builds **MUST** run against the
platform at `HEAD`, not against a released pin. A downstream job that resolves its dependency from
an old release cannot fail for any change, which makes a green board actively misleading rather than
merely uninformative.

---

### 3.2 Dependencies between components (normative)

One distribution removed the packaging friction that used to discourage a component from reaching
into another. These are the rules that replace it. They are **positive rules** — they say what is
allowed, not only what is forbidden — because "no private imports" was never a dependency policy.

**Three tiers.**

| Tier | Members | May depend on | Depended on by |
|---|---|---|---|
| **0 — the waist** | [Core](core.md) | nothing | everything |
| **1 — companions** | [Spice](spice.md) · [Seal](seal.md) | Core only | anything, freely |
| **2 — components** | every other component | tiers 0 and 1 freely; tier 2 under the rules below | — |

- **Any component MAY depend on Core, Spice, or Seal without justification.** All three are the
  platform's *single* implementation of something that must not disagree — the contract vocabulary,
  frame and epoch resolution, and artifact integrity (charter §9.6). Duplicating any of them is the
  failure mode; depending on them is the design.
- **A companion MUST depend on Core only.** It MUST NOT depend on another companion, and MUST NOT
  depend on a tier-2 component. A companion that needs a component is not a companion.
- **Core depends on nothing.** No heavy dependency, no crypto, no service, no component.

**Lateral dependencies (tier 2 → tier 2) are permitted, and constrained.**

1. **Acyclic, always.** The component import graph **MUST** be a DAG. A cycle is not a
   dependency problem to be managed; it is two components that are one component, or a missing
   Core contract. Asserted by test (§11).
2. **Minimal, and argued.** A lateral edge **MUST** be recorded in the depending component's
   document, §6 (integration architecture), with the reason. *Convenient* is not a reason. The test
   is simple: **could the collaborator be a Protocol the caller passes in?** If yes, the edge should
   not exist — see dependency inversion below.
3. **Pointing down, never up.** Dependencies follow the layer table in
   [README.md](README.md): a lower layer MUST NOT import a higher one. An upward edge is a design
   defect, and the fix is inversion rather than permission. (Live example: `sim → bench`. Bench runs
   Sim through the `EpisodeRunner` seam, so Sim importing the benchmark harness has the arrow
   backwards.)
4. **Runtime and type-only edges are both edges, and are not the same edge.** An import under
   `TYPE_CHECKING`, or inside a function body, still counts for acyclicity — it is still a design
   dependency. It does **not** count against import cost (§8), which is why deferring one is a
   legitimate way to keep the local tier light. The layering test reports the two separately, because
   a component with many type-only edges and no runtime edges is telling you it wants its
   collaborators injected.

**The shape a lateral edge should have, when it must exist.** All three of today's genuine edges
share it, and it is worth naming as the acceptable form: the dependency is **confined to a single
adapter module named for the other component** (`allocate/mind.py`, `guard/mind/plugin.py`,
`sim/bench/`), and it exists so the *provider* can implement the *host's* plugin protocol. That is
dependency inversion in the classic sense — the plugin depends on the host's abstraction, never the
reverse — with one defect left: the abstraction lives in a component instead of at the waist. A
lateral edge scattered across a component's modules is a different thing entirely, and is not
permitted.

**Where this stands today.** Nine runtime module-scope lateral edges exist, six of them to
companions. The three genuine component-to-component edges — `allocate → mind`, `guard → mind`,
`sim → bench` — each have the shape above and each disappear when their protocol moves to Core;
`TierPlugin` already has two implementors, which by §3.3 makes it Core's to own today. Separately,
[Hub](hub.md) is referenced by eight components and imported at runtime module scope by **none**:
every edge is `TYPE_CHECKING` or deferred. That is dependency inversion already being done by hand,
with the crudest available tool, and it is the case the next section exists to serve properly.

### 3.3 Dependency inversion (normative)

**A component MUST NOT reach for a collaborator it can be given.**

- Where a component needs a capability another component provides, the contract is a **Protocol**,
  and the concrete implementation is **passed in by the caller** — constructor argument or factory
  parameter, never a module-level lookup, never an import at the point of use.
- **Core owns the Protocol when two or more components share it.** A Protocol used by one component
  and implemented by another may live with the consumer. Once a second consumer appears it belongs
  at the waist, by the same rule that governs schemas (§3.1).
- A component **MUST NOT** import a concrete implementation in order to type against it. `from
  astro_mine.cloud.artifacts.store import ArtifactStore` is a Core Protocol wearing a component's
  address.

**Wiring happens at composition roots, and only there.** The platform uses
[`svcs`](https://svcs.hynek.me/) — a small, explicit, typed registry, no decorators and no
import-time magic — at the four places that compose the platform into an application:
[`astro-mine-cli`](cli.md), [`astro-mine-api`](api.md), the Cloud in-pod worker, and Studio's
orchestration worker.

```python
# a component: no container, no framework, no import of an implementation
class SimEpisodeRunner:
    def __init__(self, store: ArtifactStore, resolver: Resolver) -> None: ...

# a composition root: the only place that knows both halves
reg = svcs.Registry()
reg.register_factory(ArtifactStore, make_hub_store)
```

Three prohibitions make that boundary real, and they matter more than the library choice:

- A component **MUST NOT** import `svcs`, construct a `Registry` or a `Container`, or resolve
  anything from one. A container inside a component is a service locator: it converts a dependency
  from something a signature declares into something only a run reveals, which defeats §3.2's DAG
  rule and the test that enforces it.
- There is **no global container**, and no module-level singleton standing in for one. A composition
  root builds its container, uses it, and drops it.
- **The library is replaceable and the inversion is not.** Protocols plus constructor injection are
  the architecture; `svcs` is a convenience at four call sites. If it were removed tomorrow, the
  wiring would become four hand-written functions and nothing else would change. Any proposal that
  makes that untrue is a proposal to be refused.

---

## 4. Transport & messaging

Three planes, chosen per latency/criticality:

- **Control plane (sync):** **gRPC** for request/response and server-streaming between
  services; **REST/OpenAPI** at the edge for browsers and third-party tools (§3, §7).
- **Eventing / orchestration (async, cloud):** **NATS + JetStream** as the default
  lightweight pub/sub and work queue (sim job lifecycle, hub events, bench result ingestion).
  **Apache Kafka** is the recommended alternative *only* where a durable, high-throughput,
  replayable event log is required at scale.
- **Real-time robotics / operations data plane:** **ROS 2 / DDS** — the charter's interop
  lingua franca — for fleet telemetry, commands, and anything that must speak to robots and
  flight stacks. `Bridge` is the boundary between this plane and the rest of the platform.

**Recorded streams** (sim outputs, ops telemetry, replays) use the **MCAP** container so a
single file carries heterogeneous, timestamped, schema-tagged channels.

---

## 5. Data architecture

| Data kind | Format / store | Used by |
|---|---|---|
| N-D arrays / physical fields | **Zarr** (cloud-native, chunked) primary; **HDF5** for interop | Worlds, Prospect, Sim |
| Planetary terrain / DEMs / rasters | **Cloud-Optimized GeoTIFF (COG)** via **GDAL**; cataloged with **STAC** | Worlds, Prospect, View |
| Tabular data / results | **Apache Parquet**; **Apache Arrow** in-memory | Bench, Learn, Allocate, Ops |
| Time-series logs / replays | **MCAP** | Sim, Ops, View, Bench |
| Large binary artifacts (datasets, policies, recordings, plugin bundles) | **S3-compatible object store** (MinIO self-host; S3/GCS in cloud), **content-addressed** | Hub, Cloud, Bench |
| Relational metadata & catalogs | **PostgreSQL** (+ **PostGIS** geospatial, **pgvector** embeddings) | Hub, Bench, Ops, Studio |
| Cache / ephemeral state / queues | **Redis** | most services |
| Live metrics | **Prometheus**; **TimescaleDB** for high-rate operational queries | Ops, View, Cloud |

**Coordinate reference systems:** all spatial data is tagged with an explicit planetary CRS
(body-fixed frame, datum, projection) resolved via SPICE/PROJ. No implicit Earth/WGS84
assumptions. Frames and time are SPICE-backed (TDB/ET, body-fixed and inertial frames).
[Core](core.md) defines the frame/time **types** (`Epoch`, `ReferenceFrame`, `PlanetaryCRS`,
`EpochWindow`) as a canonical interface — a JSON Schema authority layer, the Pydantic models it
pins, and a Protobuf / Cap'n Proto wire form — so the vocabulary and its guards are enforceable in
every language binding, not Python alone. Core defines the `require_frame`/`require_crs` fail-loud
guards but defers SPICE **resolution** — kernels, `spkpos`, `pxform`, topocentric geometry — to
**[Spice](spice.md)** (`astro_mine.spice`), the single shared resolver every SPICE consumer
(Worlds, Link, Sim, Transit) depends on. Core cannot host that resolution itself
(`spiceypy`/`numpy` are heavy deps the narrow waist excludes — core.md §2 principle 3); centralizing
it in one component keeps frame/aberration conventions singular platform-wide. That every component
now installs `spiceypy` regardless does not weaken the rule: the point was never that a user could
avoid the dependency, it is that exactly one code path resolves a frame.

**Units on the wire (normative).** A physical quantity crossing an interface MUST carry its unit,
and the unit MUST come from Core's shared units vocabulary, referenced by `$id` (§3.1) rather than
restated. Field names MUST carry the unit as a suffix where the schema does not
(`reference_radius_m`, `mass_kg`, `duration_s`); a bare numeric field whose unit lives only in a
docstring is how two correct components disagree. Unit conversion at a boundary is the sender's
responsibility, never inferred by the receiver.

**Frame/CRS/time guard rules (normative).** `require_frame`/`require_crs` and the epoch guards
enforce the following as **MUST** requirements on **any** Core binding — Python is the reference
implementation (core.md §8), and the rules are conformance-tested by a shared vector file Core
ships:

1. A reference frame MUST be present, and its `name` (and `center`, when given) MUST be non-empty,
   whitespace-free tokens.
2. `frame_class` MUST be a member of `FrameClass`; `scale` MUST be a member of `TimeScale`.
3. `TimeScale.ET` and `TimeScale.TDB` denote the **same** scale (SPICE ET ≡ TDB). A consumer MUST
   NOT reject or reinterpret an epoch on the grounds that its scale is spelled `et` rather than
   `tdb`; a naive `scale == TDB` comparison is a bug.
4. A planetary CRS MUST be present; `body` and `body_fixed_frame` MUST be tokens;
   `reference_radius_m` MUST be finite and `> 0`.
5. `EpochWindow.start` and `.end` MUST both be present, with `end` strictly after `start`.
6. An Earth CRS is not forbidden, but an **implicit** one is. An Earth datum or projection marker
   (`WGS84`, `EPSG:4326`, `urn:ogc:def:crs:OGC`) MUST be **rejected when `body` is not `EARTH`** —
   that combination can only be a defaulting bug — and MUST be **accepted when `body` is `EARTH`**,
   because Phase-2 Earth-analog deployments need Earth CRSs to be expressible. This is the **Core**
   rule, a body/datum *consistency* check. A component MAY additionally refuse Earth CRSs outright
   as a **component-local policy** — [View](view.md) does, because it renders planetary bodies only —
   but that is View's rule, not Core's, and the conformance vectors MUST NOT conflate the two:
   `body="EARTH"` with a WGS84 datum is valid at the waist.

**Provenance:** every generated artifact records its inputs (content hashes), the producing
code version, the environment lockfile, and the random seed. Datasets and policies are
**content-addressed** so a benchmark result can be reproduced exactly.

---

## 6. Machine learning & policies

- **Frameworks:** **PyTorch** (primary) and **JAX/Brax** (differentiable / massively parallel
  rollouts). GNNs and neural operators for surrogates; Gaussian processes for uncertainty.
- **Distributed training & RL:** **Ray** (RLlib) on **KubeRay**; PettingZoo/Gymnasium envs.
- **Policy interchange:** **ONNX** is the portable policy artifact; **ONNX Runtime** for
  inference at the edge/ops. Training-framework-specific checkpoints stay internal.
- **Experiment tracking:** **MLflow** (open-source default); Weights & Biases as a hosted
  option. Runs link to Bench results and Hub artifacts by content hash.

---

## 7. Compute, packaging & deployment

### 7.1 The four distributions

The component catalog is a map of design boundaries; it is **not** a map of published artifacts.
Astro-Mine publishes four things, and a component belongs to exactly one of them:

| Distribution | Kind | Contents | Depends on |
|---|---|---|---|
| **`astro-mine-platform`** | Python wheel (maturin; bundles Guard's Rust core) | every component as `astro_mine.<name>` — a **library**, no console scripts | — |
| **`astro-mine-cli`** | Python wheel | the one `astro-mine` executable and every command | the platform |
| **`astro-mine-api`** | Python wheel / OCI image | every REST surface as FastAPI route modules | the platform |
| **`astro-mine-ui`** | npm packages under `@astro-mine` | the console shell, its surface contract, the design system, the visualization library, and the per-component surfaces | the API at runtime |

> **Where this stands.** The platform and CLI distributions ship. `astro-mine-api` and
> `astro-mine-ui` are **not yet stood up**: the REST route modules and the `@astro-mine/*` packages
> exist and run, but still sit in the repositories they were written in. The rules below are
> normative for both today — a new REST surface is written as a route module, not woven into a
> component — and the move is tracked in the [roadmap](../roadmap/README.md).

Normative consequences:

- **One version, no matrix.** A user installs `astro-mine-cli` and holds the whole platform at one
  self-consistent version. Components MUST NOT declare version constraints on each other — there is
  nothing to constrain — and MUST NOT be released independently.
- **One base dependency set.** The platform's `[project.dependencies]` is the union of what its
  components require. Heavy *optional* stacks MUST stay behind extras, and an extra is named
  **`<component>-<extra>`** (`learn-rllib`, `sim-mujoco`, `mind-onnx`) because bare extra names
  collide across components.
- **The local tier still has to work** without any of those extras, without a service, and without
  an account (§7.2 tier 1). That is the property the consolidation had to preserve, and the one to
  check first when adding a base dependency.
- **A new component is a new subpackage**, not a new repository. Adding one is a directory under
  `src/astro_mine/`, a test directory, and an entry in the test runner — never a release process.

### 7.2 Deployment

- **Containers:** OCI images for every deployable; multi-arch where relevant. Reproducible
  builds; pinned base images.
- **Orchestration:** **Kubernetes** is the substrate (charter). **Ray** for distributed sim
  and training; **Argo Workflows** for DAG-style batch sweeps; **KubeRay** + **NVIDIA GPU
  Operator** for GPU scheduling (MIG for sharing).
- **Deployment tiers:**
  1. **Local/dev** — a workstation; one Python environment, or `docker compose` where a tier-2
     service is genuinely wanted. A researcher can install, run a scenario, and score a baseline in
     an afternoon. *This tier MUST always work.*
  2. **Cloud** — K8s + Ray for scale-out (`Cloud`, large `Sim` sweeps, `Learn` training,
     `Bench` leaderboard eval), with `astro-mine-api` serving the hosted surfaces.
  3. **Operations / ground** — `Ops` + `Bridge` + `View` near operators; ROS 2/DDS data plane.
  4. **Flight-adjacent** (Phase 3, mostly out of open scope) — `Bridge` adapters to cFS/F´.
- **Releases:** **SemVer** for every distribution; Python wheels on an index and npm packages under
  the `@astro-mine` scope; OCI artifacts for content. The full policy — what versions mean, how the
  four distributions move relative to one another, and the held Core interface version — is
  [VERSIONING.md](../VERSIONING.md).
- **Plugin distribution:** plugins are **OCI artifacts** in a registry (Harbor/ghcr),
  described by a Core plugin manifest and discovered via `Hub`. In-process plugins use Python
  entry points; untrusted or non-Python plugins run **out-of-process** (gRPC + sandboxed
  container). A third-party plugin is its own distribution and always was — that path is
  unchanged by consolidation, and is the one extension mechanism that MUST NOT require a change to
  any Astro-Mine distribution (§1 tenet 3, §13).

---

## 8. Performance & scalability principles

- **Multi-fidelity everywhere.** Expensive physics has a fidelity dial; the scheduler trades
  accuracy for speed per task. Surrogates carry tracked error bounds and are validated against
  ground truth periodically.
- **Scale horizontally.** Sim rollouts, sweeps, and training fan out across Ray/K8s; services
  are stateless behind load balancers with state in Postgres/Redis/object store.
- **Cloud-native data access.** Chunked, range-readable formats (Zarr, COG, Parquet) so
  workers stream only the slices they need from object storage.
- **Back-pressure & graceful degradation.** Streaming paths are bounded and shed load; swarm
  coordination must degrade, not collapse, when comms drop.
- **Import cost is a performance budget.** One wheel carrying every component makes eager
  top-level imports everyone's problem: a component MUST NOT import a heavy optional dependency at
  module scope, and the CLI MUST NOT import a component to render help. You pay for the code path
  you ran.
- **Measure before optimizing.** Every component ships representative benchmarks; performance
  claims are reproducible.

---

## 9. Identity, security & supply chain

- **AuthN:** OIDC (Keycloak self-host or cloud IdP). **AuthZ:** RBAC enforced with **Open
  Policy Agent (OPA)** for fine-grained, auditable policy.
- **Service-to-service:** **mTLS** (service mesh optional — Linkerd if adopted).
- **Secrets:** External Secrets Operator + Vault/cloud KMS. No secrets in images or repos.
- **Plugin isolation:** untrusted plugins run in containers with **seccomp/gVisor**; **WASM
  (wasmtime)** is the forward-looking sandbox for safe untrusted compute.
- **Supply chain:** signed artifacts (**Sigstore/cosign**), **SLSA** provenance, **SBOM**
  (Syft/CycloneDX). One implementation of all of it — [Seal](seal.md) — because two signers that
  disagree fail silently. Org defaults on: Dependabot alerts and automated security fixes,
  read-only default Actions permissions. Secret scanning, push protection and branch rulesets are
  **not** available for private repositories on the current plan and are due at the public flip;
  treating them as already on is how a gap gets inherited.
- **Safety-critical paths** (`Guard`, `Ops`, `Bridge`) follow the assurance conventions in
  their own docs: hard constraints enforced independently of learned components.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** SDK in every service → traces, metrics, logs.
- **Metrics & dashboards:** **Prometheus** + **Grafana**.
- **Logs:** structured JSON; aggregated with **Loki**.
- **Tracing:** distributed traces across the design and operations loops (a replan in `Ops`
  is traceable through `Mind`/`Allocate`/`Guard`).
- **Health:** standard liveness/readiness endpoints; SLOs defined per service.

---

## 11. Testing, validation & reproducibility

- **Unit/integration:** `pytest`; property-based testing with **Hypothesis** for schema and
  numerical invariants; `gtest` for C++.
- **One suite, per-component selections.** Tests live under `tests/<component>/`, and each
  component keeps its own default selection and marker set — a single `addopts` cannot express
  seventeen different ones. The platform's test runner re-applies each component's selection, and
  CI names the marker expression per component. Opt-in lanes that need a service, a cluster, or
  hardware MUST be marker-gated and MUST self-skip rather than fail when absent.
- **Physics validation:** regression against external oracles (**STK/GMAT/Basilisk** for
  orbits; analytic cases and lab data for terramechanics) with explicit error budgets.
- **Golden tests & determinism gates:** seeded runs compared to stored references; CI fails on
  non-reproducibility.
- **Layering tests (normative).** Because components no longer sit behind package boundaries, the
  rules of §1, §3.1, §3.2 and §3.3 MUST be asserted by test. A layering rule that is only written
  down is a layering rule that has already been broken somewhere. The suite MUST fail on:
  - a **cycle** in the component import graph (§3.2 rule 1);
  - a **companion** (Spice, Seal) importing another companion or a tier-2 component;
  - **Core** importing any component, or any dependency above its declared floor;
  - an import of another component's **underscore-private** module, or of a name absent from its
    `__all__`;
  - a component importing the **CLI or API** distribution, or importing **`svcs`** (§3.3);
  - a front-end **surface** package importing another surface.

  It MUST also *report* — without failing — the runtime and type-only lateral edges separately, and
  fail on a **new runtime lateral edge** that is not recorded in the depending component's §6. The
  point is not to forbid lateral edges but to make adding one a deliberate, visible act.
- **CI/CD:** GitHub Actions (read-only default workflow permissions, per org policy); artifacts
  signed on release.
- **Contract tests:** every component proves it honors the Core interface versions it claims, and
  the CLI, API, and front-end distributions build and test against the platform at `HEAD` (§3.1).
- **Front-end lanes** (§2.1): **Vitest + Testing Library** (`jsdom`) for logic and components;
  **Playwright** against the **built** artifact, so the test exercises what actually ships; and an
  **automated accessibility lane** that fails the build. The two lanes stay separate — WebGL has no
  `jsdom` context, so anything touching a canvas belongs in Playwright, not Vitest.
- **Design-system gates.** Where a package ships design tokens, the properties asserted about them
  are **checked, not claimed**: colour-contrast conformance across every theme and mode, colour-vision
  separation for chart palettes, and generated artifacts matching their source. An accessibility
  claim nobody runs is an accessibility claim that quietly stops being true.

---

## 12. Export control & dual-use posture

- Default-open for the **science, simulation, and coordination** commons.
- **Partition** genuinely sensitive operational capability (e.g., certification-grade flight
  targeting — explicitly out of scope per charter) behind capability tags and, where the code would
  otherwise ship in the open library, into a separate access-controlled distribution.
- Follow `astro-mine/.github` **EXPORT_CONTROL.md**; document a clear EAR/ITAR posture per
  component where relevant (notably `Bridge`, `Ops`, parts of `Mind`/`Allocate`).
- "Open does not mean naive": capability gating is a first-class design concern, not a bolt-on.
- **Capability tags are checked at a boundary, not honoured by convention.** The gate is enforced at
  the registry (`Hub` admission) and at the operations edge (`Bridge` dispatch) — the two places
  where a capability leaves the commons. A tag consulted only by the component that declares it
  gates nothing.
- **Trajectory & mission design are design-time only:** reference trajectories and Δv budgets are
  *descriptive* artifacts for trade studies; operational maneuver targeting and guided atmospheric
  entry are partitioned out and gated by an `operational_targeting` capability tag. Predicting a
  **live mission's** communications windows is gated the same way, because the geometry that
  schedules a simulated relay pass schedules a real one. Mission economics (`Ledger`) ships as an
  open framework with proprietary cost data kept in the commercial layer.

---

## 13. Naming, versioning & docs conventions

- **Components** are named `Astro-Mine-<Name>` in prose and imported as `astro_mine.<name>`. The
  name is **not** a distribution name: `astro_mine.sim` ships in `astro-mine-platform`, and
  `pip install astro-mine-sim` installs nothing, because no such distribution exists. The four
  distribution names are in §7.1.
- **CLI naming (normative).** The platform installs **exactly one** executable, `astro-mine`, from
  `astro-mine-cli`, under **one** grammar:

  ```
  astro-mine <component> <verb> [options]
  ```

  Rules that follow from it:
  - The platform distribution declares **no** console scripts. A component MUST NOT introduce one.
    (A small number of `python -m` entry points remain for machine-facing plumbing — a container
    entrypoint, an in-pod harness — because each is invoked by other code rather than typed.)
  - **Component-first, then verb.** The user names the thing that owns the action, then the action.
    Top-level verbs are reserved for the three *routers* that answer a question no single component
    can — "who owns this?": `validate` (routed by the document's schema `$id`), `new` (scaffold an
    authored document), and `plugin new` (scaffold a plugin package).
  - **The CLI is lazy.** `astro-mine --help` MUST NOT import a component; dispatch imports exactly
    the one module the user named (§8). The cost of that choice is that top-level help lists
    components, not their verbs, and `astro-mine <component> --help` is where a component's real help
    lives.
  - **Third parties extend by entry point, never by a pull request.** The `astro_mine.cli`,
    `astro_mine.cli.validators`, `astro_mine.cli.scaffolds`, and `astro_mine.cli.plugin_scaffolds`
    groups stay live for outside packages, and a discovered command is presented
    indistinguishably from a first-party one. First-party commands are dispatched statically,
    because federating them through entry points hid which function ran and bought nothing once
    every component was always present.
  - **No prefixed per-component binaries, and no aliases.** The earlier scheme gave each component
    its own `astro-mine-<component>` script, with bare legacy names (`fleet`, `worlds`, `link`,
    `prospect`) and one mis-nouned prefixed name (`astro-mine-train`) kept as deprecated aliases. All
    of them are gone.
    Any such name in a document, a docstring, or a blog post is historical.
- **Front-end packages** (§2.1) are npm packages under the **`@astro-mine`** scope:
  `@astro-mine/<name>`, lowercase and hyphenated. A per-component *surface* is named for its
  component with a `-ui` suffix — `@astro-mine/bench-ui`, `@astro-mine/studio-ui`,
  `@astro-mine/hub-ui` — which is also what the console's layering check keys on to tell a surface
  from a library. The workspace root is private and unpublished; only the packages it ships
  carry the scope.
- **Artifact names (normative).** A published artifact's registry name is **bare kebab-case** —
  `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, lowercase ASCII, hyphen-separated, starting with a letter. No
  dots, no underscores, no uppercase, and **no package or component prefix**: the name is
  `prospecting-rover`, not `astro-mine.fleet.prospecting-rover` or `shackleton_water_ice`. A
  registry name is **content identity, not an import path**. Which component produced an artifact
  is a fact about its `kind` — which Hub already carries as a first-class annotation — not about
  what to call it, and on a remote each name is one repository
  (`ghcr.io/<prefix>/<name>:<version>`) — exactly what makes the dotted form read as the path
  component it is not. **The version lives in the tag, never in the name**:
  `shackleton-de-gerlache:0.4.0`, not
  `shackleton-de-gerlache-v1:0.4.0`; `shackleton-water-ice:1.0.0`, not
  `shackleton_water_ice_v1:1.0.0` — a name carrying its own `-v1` beside a SemVer tag states two
  version numbers and says which one moves in neither. **Names are flat and unique across kinds**:
  Hub keys artifacts on `name:version` alone (`kind` is *not* part of the key), so a name MUST be
  descriptive enough to stand without it — `excavation-gns` over `gns`, `relay-orbiter` over
  `orbiter`. New artifacts are born conformant, and a producer SHOULD reject a non-conforming name
  at publish rather than admit it to the registry.
- **Artifact-name migration (normative).** The published anchor set predates the rule above and does
  not follow it. Registry names are immutable once published, so conforming is a **re-publish under
  a new name, not a rename** — it mints new digests, re-pins the scenario zoo, and MUST leave every
  previously published scorecard resolvable. The migration is therefore **gated on the public
  flip**: it is far cheaper while no outside consumer holds the old names, and MUST be done as one
  sweep rather than piecemeal, so the registry never carries a half-migrated set. Until that sweep,
  the legacy names stand as published and MUST NOT be treated as errors; enforcement applies to new
  names only.
- **Shipped examples (normative).** A component that defines an authored format MUST ship at least
  one working example of it, and the example MUST be reachable **two ways**, because the two
  audiences are different: **package data** under `src/astro_mine/<component>/reference/` for a
  reader who has installed the wheel and calls `importlib.resources.files(...)`, and a path under
  the platform's **`examples/`** tree for a reader browsing on GitHub. Where both exist, one
  is the file and the other points at it — never two copies that can drift. An example MUST validate
  under its owner's validator (`astro-mine validate`, or the owning component's own verb) at merge
  time, and the component's documentation MUST name it by path and show the call that loads it. A
  format whose only example is authored inside a build script does not satisfy this: content that
  ships but cannot be found is content that does not exist.
- **Documentation.** Each of the four repositories carries an `ARCHITECTURE.md` that links back to
  this directory; a component's design lives in `architecture/<component>.md` here, not in the
  source tree.
- Interface versions are independent of implementation versions; a component declares the Core
  interface major versions it supports.
- This directory is the **source of truth** for cross-cutting decisions; component docs cite it
  with relative links (e.g., `see conventions.md §4`).
