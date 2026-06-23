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
| Control plane, APIs, ML, orchestration glue, most component logic | **Python 3.11+** | The research community's lingua franca; PyTorch/JAX/Gymnasium ecosystem. Type-hinted, checked with `mypy`/`pyright`. |
| Performance-critical kernels (physics, contact, granular, hot inner loops) | **C++20** | Pybind11 bindings exposed to Python. Integrates with Drake / MuJoCo / Isaac / BehaviorTree.CPP. |
| High-assurance & safety-critical logic, schema/codegen tooling, CLIs | **Rust** | Recommended where memory safety + performance matter most: `Guard` runtime monitors, `Core` schema validation/codegen, content-addressed registry tooling. Optional elsewhere. |
| GPU kernels | **CUDA** (+ vendor-neutral fallback) | Used inside Sim/Surrogate; abstracted behind device-agnostic interfaces where feasible. |
| Web front-ends | **TypeScript + React** | Studio, View, Hub web UI. |

**Rule:** the *public* API surface of any component MUST be reachable from Python. Native code
sits behind Python bindings or a gRPC service.

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
- **Packaging & releases:** Python wheels on an index; OCI artifacts for content; **SemVer**
  for all packages. Multi-repo (one repo per package per charter) with `Core` published as a
  versioned dependency.
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
- Every component repo carries an `ARCHITECTURE.md` that links back to this directory.
- Interface versions are independent of implementation versions; a component declares the Core
  interface major versions it supports.
- This directory is the **source of truth** for cross-cutting decisions; component docs cite it
  with relative links (e.g., `see conventions.md §4`).
