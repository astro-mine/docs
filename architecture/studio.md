# Astro-Mine-Studio — Technology Architecture

> Layer: **Design studio (offline mode)** · Phase: **1** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> The design front door — goal-in, design-out: capture intent, explore the design space, author campaigns.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Studio` is the platform's **primary authoring environment** — the *design front door*. A
mission designer specifies an **objective** (e.g., "produce 10 tonnes of water per month from
this crater") and the **assets available** (or a budget for them); Studio proposes swarm
compositions, orbital/relay infrastructure, and candidate policies, runs **trade studies**
across that design space, and lets the user author **campaigns and contingencies**. It is where
options are designed and compared *before anything is committed* to operations.

Studio's job is **orchestration and authoring**, not computation. It owns:

- **Intent capture** — turning a stated goal + constraints into a validated, machine-checkable
  mission/objective spec (optionally LLM-assisted "intent-to-mission");
- **Design-space exploration** — driving a trade-study engine that proposes, evaluates, and
  Pareto-ranks candidate designs by calling the simulation and autonomy components;
- **Workspace/project management** — versioned design artifacts, comparisons, and provenance;
- **Visualization & review** — embedding [View](view.md) so designers can inspect candidates;
- **Hand-off** — packaging a chosen, validated design for [Ops](ops.md).

**Explicitly out of scope:** Studio contains *no* physics, *no* solvers, *no* learning, *no*
renderer of its own, and *no* operations runtime. It computes nothing about the world — it
*asks* [Sim](sim.md) to simulate, [Learn](learn.md)/[Mind](mind.md) to produce policies,
[Allocate](allocate.md) to assign, [Guard](guard.md) to certify, and [Bench](bench.md) to score.
It runs no flight-path or operations loop (that is [Ops](ops.md)). Heavy compute is offloaded to
[Cloud](cloud.md). Studio is the *conductor*; every section of the orchestra is a sibling
component reached through [Core](core.md) contracts.

**Primary users:** mission designers, startups, and educators — people exploring *what to build*
and *how to operate it* rather than implementing the engines underneath.

**Mission Architect mode (RFC-0001).** Studio gains an upstream design *stage* — the **Mission
Architect** — that authors a `MissionSpec` (an ordered set of phases across regimes; see
[mission-model](mission-model.md)) and **co-optimizes trajectory ⇄ fleet ⇄ swarm ⇄ economics** in
one loop. It is a **new mode/stage inside Studio, not a separate application**: the same backend
and trade-study engine, extended to orchestrate [Trajectory](trajectory.md),
[Sizing](sizing.md), and [Ledger](ledger.md) alongside the existing Sim/Learn/Mind/Allocate/Guard.
A distinct *workspace and persona* (mission & systems engineers, astrodynamicists, resource
economists) is honored in the UI without forking the loop. Per RFC-0001 R2, the **phase-sequencing
policy** (phase ordering, contingencies, cross-phase replanning) is authored here; the validated
`MissionSpec` is handed to [Ops](ops.md), which owns the live executor. This stage gates behind the
lunar MVP and is opt-in — a single-`surface`-phase mission is exactly today's campaign.

**Charter alignment:** §5.5 ("the design front door: goal-in, design-out … runs trade studies …
intent capture can be LLM-assisted, reusing the 'intent-to-mission' idea"); §6 ("Astro-Mine-Studio
sits on top, orchestrating this loop to turn a stated goal into a candidate design"); §11
(Phase 1, "Autonomy & studio").

---

## 2. Architecture principles

1. **Studio computes nothing.** Every physics, learning, planning, allocation, safety, or
   scoring decision is delegated to a sibling component through a Core contract. Studio holds
   state, orchestrates, and presents — it never reimplements an engine. If a feature requires
   new computation, it belongs in a sibling, not in Studio.
2. **Goal-in, design-out is a pipeline of validated artifacts.** Each stage (intent → objective
   spec → design candidate → evaluated candidate → campaign) is a typed, versioned, Core-validated
   artifact. Stages compose; any artifact can be inspected, diffed, forked, and shared.
3. **The LLM is optional, abstracted, and never authoritative.** Intent capture *may* use an
   LLM, but Studio MUST be fully usable without one. The LLM only drafts specs that a human
   reviews; it is never in a safety, planning-guarantee, or flight path, and every LLM output is
   validated against Core schemas before it is allowed to flow downstream (see §9).
4. **Author against declarations, not types.** Studio composes swarms from [Fleet](fleet.md)
   SADF assets and policies from [Hub](hub.md) by *negotiating against their declared
   capabilities* (Core principle), so new asset kinds and planners appear in the studio without
   code changes.
5. **Long jobs are first-class and asynchronous.** A trade study is minutes-to-hours of
   distributed simulation/training. Studio treats design exploration as durable, cancelable,
   resumable background work — never a blocking request — and stays responsive while it runs.
6. **Reproducible by construction.** Every candidate records its inputs (content hashes), the
   Core interface versions, the engine versions, seeds, and the environment lockfile
   (conventions.md §5). Re-running a trade study with the same inputs reproduces the same
   Pareto front. A design you can't reproduce is a design you can't trust to hand to Ops.
7. **Uncertainty is shown, not hidden.** Surrogate-derived scores, resource-field estimates, and
   sim-to-real claims carry explicit error bounds (conventions.md §1.6); the comparison UI
   surfaces them rather than presenting single point estimates as truth.
8. **Thin web edge over a library core.** The orchestration logic is an importable Python
   library usable from a notebook or CLI; the FastAPI service and React UI are a *deployment* of
   that library (conventions.md §1.4), not a separate codebase.
9. **Hand-off, don't fork.** A design validated in Studio is the same artifact [Ops](ops.md)
   consumes — no translation layer, no re-derivation. Studio and Ops are two modes over one
   Core-defined campaign artifact.

---

## 3. Application architecture

Studio is a **web application** (React/TypeScript front end + FastAPI back end) wrapping a Python
**design-orchestration library**. Its modules:

```
astro_mine.studio
├── intent/          # Intent capture: NL → validated objective spec (LLM-optional)
│   ├── llm/         # Provider-abstracted LLM client (Anthropic adapter), tool/structured-output
│   ├── forms/       # Deterministic, no-LLM structured intent authoring (always available)
│   └── validate/    # Core-schema validation of every captured/produced spec
├── designspace/     # Trade-study / DSE engine: parameterization, DoE, multi-objective search
│   ├── search/      # Optimizer adapters (Optuna/Ax/pymoo/Ray Tune) behind one interface
│   ├── pareto/      # Pareto-front computation, dominance, hypervolume, ranking
│   ├── encode/      # Design <-> decision-variable encoding/decoding
│   └── mdo/         # RFC-0001: Sizing+Ledger shared OpenMDAO graph (vehicle⇄economics inner loop)
├── mission/         # RFC-0001 Mission Architect: MissionSpec authoring + Trajectory/Sizing/Ledger orchestration (phase 3)
├── orchestrate/     # The design loop: fan out candidates to Sim/Learn/Mind/Allocate/Guard/Bench
│   ├── jobs/        # Async job model: submit, track, cancel, resume; Cloud offload
│   └── clients/     # gRPC clients to sibling components (generated from Core schemas)
├── workspace/       # Projects, designs, comparisons, versioning, provenance (PostgreSQL)
├── campaign/        # Campaign + contingency authoring; hand-off package for Ops
├── api/             # FastAPI app: REST/OpenAPI 3.1 edge + (optional) GraphQL for UI queries
└── webui/           # React + TypeScript front end (separate build; talks to api/)
```

### Key abstractions exposed

- **`ObjectiveSpec`** — a Core-schema'd statement of intent: target product/quantity/rate, the
  body/region (CRS-tagged), available-asset inventory or budget, hard constraints (power,
  thermal, comms, safety), and the optimization objectives + weights. The canonical output of
  intent capture and the canonical input to design-space exploration.
- **`DesignCandidate`** — a proposed solution: an SADF swarm composition (asset mix + counts),
  orbital/relay infrastructure, and a policy/planner stack drawn from [Hub](hub.md), plus the
  decision-variable vector that produced it. Composable and forkable.
- **`TradeStudy`** — a parameterized exploration: the design-space definition, the search
  strategy, the objective set, the evaluation budget, and the resulting **evaluated candidates +
  Pareto front**. The unit of reproducible design work.
- **`Campaign`** — a chosen design plus its timeline, phases, and contingency branches; the
  Core-defined artifact handed to [Ops](ops.md).
- **`MissionSpec`** *(RFC-0001)* — the Mission Architect's top-level artifact: an objective
  reference, fleet (incl. reusable LEO inventory), global constraints, and an ordered list of
  **phases across regimes**, each with entry/exit conditions, an optional per-phase swarm campaign,
  and per-leg `ManeuverBudget`s. Per R4 it stays **declarative** — it records the *result* of the
  trade study, not the optimization formulation, which lives in the trade-study engine. A single
  `surface`-phase `MissionSpec` is exactly today's `Campaign`. Schema in [Core](core.md); see
  [mission-model](mission-model.md).

### Key abstractions consumed (via Core)

- **SADF** assets from [Fleet](fleet.md); **plugins/policies** indexed by [Hub](hub.md) via Core
  manifests; the **Environment API** (worlds from [Worlds](worlds.md)/[Prospect](prospect.md)/[Link](link.md), implemented by [Sim](sim.md));
  the **Policy/Planner API** ([Mind](mind.md)/[Learn](learn.md)/[Allocate](allocate.md)/[Guard](guard.md));
  Core **message schemas** for every cross-component call; **scenario/scoring** definitions from [Bench](bench.md).

### Extension points

- **Optimizer plugins** — new search backends register behind the `designspace.search`
  interface (DoE, Bayesian, evolutionary, hyperparameter-search) without touching the loop.
- **LLM provider adapters** — the `intent.llm` interface is provider-agnostic; the default
  adapter targets the Claude API, and the whole subsystem is removable.
- **Objective/metric plugins** — custom objectives and scoring map onto [Bench](bench.md) metric
  definitions rather than being hard-coded.

### Interaction patterns

Browser → **REST/OpenAPI** (and GraphQL where a UI view's query shape demands it,
conventions.md §3) → FastAPI. The back end submits trade-study work to an **async job queue**;
workers fan candidates out to siblings over **gRPC**, offloading heavy batches to [Cloud](cloud.md).
Results stream back to the UI (SSE/WebSocket) as candidates are evaluated. Studio is also usable
**in-process as a library** — the same orchestration code drives a notebook or CLI with no service.

---

## 4. Application programming & runtime platforms

- **Front end:** **TypeScript + React** (conventions.md §2) — Vite build; component library and a
  charting stack (e.g., Plotly/D3/visx) for Pareto fronts and trade-off scatter/parallel-coordinate
  plots; embeds [View](view.md) for 3D scene/terrain visualization. State via TanStack Query over
  the OpenAPI client; types generated from the FastAPI OpenAPI 3.1 schema. (Deviation note: the
  charts and Pareto-exploration views are GraphQL candidates per conventions.md §3 — REST is the
  default, GraphQL only where a view's query shape demands it.)
- **Back end:** **Python 3.12+** (conventions.md §2), **FastAPI** for the REST/OpenAPI edge,
  **Pydantic v2** for request/response and config models (and for typed Core models generated
  from JSON Schema). `mypy`/`pyright` type-checked.
- **Trade-study / DSE engine:** Python multi-objective optimization libraries behind a single
  internal interface — **Optuna** (samplers incl. NSGA-II, TPE; ask-and-tell; pruning), **Ax/BoTorch**
  (Bayesian / Gaussian-process optimization for expensive evaluations), **pymoo** (classical
  evolutionary multi-objective: NSGA-II/III, MOEA/D), and **Ray Tune** (when the search itself must
  scale across the cluster). Design-of-experiments (LHS, Sobol) for initial space-filling.
- **LLM (optional):** the official **Anthropic Python SDK** (`anthropic`) behind a
  provider-abstracted adapter. Default models: **Opus 4.8** (`claude-opus-4-8`) for heavy
  intent-synthesis/reasoning, **Sonnet 4.6** (`claude-sonnet-4-6`) for interactive
  lower-latency steps, **Haiku 4.5** (`claude-haiku-4-5`) for cheap classification/triage. Uses
  **adaptive thinking** (`thinking={"type": "adaptive"}`) for synthesis, **tool use / structured
  outputs** (`output_config.format` with a JSON schema, or strict tool definitions) to coerce NL
  into a validated `ObjectiveSpec`, **prompt caching** for the large fixed context (catalog of
  asset kinds, SADF/objective schemas, examples — placed before any volatile content), and **MCP**
  to expose platform tools (asset search, Hub lookup, schema validation) to the model. The
  subsystem is fully optional and provider-swappable — see §9 and §11.
- **Async work:** job queue + workers (see §6/§7). NATS + JetStream is the default eventing/queue
  substrate (conventions.md §4); a workflow engine (Argo/Temporal — see §11) sequences multi-stage
  studies.
- **Build/packaging:** back end as a Python wheel `astro-mine-studio` + an OCI image; front end as
  static assets served by the API container or a CDN. **SemVer**; declares the Core interface major
  versions it supports (conventions.md §13).

---

## 5. Data architecture

Studio **owns workspace/design state** and **produces campaign artifacts**; it does not own world,
asset, policy, or result data (those belong to siblings and are referenced by content hash).

| Data | Role | Format / store |
|---|---|---|
| Projects, designs, trade studies, comparisons, audit log | **Owned** | **PostgreSQL** (+ **pgvector** for intent/design embeddings used in search & similarity; conventions.md §5) |
| `ObjectiveSpec`, `DesignCandidate`, `TradeStudy`, `Campaign` | **Produced** | Core-schema'd JSON/YAML (JSON Schema + Pydantic v2); canonical Protobuf wire form for cross-component calls |
| `MissionSpec` + per-leg `ManeuverBudget`s (RFC-0001, Mission Architect) | **Produced** | Core-schema'd JSON/YAML; `TrajectoryRef`/`ManeuverBudget` are *descriptive design-time* artifacts (no guidance), consumed by [Ops](ops.md) unchanged |
| Captured intent (raw NL + LLM transcript/tool calls) | **Owned** | PostgreSQL (provenance); large transcripts in object store, content-addressed |
| Large artifacts (exported campaign bundles, big result sets) | **Produced** | **S3-compatible object store** (MinIO/S3/GCS), **content-addressed** (conventions.md §5) |
| Cache / session / job status | Ephemeral | **Redis** |
| SADF assets, policies, plugins | **Consumed (by ref)** | Pulled from [Fleet](fleet.md)/[Hub](hub.md) by content hash; never copied authoritatively |
| Worlds, sim outputs, scores | **Consumed (by ref)** | Zarr/COG/MCAP/Parquet produced by siblings; Studio stores **references**, not the bytes |

**Schemas:** `ObjectiveSpec`/`DesignCandidate`/`TradeStudy`/`Campaign` are versioned schemas; the
swarm-composition and campaign artifacts are Core-defined or Core-derived so that [Ops](ops.md)
consumes a `Campaign` with no translation. Spatial fields in an `ObjectiveSpec` carry an explicit
planetary CRS (conventions.md §5) — no implicit Earth assumptions.

**Lifecycle:** intent → objective spec (validated) → trade study (candidates evaluated against
pinned engine/Core versions) → chosen candidate → campaign → hand-off bundle. Drafts are mutable;
once a study runs or a campaign is handed off, the artifact is frozen and content-addressed.

**Provenance & versioning:** every produced artifact records input content hashes, Core interface
versions, sibling engine versions, random seeds, and the environment lockfile (conventions.md §5),
so any candidate or front can be reproduced exactly. Designs are versioned (SemVer-ish per
project); the audit log records who changed what, and which LLM model/version (if any) drafted a
spec.

---

## 6. Integration architecture

Studio is a **pure consumer** of Core contracts — it integrates with nearly every other component.

- **Through [Core](core.md):** Studio generates its gRPC stubs and typed data models from Core
  schemas (SADF, Environment API, Policy/Planner API, message catalog, plugin manifest). It speaks
  only Core contracts — no private side-channels (conventions.md §1.1).
- **The design loop (per candidate, via gRPC, conventions.md §4):**
  1. compose an SADF swarm from [Fleet](fleet.md) assets;
  2. instantiate the world via the Environment API ([Worlds](worlds.md)/[Prospect](prospect.md)/[Link](link.md), implemented by [Sim](sim.md));
  3. obtain/condition policies via [Learn](learn.md) (training) and [Mind](mind.md) (planning/composition);
  4. solve task assignment with [Allocate](allocate.md);
  5. wrap and certify with [Guard](guard.md) (hard-constraint check);
  6. simulate the candidate on [Sim](sim.md) (multi-fidelity, [Surrogate](surrogate.md)-accelerated);
  7. **score** the candidate via [Bench](bench.md) against the objective metrics.
- **Mission Architect loop (RFC-0001, Phase 3):** for a multi-regime `MissionSpec`, the same
  trade-study engine additionally orchestrates [Trajectory](trajectory.md) (design-time Δv/ToF and
  window scans → `TrajectoryRef`/`ManeuverBudget`), [Sizing](sizing.md) (mass/power/propellant/
  staging → sized SADF), and [Ledger](ledger.md) (techno-economic objective). Per R4,
  **[Sizing](sizing.md) and [Ledger](ledger.md) share one OpenMDAO graph** for the tight
  vehicle⇄economics inner loop, with trajectory and swarm in the outer co-optimization. The
  coupling lives here, not in Core — `MissionSpec` stays declarative.
- **[Hub](hub.md):** Studio reads assets, policies, and plugins (indexed by Core manifest) and can
  write back published designs/campaigns as content-addressed, signed artifacts.
- **[Cloud](cloud.md):** large fan-out (hundreds of candidates × many seeds, or
  training-in-the-loop) is submitted to Cloud's K8s/Ray scale-out; Studio tracks jobs, not workers.
- **[View](view.md):** embedded for 3D inspection of worlds and candidate swarms in the comparison UI.
- **[Ops](ops.md):** a validated `Campaign` (plus contingencies) is handed off — the operations
  loop consumes the same Core-defined artifact Studio produced.
- **Transport:** **gRPC** for service-to-service (streaming candidate results), **REST/OpenAPI** at
  the browser edge, **NATS+JetStream** for the async job lifecycle (conventions.md §4). Distributed
  tracing (conventions.md §10) spans a trade study across all touched siblings.

---

## 7. Infrastructure & deployment

- **Deployment tier:** primarily **Cloud** (conventions.md §7) — a stateless FastAPI service +
  React assets + async workers on **Kubernetes**, with heavy compute delegated to [Cloud](cloud.md)
  (K8s + Ray). Also **Local/dev**: the orchestration library + a single FastAPI process via
  `docker compose`, driving a local [Sim](sim.md) for small studies (the local tier MUST work —
  conventions.md §7).
- **Containerization:** OCI images (API+workers; static UI served by the API container or a CDN),
  pinned reproducible base images (conventions.md §7).
- **Compute profile:**
  - *API/UI:* CPU-light, memory-modest, horizontally scaled behind a load balancer (stateless;
    state in Postgres/Redis/object store, conventions.md §8).
  - *Trade-study workers:* CPU for the optimizer/orchestration loop; **the heavy GPU/CPU cost is
    incurred in [Sim](sim.md)/[Learn](learn.md)/[Surrogate](surrogate.md) on [Cloud](cloud.md)**,
    not in Studio. Studio workers are mostly I/O-bound on gRPC + result aggregation.
- **Orchestration & scaling:** Kubernetes; **Ray** when the *search itself* (Ray Tune) scales out;
  **Argo Workflows** (or Temporal — §11) for DAG-style multi-stage studies. Workers scale on queue
  depth (NATS/JetStream).

---

## 8. Performance & scalability

- **Targets:** UI interactions and job-status reads are sub-second; intent capture (LLM or form)
  feels interactive (Sonnet/Haiku for the interactive steps); a trade study runs as durable
  background work whose **wall-clock is dominated by sibling compute**, not by Studio overhead.
- **Primary bottleneck = candidate evaluation cost** (each candidate is a sim, possibly a training
  run). Mitigations:
  - **Multi-fidelity evaluation** (conventions.md §8): cheap [Surrogate](surrogate.md)/low-fidelity
    [Sim](sim.md) passes to prune the space, escalating fidelity only for promising candidates;
  - **Sample-efficient search** — Bayesian optimization (Ax/BoTorch) and pruning (Optuna) to
    minimize expensive evaluations; DoE space-filling to seed;
  - **Massive horizontal fan-out** on [Cloud](cloud.md) (Ray/K8s) — candidates and seeds evaluate
    in parallel; the optimizer's ask-and-tell loop batches proposals;
  - **Result & artifact caching** — content-addressed candidates mean identical (design, world,
    seed) tuples are never re-evaluated.
- **Scaling strategy:** stateless API/workers scale horizontally; search parallelism scales with
  [Cloud](cloud.md) capacity; **back-pressure** on the job queue sheds/queues load gracefully
  (conventions.md §8) rather than overrunning the cluster.
- **Secondary bottleneck = LLM latency/cost** (optional path): mitigated by **prompt caching** of
  the large fixed schema/catalog context, model tiering (Haiku for classification, Sonnet for
  interactive synthesis, Opus only for the hardest intent reasoning), and **streaming** responses.
- **Measure before optimizing** (conventions.md §8): Studio ships representative trade-study
  benchmarks (synthetic objective + stub Sim) so orchestration overhead is tracked separately from
  sibling compute.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** OIDC (Keycloak/cloud IdP) for users; **RBAC via OPA** for project/workspace
  access and for gating who may run large [Cloud](cloud.md) jobs or publish to [Hub](hub.md)
  (conventions.md §9). Service-to-service over **mTLS**.
- **The LLM is never on a safety or guarantee path — this is a hard architectural rule:**
  - The LLM is **optional**: Studio is fully usable through deterministic structured-intake forms
    with no model present (`intent.forms`).
  - The LLM **only authors specs that a human reviews**; it is never in the planning, allocation,
    safety-certification, or flight path. Planning guarantees come from [Mind](mind.md)/[Allocate](allocate.md);
    safety from [Guard](guard.md) (conventions.md §9 — hard constraints enforced independently of
    learned/generated components).
  - **Every LLM output is validated against Core schemas at the boundary** (Core principle:
    "fail validation early and loudly"). An `ObjectiveSpec` that doesn't validate is rejected and
    surfaced for human correction — it never flows downstream. *(RFC-0001)* The same optional,
    provider-abstracted LLM may now also help draft a `MissionSpec`; it is validated against Core
    schemas identically and is **never on a safety, planning-guarantee, or flight path** — and never
    near trajectory guidance, which is descriptive-only by schema.
  - The provider is **abstracted**; no platform behavior depends on a specific model or vendor.
- **Supply chain:** signed artifacts (Sigstore/cosign), SBOM (Syft/CycloneDX), SLSA provenance;
  org defaults (Dependabot, secret scanning, push protection) on (conventions.md §9). LLM **API
  keys** live in External Secrets/Vault — never in images, repos, prompts, or the workspace DB.
- **Prompt-injection posture:** untrusted text (catalog descriptions, user-pasted requirements)
  that reaches the model is treated as data; the **validation-as-security** gate (Core-schema
  validation of all produced specs) is the backstop. Operator-authority instructions are not
  spoofable from user content.
- **Export control / dual use:** Studio is a *design* tool over the open science/simulation/coordination
  commons (conventions.md §12). Designs that touch genuinely sensitive operational capability are
  gated via Core **capability tags** + OPA at the [Hub](hub.md)/[Ops](ops.md) boundary; Studio
  honors but does not redefine that partition. LLM transcripts and objective specs may carry
  sensitive intent → workspace data is access-controlled and retention-bounded.

---

## 10. Observability & operability

- **Telemetry:** OpenTelemetry in the FastAPI service and workers → traces/metrics/logs
  (conventions.md §10); a trade study is **traceable end-to-end** across [Sim](sim.md)/[Learn](learn.md)/[Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md)/[Bench](bench.md)
  (the same way an Ops replan traces through autonomy).
- **Metrics & dashboards:** Prometheus + Grafana — job throughput, queue depth, per-candidate
  evaluation latency, optimizer convergence, **LLM call latency/token-cost/cache-hit-rate** and
  **spec-validation failure rate** (a rising validation-failure rate is the early signal of an LLM
  or schema regression). Structured JSON logs aggregated with Loki.
- **Testing & validation:**
  - `pytest` + **Hypothesis** for schema/encoding invariants (every produced spec round-trips and
    validates; design↔decision-variable encode/decode is lossless);
  - **Contract tests** against [Core](core.md) interface versions Studio claims (conventions.md §11);
    consumer-driven contract tests against each sibling's gRPC surface, run with stubs in CI;
  - **Determinism gates** — a seeded trade study against a stub Sim reproduces the same Pareto
    front; CI fails on non-reproducibility (conventions.md §11);
  - **LLM path** tested with **recorded/mock transcripts** so CI never depends on a live model; a
    small evaluation set checks that representative NL prompts produce valid `ObjectiveSpec`s, and
    every test asserts the validation gate rejects malformed model output.
- **Health:** standard liveness/readiness endpoints; SLOs on API latency and job-acceptance time.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Front-end framework | **React + TypeScript**; Vue; Svelte | **React + TypeScript** — mandated by conventions.md §2; shared component/charting stack with [View](view.md)/[Hub](hub.md) UI |
| Back-end API | **FastAPI (REST/OpenAPI 3.1)**; Flask; Django; Node | **FastAPI** — conventions.md §3; Pydantic v2 reuse, auto OpenAPI client gen; GraphQL only for query-heavy comparison views |
| Trade-study engine | **Optuna**; **Ax/BoTorch** (Bayesian); **pymoo/NSGA-II** (evolutionary); **Ray Tune** | **Pluggable, multi-backend**: Ax/BoTorch as the default for *expensive* candidate evaluation (sample-efficient Bayesian MO), Optuna/pymoo (NSGA-II) for cheaper/large-population evolutionary MO, **Ray Tune** when the search itself must scale across [Cloud](cloud.md). One internal interface; pick per study. |
| DoE / seeding | LHS; Sobol; random | **Sobol/LHS** space-filling to seed the optimizer |
| Long-job orchestration | Synchronous request; **async job queue (NATS/JetStream)**; **+ workflow engine (Argo / Temporal)** | **Async job queue + workflow engine** — NATS+JetStream (conventions.md §4) for the job lifecycle; **Argo Workflows** for DAG-style batch studies (conventions.md §7), **Temporal** if durable, long-running, human-in-the-loop authoring workflows justify it. Synchronous is unacceptable for trade studies. |
| LLM integration depth | None; **structured-output intent extraction**; full agentic authoring | **Structured-output intent capture, provider-abstracted, optional** — NL → validated `ObjectiveSpec` via Claude API tool-use/structured outputs; *not* an autonomous agent that designs unattended. Human reviews every spec. |
| LLM provider/model | **Anthropic Claude (Opus 4.8 / Sonnet 4.6 / Haiku 4.5)**; others behind the adapter | **Claude API** as the default adapter (Opus 4.8 for synthesis, Sonnet 4.6 interactive, Haiku 4.5 classification), behind a provider-agnostic interface; the whole subsystem is removable |
| Design-artifact representation | Ad-hoc per study; **Core-schema'd, content-addressed, versioned** | **Core-schema'd + content-addressed + versioned** — `ObjectiveSpec`/`DesignCandidate`/`TradeStudy`/`Campaign`; the `Campaign` is consumed unchanged by [Ops](ops.md) |
| Workspace store | **PostgreSQL (+ pgvector)**; document DB | **PostgreSQL (+ pgvector)** — conventions.md §5; relational projects + embedding search for similar designs |

**Open questions / research dependencies:**

- **Design-space encoding** — how to encode a *heterogeneous, variable-cardinality* swarm
  (mix of asset kinds + counts + infrastructure + policy choices) into a decision-variable space
  that multi-objective optimizers handle well, without an explosion of conditional variables.
  Co-designed with [Fleet](fleet.md) (SADF expressiveness) and the search backends.
- **Objective definition** — how mission objectives ("10 t/month water") map onto [Bench](bench.md)
  metrics and constraints in a way that is both LLM-extractable and optimizer-usable. Co-designed
  with [Bench](bench.md).
- **Fidelity scheduling** — the policy for promoting candidates from [Surrogate](surrogate.md) to
  high-fidelity [Sim](sim.md) inside a study (the accuracy/cost trade-off). Co-designed with
  [Sim](sim.md)/[Surrogate](surrogate.md).
- **Intent-to-mission grounding** — how far LLM intent capture can be trusted to draft *correct*
  objective specs (vs. merely valid ones), and where the human-review UI must force confirmation.

---

## 12. Roadmap alignment

- **Phase 1** (charter §11, "Autonomy & studio"): Studio ships as the authoring front end once the
  autonomy stack ([Mind](mind.md)/[Learn](learn.md)/[Allocate](allocate.md)/[Guard](guard.md)) and
  [Hub](hub.md) exist. The **MVP**: structured (no-LLM) intent capture → a single-objective or
  small multi-objective trade study driving [Sim](sim.md)+[Bench](bench.md) over the Phase-0
  reference scenario (lunar polar water-ice prospecting) → a comparison view → a `Campaign`
  artifact. This proves goal-in, design-out end-to-end on one scenario.
- **Later in Phase 1:** LLM-assisted intent capture (Claude API adapter, optional); the full
  trade-study engine (multi-backend, multi-fidelity, [Cloud](cloud.md) fan-out); embedded
  [View](view.md); Pareto-front exploration UI; publish-to-[Hub](hub.md).
- **Phase 2** (ops bridge): the `Campaign` hand-off to [Ops](ops.md) matures into the design→operations
  loop, so a Studio-authored campaign drives the operations runtime over Earth analogs.
- **Phase 3** (RFC-0001): the **Mission Architect mode** ships — `MissionSpec` authoring and the
  trajectory⇄fleet⇄swarm⇄economics co-optimization over [Trajectory](trajectory.md)/[Sizing](sizing.md)/[Ledger](ledger.md).
  The additive Core schema hooks it depends on (`MissionSpec`/`regime`/`PhaseTransition`) are
  **reserved in Phase 1** (R5); only the implementations are Phase 3, and the track is opt-in and
  off the lunar-MVP critical path.
- **Stability stance:** Studio adds no Core surface of its own — it is a *consumer*. Its measure of
  success is how much design power it unlocks while changing [Core](core.md) as little as possible;
  any new contract it needs goes through the RFC process (conventions.md, GOVERNANCE.md).
