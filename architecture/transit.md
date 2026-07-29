# Astro-Mine-Transit — Technology Architecture

> Status: **Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) — implementation Phase 3.
> Layer: **World & environment models** · Phase: **3** (proposed)
> The deep-space / free-space environment *between* bodies: the n-body dynamical substrate
> and the long-cruise hazard environment (radiation, thermal/eclipse, micrometeoroid) for the
> `interplanetary_transit` regime and body-proximity station-keeping.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Transit` is the **free-space physical environment** — the dynamical and hazard
substrate that exists *between* celestial bodies. Where [Worlds](worlds.md) answers "what is it
like *on* a body," Transit answers "what is it like *in deep space* and in a body's gravitational
neighborhood." It is the environment the `interplanetary_transit` regime (and the free-space half
of `proximity_orbit`) runs in, per [mission-model.md §1.2](mission-model.md).

Transit provides two coupled environment surfaces:

- **The gravitational / dynamical environment** — n-body ephemerides and the **force model** a
  propagator integrates against: point-mass gravity plus perturbations — **solar radiation pressure
  (SRP)**, **third-body** attraction, **non-spherical gravity** (spherical-harmonic near
  planets/moons, **polyhedral/mascon** near small bodies), and relativistic corrections at the
  high-precision tier. It supplies the acceleration field; it does *not* integrate it.
- **The deep-space hazard environment** — survival-relevant fields a long cruise traverses:
  **ionizing-radiation flux and dose** (trapped particles, solar energetic particles, galactic
  cosmic rays), **thermal & eclipse geometry** (solar flux, Sun/body occultation, planetary
  IR/albedo), and **micrometeoroid & debris flux** — the free-space analog of Worlds'
  illumination/thermal fields.

**What it explicitly does NOT do** (the boundaries are load-bearing):

- **No trajectory optimization or maneuver planning.** Transit gives the force model and geometry;
  computing transfers, low-thrust arcs, Δv/ToF budgets, and reference trajectories is
  [Trajectory](trajectory.md) — Transit provides the *environment*, not the *maneuvers*
  ([mission-model.md §2.3](mission-model.md)).
- **No dynamics integration.** Propagating state through the force field is [Sim](sim.md), just as
  Worlds parameterizes gravity but Sim integrates motion (worlds.md §1).
- **No comms link budget.** [Link](link.md) computes antenna gain/SNR/data rate; Transit shares the
  same Sun/Earth/body **geometry** but computes no link budget.
- **No surface terrain, regolith, or resource fields** — that is [Worlds](worlds.md) /
  [Prospect](prospect.md). A small body's *surface* is a Worlds body-pack; its *external gravity
  field and proximity hazard* is Transit.
- **No new transport, schema, or auth machinery** — owned by [Core](core.md), fixed by
  [conventions.md](conventions.md).

**Primary users:** mission/trajectory designers (force-model selection), simulation builders (the
cruise/proximity environment a scenario propagates through), and spacecraft-systems engineers
(radiation/thermal exposure budgets) — indirectly every interplanetary mission.

**Charter alignment:** §5.1 (World & environment models), §7 "Astrodynamics and geometry"
(SPICE/NAIF, Orekit, GMAT, Basilisk; STK/GMAT as oracles), §8 (ultra-long-horizon energy/
thermal-aware planning — here, *survival across a multi-month cruise*), §9 ("a durable abstraction
across orbital, surface, manipulation, ISRU" — Transit is the orbital/free-space half), §11 Phase 3.

---

## 2. Architecture principles

1. **Environment, not maneuvers.** Transit exposes acceleration and hazard fields as pure functions
   of (state, epoch); it never decides *where to go*. The environment ⇄ optimizer split mirrors the
   Worlds ⇄ Sim parameter ⇄ physics split (worlds.md §2.6), drawn at the [Core](core.md) API.
2. **Frames, epochs, and units are explicit and SPICE-backed.** Every state carries an explicit
   inertial/body-centered frame and a **TDB/ET** epoch; every quantity is SI (conventions.md §5,
   core.md §2.8). No implicit J2000 or "now" — the free-space analog of Worlds' mandatory CRS.
3. **No surface, n-body frame context.** Transit implements the **free-space / no-terrain** profile
   of the Environment API ([mission-model.md §2.2](mission-model.md)): observations carry which
   bodies are gravitationally relevant instead of ground geometry.
4. **Fidelity is a dial, not a fork.** Point-mass patched-conic and high-precision ephemeris-backed
   perturbed models are the **same interface at different fidelity levels**, so [Sim](sim.md) trades
   accuracy for speed per task (conventions.md §8).
5. **Standard models in, reproducible fields out.** Force, ephemeris, radiation, and micrometeoroid
   environments come from **authoritative published models and kernels** (SPICE, AE8/AP8-class, GCR,
   micrometeoroid flux), not invented physics — the deep-space mirror of worlds.md §2.1.
6. **Uncertainty is carried.** Ephemeris covariance, force-model truncation error, and hazard models
   are statistical; fluxes and doses ship with confidence bounds (conventions.md §1.6). A single
   dose number is an anti-pattern.
7. **Validate against external oracles.** Propagated states are regression-tested against **GMAT /
   Orekit / Basilisk / STK** for canonical cases with explicit error budgets (conventions.md §11).
8. **Library first, then a plugin-extensible service.** Importable on a workstation (build a force
   model, query dose along an arc) before it is a field service (conventions.md §1.4); a new body's
   gravity field or hazard model is a registry plugin, never a core change (charter §9.2).

---

## 3. Application architecture

Transit is a Python library with native acceleration for the hot force-evaluation and
ray/occultation kernels, plus an optional read-only field/precompute service.

```
astro_mine.transit
├── ephemeris/      # SPICE meta-kernel mgmt; body states, frames, epochs (TDB/ET); SPK/PCK/FK/LSK
├── frames/         # inertial/body-centered frame registry; SPICE frame resolution & transforms
├── force/          # the force-model assembly (the dynamical environment)
│   ├── pointmass/  #   n-body point-mass gravity
│   ├── harmonics/  #   spherical-harmonic non-spherical gravity (planets/moons)
│   ├── smallbody/  #   polyhedral / mascon gravity for irregular small bodies
│   ├── srp/        #   solar radiation pressure (cannonball → flat-plate, with shadow model)
│   ├── thirdbody/  #   third-body perturbations
│   └── relativity/ #   PPN / Schwarzschild corrections (high-precision tier)
├── geometry/       # Sun/Earth/body geometry: eclipse/occultation, phase, ranges (shared w/ Link)
├── hazard/
│   ├── radiation/  #   trapped (AE8/AP8-class), SEP, GCR flux & dose; shielding-depth curves
│   ├── thermal/    #   solar flux, eclipse-driven thermal env, planetary IR/albedo
│   └── debris/     #   micrometeoroid & orbital-debris flux models
├── field/          # precomputed Zarr hazard/environment fields; sampling & interpolation
├── env/            # Core Environment-API free-space provider; force-model + hazard surface
├── service/        # optional gRPC/FastAPI field & precompute service
└── registry/       # Core plugin manifest: body gravity packs, model packs, registration
```

### Key abstractions exposed

- **`TransitEnvSpec`** — the declarative description of a free-space environment: gravitationally
  relevant **bodies** (by SPICE ID), the **central frame**, epoch range, SPICE meta-kernel
  reference, enabled **force models** (with fidelity tier + parameters), and enabled **hazard
  models** (radiation/thermal/debris sources). Authored as **YAML validated by JSON Schema** with a
  canonical Protobuf wire form (conventions.md §3); hashed with its resolved inputs to a
  **content-addressed environment ID** — the free-space analog of Worlds' `WorldSpec`.
- **`ForceModel`** — `acceleration(state, epoch) -> (a_vec, [partials])` in an explicit frame,
  assembled by composition from the enabled force terms; optionally returns the state-transition
  partials (∂a/∂state) that variational propagation and [Trajectory](trajectory.md)'s optimizer
  consume. The **dynamical** surface of the Environment API for the transit regime.
- **`HazardField`** — `flux(state, epoch) -> {radiation, micrometeoroid, …}`, `dose(arc, shielding)
  -> (dose, ci)`, and `thermal_env(state, epoch) -> (solar_flux, eclipse_state, planetary_ir)`. Pure
  environment data with carried uncertainty; the asset-side power/thermal/survival response is
  computed by [Sim](sim.md) from [Fleet](fleet.md) SADF budgets.
- **`GeometryService`** — `occultation`, `eclipse`, `phase_angle`, `range` — the same Sun/Earth/body
  geometry [Link](link.md) needs for free-space visibility, shared rather than duplicated.

### Extension / plugin points

Hosted through the [Core](core.md) registry (conventions.md §1.3): **body gravity packs** (a small
body's polyhedral/mascon field + harmonics, paired with the corresponding Worlds surface body-pack
but shipping the *external field* — "support a new target body" is a package, never a patch);
**force-model packs** (alternative SRP/drag/high-precision dynamics against the same `ForceModel`);
and **hazard-model packs** (alternative radiation/thermal/micrometeoroid sources, selected in
`TransitEnvSpec`).

### Interaction patterns

- **In-process library** (default): assemble a `ForceModel`/`HazardField` and query it directly —
  the path [Sim](sim.md)/[Trajectory](trajectory.md) use when co-located.
- **Read-only field/force service** (cloud tier): gRPC for workers, REST/OpenAPI for tools; serves
  precomputed hazard Zarr fields and on-demand force/geometry evaluation.
- **Batch precompute**: `Argo`/`Ray` jobs compute hazard fields (dose maps over an epoch window,
  GCR/SEP environments), then publish the immutable environment bundle to [Hub](hub.md).

---

## 4. Application programming & runtime platforms

Aligned with conventions.md §2:

- **Language:** **Python 3.12+** for the API, model assembly, ephemeris/frame handling, and
  orchestration (type-hinted, `mypy`/`pyright`). **C++20** (Pybind11) for the **hot inner loop** —
  per-step force evaluation, polyhedral-gravity summation, ray/occultation — that a propagator calls
  millions of times. **Rust** optional for the content-addressed bundle packing/verification tool.
- **Astrodynamics & force models:** ephemerides, frames, epochs (TDB/ET), and Sun/Earth/body geometry
  via the shared **`astro-mine-spice`** foundation ([RFC-0002](../rfc/0002-shared-spice-foundation.md); SpiceyPy/CSPICE under the hood) — the charter §6 standard, the same resolver Worlds and Link use. **Orekit** (py-wrapped)
  and/or **Basilisk** supply validated force models (harmonics, SRP, third-body, drag); **GMAT/STK**
  serve as external verification oracles. Small-body **polyhedral gravity** via an established C++
  kernel; spherical harmonics via a `pyshtools`-class evaluator, mirroring Worlds' gravity stack.
- **Hazard & space-environment models:** standard published radiation models — **AE8/AP8** (and
  successors AE9/AP9) for trapped particles, **SEP** and **GCR** (ISO-15390 / Badhwar–O'Neill-class)
  — and **micrometeoroid/debris flux** models (Grün-class interplanetary flux, NASA MEM-class,
  ORDEM-class near Earth), packaged behind `HazardField` in the **SPENVIS-style** tradition rather
  than reinvented.
- **Numerics & store:** NumPy/SciPy; **Numba**/CuPy where a Python kernel must be fast but not C++.
  **Zarr** (chunked, range-readable) with **xarray** for precomputed hazard fields (conventions.md
  §5); USD/glTF only where a proximity scene is visualized in [View](view.md).
- **Service layer:** **FastAPI** (REST/OpenAPI 3.1) + **gRPC** service-to-service (conventions.md §3,
  §4).
- **Build/packaging:** Python wheel `astro-mine-transit` (Pybind11 native extension, manylinux); OCI
  image for the service; **environment bundles are OCI artifacts** discovered via [Hub](hub.md).
  SemVer on the package; content hashes on bundles (conventions.md §7).

---

## 5. Data architecture

Transit is both a **field producer** (precomputed hazard/dose maps) and an **on-demand evaluator**
(force/geometry), per conventions.md §5.

| Data | Format / store | Notes |
|---|---|---|
| Ephemerides & kernels (SPK/PCK/FK/LSK) | **SPICE kernels** from NAIF, referenced by hash | Consumed, not owned; pinned per bundle |
| Gravity coefficients / polyhedral & mascon models | **Zarr/HDF5** + model files | Harmonic coefficients; small-body shape/mascon models |
| Precomputed hazard fields (dose maps, GCR/SEP/trapped flux, thermal/eclipse) | **Zarr** (chunked); **HDF5** interop | N-D fields consumed by [Sim](sim.md); carry uncertainty companions |
| Force/hazard parameter sets | **JSON/YAML** (Pydantic v2) | Versioned with the bundle |
| Reference/validation arcs (oracle comparisons) | **Parquet** / **MCAP** | GMAT/Orekit/Basilisk states with error budgets |
| `TransitEnvSpec` & bundle manifest | **JSON Schema + Pydantic v2**; Protobuf wire | Owned by Transit; content-addressed |
| Environment bundle (the deliverable) | **OCI artifact**, content-addressed object store (MinIO/S3) | Manifest + kernels-by-ref + force/hazard params + fields |
| Bundle catalog & metadata | **PostgreSQL** | Index of environments, bodies, epoch ranges, model versions |

- **Owned:** `TransitEnvSpec` schema, the bundle manifest, precomputed hazard fields, validation
  arcs. **Consumed:** NAIF SPICE kernels; published gravity, radiation, micrometeoroid model data
  (charter §6).
- **Schemas:** `TransitEnvSpec` and the manifest are JSON Schema + Pydantic v2 (conventions.md §3),
  owned by Transit; the **force-model and hazard surface of the Environment API is a [Core](core.md)-
  owned Protobuf contract** (the free-space profile, [mission-model.md §2.2](mission-model.md)).
  Every field/arc carries explicit **frame, epoch (TDB/ET), and units** — ingest fails loudly on a
  missing/defaulted frame, the free-space analog of Worlds' mandatory-CRS gate (worlds.md §5).
- **Provenance & lifecycle:** every derived field/arc records the SPICE kernel set, model versions,
  code version, lockfile, and seed (conventions.md §5); an environment ID is the hash of its
  `TransitEnvSpec` + resolved inputs. Environments are immutable once published (new version on
  update); SemVer on the package, content hash on the bundle — so a benchmark on "NEO-cruise-env vN"
  is exactly reproducible (conventions.md §1.5).

---

## 6. Integration architecture

Transit plugs in **exclusively through [Core](core.md) contracts** (conventions.md §1.1; no private
side-channels):

- **↔ [Core](core.md).** Implements the **free-space / no-terrain profile of the Environment API**
  ([mission-model.md §2.2](mission-model.md)): observations carry an n-body frame context and hazard
  exposure instead of ground geometry; **`PhaseTransition` handoffs** deliver the terminal cruise
  state as the next phase's initial state. Depends on Core for the manifest/registry, units/frames/
  time conventions, and message schemas.
- **→ [Sim](sim.md) (primary consumer).** Sim **propagates state through Transit's `ForceModel`** and
  reads its `HazardField`/`thermal_env` to evolve power/thermal and survival state across the cruise.
  The split mirrors Worlds↔Sim: *Transit supplies the acceleration and hazard fields; Sim runs the
  integrator and the asset-response constitutive models* against [Fleet](fleet.md) SADF budgets.
  In-process when co-located; gRPC field streaming when sharded.
- **→ [Trajectory](trajectory.md).** Transit is the **force model [Trajectory](trajectory.md)
  optimizes over** — point-mass + perturbations, with state-transition partials for variational and
  low-thrust optimization. Trajectory produces `TrajectoryRef`/`ManeuverBudget` *design-time*
  artifacts ([mission-model.md §2.3, §4](mission-model.md)); Transit produces none, only the dynamics
  they are computed against.
- **↔ [Link](link.md).** Transit and Link **share Sun/Earth/body geometry** (occultation, range,
  phase) for the free-space regime via the same `GeometryService`, so eclipse/occultation is computed
  once. Link adds the link budget; Transit adds none.
- **→ [Fleet](fleet.md) / [Sim](sim.md).** Transit's radiation/thermal/micrometeoroid exposure fields
  inform survival modeling against the **SADF power/thermal budgets and shielding** declared in Fleet
  (mission-model.md §2.1); Sim joins exposure to asset response.
- **→ [Worlds](worlds.md).** Complementary, never overlapping: Worlds owns *on-body* surface and
  near-surface; Transit owns *free-space and external proximity*. A small-body Worlds surface
  body-pack and a Transit gravity pack are co-published for the same target and share the body
  frame/SPICE ID.
- **→ [Hub](hub.md) / [Cloud](cloud.md) / [Bench](bench.md).** Environment bundles are published and
  discovered as content-addressed OCI artifacts via [Hub](hub.md) (charter §5); heavy ephemeris/
  hazard precompute (dose maps, GCR/SEP fields, long reference arcs) runs as `Argo`/`Ray` batch on
  [Cloud](cloud.md); [Bench](bench.md) pins an environment + Core interface version per scenario for
  exactly reproducible leaderboard results (conventions.md §1.5).

**Transport:** gRPC for service-to-service force/geometry/field reads; REST/OpenAPI at the edge;
NATS/JetStream events on precompute/publish completion. High-rate per-step force evaluation is
**in-process native** (not message-passed); precomputed hazard fields stream via chunked Zarr range
reads (conventions.md §8).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — `pip install astro-mine-transit`; assemble a force model, query dose along an
     arc on a workstation. *This tier MUST work* (charter §12).
  2. **Cloud** — the stateless field/force service on **Kubernetes** reading immutable bundles from
     S3-compatible storage; **Argo Workflows**/**Ray** on [Cloud](cloud.md) for batch precompute.
  3. **Operations/ground** — read-only force/geometry queries for [Ops](ops.md)/[View](view.md)
     cruise monitoring; no real-time control role.
- **Compute profile:** *force evaluation* is CPU-bound and latency-critical — the native per-step
  kernel sits in Sim's/Trajectory's tightest loop, co-located in-process, vectorized over a state
  ensemble. *Hazard precompute* is embarrassingly parallel (dose/flux integration over epoch windows
  and shielding depths) and fans out across [Cloud](cloud.md), GPU optional for polyhedral-gravity
  grids. The *field service* is light, stateless, and scales out behind a load balancer.
- **Containerization & scaling:** OCI images with the **pinned SPICE/Orekit/Basilisk toolchain** (a
  deliberate, scanned supply-chain surface, as with Worlds' GDAL/PROJ/SPICE); environments are
  partitioned by **target body / epoch window / fidelity tier**, so precompute and serving fan out
  naturally and immutable content-addressed bundles cache cleanly.

---

## 8. Performance & scalability

- **Targets (indicative):** evaluate a perturbed n-body force model fast enough to propagate a
  multi-month cruise interactively on a workstation; return a hazard dose along a reference arc in
  well under a second; precompute a NEO-cruise hazard field within a single batch job; serve
  force/geometry queries to a Sim ensemble at scheduler rates.
- **Bottlenecks & mitigations:**
  - *Per-step force evaluation* (the dominant cost) — **native C++/Pybind11 kernel**, **vectorized
    ensemble evaluation**, and a **fidelity dial** (patched-conic fast → perturbed n-body validation)
    so the [Sim](sim.md) scheduler buys only the accuracy a task needs (conventions.md §8).
  - *Polyhedral/mascon small-body gravity* — **precomputed harmonic/interpolated field** outside the
    body's resonance region, the exact polyhedral model only in close proximity.
  - *Hazard dose integration* — precompute **dose-vs-shielding curves and flux fields** over the
    epoch/region window once and interpolate at query time (the Worlds thermal-precompute pattern).
  - *SPICE kernel I/O* — pinned, pre-staged kernels; reuse one kernel pool across an ensemble.
- **Multi-fidelity & uncertainty:** both the force model (patched-conic → perturbed n-body →
  high-precision) and the hazard model (climatological mean → time-resolved SEP events) expose a
  fidelity dial chosen per task (conventions.md §8); force-model partials support variational
  covariance propagation and hazard fields carry confidence bounds, so survival margins are honest
  (conventions.md §1.6).

---

## 9. Security, safety & compliance

- **AuthN/Z, isolation, supply chain:** OIDC + RBAC via **OPA** and service-to-service **mTLS** on
  the service; body gravity/force/hazard plugins are untrusted code, loaded via the Core registry,
  run in-process only when signed/trusted else **out-of-process (gRPC + sandboxed container,
  seccomp/gVisor)**, forward path WASM; signed bundles/images (**Sigstore/cosign**), **SLSA**
  provenance, **SBOM** (Syft/CycloneDX), with the pinned **SPICE/Orekit/Basilisk** toolchain as a
  deliberate, scanned dependency surface (conventions.md §7, §9).
- **Export control / dual-use:** Transit publishes **published ephemerides and standard
  space-environment models** — open science, squarely in the commons (charter §11, conventions.md
  §12). **The dual-use line is at [Trajectory](trajectory.md), not here** ([mission-model.md
  §4](mission-model.md)): Transit provides the *force model and environment*, not *executable maneuver
  guidance* or *operational targeting*, and deliberately exposes **no closed-loop guidance and no
  atmospheric-EDL** capability. The `operational_targeting` tag gates anything crossing that line
  downstream at the registry/[Bridge](bridge.md) boundary, so Transit carries a **low-risk EAR/ITAR
  posture** — yet still honors capability tags so an unusually sensitive model (e.g. a restricted
  high-precision gravity field) can be partitioned via the standard mechanism.
- **Safety:** not on a real-time control path, but the **radiation dose, thermal/eclipse, and force
  fields it produces feed safety-relevant survival decisions** (radiation budget, eclipse power
  survival, station-keeping margins) in [Guard](guard.md)/[Sim](sim.md). Correctness is therefore a
  first-class safety concern: validated frames/epochs, carried ephemeris/model uncertainty, and
  golden-test regression against external oracles.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** in the service — traces across assemble → precompute → publish and
  across a force/field read; metrics (force-eval latency, field cache hit rate, precompute duration);
  structured JSON logs to **Loki**; **Prometheus + Grafana** dashboards (conventions.md §10). Standard
  liveness/readiness; per-service SLOs.
- **Testing & validation:** `pytest` + **Hypothesis** property tests (frame round-trips, force
  superposition, energy/momentum invariants of conservative terms); **physics validation** of
  propagated states against **GMAT / Orekit / Basilisk / STK** for canonical transfers and perturbed
  cases with explicit error budgets, geometry against NAIF reference cases, and radiation/
  micrometeoroid outputs against **SPENVIS-style reference cases** (conventions.md §11, charter §6);
  **determinism gates** (same `TransitEnvSpec` + pinned kernels/toolchain ⇒ same environment hash and
  propagated arc; CI fails otherwise); **contract tests** proving the claimed [Core](core.md)
  free-space Environment-API version; and a **frame/epoch sanity gate** — every field/arc must carry a
  valid frame, epoch (TDB/ET), and SI units before publish, a hard CI failure otherwise.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Force-model fidelity tier** | Point-mass patched-conic; perturbed n-body (point-mass + SRP/third-body/harmonics); high-precision ephemeris-backed (+ relativity, full perturbations) | **All three behind one `ForceModel` interface as a fidelity dial** — patched-conic for fast/interactive design, **perturbed n-body as the default** working tier, high-precision for validation; the Sim scheduler selects per task (conventions.md §8). |
| **Force-model engine** | Roll-our-own; **Orekit**; **Basilisk**; mix | **Wrap Orekit/Basilisk validated force models behind the Core surface**; native C++ kernel only for the hottest path and small-body polyhedral gravity (charter §6 "reinvent as little as possible"); **GMAT/STK as oracles**. |
| **Small-body gravity** | Point-mass; spherical harmonics; **polyhedral**; mascon | **Polyhedral (exact) in close proximity + harmonic/interpolated field farther out** — the proximity analog of Worlds' "polyhedral via body packs" (worlds.md §11), shipped as gravity packs. |
| **Radiation/hazard source** | Build from first principles; **standard published models (AE8/AP8, AE9/AP9, GCR, SEP)**; couple SPENVIS-class libraries | **Standard published models behind `HazardField`** (AE8/AP8 → AE9/AP9 trapped; ISO-15390/Badhwar–O'Neill GCR; SEP event models), SPENVIS-style, swappable as model packs. Never invented. |
| **Micrometeoroid/debris model** | None; interplanetary flux (Grün-class); NASA **MEM**-class; ORDEM near Earth | **Grün/MEM-class interplanetary flux as default; ORDEM-class near Earth** — as hazard-model packs with carried uncertainty. |
| **Where hazard modeling lives** | All in Sim; all in Worlds; **environment fields in Transit, asset response in Sim** | **Transit owns the free-space *exposure fields*; [Sim](sim.md) computes the asset *response*** against [Fleet](fleet.md) SADF shielding/thermal — mirroring Worlds(fields)↔Sim(physics). Worlds keeps *on-surface*; Transit keeps *free-space*. |
| **Environment representation** | Analytic/on-demand (SPICE + live force/hazard eval); precomputed Zarr fields; **hybrid** | **Hybrid (recommended): on-demand force & geometry evaluation** (cheap, and must be exact for propagation) **+ precomputed Zarr hazard fields** (expensive integrals reused across many queries) — the same on-demand-vs-precompute split Worlds draws for ray-cast vs horizon maps (worlds.md §11). |
| **Eclipse/occultation geometry** | Duplicate in Transit and Link; **shared `GeometryService`** | **Single shared geometry service** with [Link](link.md) — compute Sun/Earth/body occultation once (conventions.md §1.1). |

**Open questions / research dependencies:**

- **Force-partials contract.** How much variational/state-transition partials structure belongs in the
  Core force-model surface vs. internal to [Trajectory](trajectory.md)? Co-design so the optimizer gets
  gradients without leaking optimization into the environment (mission-model.md §6).
- **Hazard fidelity for survival planning.** How time-resolved must the radiation environment be
  (climatological mean vs. modeled SEP events) for ultra-long-horizon survival planning to be honest
  (charter §7)? Resolve with [Guard](guard.md)/[Sim](sim.md) against reference cruises.
- **Proximity-regime boundary with Worlds.** For `proximity_orbit`, where does the Transit external
  field hand off to a Worlds small-body surface near-field? Co-design the pairing and shared frame
  (mission-model.md §1.2).
- **Hazard-field uncertainty representation.** What stable, validated uncertainty form do
  radiation/micrometeoroid fields carry into Sim/Guard (conventions.md §1.6)?
- **Surrogate force/hazard models.** Could a learned surrogate replace expensive polyhedral gravity or
  dose integration at ensemble scale, with tracked error? Co-design with [Surrogate](surrogate.md).

---

## 12. Roadmap alignment

- **Phase 1 (schema hooks only).** No Transit implementation yet; the **free-space Environment-API
  profile, `regime` descriptor, and `PhaseTransition` handoff land in Core** as additive schema hooks
  ([mission-model.md §3](mission-model.md)), so the waist is multi-regime-ready before the
  implementation exists — avoiding the retrofit-into-a-frozen-waist failure the charter warns of (§9).
- **Phase 3 (proposed) — MVP.** Transit ships with [Trajectory](trajectory.md)/[Sizing](sizing.md)/
  [Ledger](ledger.md) and the mission model for the **first interplanetary reference scenario** (e.g.
  a NEO water/volatiles prospecting cruise, charter §10 Phase 3): SPICE-backed heliocentric/
  body-centered frames; a **perturbed n-body force model** (point-mass + SRP + third-body +
  harmonics) behind the Core free-space surface with patched-conic and high-precision tiers,
  validated against GMAT/Orekit/Basilisk; **small-body gravity packs** (polyhedral + harmonic) paired
  with a Worlds surface body-pack; a **deep-space hazard environment** (radiation dose
  trapped/SEP/GCR, thermal/eclipse, micrometeoroid flux) as precomputed Zarr fields with carried
  uncertainty, consumable by [Sim](sim.md); and the `TransitEnvSpec` schema + content-addressed
  bundle publishable to [Hub](hub.md). Goal: a designer can propagate/score an interplanetary baseline.
- **Phase 3+ — ecosystem.** New target bodies (asteroids, icy-moon systems), richer time-resolved SEP
  modeling, finer micrometeoroid environments, and learned force/hazard surrogates arrive purely as
  community **packs** — "support a new transit environment" stays a package, never a Transit core change
  (charter §9.2, §10).
