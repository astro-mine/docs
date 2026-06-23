# Astro-Mine-Sizing — Technology Architecture

> Status: **Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) — implementation Phase 3.
> Layer: **Mission architecture & logistics (NEW layer)** · Phase: **3** (proposed)
> Spacecraft & payload systems-engineering sizing: mass/power/propellant/staging budgets, payload packing, launch manifesting, reusable-LEO accounting.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Sizing` is the platform's **conceptual / preliminary systems-engineering sizing**
engine. It closes a single, sharply-scoped gap that the multi-regime extension opens:

> *"What spacecraft do I actually need, carrying what payload, staged how, launched on what — and
> what can I reuse from an existing LEO inventory?"*

Given a mission Δv and time-of-flight budget (from [Trajectory](trajectory.md)) and an ISRU/mining
throughput requirement (from [Studio](studio.md)'s objective and the [mission-model](mission-model.md)
`MissionSpec`), Sizing produces **feasible, sized asset configurations** — closed mass/power/
propellant/thermal/structure budgets, a packed-and-manifested launch plan, and a reusable-LEO-
asset ledger — expressed as concrete **[Fleet](fleet.md) SADF** using the propulsion / staging /
return SADF extensions in [mission-model §2.1](mission-model.md). It is the bridge between an
*abstract* Δv-and-throughput requirement and a *concrete*, instantiable, simulatable vehicle set.

Sizing owns the coupled-subsystem closure problem: rocket-equation/staging math, mass-estimating
relationships (MERs), parametric power/thermal/structure/propulsion models, payload packing, and
launch manifesting (mass-to-orbit curves and fairing volume), driven by a multidisciplinary design
analysis & optimization (MDAO) backbone so subsystems converge consistently rather than each being
sized in isolation.

**What Sizing explicitly does NOT do:**

- It does **not design trajectories** — Δv, ToF, windows, and arcs come from
  [Trajectory](trajectory.md). Sizing *consumes* a `ManeuverBudget`, never computes one.
- It does **not run physics** — it produces *design-time* budgets and configurations;
  [Sim](sim.md) instantiates and validates them dynamically. Sizing's MERs are calibrated
  *against* Sim/flight data, not a substitute for it.
- It does **not do detailed design** — no CAD, no FEA/structural analysis, no thermal-network
  solve at part level. This is **conceptual/preliminary** (pre-Phase-A) sizing, not Phase-C
  engineering.
- It does **not define SADF** — that is [Core](core.md)'s. Sizing *parameterizes and emits* SADF
  configurations that [Fleet](fleet.md) holds, exactly as [Fleet](fleet.md) authors content
  against the Core schema without widening it.
- It does **not own economics** — it emits mass/propellant/launch-slot quantities that
  [Ledger](ledger.md) prices; it never embeds a cost model of record.

**Primary users:** mission architects running trade studies in [Studio](studio.md); contributors
publishing subsystem models; campaign designers who need a believable, closed vehicle set before
committing simulation compute.

**Charter alignment:** charter §7 (leverage mature foundations — OpenMDAO, parametric SE models),
§9 ("a durable abstraction across orbital, surface, manipulation, and ISRU"; "heterogeneity without
abstraction collapse" — Sizing must close budgets for orbiters *and* excavators alike), and the
multi-regime extension ([mission-model](mission-model.md)).

---

## 2. Architecture principles

1. **Produce SADF, never widen it.** Sizing's output is a *valid, sized* SADF configuration against
   the current Core schema — including the propulsion/staging/return blocks from
   [mission-model §2.1](mission-model.md). If a sized result cannot be expressed in SADF, the
   response is a Core RFC, never a private side-channel (conventions.md §1, §3; mirrors
   [Fleet](fleet.md) principle 1).
2. **Sizing closes budgets; it does not simulate them.** Every quantity Sizing reports is a
   *design-time estimate with explicit uncertainty*. The authoritative check is
   [Sim](sim.md)/[Surrogate](surrogate.md). Sizing fails fast when a configuration cannot close
   (negative margin, no convergent staging) rather than emitting an unphysical asset.
3. **Coupled by construction.** Subsystems (propulsion, power, thermal, structure, payload) are
   *mutually dependent* (more propellant → more tank mass → more structure → more Δv needed). They
   MUST be solved as a converged system via MDAO, not in a one-pass spreadsheet order.
4. **Uncertainty is first-class** (conventions.md §6). MERs carry residual error bands; sized
   budgets carry margins (mass-growth allowance, power contingency) and propagate uncertainty so a
   "feasible" verdict is a *probability of closure*, not a point claim.
5. **Library first, service second** (conventions.md §1). Sizing is an importable Python package
   that closes one vehicle on a workstation before it is a [Cloud](cloud.md) sweep service.
6. **Subsystem models are plugins** (conventions.md §1 "plugins over patches"). A propulsion model,
   a MER set, a launch-vehicle performance curve, or a fidelity tier is a registered plugin
   discovered via [Hub](hub.md) — never a core code change.
7. **Determinism & reproducibility by default** (conventions.md §5, §11). Same requirement + same
   model set + same seed ⇒ same sized SADF bytes, so a [Bench](bench.md)/[Studio](studio.md) trade
   is reproducible to the configuration.
8. **Frame- and unit-explicit, provenance-tracked** (conventions.md §5; core.md principle 8). Every
   budget is SI; every sized asset records the requirement, model versions, optimizer settings, and
   input hashes it was derived from.
9. **Honest dual-use boundary** (conventions.md §12; [mission-model §4](mission-model.md)). Sizing
   consumes *descriptive* `ManeuverBudget` Δv — never executable guidance — and produces vehicle
   budgets, not targeting. It stays firmly in the open commons.

---

## 3. Application architecture

Sizing is **library-first**: an importable Python package plus a CLI for closing/optimizing a
vehicle and emitting SADF, and an optional sweep service for [Cloud](cloud.md). It exposes no
per-tick hot path.

```
astro_mine.sizing
├── requirements/   # parse MissionSpec/objective → typed sizing requirements (Δv, ToF, throughput, constraints)
├── subsystems/     # parametric subsystem models, each a plugin:
│   ├── propulsion/ #   rocket-equation, staging, chem/electric/cold-gas/solar-sail Isp & thrust models
│   ├── power/      #   solar array / RTG / battery sizing vs. distance, duty cycle, eclipse/night
│   ├── thermal/    #   radiator/heater MERs, survival-power for lunar night & deep cruise
│   ├── structure/  #   structural-mass fraction & tank MERs, mass-growth allowance
│   ├── payload/    #   ISRU/mining throughput → plant mass/power; instrument & sample-canister mass
│   └── mass/       #   mass-estimating relationships (MERs) + margin/contingency policy
├── mdao/           # OpenMDAO problem assembly: components, couplings, solvers, drivers, design vars
├── staging/        # multi-stage Δv split, optimal staging, drop-mass bookkeeping across phases
├── manifest/       # launch manifesting: mass-to-orbit curves, fairing-volume packing, multi-launch split
├── packing/        # geometric payload/stowage packing into fairing/lander volume (bin-packing)
├── inventory/      # reusable-LEO-asset accounting: fixed assets vs. design variables, in-orbit state
├── sweep/          # design-of-experiments & optimization sweeps (DOE, Pareto fronts) → Cloud
├── emit/           # converged design → sized SADF config (Fleet) + mass/cost records (Ledger)
└── cli/            # `sizing close|optimize|manifest|sweep|emit|validate`
```

### Key abstractions exposed

- **SizingRequirement** — the typed input: per-phase Δv/ToF (from a `ManeuverBudget`), throughput
  and payload targets, global constraints (budget, schedule, launch capacity, export gating) lifted
  from the [mission-model](mission-model.md) `MissionSpec`.
- **VehicleModel** — an MDAO problem: a graph of subsystem components with declared couplings,
  design variables (e.g. stage propellant, array area), constraints (margins ≥ 0, fairing fit), and
  an objective (min IMLEO, min launches, max delivered mass).
- **SizedConfiguration** — the output: a converged budget set (mass/power/propellant/thermal/
  structure with margins), a staging plan, a launch manifest, an inventory delta, and the **SADF
  patch** that realizes it — plus a closure verdict with uncertainty.
- **SubsystemModel plugin** — a parametric model (MER set, performance curve, fidelity tier) with a
  declared input/output signature and an error band, registered through a Core manifest.

### Key abstractions consumed

- the **SADF schema + propulsion/staging/return extensions** ([Core](core.md);
  [mission-model §2.1](mission-model.md)) — the emit target;
- the **`MissionSpec` / `ManeuverBudget` / `TrajectoryRef`** schemas
  ([mission-model §2.3](mission-model.md)) — the requirement source;
- the **plugin manifest** and **units/frames/time** conventions ([Core](core.md));
- **asset templates** from [Fleet](fleet.md) — Sizing parameterizes an existing parametric family
  rather than inventing geometry.

### Extension points

- A **new subsystem model** (e.g. a higher-fidelity electric-propulsion sizing model, a new MER
  fit) registers via Python entry points and is discovered/pulled via [Hub](hub.md) — no Sizing
  code change (mirrors [Fleet](fleet.md)'s importer/resolver plugins).
- **New launch-vehicle performance curves** (mass-to-orbit vs. orbit, fairing envelopes) are data
  plugins.
- **New MDAO drivers** (a different optimizer, surrogate-based optimization) plug into the `mdao`
  layer behind a stable driver interface.

### Interaction patterns

Consumed **in-process as a library** at design time (close/optimize one vehicle), and as a **batch
sweep** on [Cloud](cloud.md) for trade spaces (DOE / multi-objective fronts). Output flows
*asynchronously*: a converged `SizedConfiguration` is emitted as a SADF patch that [Fleet](fleet.md)
holds and packages, and as mass/propellant/launch records that [Ledger](ledger.md) prices. Sizing
never sits on a simulation or operations hot path.

---

## 4. Application programming & runtime platforms

- **Languages.** **Python 3.11+** (conventions.md §2) for requirements parsing, subsystem models,
  MDAO assembly, manifesting, emit, and CLI — Python is both the conventions default and OpenMDAO's
  native language. No C++ is required; the math is algebraic/iterative, not a hot inner loop. A
  **Rust** path is *optional* only for a future fast packing/bin-fit kernel if it ever bottlenecks
  large sweeps.
- **MDAO backbone.** **OpenMDAO** (NASA's open-source multidisciplinary design analysis &
  optimization framework, charter §7) is the recommended backbone: it provides the component model,
  analytic/coupled derivatives, Newton/nonlinear-block-Gauss-Seidel solvers for converging coupled
  subsystems, and a driver interface to gradient (SLSQP/SciPy, pyOptSparse/SNOPT) and gradient-free
  (DOE, genetic) optimizers. Its derivative machinery is what makes coupled trajectory⇄vehicle
  trades tractable (see §11).
- **Numerics & libraries.** **NumPy/SciPy** for the MERs and rocket-equation math;
  **Pydantic v2** typed models generated from the Core/mission `MissionSpec`/`ManeuverBudget` JSON
  Schema (`datamodel-code-generator`); `jsonschema` for boundary validation (conventions.md §3).
  Bin-packing/stowage via a constraint solver (**OR-Tools CP-SAT**, charter §7) where geometric
  packing is non-trivial.
- **SADF emit.** Reuses [Fleet](fleet.md)'s authoring helpers and Core SADF Pydantic types so a
  `SizedConfiguration` produces a *valid* SADF document that [Fleet](fleet.md) lints and packages —
  Sizing does not re-implement SADF serialization.
- **Build/packaging.** Python wheel `astro-mine-sizing` (import `astro_mine.sizing`,
  conventions.md §13); **SemVer**. Subsystem-model and launch-curve *data* are versioned and
  distributed independently as **OCI artifacts** via [Hub](hub.md) (conventions.md §7), so model
  updates don't require a toolchain release.

---

## 5. Data architecture

Sizing **produces sized configurations and consumes requirements**; it owns *no* schema
(that is [Core](core.md)) and *no* cost model (that is [Ledger](ledger.md)).

| Data | Role | Format / store |
|---|---|---|
| Sizing requirements | Consumed | `MissionSpec` + `ManeuverBudget`/`TrajectoryRef` (Core/mission schemas, conventions.md §3) |
| Subsystem models / MERs | Consumed / produced | Parametric model code (plugins) + coefficient tables in **Parquet/JSON**, each with a calibration provenance record and error band |
| Launch-vehicle performance | Consumed | Mass-to-orbit curves + fairing envelopes as versioned **data plugins** (Parquet/JSON, OCI artifacts) |
| Sized configurations | **Produced** | **SADF** documents/patches in YAML/JSON (authored) + Core Protobuf wire form, validated by the Core schema — held and packaged by [Fleet](fleet.md) |
| Trade-study results | Produced | **Apache Parquet** tables (design points, margins, Pareto fronts); **Arrow** in-memory (conventions.md §5) — ingested by [Studio](studio.md)/[Bench](bench.md) |
| Mass / propellant / launch records | Produced | Tabular quantity records handed to [Ledger](ledger.md) for pricing (conventions.md §5) |
| Reusable-LEO inventory | Consumed / updated | Fleet members with an initial in-orbit state ([mission-model §2.1](mission-model.md)); inventory deltas recorded per design |

**Schemas.** Sizing authors *against* Core's SADF schema and embeds the Core/mission schema version
each sized asset targets (conventions.md §3; core.md §6 version negotiation), so [Sim](sim.md) and
[Studio](studio.md) can negotiate compatibility.

**Provenance & reproducibility** (conventions.md §5). Every `SizedConfiguration` records: the input
requirement hash (`ManeuverBudget`/`MissionSpec`), the **subsystem-model versions** and their
calibration lineage, the **MDAO driver + settings + seed**, the margin/contingency policy, and the
toolchain version — so any [Bench](bench.md) result or [Studio](studio.md) trade that used a sized
vehicle is reproducible to the exact converged design.

---

## 6. Integration architecture

Sizing sits in the **new mission-architecture & logistics layer**, between trajectory design and
asset content. Every integration crosses a [Core](core.md) contract — no private side-channels
(conventions.md §1).

- **[Core](core.md):** foundational dependency. Sizing consumes the SADF schema (incl. the
  propulsion/staging/return extensions), the `MissionSpec`/`ManeuverBudget` schemas, the plugin
  manifest, and units/frames. Each subsystem model and launch curve ships a **Core plugin manifest**
  (kind = sizing-model; declared interface versions; provenance; signature).
- **[Trajectory](trajectory.md):** the upstream Δv/ToF source. Sizing **consumes** a descriptive
  `ManeuverBudget` (per-phase Δv, time of flight, window) — never executable guidance
  ([mission-model §4](mission-model.md)). The trajectory⇄vehicle coupling (sequential vs. fully
  coupled MDO) is the key design seam — see §11.
- **[Fleet](fleet.md):** the **emit target and template source**. Sizing parameterizes a Fleet
  parametric asset family (mass/power/propellant exposed as parameters) and writes back a *sized,
  valid* SADF configuration that Fleet holds, lints, and packages. Sizing **produces** what
  [Fleet](fleet.md) **holds** — the same SADF/Core boundary [Fleet](fleet.md) keeps with
  [Core](core.md).
- **[Studio](studio.md):** the primary caller. Sizing is part of Studio's **Mission Architect**
  trade studies, co-optimized with trajectory and swarm design — Studio supplies the objective/
  throughput requirement and consumes Pareto fronts of sized vehicles.
- **[Sim](sim.md):** the **validation backstop**. A sized SADF is instantiated and flown in Sim; Sim
  outputs (achieved Δv, power/thermal behavior, mass utilization) calibrate Sizing's MERs and catch
  configurations that *close on paper but fail dynamically* (mirrors [Fleet](fleet.md)'s Sim smoke
  test).
- **[Ledger](ledger.md):** the **economics consumer**. Sizing emits mass/propellant/launch-slot
  quantities; Ledger prices them. Sizing carries no cost model of record.
- **[Cloud](cloud.md):** heavy MDO sweeps (DOE, multi-objective fronts) fan out here
  (conventions.md §7).
- **[Hub](hub.md):** subsystem models, MER sets, and launch curves are **published/discovered** as
  signed OCI artifacts; sized reference designs are shared for reuse (charter §5.7).
- **[Surrogate](surrogate.md):** optionally provides fast surrogates of expensive subsystem physics
  to keep large MDO sweeps interactive (conventions.md §8 multi-fidelity).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — close or optimize a single vehicle and emit SADF on a workstation in seconds.
     *This tier MUST always work* (conventions.md §7 tier 1).
  2. **Cloud** — large MDO sweeps / Pareto fronts fan out on **Kubernetes + Ray** or **Argo
     Workflows** (DAG-style DOE) via [Cloud](cloud.md) (conventions.md §7).
- **Compute.** **CPU-bound and modest.** Closing one coupled vehicle is sub-second to seconds; cost
  scales with *sweep breadth*, not per-vehicle work. **No GPU** required. Gradient-based MDO with
  analytic derivatives keeps even large design spaces tractable on CPU.
- **Containerization.** An OCI **toolchain image** (Python + OpenMDAO + SciPy + OR-Tools) for
  reproducible CI and Cloud sweeps (conventions.md §7). Subsystem-model/launch-curve *data* ships as
  separate content-addressed OCI artifacts, not code images.
- **Orchestration.** None at runtime (library + optional batch). Sweeps use **Argo Workflows /
  Ray** on [Cloud](cloud.md); CI is **GitHub Actions** (conventions.md §11).
- **Scaling.** Horizontal across design points — embarrassingly parallel DOE samples cached by input
  hash (conventions.md §5, §8); no central runtime to saturate.

---

## 8. Performance & scalability

- **Targets.**
  - Single-vehicle closure (converged coupled MDAO solve): **sub-second to a few seconds**, so
    [Studio](studio.md) trade studies stay interactive.
  - SADF emit + Core schema-validate per configuration: **negligible** relative to the solve
    (reuses [Fleet](fleet.md)/Core validators).
  - A 10³–10⁵-point design sweep completes in **minutes on [Cloud](cloud.md)** via parallel DOE.
- **Bottlenecks.** (1) Convergence of strongly-coupled subsystem loops (propellant ⇄ structure ⇄
  Δv); (2) gradient-free optimization over high-dimensional design spaces; (3) the
  trajectory⇄vehicle coupling if every sizing iteration re-invokes [Trajectory](trajectory.md).
- **Mitigations.**
  - **Analytic/coupled derivatives** (OpenMDAO) for gradient-based optimization instead of
    finite-difference, collapsing iteration counts on the coupled loop.
  - **Multi-fidelity** (conventions.md §8): cheap MERs for broad sweeps; physics-based subsystem
    models or [Surrogate](surrogate.md) only where a trade is sensitive — Sizing *declares* the
    fidelity tier, the sweep scheduler *chooses* it.
  - **Decouple the trajectory loop** by default (sequential Δv→sizing) with a *surrogate of
    trajectory* (Δv as a smooth function of design vars) for the inner MDO, reserving fully-coupled
    co-optimization for final trades (see §11).
  - **Content-address and cache** design points so unchanged requirements/models are never
    re-solved (conventions.md §5).
- **Scaling strategy.** Horizontal across design points on Ray/Argo (conventions.md §7, §8); the
  library itself adds no central bottleneck.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ.** Sizing is a library; access control lives at the **publish boundary** to
  [Hub](hub.md) and at the [Cloud](cloud.md) sweep service (OIDC + OPA RBAC, conventions.md §9).
- **Supply chain.** Subsystem-model and launch-curve bundles are **signed (Sigstore/cosign)** with
  **SLSA provenance** and an SBOM-equivalent manifest (coefficient lineage, calibration source),
  per conventions.md §9; [Hub](hub.md)/[Core](core.md) verify signatures before load.
- **Validation-as-security.** Strict boundary validation rejects malformed requirements and
  guarantees every emitted SADF re-validates against the Core schema before [Fleet](fleet.md)/
  [Sim](sim.md) ever see it (mirrors core.md §9, [Fleet](fleet.md) §9).
- **Safety.** Sizing produces the **authoritative physical-limit data** (mass/power/thermal floors,
  propellant margins, structural-mass fractions) that downstream [Guard](guard.md) enforces as hard
  constraints; Sizing does not enforce runtime safety, it supplies the budgeted envelopes. A
  *failed closure* is surfaced loudly, never silently coerced into a feasible-looking asset.
- **Export-control / dual-use** (conventions.md §12; [mission-model §4](mission-model.md)). Sizing
  is firmly in the **open commons**: it consumes *descriptive* `ManeuverBudget` Δv (not guidance)
  and produces *vehicle budgets* (not targeting). It does **not** turn a reference trajectory into
  executable maneuver guidance — that crosses the `operational_targeting` line and is partitioned
  out. Propulsion/return capability tags on emitted SADF carry the same export gating
  [Fleet](fleet.md) applies, so sensitive vehicle classes are policy-gated at publish/discovery.

---

## 10. Observability & operability

- **Diagnostics.** The requirements→closure pipeline emits **structured JSON** diagnostics
  (requirement id, subsystem, constraint, margin, residual, fix hint) via standard logging/
  OpenTelemetry (conventions.md §10), so a *non-closure* is precise and actionable — *which* margin
  went negative, by how much (mirrors [Fleet](fleet.md) §10, core.md §10).
- **Metrics.** Sweep services publish Prometheus metrics (conventions.md §10): closure rate, mean
  margins by subsystem, optimizer iterations/convergence, sweep throughput.
- **Tracing.** A Studio trade study is traceable through Sizing's MDO solve (which subsystem loop
  dominated, which constraint was active) alongside the [Trajectory](trajectory.md) leg it consumed
  (conventions.md §10).
- **Testing & validation strategy** (conventions.md §11).
  - **Analytic golden cases:** rocket-equation/staging/MER closures checked against hand-computed
    reference vehicles (`pytest`); **Hypothesis** property-based tests over requirement ranges
    (e.g. monotonicity: more Δv ⇒ ≥ propellant) (conventions.md §11).
  - **External-oracle validation:** sized vehicles cross-checked against published mission
    references / textbook sizing exercises and, where available, against [Sim](sim.md)/Basilisk Δv
    closure (conventions.md §11 physics validation) with explicit error budgets.
  - **Round-trip / instantiation:** every emitted SADF spawns and steps in [Sim](sim.md) in CI,
    catching configs that close on paper but cannot be realized (mirrors [Fleet](fleet.md) §10).
  - **Determinism gates:** same requirement + model set + seed ⇒ identical sized SADF bytes
    (conventions.md §11).
  - **Contract tests:** Sizing proves it honors the Core SADF/mission interface versions it claims
    (consumer-driven contract tests against [Core](core.md), conventions.md §11).

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| MDAO framework | **OpenMDAO**; Dakota (Sandia); custom MDO loop | **OpenMDAO** — NASA-native, charter §7; analytic/coupled derivatives, mature solver+driver ecosystem, Python-native (conventions.md §2). Dakota is a strong gradient-free sampler but is C++-centric and less natural for coupled-derivative SE; reach for it only as an external DOE/UQ driver. A custom loop reinvents the waist. |
| Subsystem-model fidelity | Parametric MERs only; physics-based models only; **tiered MERs + optional physics/[Surrogate](surrogate.md)** | **Tiered: parametric MERs as the default for breadth and speed, with physics-based subsystem models (or [Surrogate](surrogate.md)) selectable per trade where sensitivity demands** — matches multi-fidelity (conventions.md §8) and keeps sweeps interactive |
| Trajectory↔sizing coupling | Sequential (Δv→sizing); **sequential default + fully-coupled MDO for final trades**; always fully coupled | **Sequential Δv→sizing as the default** (consume a fixed `ManeuverBudget`), with **fully-coupled trajectory⇄vehicle MDO available for final co-optimization** in [Studio](studio.md)'s Mission Architect — avoids re-running [Trajectory](trajectory.md) every iteration while still capturing the coupling where it pays off (a low-thrust trade where Δv and vehicle mass are inseparable) |
| Writing sized configs as SADF | New Sizing-private format; annotate Fleet asset in place; **emit a SADF patch against a [Fleet](fleet.md) parametric template** | **Emit a validated SADF patch that parameterizes an existing [Fleet](fleet.md) template** (propulsion/staging/return per [mission-model §2.1](mission-model.md)) — Sizing produces, Fleet holds; no private format, waist stays neutral (conventions.md §1, §3) |
| Reusable-LEO inventory | Fixed assets only; design variables only; **fixed-by-default, optionally promotable to design variables** | **Treat reusable-LEO assets as fixed inventory by default** (Fleet members with an initial in-orbit state, [mission-model §2.1](mission-model.md)), **promotable to MDO design variables** when the trade asks "what *should* we keep in LEO?" — covers both "use what we have" and "design the depot" without two code paths |
| Launch manifesting | Single LV curve; **pluggable mass-to-orbit + fairing-volume curves with multi-launch split** | **Pluggable launch-vehicle data plugins (mass-to-orbit vs. orbit + fairing envelope), with packing/multi-launch split** — new launchers arrive as data, not code (conventions.md §1) |
| Payload packing | Mass-only budgets; **mass + geometric volume packing (OR-Tools CP-SAT)** | **Mass budgets always; geometric fairing/stowage packing via OR-Tools CP-SAT** (charter §7) where volume, not mass, is the binding constraint |

**Open questions / research dependencies:**

- **Coupling depth (charter §9 "durable abstraction"):** exactly which trades justify fully-coupled
  trajectory⇄vehicle MDO over sequential, and how much of that coupling [mission-model](mission-model.md)
  should encode vs. leave to [Studio](studio.md)'s trade engine ([mission-model §6](mission-model.md)).
- **MER calibration for novel regimes:** mass-estimating relationships for asteroid-mining and ISRU
  *plant* hardware are far less established than for conventional spacecraft — calibrate against
  [Sim](sim.md) and published references, flag extrapolation beyond the fitted envelope.
- **ISRU throughput → plant sizing:** the map from mining/throughput requirement to plant mass/power
  is the least-settled subsystem model and couples to the charter's hardest physics
  (granular/excavation, charter §9) — co-design with [Sim](sim.md)/[Surrogate](surrogate.md).
- **Uncertainty propagation:** how to report a closure *probability* (margins-as-distributions)
  through coupled MDO without making every sweep a Monte-Carlo (conventions.md §6).
- **SADF expressiveness for staging/return:** whether the [mission-model §2.1](mission-model.md)
  propulsion/staging blocks fully capture drop-mass bookkeeping across phases, or need a Core RFC.

---

## 12. Roadmap alignment

- **Phase 3 (proposed):** Sizing is part of the multi-regime extension and lands when
  [Trajectory](trajectory.md), [Ledger](ledger.md), and the [mission-model](mission-model.md)
  implementations land (the `MissionSpec`/`ManeuverBudget`/propulsion-SADF *schema hooks* arrive in
  Core during **Phase 1** per [mission-model §3](mission-model.md), ahead of implementation). MVP:
  - the coupled-subsystem MDAO closure for a single vehicle (OpenMDAO + MER subsystem models);
  - rocket-equation/staging math and reusable-LEO inventory accounting;
  - launch manifesting (mass-to-orbit + fairing packing);
  - SADF emit back to a [Fleet](fleet.md) parametric template and mass/cost records to
    [Ledger](ledger.md);
  - **Goal:** given a NEO-mining mission's Δv and throughput requirement, produce a *feasible,
    sized, instantiable* asset set that [Sim](sim.md) flies and [Studio](studio.md) trades.
- **Beyond MVP:** fully-coupled trajectory⇄vehicle co-optimization in Studio's Mission Architect;
  physics-based/[Surrogate](surrogate.md)-backed subsystem fidelity tiers; community-contributed
  subsystem models, MER sets, and launch curves as plugins via [Hub](hub.md). The measure of
  success (mirroring [Fleet](fleet.md)): new subsystem models and launchers arrive as **plugins/
  data**, never as Sizing code changes — and a sized vehicle is always a *valid SADF asset*, never a
  Sizing-private artifact.
