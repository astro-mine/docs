# Astro-Mine-Bench — Technology Architecture

> Layer: **Commons backbone & platform infrastructure** · Phase: **0** · Extended for multi-regime missions (Phase 3)
> Ships in: [`astro-mine-platform`](platform.md) (harness, scoring, the leaderboard library) · [`astro-mine-api`](api.md) (the leaderboard routes) · [`astro-mine-ui`](ui.md) (`@astro-mine/bench-ui`)
> The academic flywheel / the growth engine. Clone, run, and score a baseline in an afternoon.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Bench` is the platform's **benchmark suite and scenario zoo**. It defines named
challenge scenarios, the metrics by which methods are scored, the **public leaderboards** that
rank them, and the **reproducibility harness** that guarantees a reported result can be
re-derived from its inputs. It is the mechanism that turns a research community into a
contributor community: researchers come to compare methods on shared tasks, publish results
that beat the leaderboard, and in doing so extend the platform.

Concretely, Bench owns and only owns:

- the **scenario specification** — a versioned, content-addressed manifest that pins a [Core](core.md)
  interface version and references reference content ([Worlds](worlds.md), [Fleet](fleet.md),
  [Prospect](prospect.md), [Link](link.md)) by content hash, plus seeds, episode/horizon
  definitions, and the metric set;
- the **scenario zoo** — the curated catalog of those specs, anchored by the **lunar polar
  water-ice prospecting** reference scenario (charter §12);
- the **metric & scoring library** — standardized, pluggable metrics and aggregation rules
  ("evaluation science for swarm campaigns", charter §7);
- the **reproducibility harness** — containerized, seeded, lockfile-pinned execution with
  determinism gates;
- the **leaderboard service** — submission intake, evaluation orchestration, ranking, and a
  public web UI.

**Multi-regime mission scenarios.** The scenario zoo extends beyond single-body
campaigns to **end-to-end missions** spanning multiple [regimes and phases](mission-model.md).
The extension adds two Phase-3 reference scenarios:

- **NEO rendezvous + sample-return** — the named Phase-3 *stepping-stone* benchmark: launch,
  interplanetary transit to a near-Earth object, proximity characterization, sampling, ascent,
  and an `earth_interface` delivery event.
- **Multi-asteroid mining + ore return** — the Phase-3 *capstone*: a multi-target tour with
  in-situ extraction and bulk ore return.

These are scored on the **same reproducibility harness** as existing scenarios — a ScenarioSpec
that now pins the `MissionSpec`/`regime` mission schema and references small-body
[Worlds](worlds.md)/[Prospect](prospect.md), propulsive [Fleet](fleet.md), and `TrajectoryRef`
content by content hash — and add **mission-level metrics** (§5).

**Explicitly out of scope:** Bench does **not** simulate (that is [Sim](sim.md)), does **not**
define the asset/world/policy formats (those are [Core](core.md)), does **not** store or
distribute artifacts (that is [Hub](hub.md)), and does **not** provide the scale-out compute
fabric (that is [Cloud](cloud.md)). Bench *composes* these: it is a thin orchestration and
scoring layer over the simulation, content, and compute substrate. It also does **not** train
policies ([Learn](learn.md)) or author designs ([Studio](studio.md)) — it scores their outputs.

**Primary users:** researchers and the whole community (charter §4.7). Secondarily,
[Studio](studio.md) consumes Bench to score candidate designs, and CI consumes Bench's
determinism gates as a regression oracle.

**Charter alignment:** §5.7 (commons backbone), §10.3 ("the academic flywheel … the growth
engine"), §8 (evaluation science as a research contribution), §11 Phase-0 ("a runnable
benchmark that attracts the first researchers"), §13 ("clone, run, and score a baseline in an
afternoon"). Bench is one of the **first** things to ship.

---

## 2. Architecture principles

1. **Reproducibility is the product.** A leaderboard number is worthless if it cannot be
   re-derived. Every scenario, every submission, and every result is content-addressed and
   replayable from pinned inputs + seed + environment lockfile (conventions.md §5, §11). This
   is a *hard* requirement, not a default (conventions.md §1.5).
2. **Bench composes, it does not own engines.** Scoring is layered over [Sim](sim.md),
   [Hub](hub.md), and [Cloud](cloud.md). Bench adds scenarios, metrics, verification, and
   ranking — never a second simulator or a private artifact store.
3. **Scenarios pin contracts, not implementations.** A scenario fixes a [Core](core.md)
   interface major version and references content by hash, so the *task* is frozen even as
   engines and content evolve. New engine versions are validated against frozen tasks, not the
   other way round.
4. **Metrics are plugins.** The metric/scoring vocabulary is extensible through the [Core](core.md)
   registry, so the community can propose new measures of "good" for swarm campaigns without a
   Bench code change (conventions.md §1.3). Bench ships reference metrics as replaceable
   examples.
5. **Adversarial by assumption.** Public leaderboards are gamed. Held-out seeds, hidden test
   scenarios, submit-policy-we-run execution, and provenance attestation are first-class, not
   bolt-ons (§9).
6. **The local tier always works.** A researcher must be able to run a scenario and score a
   baseline on a single workstation, offline, with no leaderboard account (conventions.md §7,
   tier 1). The hosted leaderboard is a deployment of the same harness, not a separate path.
7. **Open and auditable.** Scenario definitions, metric code, scoring rules, baseline policies,
   and the full result lineage are public and inspectable. Trust comes from transparency, not
   from a black box.
8. **Evaluation is itself research.** Defining what "good" means for multi-week, multi-robot
   ISRU campaigns is an open problem (charter §7); metric definitions are versioned, citable,
   and debatable as an ordinary change to this document (conventions.md §13).

---

## 3. Application architecture

Bench is a **library + a service**: a `pytest`-style harness usable on a workstation, and a
leaderboard service that is a deployment of that same library (conventions.md §1.4).

```
astro_mine.bench
├── spec/          # ScenarioSpec schema, loader, validator, content-hash resolver
├── zoo/           # the curated scenario catalog (the anchor scenario lives here)
├── metrics/       # metric plugin interface + reference metrics + scoring/aggregation
├── harness/       # deterministic runner: env build, seeding, lockfile pinning, gates
├── submit/        # submission intake, manifest validation, policy/plugin resolution
├── eval/          # evaluation-batch planner; dispatch to Sim via Cloud; result collection
├── verify/        # determinism/anti-cheat: re-execution, attestation, seed disclosure
├── leaderboard/   # ranking, statistics, history (the service library; its REST routes
│               #   ship in astro-mine-api — see api.md)
└── report/        # scorecards, provenance bundles, MCAP replay export, View handoff
```

### Key abstractions exposed

- **ScenarioSpec** — the central artifact. A versioned, JSON-Schema-validated (conventions.md §3)
  document that declares: the pinned [Core](core.md) interface major version; referenced
  [Worlds](worlds.md)/[Fleet](fleet.md)/[Prospect](prospect.md)/[Link](link.md) content by
  **content hash**; episode/horizon and termination conditions; the **public seed set** and a
  **held-out seed set** (disclosed only at evaluation time); the metric set and aggregation
  rule; resource budgets (wall-clock, sim-step, compute) per submission; and the
  observation/action interface the submitted policy must satisfy. The spec *is* the task; its
  content hash *is* the task identity. **Multi-regime mission scenarios** additionally
  pin the new **`MissionSpec`/`regime`** mission schema at the pinned Core interface minor and
  reference small-body content, propulsive [Fleet](fleet.md), and design-time `TrajectoryRef`s by
  content hash — no new ScenarioSpec mechanism, just richer pinned content (see
  [mission-model](mission-model.md)).
- **Metric** — a plugin (`(episode_trace) -> scalar | distribution`) with a declared name,
  units, direction (higher/lower-better), and uncertainty handling. Metrics consume the
  [Sim](sim.md) episode trace (an [MCAP](conventions.md) recording) and emit Arrow/Parquet rows.
- **Submission** — a [Core](core.md) plugin manifest pointing at an **ONNX policy** and/or a
  **plugin OCI artifact** (conventions.md §6, §7), resolved from [Hub](hub.md) by content hash,
  plus metadata (method, paper, author, license).
- **Result / Scorecard** — a content-addressed record binding a Submission to a ScenarioSpec
  to per-seed metric values, aggregate score, rank, and a full **provenance bundle**
  (inputs, code version, lockfile, seeds — conventions.md §5).

### Extension points

- **New scenarios** are authored as ScenarioSpec documents and registered in the `zoo` — never
  a code change (conventions.md §1.3).
- **New metrics** are [Core](core.md)-registry plugins discovered via [Hub](hub.md).
- **New scoring/aggregation rules** (e.g., Pareto fronts for multi-objective campaigns) are
  pluggable strategies in `metrics`.

### Interaction patterns

In-process for the local tier (import `astro_mine.bench`, call `run(spec, policy)`); over
**gRPC/REST** for the hosted tier. Evaluation batches are dispatched asynchronously over
**NATS/JetStream** (conventions.md §4) to [Cloud](cloud.md), which executes [Sim](sim.md)
rollouts; results flow back as Arrow/Parquet + MCAP and are ingested into the leaderboard.

---

## 4. Application programming & runtime platforms

- **Language:** Python 3.12+ for the harness, metric library, and service (conventions.md §2);
  type-checked with `mypy`/`pyright`. Hot metric kernels may drop to vectorized NumPy/Arrow or
  a small Rust extension where profiling justifies it.
- **Web/API:** **FastAPI** + **REST/OpenAPI 3.1** for the public leaderboard and submission
  API (conventions.md §3); internal service-to-service over **gRPC** where streaming/typed
  efficiency matters. The leaderboard's web UI follows the platform front-end baseline
  (conventions.md §2.1) and ships as the `@astro-mine/bench-ui` **surface** composed by the console
  — greenfield work, since Bench ships no front-end code today. Rich scenario/replay
  views are delegated to [View](view.md): Bench owns the surface, View owns the globe and replay
  primitives it embeds.
- **Schemas:** ScenarioSpec, Submission manifest, and Result as **JSON Schema + Pydantic v2**
  (conventions.md §3); wire/result messages share the [Core](core.md) Protobuf catalog.
- **Eval orchestration:** **Argo Workflows** for DAG-style evaluation sweeps and **Ray** for
  fan-out rollouts, both on [Cloud](cloud.md) (conventions.md §7).
- **Determinism tooling:** containerized execution (OCI), pinned base images, and lockfiles
  (`uv`/`pip` for Python, Conda where native deps demand it) captured into the provenance
  bundle.
- **Build/packaging:** the harness, scoring and leaderboard *library* ship in the
  [`astro-mine-platform`](platform.md) wheel; the leaderboard's REST routes ship in
  [`astro-mine-api`](api.md) as a multi-arch OCI image. The scenario zoo is published as **versioned
  OCI artifacts** (each ScenarioSpec plus its content references is itself content-addressed and
  signed) — and the zoo, not the code, is what a result is reproducible against
  (conventions.md §7.1, §13).

---

## 5. Data architecture

Bench owns the *evaluation* data; it references but does not own content or artifacts.

| Data | Format / store | Notes |
|---|---|---|
| **ScenarioSpec** (the task) | YAML/JSON + JSON Schema; published as signed **OCI artifact** | Content-addressed; pins Core interface version + content hashes (conventions.md §3, §5) |
| **Scenario zoo catalog** | **PostgreSQL** | Indexes specs, versions, lineage; pgvector for similarity/search |
| **Submissions** | [Core](core.md) manifest → **ONNX** / **plugin OCI** in [Hub](hub.md) | Resolved by content hash; Bench stores only references + metadata |
| **Episode traces** | **MCAP** in **S3-compatible** object store | Timestamped, schema-tagged sim output (conventions.md §4, §5) |
| **Per-seed metric values & results** | **Apache Parquet** / **Arrow** | Columnar, queryable; the leaderboard's raw fuel (conventions.md §5) |
| **Leaderboard metadata & ranks** | **PostgreSQL** | Submissions, runs, ranks, history, embargo state |
| **Provenance bundles** | content-addressed JSON + lockfiles in object store | Inputs, code version, env lockfile, seeds (conventions.md §5) |
| **Held-out seeds / hidden specs** | encrypted; secrets-managed | Disclosed only at eval time (§9) |
| **Cache / job state / rate limits** | **Redis** | Service ephemeral state (conventions.md §5) |

**Mission-level metrics.** Multi-regime scenarios extend the charter's "evaluation
science" (§8) from campaign performance to **mission value**: delivered resource mass, Δv /
propellant efficiency, and total mission duration, plus **ROI / value-with-uncertainty** computed
through [Ledger](ledger.md)'s open techno-economic framework. These are ordinary pluggable
[Metric](#key-abstractions-exposed) plugins consuming the [Sim](sim.md) episode trace across all
phases — Bench scores them, it does not compute the value model. Per-seed mission metrics are
stored as Parquet/Arrow alongside campaign metrics.

**Provenance & versioning:** every Result records its full lineage — ScenarioSpec hash, Core
interface version, content hashes, submission hash, code version, environment lockfile, and
seed — so any leaderboard entry is **byte-for-byte reproducible** (conventions.md §5, §11). All
spatial data inherits explicit planetary CRS tagging from the referenced [Worlds](worlds.md)
content (conventions.md §5); Bench adds no implicit frame assumptions.

**Lifecycle:** scenarios are versioned and immutable once published; a fix is a new version
(old leaderboards remain valid for their pinned spec). Episode traces follow a retention
policy (full retention for top-N and disputed runs; sampled/aged-out otherwise) to bound
object-store cost.

---

## 6. Integration architecture

Bench sits at the confluence of the commons backbone and is deliberately a *composer*:

- **[Core](core.md)** — Bench pins a Core **interface major version** per scenario and validates
  every submission manifest and ScenarioSpec against Core schemas; it consumes Core's
  contract-test utilities to assert a submitted policy honors the declared
  observation/action/Policy interface (conventions.md §11).
- **[Sim](sim.md)** — the execution substrate. Bench builds the environment from the scenario's
  pinned content and asks Sim to run seeded episodes at a declared fidelity, collecting MCAP
  traces. Bench never re-implements physics.
- **[Worlds](worlds.md) / [Fleet](fleet.md) / [Prospect](prospect.md) / [Link](link.md)** —
  referenced **by content hash** from the ScenarioSpec, guaranteeing the exact same world,
  robots, resource field, and comms environment on every run.
- **[Hub](hub.md)** — the artifact plane. Submitted ONNX policies and plugin OCI artifacts are
  ingested from Hub by content hash; baseline policies and the scenario-zoo OCI artifacts are
  published to Hub. Bench holds references, not copies.
- **[Cloud](cloud.md)** — the compute fabric. Large evaluation batches (many seeds × many
  submissions × many scenarios) are scheduled onto K8s + Ray via Argo, with job lifecycle
  events on NATS/JetStream (conventions.md §4, §7).
- **[View](view.md)** — surfaces leaderboards, scorecards, and 3D/geospatial replays of
  evaluation episodes; Bench provides the data and MCAP replays, View renders them.
- **[Studio](studio.md)** — consumes Bench programmatically to score candidate designs during
  trade studies (the design loop, charter §5).
- **[Learn](learn.md)** — links training runs (via **MLflow**, conventions.md §6) to Bench
  results by content hash, closing the train→evaluate loop.

**Message flow (a submission):** submit (REST) → manifest validation against Core → resolve
artifact from Hub by hash → plan eval batch → dispatch to Cloud (NATS) → Sim rollouts produce
MCAP → metrics compute Parquet → verify (determinism/anti-cheat) → ingest result → re-rank →
publish to leaderboard/View. The async lifecycle uses NATS/JetStream; the public edge is
REST/OpenAPI (conventions.md §3, §4).

---

## 7. Infrastructure & deployment

- **Deployment tiers (conventions.md §7):**
  1. **Local/dev** — `pip install astro-mine-cli`; run a scenario and score a baseline via
     `docker compose` or a single Python env, offline. *This tier MUST always work* (charter
     §13). Determinism gates run here as ordinary tests.
  2. **Cloud** — the hosted leaderboard: FastAPI service + PostgreSQL + Redis + object store on
     **Kubernetes**; evaluation executed via **Argo Workflows** + **Ray** on
     [Cloud](cloud.md), GPU rollouts via **KubeRay** + **NVIDIA GPU Operator** (MIG sharing).
- **Containerization:** every deployable is an OCI image with pinned base images; the
  evaluation runner image is itself content-addressed and recorded in each result's provenance
  bundle (conventions.md §7).
- **Compute:** the leaderboard service is light (a few CPU cores, GB-scale RAM, stateless
  behind a load balancer). The *cost center* is evaluation: rollout workers inherit
  [Sim](sim.md)'s CPU/GPU/memory profile and scale on [Cloud](cloud.md). GPU is required only
  for high-fidelity or learned-surrogate rollouts; many seeds fan out across CPU workers.
- **Scaling:** services are stateless with state in Postgres/Redis/object store
  (conventions.md §8); evaluation scales horizontally — embarrassingly parallel across seeds
  and submissions. A leaderboard refresh is a re-rank query, not a re-run.

---

## 8. Performance & scalability

- **Targets.** *Local*: clone → run anchor scenario → score one baseline **in an afternoon** on
  a workstation (charter §12) — the headline SLO. *Hosted*: submission acknowledged in
  seconds; a standard-budget evaluation (e.g., 50 seeds of the anchor scenario) completes in
  minutes-to-low-hours on [Cloud](cloud.md); leaderboard re-rank in well under a second.
- **Bottlenecks.** (1) Simulation cost dominates — owned by [Sim](sim.md)'s multi-fidelity
  scheduler (conventions.md §8). (2) Result ingestion and ranking over many submissions —
  mitigated by columnar Parquet/Arrow and indexed Postgres. (3) Verification re-execution cost
  (§9) — mitigated by sampling rather than re-running every submission.
- **Mitigations.** Per-scenario **compute budgets** bound any single submission; fan-out across
  seeds/submissions over Ray; chunked range-reads of Zarr/COG/Parquet so workers stream only
  needed slices (conventions.md §8); back-pressure on the submission queue with fair-share
  quotas per user.
- **Scaling strategy.** Add Cloud workers to absorb evaluation load; the leaderboard tier
  scales independently and trivially. The scenario zoo grows by *adding* immutable specs, never
  by mutating existing ones, so historical leaderboards never need recomputation.

---

## 9. Security, safety & compliance

- **AuthN/Z.** OIDC (Keycloak/cloud IdP); RBAC via **OPA** for submission quotas, embargo
  control, and metric/scenario authoring rights (conventions.md §9).
- **Submission execution is untrusted code.** Submitted policies/plugins run **out-of-process**
  in sandboxed containers (**seccomp/gVisor**; **WASM/wasmtime** as the forward-looking
  sandbox), with no network egress and strict CPU/GPU/memory/time limits (conventions.md §7,
  §9). This is the central safety concern for Bench: the leaderboard runs arbitrary
  community code at scale.
- **Supply chain.** Submission artifacts (ONNX/OCI) are verified via **Sigstore/cosign**
  signatures and **SLSA** provenance; SBOMs (Syft/CycloneDX) recorded; the evaluation runner
  image is signed and pinned (conventions.md §9).
- **Anti-cheat / submission integrity (the leaderboard threat model).** Public leaderboards
  *will* be gamed; integrity is a primary requirement:
  - **Submit-policy-we-run** is the default trust model — Bench executes the policy itself
    rather than trusting reported numbers, eliminating the largest class of fabrication.
  - **Held-out seeds** and **hidden test scenarios**: each spec carries a public seed set for
    development and an embargoed held-out set disclosed only at evaluation time, so methods are
    scored on instances they could not have overfit.
  - **Determinism enforcement**: a sampled fraction of submissions is **re-executed** from the
    provenance bundle; mismatching the recorded result flags the entry (non-determinism or
    tampering).
  - **Budget & resource caps** prevent compute-for-score and runaway submissions.
  - **Rate limiting and identity** bound brute-force seed-search attacks; results carry full
    provenance so disputes are auditable.
- **Export control / dual use.** Bench is squarely inside the **open** science/simulation/
  coordination commons (conventions.md §12, charter §9.5). It does not introduce sensitive
  operational targeting. Scenarios that would reference capability-gated content honor
  [Core](core.md) capability tags and OPA gating; genuinely sensitive scenarios are partitioned
  per `EXPORT_CONTROL.md`. The default posture is fully open and reproducible.

---

## 10. Observability & operability

- **Telemetry.** OpenTelemetry traces/metrics/logs across submit → evaluate → score → rank, so
  a leaderboard entry is traceable end-to-end through [Cloud](cloud.md) and [Sim](sim.md)
  (conventions.md §10).
- **Metrics & dashboards.** Prometheus + Grafana for queue depth, evaluation throughput,
  re-execution mismatch rate (a key integrity signal), and per-scenario cost; structured JSON
  logs to Loki.
- **Testing & validation.** `pytest` + **Hypothesis** for spec/metric invariants; **golden
  tests / determinism gates** as the core regression mechanism — Bench's own harness is the
  oracle CI uses to detect non-reproducibility across the platform (conventions.md §11). Every
  reference metric ships with property tests (monotonicity, units, bounds).
- **Self-validation.** Baselines in the zoo are re-run on a schedule; drift between a baseline's
  recorded and freshly-computed score is an alarm — it means an engine, content, or harness
  regression has broken reproducibility.
- **Health/SLOs.** Standard liveness/readiness endpoints; SLOs on submission acknowledgement
  latency, evaluation completion time, and the determinism-gate pass rate.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Leaderboard / eval platform | Self-hosted **FastAPI + PostgreSQL**; integrate **EvalAI**; HF-Spaces-style hosted | **Self-hosted FastAPI + PostgreSQL** — neutral commons, full control of the reproducibility harness and anti-cheat; align with conventions.md §3/§5 rather than couple to an external platform |
| Submission & verification model | Submit-policy-we-run; submit-results-we-spot-check; **hybrid** | **Submit-policy-we-run as default**, with a **hybrid** lane (submit-results + mandatory provenance bundle + sampled re-execution) for very expensive methods |
| Reproducibility enforcement | Full container re-execution of every run; **sampled re-execution**; trusted-runner attestation | **Sampled re-execution + signed runner attestation** — full re-execution is the audit tool, not the steady state (cost) |
| Scenario identity | Version string; **content hash of spec + pinned content** | **Content-hash identity** pinning Core interface version + content (conventions.md §5) — the task is frozen, results are reproducible |
| Metric extensibility | Hard-coded metric set; **pluggable metrics via Core registry** | **Pluggable metrics** discovered via [Hub](hub.md); reference metrics ship as replaceable examples (conventions.md §1.3) |
| Anti-gaming | Public seeds only; **public + held-out seeds + hidden scenarios** | **Public dev seeds + embargoed held-out seeds + hidden test scenarios** |
| Eval orchestration | Bespoke queue; **Argo Workflows + Ray**; Kubeflow Pipelines | **Argo Workflows + Ray on [Cloud](cloud.md)** (conventions.md §7) |
| Result store | Postgres rows; **Parquet/Arrow + Postgres index** | **Parquet/Arrow for metric data, Postgres for catalog/rank** (conventions.md §5) |
| Submission artifact | ONNX policy only; plugin OCI only; **both** | **Both** — ONNX for portable policies, plugin OCI for richer methods (conventions.md §6, §7) |

**Open questions / research dependencies:**

- **Evaluation science (charter §7).** What metrics actually capture "good" for a multi-week,
  multi-robot ISRU campaign — throughput, energy survival across lunar night, robustness to
  comms dropout, resource-uncertainty reduction? The anchor scenario's metric set is a
  Phase-0 *proposal* to be refined in the open, co-designed with [Prospect](prospect.md) and
  [Mind](mind.md)/[Allocate](allocate.md). **Mission value.** Phase-3 multi-regime
  scenarios extend this question to mission-level value — delivered mass, Δv efficiency, duration,
  and ROI-with-uncertainty via [Ledger](ledger.md) — an open metric-definition problem for
  interplanetary resource campaigns.
- **Held-out generalization.** How much held-out seed/scenario diversity is needed to prevent
  overfitting without making leaderboards noisy or unfair — an empirical question resolved as
  submissions accumulate.
- **Cost/integrity trade-off.** The right re-execution sampling rate and attestation strength
  vs. compute budget — tuned against the observed mismatch rate.
- **Multi-objective ranking.** Single scalar vs. Pareto-front leaderboards for inherently
  multi-objective campaigns — likely a pluggable scoring strategy.

---

## 12. Roadmap alignment

- **Phase 0 (now) — ships first, with the runnable loop.** The anchor **lunar polar water-ice
  prospecting** ScenarioSpec; the reproducibility harness (containerized, seeded,
  lockfile-pinned, determinism gates); the reference metric set; a baseline policy; the local
  tier (`clone → run → score in an afternoon`, charter §12); and a minimal leaderboard service
  (FastAPI + Postgres). This is what proves [Sim](sim.md) + [Worlds](worlds.md) +
  [Fleet](fleet.md) + Core work end-to-end and attracts the first researchers (charter §10
  Phase 0). MVP integrity: submit-policy-we-run + held-out seeds + sampled re-execution.
- **Phase 1 — the flywheel turns.** First **public leaderboards**; ingestion of community
  ONNX/plugin submissions from [Hub](hub.md); scale-out evaluation on [Cloud](cloud.md);
  pluggable community metrics; richer scenario zoo; [View](view.md) leaderboard/replay UI;
  [Studio](studio.md) scoring integration (charter §10 Phase 1, §10.3).
- **Phase 2+ — breadth & rigor.** Hidden test scenarios, multi-objective ranking, terrestrial
  analog / digital-twin validation scenarios alongside [Ops](ops.md)/[Bridge](bridge.md), and
  expansion of the zoo to new bodies (asteroids, icy moons) as plugin content. Evaluation
  science matures into citable, RFC-governed metric standards.
- **Phase 3 — multi-regime missions.** The named **NEO rendezvous + sample-return**
  stepping-stone and the **multi-asteroid mining + ore return** capstone scenarios land, with
  mission-level metrics (delivered mass, Δv efficiency, duration, ROI via [Ledger](ledger.md))
  on the same harness. The enabling Core hooks (`MissionSpec`/`regime`) are reserved in **Phase 1**
  (see [mission-model](mission-model.md)); the scenarios are opt-in and do not gate the lunar MVP.
