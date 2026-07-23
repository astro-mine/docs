# Cross-Cutting Technology Conventions

> **Status:** Phase-0 draft. Normative for all `Astro-Mine-*` components.
> Changes to anything in this document that affects a published interface go through the
> [RFC process](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

This document defines the technology decisions that are shared across **every** Astro-Mine
component. Component architecture docs in this directory **reference** these decisions rather
than restating them; a component only documents where it *deviates* and *why*. The goal is a
**thin, stable core with thick, swappable edges**: the narrow-waist contracts here change
slowly and deliberately; everything else can evolve independently.

When this document says **MUST / SHOULD / MAY**, read them in the RFC-2119 sense.

---

## 1. Architecture tenets (apply to all components)

1. **Narrow waist.** Everything integrates through a small set of stable contracts owned by
   `Astro-Mine-Core` (SADF, environment API, policy/planner API, message schemas, plugin
   registry). Components MUST NOT create private side-channels that bypass Core contracts.
2. **Contribute once, use everywhere.** A world, asset, planner, policy, or ISRU process is
   authored against Core interfaces and is then usable in design, training, operations, and
   benchmarks without modification.
3. **Plugins over patches.** New content (bodies, robots, sensors, planners, processes) is a
   plugin discovered through the registry — never a core code change. Reference
   implementations ship as *replaceable examples*, not privileged internals.
4. **Library first, service second.** Every component is usable as an importable library on a
   single workstation before it is a network service. The service is a deployment of the
   library, not a separate codebase.
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
| High-assurance & safety-critical logic, schema/codegen tooling, CLIs | **Rust** | Recommended where memory safety + performance matter most: `Guard` runtime monitors, `Core` schema validation/codegen, content-addressed registry tooling. Optional elsewhere. |
| GPU kernels | **CUDA** (+ vendor-neutral fallback) | Used inside Sim/Surrogate; abstracted behind device-agnostic interfaces where feasible. |
| Web front-ends | **TypeScript + React** | Console, Studio, View, Hub, Bench. The full baseline is §2.1. |

**Rule:** the *public* API surface of any component MUST be reachable from Python. Native code
sits behind Python bindings or a gRPC service.

**Scope of that rule.** It binds *components* — the Python packages that own platform capability.
It does **not** bind the **front-end packages** of §2.1 (`@astro-mine/surface`, `@astro-mine/ui`,
`@astro-mine/console`, `@astro-mine/view`, and the per-component surfaces), which are TypeScript
and have no Python surface at all. That is not an exemption from the rule but a consequence of it:
a front-end package renders capability that a component already exposes from Python, and adds none
of its own. A front-end package that needed its own Python API would be a component wearing the
wrong clothes.

### 2.1 The front-end baseline

Normative for every front-end package. This is the **only** place it is stated; a component doc
cites it rather than restating it, and documents only where it deviates and why (§13).

| Concern | Standard |
|---|---|
| Language / framework | **TypeScript 5.5** · **React 18.3** |
| Runtime | **Node >= 20.19** (Vite 8 and Vitest 4 require it) |
| Package manager | **pnpm 11.10.0**, pinned per repo via `package.json` `packageManager` |
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
statement that newer is unusable; move it deliberately, in one sweep, not per repo.

**On server state.** The platform deliberately ships **no** data-fetching or client-cache library.
Every front end already uses bare `fetch`, and the loading / error / empty discipline lives in a
shared `AsyncState` component instead — which is where it belongs, because the discipline is about
what the user is shown when a request is in flight or has failed, not about how the request was
made. Adding a cache layer is a real dependency in every surface and buys little for screens that
are read-mostly and human-paced. Revisit it when a surface has a concrete need (optimistic writes,
polling, cross-surface cache invalidation) — as an RFC, not as an import.

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
| **External / web-facing APIs** | **REST + OpenAPI 3.1** via **FastAPI** | Browser- and tool-friendly, self-documenting | GraphQL only where a UI's query shape demands it (View/Studio) |
| **Internal service-to-service** | **gRPC** over HTTP/2 | Streaming, typed, efficient | — |

**Schema evolution:** Protobuf fields are append-only; never renumber or repurpose tags.
Breaking a Core contract requires a new major interface version and a deprecation window. All
schemas are versioned with the package that owns them and published as generated client
libraries.

### 3.1 Referencing a Core schema from another package ([RFC-0009](../rfc/0009-cross-package-schema-resolution.md))

Core owns schemas that other packages `$ref` across files — above all the shared units vocabulary
([RFC-0007](../rfc/0007-units-frames-wire-schema.md)). Until RFC-0009 this document said nothing
about **how**, so six packages invented five different techniques to name one schema — path
arithmetic reconstructing Core's directory layout, `$id` squatting inside Core's namespace, a
hardcoded copy of a private URI, runtime derivation, and a vendored byte-copy. Only one was
correct. These rules are what was missing.

**One name.**

- A Core schema is referenced by its absolute **`$id`**. A package's schema **MUST** `$ref` it that
  way — never by a relative path, never by a URI derived from Core's directory layout.

  ```json
  { "$ref": "https://schemas.astro-mine.org/core/units/v0.1/units.schema.json#/$defs/ReferenceFrame" }
  ```

- A published `$id` is **public, append-only API**. It **MUST NOT** be repurposed or removed; a new
  schema minor takes a new `$id` (`…/v0.2/…`). Changing a Core schema's `$id`, or the set of URIs
  its `$ref` graph resolves to, is a **breaking change**.

**`$id` namespaces are owned.**

- A package **MUST** declare `$id`s only under its own namespace
  (`https://schemas.astro-mine.org/<package>/…`). It **MUST NOT** publish an `$id` under another
  package's namespace, and two packages **MUST NOT** publish the same `$id`. A colliding or
  squatted `$id` is a silent wrong-schema resolution.

**One mechanism.**

- These URIs are **nominal**: nothing serves them, and resolution **MUST** work offline (§11).
  Resolution is therefore always by registry, **never over the network**.
- A validator **MUST** be built with `astro_mine.core.schema_registry()`, which resolves every Core
  schema by `$id`:

  ```python
  Draft202012Validator(my_schema, registry=schema_registry(my_schema))
  ```

- A package **MUST NOT** import Core modules that are underscore-private or absent from a package's
  `__all__`. Correspondingly, **Core MUST provide a public, documented equivalent** for any
  capability a consumer legitimately needs — the absence of one is what produced all five
  workarounds, and a private API with five importers is a Core defect, not a consumer defect.

**Cross-language and vendored consumers.**

- A package that cannot import Core (a non-Python binding) **MUST** resolve Core schemas from the
  **published bundle**, using its `schema_index` (`$id` → path).
- A package that nonetheless **vendors** a copy of a Core schema **MUST** guard it against drift by
  pinning `astro_mine.core.SCHEMA_DIGEST` (or the bundle's `schema_digest`) and **failing** CI when
  the copy no longer matches. A hand-resynced copy guarded by a comment is drift with extra steps.

**Compatibility is verified, not assumed.** Core CI **MUST** run the schema tests of its consumers
against Core@HEAD (the *downstream canary*), so breaking a consumer fails the Core PR that breaks
it. A green Core board that says nothing about downstream compatibility is worse than no check: the
job this replaced resolved Core from a two-tags-old release and could not fail for any change.

---

## 4. Transport & messaging

Three planes, chosen per latency/criticality:

- **Control plane (sync):** **gRPC** for request/response and server-streaming between
  services; **REST/OpenAPI** at the edge for browsers and third-party tools.
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
every language binding, not Python alone ([RFC-0007](../rfc/0007-units-frames-wire-schema.md)). Core
defines the `require_frame`/`require_crs` fail-loud guards but defers SPICE **resolution** — kernels,
`spkpos`, `pxform`, topocentric geometry — to **[`astro-mine-spice`](../architecture/spice.md)**
(`astro_mine.spice`, [RFC-0002](../rfc/0002-shared-spice-foundation.md)), the single shared resolver
every SPICE consumer (Worlds, Link, Sim, Transit) depends on. Core cannot host that resolution itself
(`spiceypy`/`numpy` are heavy deps the narrow waist excludes — core.md §2 principle 3); centralizing
it in one package keeps frame/aberration conventions singular platform-wide.

**Frame/CRS/time guard rules (normative).** `require_frame`/`require_crs` and the epoch guards
enforce the following as **MUST** requirements on **any** Core binding — Python is the reference
implementation (core.md §8), and the rules are conformance-tested by a shared vector file Core
ships ([RFC-0007](../rfc/0007-units-frames-wire-schema.md) Design §3):

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

- **Containers:** OCI images for every deployable; multi-arch where relevant. Reproducible
  builds; pinned base images.
- **Orchestration:** **Kubernetes** is the substrate (charter). **Ray** for distributed sim
  and training; **Argo Workflows** for DAG-style batch sweeps; **KubeRay** + **NVIDIA GPU
  Operator** for GPU scheduling (MIG for sharing).
- **Deployment tiers:**
  1. **Local/dev** — a workstation; `docker compose` or a single Python env. A researcher can
     clone, run a scenario, and score a baseline in an afternoon. *This tier MUST always work.*
  2. **Cloud** — K8s + Ray for scale-out (`Cloud`, large `Sim` sweeps, `Learn` training,
     `Bench` leaderboard eval).
  3. **Operations / ground** — `Ops` + `Bridge` + `View` near operators; ROS 2/DDS data plane.
  4. **Flight-adjacent** (Phase 3, mostly out of open scope) — `Bridge` adapters to cFS/F´.
- **Packaging & releases:** Python wheels on an index; **npm packages under the `@astro-mine`
  scope** for front-end libraries (§2.1, §13); OCI artifacts for content; **SemVer** for all
  packages. Multi-repo (one repo per package per charter) with `Core` published as a
  versioned dependency. *(This is the public end-state; during private incubation it is deferred —
  see [VERSIONING.md](../VERSIONING.md) §5–7: a source-pinned `uv` Git dependency + PAT, no public
  index yet.)*
- **Plugin distribution:** plugins are **OCI artifacts** in a registry (Harbor/ghcr),
  described by a Core plugin manifest and discovered via `Hub`. In-process plugins use Python
  entry points; untrusted or non-Python plugins run **out-of-process** (gRPC + sandboxed
  container).

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
  (Syft/CycloneDX). Org defaults already on: Dependabot, secret scanning, push protection,
  read-only default Actions permissions.
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
- **Physics validation:** regression against external oracles (**STK/GMAT/Basilisk** for
  orbits; analytic cases and lab data for terramechanics) with explicit error budgets.
- **Golden tests & determinism gates:** seeded runs compared to stored references; CI fails on
  non-reproducibility.
- **CI/CD:** GitHub Actions (read-only default workflow permissions, per org policy); artifacts
  signed on release.
- **Contract tests:** every component proves it honors the Core interface versions it claims
  (consumer-driven contract tests against `Core`).
- **Front-end lanes** (§2.1): **Vitest + Testing Library** (`jsdom`) for logic and components;
  **Playwright** against the **built** artifact, so the test exercises what actually ships; and an
  **automated accessibility lane** that fails the build. The two lanes stay separate — WebGL has no
  `jsdom` context, so anything touching a canvas belongs in Playwright, not Vitest.
- **Design-system gates.** Where a repo ships design tokens, the properties asserted about them are
  **checked, not claimed**: colour-contrast conformance across every theme and mode, colour-vision
  separation for chart palettes, and generated artifacts matching their source. An accessibility
  claim nobody runs is an accessibility claim that quietly stops being true.

---

## 12. Export control & dual-use posture

- Default-open for the **science, simulation, and coordination** commons.
- **Partition** genuinely sensitive operational capability (e.g., certification-grade flight
  targeting — explicitly out of scope per charter) into separate, access-controlled repos.
- Follow `astro-mine/.github` **EXPORT_CONTROL.md**; document a clear EAR/ITAR posture per
  component where relevant (notably `Bridge`, `Ops`, parts of `Mind`/`Allocate`).
- "Open does not mean naive": capability gating is a first-class design concern, not a bolt-on.
- **Trajectory & mission design are design-time only** ([RFC-0001](../rfc/0001-multi-regime-missions.md)):
  reference trajectories and Δv budgets are *descriptive* artifacts for trade studies; operational
  maneuver targeting and guided atmospheric entry are partitioned out and gated by an
  `operational_targeting` capability tag at the registry/`Bridge` boundary. Mission economics
  (`Ledger`) ships as an open framework with proprietary cost data kept in the commercial layer.

---

## 13. Naming, versioning & docs conventions

- Packages: `Astro-Mine-<Name>` (PyPI/dist name lowercase `astro-mine-<name>`; import
  `astro_mine.<name>`).
- **CLI naming (normative — [RFC-0011](../rfc/0011-umbrella-cli.md)).** A component's **direct
  console script is `astro-mine-<package>`** — the prefix is uniform (it removes the `PATH`
  land-grab of generic bare names like `fleet`/`link`/`prospect`) and names the command after its
  package. The **discoverable umbrella surface is `astro-mine <verb>`** (verb-first — the user
  guesses the *action*); component-scoped actions read as `astro-mine <component> <verb>` (e.g.
  `astro-mine studio serve`). The umbrella (`astro-mine-cli`, import `astro_mine.cli`) **discovers**
  subcommands from the **`astro_mine.cli`** entry-point group, so a component contributes a verb by
  declaring an entry point — **never by a PR to the umbrella** — and it must **degrade honestly**
  when a component is absent (name the `pip install`, never traceback). A missing first-party verb
  names its fix; existing component CLIs keep working directly (the umbrella is additive). Any bare
  or mis-nouned legacy name (`fleet`/`worlds`/`link`/`prospect`; `astro-mine-train`) is kept as an
  **alias for one deprecation cycle**, removed at the public-flip gate. New CLIs are born under the
  prefixed rule — the alias surface only shrinks.
- **Front-end packages** (§2.1) are npm packages under the **`@astro-mine`** scope:
  `@astro-mine/<name>`, lowercase and hyphenated. A per-component *surface* is named for its
  component with a `-ui` suffix — `@astro-mine/bench-ui`, `@astro-mine/studio-ui`,
  `@astro-mine/hub-ui` — which is also what the console's layering check keys on to tell a surface
  from a library. A repo's workspace root is private and unpublished; only the packages it ships
  carry the scope.
- Every component repo carries an `ARCHITECTURE.md` that links back to this directory.
- Interface versions are independent of implementation versions; a component declares the Core
  interface major versions it supports.
- The full **release & version policy** — per-package SemVer, the Git tag as the version source
  of truth, the private-incubation distribution stance, and the held Core interface version — is
  specified in [VERSIONING.md](../VERSIONING.md).
- This directory is the **source of truth** for cross-cutting decisions; component docs cite it
  with relative links (e.g., `see conventions.md §4`).
