# Astro-Mine-Trajectory — Technology Architecture

> Status: **Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) — implementation Phase 3.
> Layer: **Mission architecture & logistics (NEW layer)** · Phase: **3** (proposed)
> Design-time trajectory & maneuver optimization across mission regimes — the platform's first component that *optimizes* trajectories rather than merely propagating them.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Trajectory` is the **design-time trajectory and maneuver optimizer** for multi-regime
missions. Given a mission's bodies, epochs, fleet propulsion capabilities, and objective, it
searches for **reference trajectories** and the **Δv / time-of-flight (ToF) budgets** that realize
them across every regime a resource mission spans: launch injection, interplanetary transfer
(impulsive *and* low-thrust), rendezvous and approach, proximity trajectory design near a small
body, and return. It scans **launch and return windows** (porkchop analysis), and it produces the
Δv↔ToF↔mass trade frontier that the rest of the design loop reasons over.

It closes the charter's single biggest analytic gap. Today nothing in the platform *optimizes* a
trajectory: [Sim](sim.md) only **propagates and validates** a trajectory it is handed (against
external oracles), and [Allocate](allocate.md) reasons over *task-level* motion costs supplied to
it, never over orbital arcs. Trajectory is the component that *finds the arc in the first place* —
and then hands it to Sim to be validated and to Allocate/Sizing/Studio to be costed.

It owns and only owns:

- the **trajectory-optimization sub-interface** that turns a `LegRequest` (origin/target regime
  boundary conditions, dynamical context, propulsion model, objective) into a `TrajectoryRef`
  and `ManeuverBudget` (mission-model.md §2.3);
- a portfolio of **optimization backends** (Lambert/patched-conic, low-thrust optimal control,
  global metaheuristics) behind one strategy interface, organized into **fidelity tiers**;
- **window-scan and trade-frontier** machinery (porkchop grids, Pareto Δv/ToF fronts);
- the **descriptive** representation of a reference trajectory in Core — and the discipline that
  keeps that representation from ever becoming an executable command format.

**Explicitly out of scope — and this exclusion is load-bearing:** Trajectory is **design-time
exploration only**. It produces **descriptive** reference arcs and budgets for trade studies. It
is **not** operational maneuver targeting, **not** guidance, **not** closed-loop or
certification-grade flight code, and it performs **no conversion of a reference arc into executable
burns**. That capability — `operational_targeting` (mission-model.md §2.4) — is **excluded from
the open commons** (charter §10.5,
[EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md)) and is
partitioned at the [Bridge](bridge.md) boundary. Trajectory also does **no** guided atmospheric
EDL; `earth_interface` is a mass/Δv accounting event, not a re-entry simulator (mission-model.md
§4). It does not own the Mission/Phase schema ([Core](core.md)/mission-model.md), does not own
dynamical models ([Transit](transit.md)), and does not propagate-to-validate ([Sim](sim.md)).

**Primary users:** mission designers and astrodynamicists running Phase-0/A concept studies
through [Studio](studio.md)'s Mission Architect mode; trajectory researchers who plug in new
optimizers and benchmark them.

