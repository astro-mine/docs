# Astro-Mine-Allocate — Technology Architecture

> Layer: **Autonomy & coordination** · Phase: **1** · Ships in: [`astro-mine-platform`](platform.md) · Extended for multi-regime missions (Phase 3)
> The combinatorial core of swarm coordination — who does what, when, and where.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Allocate` is the **specialist allocation-and-scheduling engine** for the platform.
Given a set of heterogeneous assets with declared capabilities, a set of tasks (prospect this
cell, excavate there, haul to the plant, relay during this contact window), and a thicket of
**coupled physical constraints**, it decides **who does what, when, and where** and returns a
time-indexed assignment that respects those constraints — ideally optimally, always feasibly,
and fast enough to be re-solved online when reality drifts. It is the package that turns the
charter's "combinatorial core of swarm coordination" (§5.4) into running code, combining
**exact constraint/MILP solvers** with **learned heuristics** that warm-start and guide search.

It owns and only owns:

- the **allocation/scheduling sub-interface** of the Core Policy/Planner API — translating an
  abstract allocation request into a concrete, solver-backed assignment;
- a **constraint-model compiler** that lifts capabilities, power budgets, contact graphs, and
  terrain costs into a canonical optimization model;
- a portfolio of **solver backends** (exact, metaheuristic, market/auction, learned-guided)
  behind one strategy interface;
- **anytime / online re-solving** machinery for replanning under change.

**Mission-level joint assignment.** With the multi-regime extension, the same engine
also decides the discrete backbone of an interplanetary resource mission: **which asset → which
target** (e.g. which asteroid) **→ which launch/transfer window → which trajectory**. This is the
discrete/continuous joint problem the RFC identified as having no owner — it sits between Allocate
and [Sim](sim.md) ([mission-model.md](mission-model.md)) and is **assigned to Allocate** for the
discrete-assignment half, mixing combinatorial choice with continuous orbital-mechanics
feasibility. Allocate still owns only the *assignment*; trajectory *optimization* is
[Trajectory](trajectory.md)'s, and the trade-study loop that couples them is
[Studio](studio.md)'s.

**Explicitly out of scope:** Allocate does **not** own the Policy/Planner API itself — that is
[Core](core.md). It is not a mission planner or behavior orchestrator — that hierarchy lives in
[Mind](mind.md), which *delegates* assignment to Allocate. It does **not** do continuous
trajectory optimization or low-level control (it reasons over *task-level* motion via traversal
costs and durations supplied by [Worlds](worlds.md), not over joint torques). It does **not**
enforce hard safety constraints at execution time — that is [Guard](guard.md); Allocate produces
*feasible-by-construction* plans, but Guard remains the independent runtime shield
(conventions.md §9). It does not train policies ([Learn](learn.md)) or run physics
([Sim](sim.md)). It is a **library first** (conventions.md §1.4): a single function call on a
workstation before it is ever a service.

**Primary users:** planning researchers (who plug in new solvers, decompositions, and
neural-guidance models and benchmark them) and mission designers (who, through
[Studio](studio.md), explore feasible campaigns and trade studies). Operators reach it
indirectly through [Ops](ops.md) for online replanning.

**Charter alignment:** §5.4 (the Allocate package), §7 ("constraint/optimization solvers —
OR-Tools, CP-SAT"), §8 ("heterogeneous, tightly-coupled task allocation … resists both pure
optimization and pure learning"), §9 ("heterogeneity without abstraction collapse"). Allocate is
the platform's direct attack on the §8 hard problem: **mixing discrete assignment with
continuous motion and hard physical constraints**.

---

## 2. Architecture principles

1. **Feasibility is non-negotiable; optimality is a budget.** Allocate must always return a
   *feasible* plan (or an explicit, explained infeasibility certificate). Optimality is pursued
   within a declared time/quality budget. A late optimal answer is a wrong answer in operations.
2. **Anytime by default.** Every solve exposes incumbent solutions with monotonically improving
   bounds, so a caller can stop at any deadline and take the best plan found, with an explicit
   optimality gap. This is the contract [Ops](ops.md) replanning depends on.
3. **Model/solver separation.** The *constraint model* (the problem) is decoupled from the
   *solver* (how it is solved). One canonical model compiles to multiple backends; swapping
   CP-SAT for HiGHS or an auction must not change problem semantics, only the path to a solution.
4. **Exact and learned compose, neither rules.** Learning *guides* exact search (warm starts,
   branching/variable-ordering hints, subproblem selection); the exact layer *guarantees*
   feasibility and bounds. We never trust a neural assignment without a feasibility check, and we
   never throw away a learned warm start that the solver can verify (charter §7).
5. **Decompose to scale.** Hundreds of robots over multi-week horizons do not fit one monolithic
   solve. Spatial/temporal partitioning and rolling-horizon decomposition are first-class, not
   afterthoughts; the architecture assumes the full problem is *never* solved at once at scale.
6. **Constraints come from upstream truth, not hardcoded assumptions.** Power budgets come from
   [Fleet](fleet.md) SADF, contact windows from [Link](link.md), traversal costs from
   [Worlds](worlds.md), resource value from [Prospect](prospect.md). Allocate is a *consumer* of
   modeled constraints; it invents none of the physics (conventions.md §1.6).
7. **Uncertainty is first-class (conventions.md §1.6).** Resource value and durations carry
   distributions, not point guesses. Allocate supports robust/stochastic formulations and, at
   minimum, treats deterministic re-solve over uncertain inputs as a degraded mode, never as
   ground truth.
8. **Deterministic and reproducible (conventions.md §1.5, §11).** Same model + same seed + same
   pinned solver version ⇒ same plan. Solver nondeterminism (threads, time-based cutoffs) is
   controlled or recorded so a [Bench](bench.md) result is reproducible.
9. **Explain the decision.** Every plan ships with its objective decomposition, binding
   constraints, optimality gap, and (on infeasibility) an irreducible conflict set. A plan that
   cannot be explained cannot be trusted by an operator or a reviewer.

---

## 3. Application architecture

Allocate is a **library with an optional gRPC service face** (conventions.md §1.4). Its internal
modules:

```
astro_mine.allocate
├── api/            # Core Policy/Planner allocation sub-interface impl; request/response types
├── model/          # Canonical constraint model: variables, constraints, objectives (solver-neutral)
│   ├── ir/         #   intermediate representation (the "allocation IR") + JSON Schema/proto
│   └── compile/    #   compilers IR → CP-SAT / MILP (Pyomo) / auction / metaheuristic encodings
├── constraints/    # Constraint builders: power, energy/thermal-horizon, comms-window, terrain, precedence
├── solvers/        # Backend plugins behind one Strategy interface (CP-SAT, HiGHS/SCIP, Gurobi, auction, ALNS)
├── guidance/       # Learned heuristics: warm-start, learning-to-branch, subproblem selection (ONNX)
├── decompose/      # Spatial/temporal partitioning, rolling-horizon, column-generation orchestration
├── uncertainty/    # Scenario sampling, robust/stochastic formulations, re-solve triggers
├── anytime/        # Incumbent/bound streaming, deadline management, gap tracking
├── explain/        # Objective breakdown, binding-constraint & IIS (irreducible infeasible set) reporting
└── registry/       # Solver/guidance plugin discovery via Core manifests
```

### Key abstractions exposed

- **`AllocationRequest`** — the Core-typed input: a set of `Task`s (kind, location, resource
  target reference, time windows, precedence, value), a set of `AssetRef`s (resolved from
  [Fleet](fleet.md) SADF with capability tags and budgets), a `ConstraintContext` (handles to
  comms contact graph, traversability layer, resource field), an `Objective` spec, and a
  `SolveBudget` (wall-clock deadline, target gap, determinism flag).
- **`Allocation`** — the output: per-asset, time-ordered task sequences with start/end times,
  the realized objective value, the optimality gap, binding constraints, provenance, and a
  feasibility/optimality status enum. Wrappable directly by [Guard](guard.md) and executable by
  [Ops](ops.md).
- **Allocation IR** — the solver-neutral problem representation (decision vars, constraints,
  objective terms) with a versioned JSON Schema + Protobuf wire form. The IR is the stable
  internal contract that lets solvers be true plugins.
- **`Solver` strategy** — `solve(model, budget, hints?) -> stream[Incumbent]`. Backends are
  plugins (CP-SAT, MILP, auction, metaheuristic) registered via a Core manifest.
- **`Guidance` provider** — produces warm starts / branching hints / subproblem rankings from an
  ONNX model given the IR; optional and always verifiable by the exact layer.

### Extension / plugin points

New **solver backends**, **constraint families**, **decomposition strategies**, and **guidance
models** are all Core-manifest plugins (conventions.md §1.3) discovered via the `registry` module
and indexed by [Hub](hub.md). A research lab ships "learning-to-branch for excavation routing" as
a guidance plugin without touching Allocate's core. Reference solvers ship as *replaceable
examples*.

**Mission-level joint assignment.** Multi-regime missions add new *constraint
families* and *edge weights* to this same machinery — no new solver paradigm. Window-feasibility,
Δv, and time-of-flight from [Trajectory](trajectory.md)'s `TrajectoryRef`/`ManeuverBudget`
artifacts enter as a constraint builder (launch/transfer windows as time-windowed availability,
Δv/ToF as edge costs), with Δv→propellant feasibility resolved via [Sizing](sizing.md); the
asset↔target↔window↔trajectory choice is encoded in the existing Allocation IR as additional
decision variables over a **time-expanded** asset-target-window graph. The combinatorial backbone
(CP-SAT / MILP + learned warm-starts) is unchanged; the constraint set and the time-expanded
structure grow. See the [mission-model](mission-model.md) for the Mission/Phase/Regime vocabulary
these constraints reference.

### Interaction patterns

In-process: [Mind](mind.md) imports Allocate and calls the allocation sub-interface directly
inside the autonomy hierarchy. Out-of-process: large or long solves run as a gRPC server with
**server-streaming** incumbents (the anytime contract), deployed by [Cloud](cloud.md). Both faces
share one library (conventions.md §1.4).

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.12+** for the control plane, model compilation, orchestration, and the
  public API (conventions.md §2); type-checked with `mypy`/`pyright`. Hot inner loops in
  metaheuristics or custom propagators drop to **C++20** via pybind11 where profiling justifies
  it; OR-Tools' CP-SAT is itself a C++ engine driven from Python.
- **Solver libraries:**
  - **Google OR-Tools / CP-SAT** — the primary engine (charter §6): a lazy-clause-generation
    CP-SAT solver that excels at the discrete scheduling + assignment + interval-reasoning shape
    Allocate has, with native cumulative/no-overlap/interval constraints, integrated objectives,
    and solver hints (warm starts) — the natural seam for learned guidance.
  - **MILP via modeling layer:** **Pyomo** (or `python-mip`/OR-Tools' MathOpt) as a
    solver-agnostic modeling front for the MILP track, targeting **HiGHS** (open, recommended
    default MILP backend) and **SCIP** (open, strong on hard MILPs/branch-and-price), with
    **Gurobi** as an optional commercial backend behind the same interface for users who have a
    license.
  - **Metaheuristics:** an in-house **ALNS / large-neighborhood-search** module (and optional
    OR-Tools routing solver) for very-large-scale routing/hauling instances where exactness is
    out of reach.
  - **Auction/market:** a distributed **consensus-based bundle (CBBA-style)** allocator for the
    decentralized, comms-limited regime.
- **ML / guidance:** PyTorch for *training* guidance models (in [Learn](learn.md) or research
  forks); **ONNX + ONNX Runtime** as the portable inference artifact at solve time
  (conventions.md §6). GNN encoders over the task/asset/contact graph are the default model class.
- **Schemas & APIs:** Pydantic v2 + JSON Schema for requests/IR; Protobuf/gRPC for the service
  face and IR wire form (conventions.md §3). Results emitted as **Apache Arrow/Parquet**
  (conventions.md §5).
- **Runtime model:** synchronous library call for small solves; an async, streaming gRPC worker
  for large ones. Solves are CPU-bound, multi-threaded within a backend, and embarrassingly
  parallel across scenarios/partitions.
- **Build/packaging:** ships in the [`astro-mine-platform`](platform.md) wheel, with CP-SAT as a
  base dependency at a deliberately tight pin; OCI image bundling the other solver binaries (HiGHS,
  SCIP) for reproducibility. Gurobi stays an optional extra, never a default dependency, to keep the
  stack fully open (conventions.md §7.1).

---

## 5. Data architecture

Allocate is largely **transformational** — it consumes constraints, produces plans — and persists
little of its own beyond results and provenance.

- **Owns / produces:**
  - the **Allocation IR schema** (versioned JSON Schema + Protobuf), the canonical model form;
  - **`Allocation` result** records — emitted as **Apache Parquet** with **Apache Arrow** in
    memory (conventions.md §5), the tabular plan plus objective/gap/binding-constraint metadata;
  - **solve traces** (incumbent/bound trajectories, branching statistics) for analysis and for
    training the next generation of guidance models;
  - **infeasibility certificates** (IIS / conflict sets) when no feasible plan exists.
- **Consumes:** SADF capability/power/thermal budgets from [Fleet](fleet.md); the **comms
  contact graph** (time-windowed connectivity, latency, bandwidth) from [Link](link.md);
  **traversability cost layers** (slope, roughness, illumination, keep-out) as Cloud-Optimized
  GeoTIFF / Zarr from [Worlds](worlds.md); **resource-value fields with uncertainty** from
  [Prospect](prospect.md) (geostatistical distributions, not point guesses). All spatial inputs
  carry an explicit planetary CRS resolved via SPICE/PROJ; all epochs are SPICE TDB/ET
  (conventions.md §5).
- **Storage:** result/trace artifacts are **content-addressed** in the S3-compatible object store
  (MinIO/S3/GCS); relational catalog of solves and their inputs in **PostgreSQL** for
  [Bench](bench.md)/[Ops](ops.md); **Redis** for caching warm starts and incremental solve state
  across re-solves.
- **Lifecycle:** request → compile-to-IR → solve (streaming incumbents) → result + trace →
  optional persistence. Online replanning keeps the IR and incumbent warm in Redis and applies a
  *delta* rather than recompiling from scratch.
- **Provenance & versioning (conventions.md §5):** every `Allocation` records the content hashes
  of all constraint inputs, the IR version, the solver backend + pinned version, the random seed,
  the time budget actually consumed, and the Core interface version — so any plan (and any
  [Bench](bench.md) score) is exactly reproducible. The IR schema is versioned with the package
  and append-only (conventions.md §3).

---

## 6. Integration architecture

Allocate sits inside the autonomy layer and integrates entirely through Core contracts
(conventions.md §1.1); it creates no private side-channels.

- **Implements (provides):** the **allocation/scheduling sub-interface** of the
  [Core](core.md) Policy/Planner API. Allocate is registered as a planner plugin via a Core
  manifest declaring the Core interface major versions it supports and its capability tags.
- **Called by [Mind](mind.md):** Mind's hierarchical planner assigns roles/regions, then
  **delegates the assignment problem to Allocate** through the Core sub-interface — the boundary
  fixed by the charter (§5.4). Mind composes; Allocate decides the combinatorics.
  - via Mind, **[Studio](studio.md)** drives Allocate in *design* mode (trade studies: "how many
    haulers minimize idle time?"), and **[Ops](ops.md)** drives it for *online replanning* when
    an anomaly or drift invalidates the current plan.
- **Consumes constraints from siblings:** [Link](link.md) (contact graph / comms windows),
  [Worlds](worlds.md) (terrain traversability), [Prospect](prospect.md) (resource targets &
  uncertainty), [Fleet](fleet.md) (asset capabilities & budgets). Where durations/costs come from
  physics, they are sourced via [Sim](sim.md)/[Surrogate](surrogate.md) rollouts or cached
  cost tables, not re-derived.
- **Mission-level constraints from [Trajectory](trajectory.md)/[Sizing](sizing.md):**
  for multi-regime missions Allocate additionally consumes `TrajectoryRef`/`ManeuverBudget`
  feasibility plus Δv/time-of-flight from [Trajectory](trajectory.md) as window-gated constraints
  and edge weights, and Δv→propellant feasibility from [Sizing](sizing.md) — alongside the
  existing power, comms-window, and terrain constraints. The Mission/Phase/Regime contract these
  reference lives in [Core](core.md) ([mission-model](mission-model.md)). [Link](link.md) supplies
  deep-space comms windows for the transit/proximity phases on the same contact-graph interface.
- **Outputs wrapped by [Guard](guard.md):** the `Allocation` is handed to Guard, which enforces
  hard constraints (collision, power floors, keep-out) **independently** of Allocate's solver
  (conventions.md §9). Feasible-by-construction plans still pass through the independent shield.
- **Scaled on [Cloud](cloud.md):** large solves and parameter sweeps fan out across **Ray** on
  Kubernetes; rolling-horizon partitions and scenario ensembles are natural parallel units.
- **Evaluated by [Bench](bench.md):** allocation quality, time-to-feasible, optimality gap, and
  robustness are scored on named scenarios (e.g., polar water prospecting), with Bench pinning
  the Core interface and solver versions.
- **Learned guidance trained by [Learn](learn.md):** solve traces feed [Learn](learn.md), which
  trains GNN guidance models exported to **ONNX** and loaded back into Allocate's `guidance`
  plugins. Guidance models are shared via [Hub](hub.md).
- **Message flows:** in-process for the design/training loop; **gRPC server-streaming** for
  online/large solves so [Ops](ops.md) receives incumbents as they improve; lifecycle events
  (solve started/incumbent/finished) on **NATS + JetStream** (conventions.md §4); a replan in Ops
  is **distributed-traceable** through Mind → Allocate → Guard (conventions.md §10).

---

## 7. Infrastructure & deployment

- **Deployment tiers (conventions.md §7):**
  1. **Local/dev** — `pip install astro-mine-cli`; small-to-medium instances solve on a
     workstation in-process. This tier MUST always work — a researcher solves a reference
     scenario in an afternoon.
  2. **Cloud** — a gRPC solver service plus **Ray** for parallel/decomposed solves and sweeps,
     on **Kubernetes**; **Argo Workflows** for batch design studies.
  3. **Operations/ground** — a low-latency Allocate replanning service co-located with
     [Ops](ops.md), tuned for anytime response within tight deadlines.
- **Compute:** **CPU-bound and memory-bound**, not GPU. CP-SAT/MILP solvers benefit from many
  cores (parallel search) and ample RAM (search trees, LP bases). A typical worker: 8–32 vCPU,
  16–128 GB RAM; large MILPs may need high-memory nodes. **GPU is used only for guidance-model
  inference** (optional; ONNX Runtime CPU is the default and is usually sufficient at solve cadence).
- **Containerization:** OCI image with pinned solver binaries (CP-SAT, HiGHS, SCIP) for
  reproducible builds (conventions.md §7); Gurobi as an optional licensed layer.
- **Orchestration & scaling:** stateless gRPC workers behind a load balancer (state in
  Redis/Postgres/object store, conventions.md §8); **horizontal scale-out** across independent
  solves and decomposition partitions via Ray/KubeRay; vertical scale (more cores/RAM) for a
  single hard monolithic solve.

---

## 8. Performance & scalability

- **Targets (indicative, refined by [Bench](bench.md)):**
  - *Design mode:* near-optimal (≤ a few % gap) plans for **tens of robots / hundreds of tasks**
    over a multi-day horizon within seconds to a few minutes.
  - *Online replanning:* a **feasible** updated plan within a hard deadline (target sub-second to
    a few seconds for incremental/local repair), improving anytime until the deadline.
  - *Scale ceiling (Phase 1 stretch):* **hundreds of robots, thousands of tasks** over
    multi-week horizons via decomposition, never as one monolithic solve.
- **Bottlenecks:** combinatorial blow-up of joint assignment + scheduling + routing; tight
  coupling between discrete choices and continuous power/comms/time constraints (the §8 hard
  problem); cost of recomputing traversal/duration tables; LP/CP search-tree memory at scale.
- **Mitigations & scaling strategy:**
  - **Decomposition (`decompose`):** spatial partitioning by region/crater, temporal
    **rolling-horizon** (plan a window, commit a prefix, slide), and **column generation /
    branch-and-price** for routing-heavy subproblems. The architecture *assumes* the full problem
    is never solved at once at scale (principle 5).
  - **Learned warm starts & guidance (`guidance`):** GNN-predicted assignments warm-start CP-SAT;
    learning-to-branch and subproblem-selection models cut search; all verified by the exact
    layer (charter §7). Warm starts from the *previous* plan dominate during online replanning.
  - **Incrementality:** keep the IR and incumbent warm in Redis; apply deltas on re-solve rather
    than rebuilding (the online path).
  - **Anytime contract (`anytime`):** stream incumbents with bounds so a caller always has a
    usable plan at its deadline.
  - **Multi-start parallelism:** fan out diversified solver configurations/seeds across Ray and
    take the best incumbent — solver portfolios are robust on heterogeneous instances.
  - **Back-pressure & graceful degradation (conventions.md §8):** under comms loss, fall back to
    the decentralized **auction** backend so coordination degrades rather than collapses.
- **Measure before optimizing (conventions.md §8):** Allocate ships a representative instance
  suite; every performance claim is a reproducible [Bench](bench.md) number with pinned solver
  versions.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** the gRPC/REST service face uses platform OIDC + RBAC enforced via **OPA**
  (conventions.md §9); service-to-service over **mTLS**. The library face inherits the host's
  trust boundary.
- **Safety boundary:** Allocate produces *feasible-by-construction* plans but is **not** the
  safety authority. Hard constraints are enforced **independently** by [Guard](guard.md) at
  execution (conventions.md §9) — a solver bug must never be able to violate a power floor or
  keep-out zone, because Guard re-checks regardless of the solver's claims.
- **Isolation & supply chain:** untrusted third-party solver/guidance plugins run
  **out-of-process** in sandboxed containers (seccomp/gVisor; WASM forward-looking) — important
  because a malicious solver could otherwise return crafted-malicious "feasible" plans
  (conventions.md §7, §9). Solver binaries are pinned; artifacts signed (**Sigstore/cosign**)
  with **SLSA** provenance and **SBOM** (conventions.md §9).
- **Determinism as integrity:** recorded seeds + pinned solver versions make a plan auditable and
  reproducible (conventions.md §11) — a tampered or non-reproducible plan is detectable.
- **Export control / dual use (conventions.md §12):** task allocation is **dual-use** — the same
  engine that schedules ice prospecting can schedule coordinated targeting. The **open commons
  scope is scientific/ISRU coordination**. Sensitive operational-targeting use is partitioned per
  [Core](core.md) capability tags and gated at registry/load time (OPA); follow
  `astro-mine/.github` **EXPORT_CONTROL.md**. Allocate is explicitly named in conventions.md §12
  as a component needing a clear EAR/ITAR posture.

---

## 10. Observability & operability

- **Telemetry (conventions.md §10):** **OpenTelemetry** SDK emits structured logs, metrics, and
  traces. A replan is **traceable end-to-end** through [Mind](mind.md) → Allocate →
  [Guard](guard.md), as called out in conventions.md §10.
- **Metrics:** time-to-first-feasible, time-to-target-gap, final optimality gap, incumbent/bound
  trajectories, constraint-violation count (should be zero), backend used, solve memory, deadline
  hit/miss rate — to **Prometheus + Grafana**; high-rate operational solve metrics to
  **TimescaleDB**.
- **Explainability (`explain`):** every result carries an objective decomposition, the binding
  constraints, the optimality gap, and — on infeasibility — an **irreducible infeasible set
  (IIS)** so an operator or mission designer learns *why* no plan exists (e.g., "no contact
  window long enough to relay the haul before the power floor"). This is an operability feature,
  not a nicety, for delay-tolerant supervisory autonomy (charter §7).
- **Testing & validation (conventions.md §11):**
  - **Unit/integration:** `pytest`; **Hypothesis** property tests asserting solver invariants
    (returned plans are always feasible against the model; objective is correctly computed;
    anytime bounds are monotone).
  - **Cross-solver consistency:** the same IR solved by CP-SAT, HiGHS, and SCIP must agree on
    optimal objective on instances small enough to close — a strong differential test of the
    model compiler.
  - **Determinism gates:** seeded solves compared against stored golden plans; CI fails on
    non-reproducibility (conventions.md §11).
  - **Contract tests:** consumer-driven contract tests prove Allocate honors the
    [Core](core.md) Policy/Planner allocation sub-interface versions it declares.
  - **Benchmark regression:** quality/latency tracked over time on [Bench](bench.md) scenarios;
    regressions block release.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Primary discrete solver | OR-Tools **CP-SAT**; MILP (HiGHS/SCIP/Gurobi); custom CP | **CP-SAT** — native interval/cumulative/no-overlap scheduling, integrated objectives, solver hints for warm starts; the natural fit for assignment+scheduling (charter §6) |
| MILP backend (modeling track) | HiGHS; SCIP; **Gurobi (commercial)**; CBC | **HiGHS default** (open, fast LP/MILP); **SCIP** for hard MILP / branch-and-price; **Gurobi as optional licensed extra**, never a default dependency (keep stack open) |
| Modeling layer | **Pyomo**; OR-Tools MathOpt; `python-mip`; raw solver APIs | **Pyomo** for the solver-agnostic MILP track; **native CP-SAT API** for the CP track — compiled from one Allocation IR |
| Coordination architecture | **Centralized** optimization; **decentralized/auction** (CBBA); **hybrid** | **Hybrid** — centralized exact/decomposed solve as the default; auction backend as the comms-degraded fallback so coordination degrades, not collapses |
| Exact vs learned vs hybrid | Pure exact; pure learned (neural combinatorial opt); **hybrid (neural-guided)** | **Hybrid** — learning *warm-starts and guides* (learning-to-branch, subproblem selection) exact search that *guarantees* feasibility/bounds (charter §7); never trust unverified learned assignments |
| Guidance model class & artifact | MLP; **GNN over task/asset/contact graph**; transformer; pointer net | **GNN encoder** (the problem is a graph) exported to **ONNX** (conventions.md §6) for portable, optional inference |
| Decomposition for scale | Monolithic; spatial partition; **rolling-horizon (temporal)**; column generation / branch-and-price | **Rolling-horizon + spatial partitioning** as the workhorse; **column generation** for routing-heavy hauling subproblems |
| Uncertainty handling | Deterministic re-solve; **stochastic (scenario/SAA)**; robust/chance-constrained | **Stochastic scenario-based** for design when distributions matter; **fast deterministic re-solve** (with warm start) as the online default; robust formulation as an opt-in mode |
| Service vs library | Library only; service only; **both (one codebase)** | **Both** — library first (conventions.md §1.4); a streaming-gRPC service is a deployment of the same library for large/online solves |

**Open questions / research dependencies:**

- **The §8 hard problem itself:** the right decomposition of *discrete assignment × continuous
  motion × hard physical constraints* — whether tight integration (logic-based Benders / branch-
  and-check over a motion oracle) beats loose coupling (assign discretely, validate with
  [Sim](sim.md)/[Surrogate](surrogate.md), repair). Co-designed with [Mind](mind.md) and resolved
  empirically on [Bench](bench.md).
- **Where learned guidance actually pays off** (which problem regimes, how much, how to keep
  guidance models from over-fitting one scenario family) — a [Learn](learn.md)/[Bench](bench.md)
  research dependency.
- **Stochastic vs robust vs re-solve** under [Prospect](prospect.md)'s resource uncertainty: how
  much does planning-to-learn (active perception / information value in the objective) buy over
  deterministic re-solve? An open evaluation question.
- **Anytime guarantees under hard ops deadlines:** bounding worst-case time-to-feasible for
  online replanning in [Ops](ops.md) — co-designed with the operations deadline model.
- **Granularity of the contact-graph and traversal-cost interface** with [Link](link.md) and
  [Worlds](worlds.md) so the IR stays solver-neutral without leaking physics.

**Mission-level joint assignment.** The asset↔target↔window↔trajectory problem reuses
every recommendation above: **CP-SAT / MILP** as the combinatorial backbone, **learned
warm-starts** for the larger search, and the **GNN-over-graph** encoder extended to the
asset-target-window graph. It is **window-gated with hard orbital deadlines** (a missed launch
window is infeasible until the next synodic opportunity), which makes it a natural fit for the
existing **anytime / rolling-horizon** re-solve. The open dependency here is the IR encoding of the
continuous Δv/ToF feasibility from [Trajectory](trajectory.md) without leaking orbital mechanics
into the solver-neutral model — the mission-scale analogue of the contact-graph question above.

---

## 12. Roadmap alignment

- **Phase 1 (this package's debut).** Allocate ships with [Mind](mind.md), [Learn](learn.md),
  [Guard](guard.md), [Studio](studio.md), and [Hub](hub.md) (charter §10) to make Astro-Mine "the
  MARL and planning commons for planetary swarms."
- **Phase-1 MVP:** the **CP-SAT** backend behind the [Core](core.md) allocation sub-interface;
  the canonical Allocation IR; constraint builders for **power, comms-window, and terrain
  traversability**; the **anytime** contract; deterministic, reproducible solves scored on the
  polar-water-prospecting benchmark via [Bench](bench.md). Called in-process by [Mind](mind.md);
  results wrapped by [Guard](guard.md). This proves the §8 problem can be *solved* before it is
  solved *well*.
- **Phase-1 later / Phase-2:** the **MILP track** (HiGHS/SCIP, optional Gurobi) and
  cross-solver consistency tests; **learned guidance** (GNN warm starts, learning-to-branch) from
  [Learn](learn.md) traces; **decomposition** (rolling-horizon, spatial partition) for scale on
  [Cloud](cloud.md); the **decentralized auction** fallback; **stochastic/robust** formulations
  over [Prospect](prospect.md) uncertainty. Online replanning hardens for [Ops](ops.md) at the
  Phase-2 operations threshold (charter §10).
- **Phase 3:** flight-adjacent replanning latency/assurance work alongside [Bridge](bridge.md);
  new task/asset regimes (asteroids, icy moons) arrive purely as constraint/solver plugins, never
  as core changes — the measure of success being how little Allocate's IR has to change as the
  edges grow.
- **Phase 3:** mission-level joint asset↔target↔window↔trajectory assignment lands as
  added constraint families/edge weights consuming [Trajectory](trajectory.md)/[Sizing](sizing.md)
  feasibility over the Mission/Phase/Regime contract ([mission-model](mission-model.md)) — Core
  schema hooks reserved in **Phase 1**, implementation in **Phase 3**; the IR and CP-SAT/MILP
  backbone are unchanged.