**Charter alignment:** §7 ("Astrodynamics … Orekit, GMAT, Basilisk; STK/GMAT as external
verification oracles"; "integrate aggressively, reinvent little"), §10.5 (dual-use posture),
§11 Phase 3 ("new environments — asteroids, icy moons — as plugins"). It is the analytic engine
behind mission-model.md's `TrajectoryRef`/`ManeuverBudget` artifacts.

---

## 2. Architecture principles

1. **Descriptive, never executable (the dual-use invariant).** Every output is a *description of
   a possibility* for a trade study — a reference arc and a budget — and carries **no** targeting,
   guidance law, closed-loop policy, or burn-execution semantics. This is enforced in the schema
   (§5, §9), not merely asserted in prose. If an output could be uplinked and flown, it does not
   belong here.
2. **Bridge, don't reinvent (conventions.md §1.7).** The world has mature, validated trajectory
   optimizers (pykep/pygmo, poliastro, Orekit). Trajectory **orchestrates** them behind one
   interface; it does not rebuild astrodynamics. We add the *commons layer* (uniform interface,
   provenance, window-scan orchestration, Core integration), not new propagators.
3. **Tiered fidelity, preliminary → verified (conventions.md §8).** A cheap patched-conic /
   Lambert tier scans the trade space; a high-fidelity tier refines the few survivors; an
   **oracle tier** validates the final arc by independent propagation. The scheduler trades
   accuracy for breadth per query.
4. **Optimization is upstream of truth, validation is downstream of it.** Trajectory *proposes*;
   [Sim](sim.md) *disposes*. Every `TrajectoryRef` that leaves the design loop is propagated and
   checked in Sim (and, where licensed, against GMAT/STK/Copernicus) before it is trusted. A
   trajectory the optimizer loves but Sim rejects is a wrong answer.
5. **Uncertainty is first-class (conventions.md §1.6).** Budgets carry margins and sensitivities
   (Δv vs. epoch/ephemeris/model error), not single guesses. A porkchop cell reports a
   *distribution*, and the trade frontier is annotated with robustness.
6. **Deterministic and reproducible (conventions.md §1.5, §11).** Same dynamical context + same
   seed + same pinned optimizer ⇒ same arc. Global/metaheuristic search controls or records its
   RNG so a [Bench](bench.md) trajectory study is reproducible to the digit.
7. **Constraints come from upstream truth.** Force models and ephemerides come from
   [Transit](transit.md) and SPICE; propulsion/Δv capability from [Fleet](fleet.md) SADF
   (mission-model.md §2.1); body shape/gravity from [Worlds](worlds.md). Trajectory invents no
   physics (conventions.md §1.6).
8. **Library first, embarrassingly parallel second (conventions.md §1.4, §8).** A single Lambert
   solve or porkchop scan runs in-process on a workstation. Window sweeps and global optimization
   are *embarrassingly parallel* and fan out on [Cloud](cloud.md) when scale demands it.

---

## 3. Application architecture

Trajectory is a **library with an optional gRPC service face** (conventions.md §1.4). Its modules:

```
astro_mine.trajectory
├── api/             # Core trajectory-optimization sub-interface impl; LegRequest/TrajectoryRef types
├── dynamics/        # Thin adapters onto Transit force models + SPICE ephemerides (no models of its own)
├── impulsive/       # Lambert solvers, patched-conic, multi-flyby, Δv/ToF; the fast preliminary tier
├── lowthrust/       # Low-thrust optimal control: Sims-Flanagan, direct collocation, indirect/shooting
├── windows/         # Porkchop / launch- & return-window grid scans; pruning; trade-frontier extraction
├── optimize/        # Global search orchestration (pygmo): metaheuristics, multi-objective, island model
├── verify/          # High-fidelity refinement + oracle adapters (Orekit; GMAT/STK/Copernicus, external)
├── budget/          # TrajectoryRef → ManeuverBudget reduction (Δv/ToF/margins/sensitivities) — descriptive only
├── uncertainty/     # Margin policy, epoch/ephemeris sensitivity, robust-window scoring
└── registry/        # Optimizer/oracle plugin discovery via Core manifests
```

### Key abstractions exposed

- **`LegRequest`** — the Core-typed input for one mission **Leg** (mission-model.md §1): origin
  and target **regime boundary conditions** (states/orbits/bodies + epoch or epoch window), a
  **dynamical context** handle (from [Transit](transit.md): which bodies, force-model fidelity,
  ephemeris kernel set), a **propulsion model** resolved from [Fleet](fleet.md) SADF
  (impulsive Δv stages and/or low-thrust profile, Isp, power), an **objective** (min-Δv,
  min-ToF, max-delivered-mass, weighted), and a **`SearchBudget`** (tier, wall-clock, target
  optimality, determinism flag).
- **`TrajectoryRef`** — the **descriptive** output (mission-model.md §2.3): a reference arc as
  **boundary states + maneuver nodes/control envelope at declared epochs in declared frames**
  (SI, SPICE-backed), the regime it spans, fidelity tier, and provenance. It is **explicitly not**
  a time-tagged thrust command sequence for flight hardware (§5, §9).
- **`ManeuverBudget`** — the reduced trade artifact: total and per-node Δv, ToF, propellant
  implied (for [Sizing](sizing.md) to expand via the rocket equation), margins, and Δv
  sensitivity to epoch/model error. This is what [Allocate](allocate.md) and [Studio](studio.md)
  consume as a *constraint/cost*, not the full arc.
- **`WindowScan`** — a porkchop/launch-window grid: per-cell feasibility + Δv/ToF, the extracted
  open windows, and the Pareto trade frontier across them.
- **`Optimizer` strategy** — `optimize(leg, context, budget) -> TrajectoryRef`. Backends
  (Lambert/patched-conic, Sims-Flanagan, collocation, pygmo global) are plugins.
- **`Oracle` verifier** — independently re-propagates a `TrajectoryRef` and reports residuals;
  the high-fidelity / external-tool check.

### Extension / plugin points

New **optimizer backends**, **window-scan strategies**, **verification oracles**, and **margin
policies** are all Core-manifest plugins (conventions.md §1.3) discovered via `registry` and
indexed by [Hub](hub.md). A lab ships "machine-learned low-thrust initial guess for NEO tours" as
an optimizer plugin without touching Trajectory's core. Reference backends ship as *replaceable
examples*.

### Interaction patterns

In-process: [Studio](studio.md)'s Mission Architect imports Trajectory and solves legs directly
inside a trade study. Out-of-process: large window sweeps and global searches run as a gRPC
worker fleet with **NATS+JetStream** job lifecycle (conventions.md §4), deployed by
[Cloud](cloud.md). Both faces share one library (conventions.md §1.4).

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.11+** for the API, orchestration, and most logic (conventions.md §2),
  type-checked with `mypy`/`pyright`. The astrodynamics ecosystem (pykep, poliastro, Orekit-via-
  `orekit_jpype`, Basilisk) is Python-native or Python-bound; hot custom kernels (e.g., a bespoke
  collocation transcription) drop to **C++20** via pybind11 only where profiling justifies it.
- **Optimization & astrodynamics libraries:**
  - **pykep + pygmo (ESA)** — the primary engine (charter §7). pykep supplies Lambert solvers,
    multiple-gravity-assist (MGA / MGA-1DSM) transcriptions, and **Sims-Flanagan low-thrust**
    models; pygmo supplies the **global-optimization** layer (metaheuristics, multi-objective,
    the island model) for window/global sweeps. This pair is the natural fit for preliminary
    trade-space search.
  - **poliastro / astropy** — clean two-body, Lambert, and porkchop primitives for the fast
    impulsive tier and for readable porkchop scans.
  - **Orekit** — high-fidelity propagation, event detection, and frames/force models for the
    **refinement** tier (consumed via [Transit](transit.md) where Transit wraps it; used directly
    here only for trajectory-specific refinement).
  - **Basilisk** — flight-like spacecraft dynamics for cross-checking proximity/return arcs at the
    refinement tier (shared with [Sim](sim.md)'s orbital regime).
  - **External verification oracles (charter §7):** **GMAT** (open), **STK**, **Copernicus** —
    invoked through the `verify`/`Oracle` adapter to independently confirm a final `TrajectoryRef`.
    These are **optional, license-gated, never default dependencies**, exactly as Gurobi is for
    [Allocate](allocate.md).
- **Low-thrust optimal control:** **Sims-Flanagan** (impulse-discretized, robust for global
  search) as the workhorse; **direct collocation** (e.g., `pygmo`/`pykep` transcriptions, or a
  CasADi-based NLP into IPOPT) for high-fidelity refinement; indirect/shooting as a research
  plugin. Tiered, not monolithic.
- **Schemas & APIs:** Pydantic v2 + JSON Schema for `LegRequest`; the `TrajectoryRef` /
  `ManeuverBudget` schemas are **owned by [Core](core.md)** (mission-model.md §2.3) — Trajectory
  *produces* them, it does not define them. gRPC/Protobuf for the service face; results emitted
  as **Apache Arrow/Parquet** (window grids, trade frontiers) per conventions.md §5.
- **Runtime model:** synchronous library call for a single leg/scan; async streaming gRPC for
  large sweeps. Search is CPU-bound and **embarrassingly parallel** across window cells, seeds,
  and pygmo islands.
- **Build/packaging:** Python wheel `astro-mine-trajectory`; OCI image bundling pinned pykep/
  pygmo/poliastro and a JVM for Orekit, for reproducible builds (conventions.md §7). GMAT/STK/
  Copernicus shipped as optional, license-gated extras, never default dependencies.

---

## 5. Data architecture

Trajectory is largely **transformational** — it consumes a dynamical context, produces reference
arcs and budgets — and persists little beyond results and provenance.

- **Produces:**
  - **`TrajectoryRef`** records (Core schema) — the descriptive reference arc: boundary states,
    maneuver nodes/control envelope at declared SPICE epochs in declared frames, fidelity tier;
  - **`ManeuverBudget`** records — Δv/ToF/margins/sensitivities, the trade artifact consumed
    downstream;
  - **`WindowScan` grids and trade frontiers** — emitted as **Apache Parquet** (Arrow in memory),
    the tabular porkchop/Pareto data for [Studio](studio.md) and [View](view.md);
  - **verification residuals** — the oracle/Sim re-propagation deltas attached to each `TrajectoryRef`.
- **Consumes:** **force models + ephemerides** from [Transit](transit.md) and SPICE geometry via the
  shared **`astro-mine-spice`** foundation ([RFC-0002](../rfc/0002-shared-spice-foundation.md); frames,
  TDB/ET epochs); **propulsion/Δv capability** from [Fleet](fleet.md) SADF
  (mission-model.md §2.1); **body shape/gravity field** from [Worlds](worlds.md) for proximity
  legs. All states carry an explicit planetary/inertial CRS resolved via SPICE/PROJ and SI units
  (conventions.md §5; mission-model.md §2.2).
- **The representation discipline (ties to mission-model.md §6 open question):** `TrajectoryRef`
  carries **just enough** structure for a trade study — *boundary states + maneuver budget +
  reference control envelope at coarse epochs* — and **deliberately not** a dense, flight-rate,
  time-tagged thrust/attitude command history. The schema **omits the fields a command format
  would require** (no actuator-level command channel, no closed-loop gains, no execution clock
  binding to flight hardware). This is the *back-door command format* failure mode named in
  mission-model.md §6, and the schema is the place it is foreclosed.
- **Storage:** `TrajectoryRef`/budget/scan artifacts are **content-addressed** in the
  S3-compatible object store (MinIO/S3/GCS) and shared as **trajectory libraries** via
  [Hub](hub.md); a relational catalog of solves and inputs in **PostgreSQL** for
  [Bench](bench.md)/[Studio](studio.md); **Redis** for caching window-scan partials across
  refinements.
- **Provenance & versioning (conventions.md §5):** every `TrajectoryRef` records the content
  hashes of the dynamical context, ephemeris kernel set, propulsion model, the optimizer backend
  + pinned version + seed, the fidelity tier, and any oracle that verified it — so any arc (and
  any [Bench](bench.md) score) is exactly reproducible. The Core `TrajectoryRef` schema is
  versioned and append-only (conventions.md §3).

---

## 6. Integration architecture

Trajectory is the keystone of the new mission-architecture layer and integrates entirely through
Core contracts (conventions.md §1.1); it creates no private side-channels.

- **Implements (provides):** the **trajectory-optimization sub-interface** of the [Core](core.md)
  Policy/Planner API (the design-time leg-solving contract), registered as a plugin via a Core
  manifest declaring supported interface versions and capability tags (mission-model.md §2.4).
- **Consumes dynamics from [Transit](transit.md):** force models, n-body context, and SPICE
  ephemerides. Trajectory holds **no** propagator of its own; it adapts Transit's
  (conventions.md §1.6).
- **Validated by [Sim](sim.md):** every `TrajectoryRef` is propagated and checked in Sim's
  orbital regime (Basilisk/Orekit, oracle-regressed) before it is trusted — Trajectory *proposes*,
  Sim *validates* (the inverse of [Allocate](allocate.md)→[Guard](guard.md)). This is the
  closure of the charter's "nothing optimizes trajectories" gap: optimize here, validate there.
- **Feeds the design loop:**
  - **[Allocate](allocate.md)** — consumes **leg feasibility + Δv/ToF as constraints/costs** for
    asset↔target↔window assignment (which spacecraft, to which body, in which launch window). The
    `ManeuverBudget` becomes an edge cost in Allocate's IR; Trajectory does the orbital reasoning
    Allocate explicitly does not.
  - **[Sizing](sizing.md)** — consumes **Δv → propellant** (Sizing expands the budget via the
    rocket equation against [Fleet](fleet.md) Isp/staging).
  - **[Studio](studio.md)** — its **Mission Architect mode** orchestrates Trajectory across a
    mission's legs inside a trade study, co-optimizing trajectory ⇄ fleet ⇄ swarm ⇄ economics
    (mission-model.md §6).
- **Shares libraries via [Hub](hub.md):** reference trajectories, window catalogs, and porkchop
  datasets are content-addressed Hub artifacts, reusable across studies.
- **Scaled on [Cloud](cloud.md):** window sweeps, pygmo island runs, and multi-start global
  optimization fan out across **Ray/Argo** on Kubernetes — the embarrassingly-parallel unit is a
  window cell or a search seed.
- **Evaluated by [Bench](bench.md):** Δv/ToF quality vs. published references, time-to-frontier,
  and oracle-residual accuracy scored on named trajectory problems (e.g., GTOC-style tours, an
  Earth→NEO→Earth sample-return leg), with Bench pinning optimizer and ephemeris versions.
- **Message flows:** in-process for the Studio trade loop; **gRPC** for large solves; lifecycle
  events on **NATS+JetStream** (conventions.md §4); a trade study is **distributed-traceable**
  through Studio → Trajectory → Sim → Allocate/Sizing (conventions.md §10).

---

## 7. Infrastructure & deployment

- **Deployment tiers (conventions.md §7):**
  1. **Local/dev** — `pip install astro-mine-trajectory`; a Lambert solve, a single low-thrust
     leg, or a modest porkchop grid runs in-process on a workstation in seconds to minutes. **This
     tier MUST always work** — a designer scans a launch window in an afternoon.
  2. **Cloud** — a gRPC optimizer service plus **Ray** for parallel window sweeps and pygmo
     islands, **Argo Workflows** for DAG-style multi-leg / multi-target campaign studies, on
     **Kubernetes** (conventions.md §7).
  3. **Design-studio integration** — co-located with [Studio](studio.md) for interactive Mission
     Architect trade studies.
  - There is **no operations/flight tier.** Trajectory is design-time only; nothing it produces is
    deployed to ground ops or flight hardware (§1, §9). The path to flight is foreclosed, not
    plumbed.
- **Compute:** **CPU-bound**, not GPU. Global optimization benefits from many cores (island
  parallelism, multi-start); a typical worker is 8–32 vCPU, 16–64 GB RAM. The Orekit refinement
  tier needs a JVM in-image. GPU is not used (low-thrust NLPs are CPU/IPOPT-bound).
- **Containerization:** OCI image with pinned pykep/pygmo/poliastro and a bundled JVM for Orekit,
  for reproducible builds (conventions.md §7); GMAT/STK/Copernicus as optional license-gated
  layers.

---

## 8. Performance & scalability

- **Targets (indicative, refined by [Bench](bench.md)):**
  - *Impulsive tier:* a single Lambert/patched-conic transfer in **milliseconds**; a porkchop grid
    of **10⁴–10⁶ cells** in seconds-to-minutes parallelized.
  - *Low-thrust tier:* a Sims-Flanagan leg in **seconds**; a high-fidelity collocation refinement
    in **seconds-to-minutes**.
  - *Global tier:* a multi-flyby / NEO-tour search (pygmo) to a near-reference frontier in
    **minutes-to-hours** with island parallelism on [Cloud](cloud.md).
- **Bottlenecks:** combinatorial blow-up of multi-flyby sequencing and launch-window grids; the
  cost and convergence fragility of low-thrust NLPs; ephemeris/force-model evaluation cost at the
  refinement tier.
- **Mitigations & scaling strategy:**
  - **Tiered search (`impulsive` → `lowthrust` → `verify`):** cheap patched-conic prunes the trade
    space; only survivors are refined; only the final arc is oracle-verified. Most compute is
    spent on the cheapest tier (conventions.md §8 multi-fidelity).
  - **Embarrassingly-parallel sweeps (conventions.md §8):** window cells, seeds, and pygmo islands
    are independent units fanned out across Ray/Argo — near-linear scale-out.
  - **Warm starts:** an impulsive solution seeds the low-thrust initial guess; an adjacent window
    cell seeds its neighbor; a prior study's `TrajectoryRef` seeds a re-study.
  - **Pruning:** dominated porkchop cells and infeasible flyby sequences are dropped early.
  - **Measure before optimizing (conventions.md §8):** a representative trajectory-problem suite
    ships; every Δv/ToF/runtime claim is a reproducible [Bench](bench.md) number with pinned
    optimizer and ephemeris versions.

---

## 9. Security, safety & compliance

This section is **central** to Trajectory; the dual-use boundary is the defining design concern
(charter §10.5, conventions.md §12, mission-model.md §4).

- **The design-time-vs-operational-targeting boundary (the load-bearing line).** Trajectory
  produces **descriptive** reference arcs and Δv/ToF budgets *for trade studies*. It contains, and
  may contain, **no**:
  - conversion of a `TrajectoryRef` into **executable maneuver guidance** (a time-tagged,
    flight-hardware-bound thrust/attitude command sequence);
  - **closed-loop / feedback** targeting or guidance laws;
  - **guided atmospheric EDL** or re-entry targeting (`earth_interface` is a mass/Δv accounting
    *event*, not a re-entry simulator — mission-model.md §4);
  - certification-grade flight code (the charter §10.5 "P3 concept", explicitly excluded).
  Anything crossing this line is the `operational_targeting` capability — **excluded from the open
  commons**, **partitioned** into separate access-controlled repos, and reachable (if at all) only
  through the [Bridge](bridge.md) boundary, **never** inside Trajectory. The exclusion is not
  documentation-only; it is structural, on three layers:
  1. **Schema (the primary control).** The Core `TrajectoryRef` schema is *descriptive by
     construction* (§5): boundary states + maneuver budget + coarse-epoch reference control
     envelope, and it **omits** the fields a command format needs (no actuator command channel, no
     closed-loop gains, no flight-clock execution binding). The schema is where the back-door
     command format (mission-model.md §6) is foreclosed; any RFC that would add such fields is
     where the dual-use review happens.
  2. **Capability tag (the gate).** Trajectory declares only design-time capability tags in its
     Core manifest; it does **not** declare `operational_targeting` (mission-model.md §2.4). The
     registry/OPA policy denies any plugin that would couple Trajectory's output to a targeting
     capability (conventions.md §9, [Core](core.md) §9).
  3. **Topology (no operational tier).** Trajectory has no ground/flight deployment tier (§7) and
     no data path to [Bridge](bridge.md)'s flight adapters. Its outputs flow to *design* siblings
     ([Allocate](allocate.md)/[Sizing](sizing.md)/[Studio](studio.md)) and to [Sim](sim.md) for
     *validation* — never toward execution.
- **EAR/ITAR posture.** Trajectory is the **most export-sensitive** component in the proposed
  extension. Its open scope — preliminary mission analysis, Δv/ToF trade studies, window scanning,
  reference arcs that are validated descriptions, using published tools (pykep/Orekit) and public
  ephemerides — is the kind of analysis universities and open mission-design tools (GMAT,
  poliastro) already publish. The sensitive line is **operational targeting / guidance**, kept out
  per the boundary above. The component documents a clear posture per
  [EXPORT_CONTROL.md](https://github.com/astro-mine/.github/blob/main/EXPORT_CONTROL.md); external
  oracles (STK/Copernicus) are user-supplied, license-gated, and not redistributed.
- **AuthN/AuthZ & supply chain.** The gRPC/REST face uses platform OIDC + RBAC via **OPA**;
  service-to-service over **mTLS** (conventions.md §9). Untrusted third-party optimizer plugins
  run **out-of-process** in sandboxed containers (seccomp/gVisor; WASM forward-looking) — a
  malicious optimizer could otherwise return crafted-infeasible "frontiers." Optimizer/ephemeris
  binaries are pinned; artifacts signed (**Sigstore/cosign**) with **SLSA** provenance + **SBOM**.
- **Validation as integrity.** A `TrajectoryRef` is only trusted after [Sim](sim.md)/oracle
  re-propagation; recorded seeds + pinned versions make every arc auditable and reproducible
  (conventions.md §11). A non-reproducible or unverified arc is detectable.

---

## 10. Observability & operability

- **Telemetry (conventions.md §10):** **OpenTelemetry** SDK emits structured logs, metrics, and
  traces. A trade study is **traceable end-to-end** through [Studio](studio.md) → Trajectory →
  [Sim](sim.md) → [Allocate](allocate.md)/[Sizing](sizing.md).
- **Metrics:** solves/sec by tier, window-grid throughput, low-thrust NLP convergence rate and
  iterations, time-to-frontier, oracle-residual magnitudes, cache hit rate — to **Prometheus +
  Grafana**.
- **Explainability:** every `TrajectoryRef` ships its objective value, the binding budget terms
  (which legs/nodes dominate Δv), the fidelity tier, the verifying oracle and its residuals, and
  the window-feasibility envelope — so a designer learns *why* a window is best and *how trusted*
  the arc is. Infeasible legs return an explained reason (e.g., "Δv exceeds fleet budget across
  the whole scanned window"), mirroring [Allocate](allocate.md)'s infeasibility certificates.
- **Testing & validation (conventions.md §11):**
  - **Unit/integration:** `pytest`; **Hypothesis** property tests on astrodynamics invariants
    (Lambert round-trips, energy/momentum conservation in two-body, Δv-budget monotonicity).
  - **Oracle regression (conventions.md §11):** reference arcs regressed against **GMAT/STK/
    Copernicus** and against published **GTOC** solutions, with explicit error budgets.
  - **Cross-tier consistency:** the patched-conic estimate must bound/approximate the high-fidelity
    refinement within a declared tolerance — a differential test of the tier ladder.
  - **Determinism gates (conventions.md §11):** seeded global searches compared against stored
    golden frontiers; CI fails on non-reproducibility.
  - **Contract tests:** consumer-driven contract tests prove Trajectory honors the [Core](core.md)
    trajectory-optimization sub-interface and emits schema-valid, *descriptive-only* `TrajectoryRef`
    (a test asserts the absence of command-format fields).

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Build vs bridge** | Build a new in-house optimizer; **bridge to pykep/Orekit/poliastro and orchestrate** | **Bridge and orchestrate** — the charter's "integrate aggressively, reinvent little" (§7); the commons value is the uniform interface + provenance + window orchestration + Core integration, not new astrodynamics |
| **Optimization approach** | Impulsive patched-conic only; full low-thrust optimal control only; global metaheuristics (pygmo) only; **tiered combination** | **Tiered** — fast impulsive/Lambert scan → low-thrust (Sims-Flanagan → collocation) refinement → global (pygmo) where sequencing is combinatorial → oracle verification. No single method spans preliminary breadth and high-fidelity depth |
| **Primary library stack** | **pykep + pygmo (ESA)**; poliastro; custom | **pykep + pygmo** for Lambert/MGA/Sims-Flanagan + global search (charter §7); **poliastro/astropy** for clean two-body/porkchop primitives |
| **Low-thrust transcription** | **Sims-Flanagan**; direct collocation (CasADi/IPOPT); indirect/shooting | **Sims-Flanagan** as the robust global-search workhorse; **direct collocation** for high-fidelity refinement; indirect as a research plugin |
| **High-fidelity / verification** | Trust the optimizer; **independent propagation in Sim + external oracle** | **Independent verification** — propagate in [Sim](sim.md) (Basilisk/Orekit) and confirm against **GMAT/STK/Copernicus** (charter §7) as optional, license-gated oracles; never a default dependency |
| **Fidelity tiers** | Single fidelity; **preliminary → high-fidelity → oracle** | **Three tiers** — patched-conic preliminary, high-fidelity refinement, oracle validation; the scheduler trades breadth for accuracy (conventions.md §8) |
| **`TrajectoryRef` representation** | Full flight-rate state/command history; **boundary states + budget + coarse reference envelope** | **Boundary states + maneuver budget + coarse-epoch reference envelope** — carries enough for a trade study, deliberately *omits* command-format fields so it cannot become a back-door command channel (mission-model.md §6, §5, §9) |
| **Window/global parallelism** | Single-node; **Ray/Argo fan-out on Cloud** | **Embarrassingly-parallel on [Cloud](cloud.md)** — window cells, seeds, and pygmo islands are independent units (conventions.md §8) |
| **Service vs library** | Library only; service only; **both (one codebase)** | **Both** — library first (conventions.md §1.4); a streaming-gRPC service is a deployment of the same library for large sweeps |

**Open questions / research dependencies:**

- **`TrajectoryRef` structure (mission-model.md §6):** the exact minimal field set that supports
  trade studies *and* Sim validation while provably excluding a command format — resolved in
  [RFC-0001](../rfc/0001-multi-regime-missions.md)
  and co-designed with [Core](core.md) and governance/export-control.
- **Co-optimization coupling (mission-model.md §6):** how tightly to couple trajectory ⇄ fleet ⇄
  Δv/propellant ⇄ swarm ⇄ economics — a fully-coupled global optimum vs. iterated fixed-point
  between Trajectory/[Sizing](sizing.md)/[Allocate](allocate.md) inside [Studio](studio.md).
- **Low-thrust global search reliability:** which transcription + global-optimizer pairing is most
  robust for many-flyby NEO tours — an open empirical question scored on [Bench](bench.md) (GTOC).
- **Uncertainty propagation:** how to attach epoch/ephemeris/model-error sensitivities to a
  `ManeuverBudget` cheaply enough to scan, co-designed with the margin policy.
- **Where the [Transit](transit.md)/Trajectory boundary sits:** which force-model and ephemeris
  responsibilities live in Transit vs. are configured per-leg here.

---

## 12. Roadmap alignment

- **Schema hooks land early (mission-model.md §3).** The Core `TrajectoryRef`/`ManeuverBudget`
  schemas land additively in **Core v0.x during Phase 1** (when Core is already being extended for
  autonomy), even though the optimizer implementation is Phase 3 — retrofitting trajectory schema
  into a frozen waist later is exactly the leaky-god-interface failure the charter warns against
  (§9, mission-model.md §3).
- **Phase 3 (this component's debut, proposed).** Trajectory ships with the new
  mission-architecture layer — [Transit](transit.md), [Sizing](sizing.md), and the
  Mission/Phase/Regime model — to make Astro-Mine span end-to-end interplanetary resource
  missions, alongside "new environments (asteroids, icy moons) as plugins" (charter §11 Phase 3).
- **Phase-3 MVP:** the **impulsive tier** (Lambert/patched-conic + porkchop window scans via
  pykep/poliastro) behind the [Core](core.md) trajectory-optimization sub-interface; the
  descriptive `TrajectoryRef`/`ManeuverBudget`; validation in [Sim](sim.md) and against GMAT;
  feeding Δv/ToF to [Allocate](allocate.md)/[Sizing](sizing.md) inside a [Studio](studio.md)
  Mission Architect trade study for one reference Earth→NEO→Earth mission. This proves the gap can
  be *closed* — trajectories can be optimized and validated — before it is closed *well*.
- **Phase-3 later:** the **low-thrust tier** (Sims-Flanagan → collocation), **global search**
  (pygmo, GTOC-class tours), full oracle suite (STK/Copernicus), uncertainty-annotated budgets,
  and cloud-scale window sweeps. New regimes (icy moons, multi-target tours) arrive purely as
  optimizer/dynamics plugins, never as core changes — the measure of success being how little the
  `TrajectoryRef` schema has to change as the edges grow, and how firmly the design-time boundary
  holds as capability expands.
