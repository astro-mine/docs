# Astro-Mine-Link — Technology Architecture

> Layer: **World & environment models** · Phase: **0–1** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> The communications environment: models *when* and *where* agents can talk to each other and
> to Earth — the constraint that makes coordination hard.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Link` is the **communications environment model**. Given a body, a terrain, an epoch
window, and a set of placed assets (surface agents, relay orbiters, Earth ground stations), it
computes the **time-varying connectivity** among them: which links are geometrically possible,
when they open and close, and — for each open link — the achievable latency and bandwidth from a
link budget. Its outputs are consumed both as a *simulation model* (so [Sim](sim.md) propagates
realistic message delivery) and as *planning constraints* (so [Allocate](allocate.md),
[Mind](mind.md), and [Ops](ops.md) can reason about contact windows and delay).

Concretely, Link:

- resolves **line-of-sight (LOS)** and **terrain occlusion** between every relevant pair of
  nodes, using ephemerides/frames from SPICE and horizon/elevation data from [Worlds](worlds.md);
- computes **relay-orbiter constellation geometry** and **Earth ground-station contact windows**
  (DSN, ESTRACK, or user-defined antennas) over an epoch range;
- runs a **link budget** per candidate link (antenna gains, path loss, pointing, system noise →
  SNR/Eb/N0 → achievable data rate, modeled against a coding/modulation table);
- emits **time-series connectivity products** — contact intervals, latency, and bandwidth — and a
  derived **contact graph** suitable for delay-tolerant routing;
- contributes **communication observation masks** to the [Core](core.md) Environment API so a
  policy literally cannot observe or message a peer that is currently unreachable.

**Deep-space comms (RFC-0001).** Under [RFC-0001](../rfc/0001-multi-regime-missions.md), Link's
scope extends from cislunar to **deep space** for the `interplanetary_transit` and `proximity_orbit`
regimes ([mission-model](mission-model.md) §1.2). The same machinery — geometry-first visibility,
parametric link budgets, store-and-forward delivery — applies, but with three regime-driven
shifts: **DSN contact scheduling** with sparse Earth-link windows; **light-time delay of minutes
to tens of minutes** (vs. the Moon's ~1.3 s one-way), which dominates latency and drives the
delay-tolerant autonomy posture; and **occultation by small / irregular bodies**, which shares its
geometry with [Transit](transit.md). This is an additive Phase-3 extension — the lunar model is
the degenerate near-Earth case and is unchanged.

**Explicitly out of scope.** Link is *not* a network stack and not a flight radio. It does **not**
implement an actual DTN agent that ships bundles in production (it *models* store-and-forward
behavior and supplies the contact plan an external DTN would use); it does **not** do RF
electromagnetic propagation/ray-tracing at the field level (it uses parametric link budgets, not a
full-wave or geometric-optics RF solver); it does **not** own terrain or ephemerides (it *consumes*
them from [Worlds](worlds.md) and SPICE); and it does **not** route application traffic at runtime
inside [Ops](ops.md) (that is the responsibility of the ops/bridge data plane — Link supplies the
constraint model the router and planners obey).

**Primary users:** comms and operations engineers; secondarily, autonomy/planning researchers who
need realistic connectivity constraints, and scenario authors building comms-denied benchmarks.

**Charter alignment:** §5.1 (the Link package definition — "models when and where agents can talk
to each other and to Earth, the constraint that makes coordination hard"); §8 ("scalable
cooperative multi-agent learning under partial observability and intermittent, delayed
communications"; "delay-tolerant supervisory autonomy"); §9 ("robust coordination under
intermittent comms and partial observability"). Link is the package that makes those problems
*concrete and reproducible* rather than hand-waved.

---

## 2. Architecture principles

1. **Geometry is the ground truth; RF is a layer on top.** Visibility is decided first from
   exact SPICE geometry and Worlds occlusion; link quality (rate/latency) is computed *only* for
   geometrically open links. The two concerns are cleanly separated so either can be dialed in
   fidelity independently.
2. **Borrow ephemerides and terrain; never re-derive them.** Frames, epochs, body orientation,
   and orbits come from SPICE/NAIF through the shared **[`astro-mine-spice`](spice.md)** foundation
   (`astro_mine.spice`, [RFC-0002](../rfc/0002-shared-spice-foundation.md)); horizons and elevation
   come from [Worlds](worlds.md), consumed through the Core `WorldProvider` contract. Link depends on
   neither a private SPICE adapter nor the `astro-mine-worlds` package — it adds only the
   *communications* interpretation, consistent with conventions.md §1.7 ("interop, don't reinvent")
   and the SPICE-backed frame/time mandate in §5.
3. **Time-varying by construction.** Connectivity is a function of epoch, not a static graph. The
   first-class product is an interval/time-series over an explicit epoch window, from which
   boolean snapshots are derived — never the other way around.
4. **Uncertainty is first-class.** Link budgets carry margins and confidence (link availability
   under fading/pointing error), and contact predictions carry the ephemeris/terrain provenance
   they depend on, per conventions.md §1.6.
5. **Constraints, not opinions.** Link reports *what is physically possible*; it never decides how
   a planner should trade comms against productivity. Planners ([Allocate](allocate.md),
   [Mind](mind.md)) consume the constraints; Link stays mechanism, not policy.
6. **Precompute when geometry is deterministic; query on demand otherwise.** For a fixed scenario
   (fixed orbits, fixed asset placement) connectivity is precomputable and cacheable
   content-addressed; for design loops with moving/parametric assets, an on-demand visibility
   query path is provided. Both serve the same products.
7. **Multi-fidelity dial.** A single Link configuration selects fidelity per query — geometric
   visibility only → parametric link budget → (optional, later) packet-level network simulation —
   honoring conventions.md §8 ("multi-fidelity everywhere").
8. **Determinism and reproducibility.** Same SPICE kernels + same terrain + same epoch window +
   same config ⇒ identical connectivity products (conventions.md §1.5). Kernel sets and DEM
   versions are pinned and hashed into provenance.
9. **Degrade, don't lie.** When inputs are missing (no kernel coverage, no DEM tile), Link fails
   loudly at the boundary rather than silently assuming full connectivity — a missing constraint
   that defaults "open" would corrupt every downstream coordination result.

---

## 3. Application architecture

Link is delivered **library-first** (importable, single-workstation usable per conventions.md
§1.4) with an optional gRPC service wrapper for cloud precompute. Internal modules:

```
astro_mine.link
├── geometry/        # LOS + occlusion: SPICE visibility, terrain horizon raycasting
│   ├── visibility.py    # node-pair LOS over epoch ranges (SPICE gfposc/gftfov style)
│   ├── occlusion.py     # terrain/horizon masking from Worlds DEM/horizon maps
│   └── frames.py        # frame/epoch helpers (thin wrapper over astro_mine.spice + Core units/frames)
├── constellation/   # relay-orbiter geometry, ground-station station-keeping geometry
│   ├── orbiters.py      # relay constellation contact geometry, multi-hop reachability
│   └── ground.py        # Earth ground-station (DSN/ESTRACK/custom) contact windows
├── budget/          # RF link budget → data rate / latency
│   ├── linkbudget.py    # gain, path loss, pointing, noise → SNR/Eb-N0 → rate
│   ├── modcod.py        # modulation/coding tables (CCSDS-ish), rate vs required Eb/N0
│   └── propagation.py   # latency model (light-time + queueing/turnaround terms)
├── network/         # connectivity products + DTN/contact-graph modeling
│   ├── contactplan.py   # contact intervals, contact graph (CGR-style), schedule export
│   ├── dtn.py           # abstract store-and-forward delivery model (Bundle Protocol concepts)
│   └── masks.py         # per-agent comms observation masks for the Core Environment API
├── products/        # serialization: time-series, contact plans, masks (Zarr/Parquet/MCAP)
├── service/         # optional gRPC server + REST/OpenAPI edge for precompute jobs
└── registry/        # Core plugin manifest: declares Link as an environment-model plugin
```

### Key abstractions exposed

- **`LinkScenario`** — the immutable inputs: body + frame, SPICE kernel set (hashed), terrain/
  horizon source from [Worlds](worlds.md), node set (surface assets, relay orbiters, ground
  stations) with antenna/radio parameters from SADF, epoch window, and fidelity config.
- **`ContactPlan`** — the central product: per node-pair, an ordered set of **contact intervals**
  `(start, end, max_rate, min_latency, mean_latency, margin, confidence)`, plus a derived
  **contact graph** for routing. Round-trips to/from a serialized form.
- **`ConnectivitySampler`** — `connectivity(epoch) -> {pair: (reachable, rate, latency)}`; the
  on-demand interface [Sim](sim.md) calls each tick (or each macro-step) without re-deriving the
  whole plan.
- **`CommsObservationMask`** — per-agent, per-epoch boolean (and rate/latency-weighted) mask
  fed through the [Core](core.md) Environment API so observation/message channels respect comms.
- **`DeliveryModel`** — given the contact plan and a message (size, priority, source→dest), returns
  modeled delivery time (or non-delivery) under store-and-forward — the abstract DTN behavior.

### Key abstractions consumed

- **SPICE/NAIF** via the shared **[`astro-mine-spice`](spice.md)** foundation (`astro_mine.spice`,
  [RFC-0002](../rfc/0002-shared-spice-foundation.md)), which realizes [Core](core.md)'s `units`/`frames`
  vocabulary (conventions.md §5): SPK ephemerides, PCK body orientation, FK/IK frames, CK pointing
  where available (SpiceyPy in Python; CSPICE in native paths). Link drives `astro_mine.spice` for
  body-fixed positions and may run `spiceypy` geometry-finder routines (`gfposc`/`gftfov`) *on top of*
  those shared primitives for its own window search (LINK-02).
- **Terrain occlusion** via the Core **`WorldProvider`** contract (`core.world`): `ray_intersect` /
  horizon-map `line_of_sight` over [Worlds](worlds.md) DEMs (Cloud-Optimized GeoTIFF via GDAL) in an
  explicit body-fixed CRS. Link consumes an **injected** provider through the contract; it does **not**
  import or depend on the `astro-mine-worlds` package (no edge→edge side-channel, conventions.md §1.1).
- **[Fleet](fleet.md)/SADF**: each node's comms capability block — antenna gain pattern, EIRP,
  G/T, frequency band, supported mod/cod, pointing capability — read from the [Core](core.md)
  SADF schema. Relay orbiters and ground stations may themselves be SADF assets.

**Deep-space extension (RFC-0001).** For the `interplanetary_transit`/`proximity_orbit` regimes,
the same modules apply with a regime-aware reach: `constellation/ground.py` schedules **DSN passes**
into sparse Earth-link windows; `budget/propagation.py` computes **light-time of minutes to tens of
minutes** from heliocentric/free-space geometry rather than the lunar ~1.3 s; `geometry/occlusion.py`
adds **small/irregular-body occultation** (shared geometry with [Transit](transit.md)); and
`network/dtn.py`'s store-and-forward becomes load-bearing over the intermittent, long-delay links.
Free-space frame context for these regimes comes from [Transit](transit.md) (no terrain), alongside
[Worlds](worlds.md) for the body itself; per-phase regime selection follows
[mission-model](mission-model.md) §1.

### Extension / plugin points

Per conventions.md §1.3, Link is itself a **Core environment-model plugin** (declared in its
manifest) and is internally pluggable on three axes: (a) **occlusion backends** (SPICE DSK ray
test vs Worlds horizon-map lookup vs analytic spherical-body); (b) **link-budget models**
(parametric default vs an ITU-/CCSDS-aligned table vs a future ns-3 bridge); (c) **delivery
models** (instantaneous-when-connected vs abstract store-and-forward vs Bundle-Protocol-fidelity).
New ground-station networks, antenna patterns, and mod/cod tables are data, not code.

### Interaction patterns

In design/training, callers construct a `LinkScenario`, request a `ContactPlan` (precomputed,
cached, content-addressed), and hand a `ConnectivitySampler` to [Sim](sim.md). In operations,
[Ops](ops.md) requests Earth-link windows and per-link latency/bandwidth as a live schedule that
its planners and the supervisory console consume. Heavy precompute runs as a gRPC/Argo job in the
cloud tier; interactive queries run in-process.

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.11+** for the public API, orchestration, and the parametric models
  (conventions.md §2). The hot occlusion/visibility kernels (per-tick raycasting over horizon maps
  for hundreds of node-pairs) are the candidate for a **C++20** core via Pybind11, or vectorized
  NumPy/Numba first and promoted only if profiling demands it ("measure before optimizing",
  conventions.md §8).
- **Geometry/astrodynamics:** SPICE/NAIF accessed through the shared **`astro-mine-spice`**
  foundation (`astro_mine.spice`; SpiceyPy/CSPICE under the hood) for ephemerides, frames, and
  body-fixed positions; Link layers its **SPICE geometry-finder** window search (`gfposc`, `gftfov`,
  occultation/visibility solvers) on top of those primitives (LINK-02). **Astropy** for
  unit/coordinate convenience where SPICE is overkill. Optional **Skyfield** as a cross-check oracle
  for ground-station passes.
- **Terrain:** **GDAL/rasterio** to read Worlds COG DEMs and horizon products (conventions.md §5).
- **Link budget:** implemented in NumPy against a CCSDS-aligned mod/cod table; no external RF
  dependency in the default path. Optional **ns-3** bridge (out-of-process) for packet-level
  fidelity (see §11).
- **Config & schemas:** **JSON Schema + Pydantic v2** for `LinkScenario`/config; **Protobuf**
  for the `ContactPlan`/`CommsObservationMask` wire types in the Core message catalog
  (conventions.md §3).
- **Runtime model:** importable library by default; optional **FastAPI** REST edge +
  **gRPC** service for cloud precompute (conventions.md §3, §4). Stateless service; products land
  in object storage.
- **Build/packaging:** Python wheel `astro-mine-link` (import `astro_mine.link`); OCI image for
  the service; SemVer; depends on a pinned `astro-mine-core` interface major version **and on
  `astro-mine-spice`** for SPICE resolution (conventions.md §7, §13). Native kernels ship as manylinux
  wheels with bundled CSPICE.

---

## 5. Data architecture

| Data | Direction | Format / store | Notes |
|---|---|---|---|
| SPICE kernels (SPK/PCK/FK/CK/LSK) | consumed | NAIF kernel files; meta-kernel pinned & hashed | Frames/epochs per conventions.md §5; coverage validated up front |
| Terrain DEMs / horizon maps | consumed | **COG** (GDAL) / **Zarr** horizon cubes from [Worlds](worlds.md) | Explicit body-fixed CRS; no implicit WGS84 (conventions.md §5) |
| Node comms capabilities | consumed | **SADF** (YAML/JSON + proto) from [Fleet](fleet.md)/[Core](core.md) | Antenna, EIRP, G/T, band, mod/cod, pointing |
| Contact plan / connectivity time-series | **produced** | **Apache Parquet** (intervals/tabular) + **Zarr** (dense per-tick rate/latency cubes) | Range-readable so Sim streams only needed slices (conventions.md §5, §8) |
| Contact graph | **produced** | Protobuf message + Parquet edge table | CGR-style for routing/planning |
| Comms observation masks | **produced** | **Protobuf** message (Core catalog); dense form in Zarr | Fed via Core Environment API |
| Modeled comms event traces (sim/ops replays) | **produced** | **MCAP** | Timestamped, schema-tagged channels (conventions.md §4) |
| Mod/cod & ground-station catalogs | owned (config) | YAML/JSON tables, content-addressed | DSN/ESTRACK/custom antennas; CCSDS mod/cod |

**Schemas.** The `ContactPlan`, contact-graph, and `CommsObservationMask` message types live in
the [Core](core.md) message catalog (Link proposes them via RFC; conventions.md §3). The
`LinkScenario`/config schema is owned by Link (JSON Schema + Pydantic).

**Lifecycle & provenance.** Connectivity products are **content-addressed** keyed on the hash of
{kernel meta-kernel, DEM/horizon version, node set + SADF radios, epoch window, fidelity config,
Link version}. A cache hit returns the exact prior plan; this is what makes a comms-denied
benchmark reproducible (conventions.md §1.5, §5). Products record producing code version,
environment lockfile, and seed (none needed for deterministic geometry, recorded if a stochastic
fading model is enabled).

**Versioning.** Link declares the Core interface major versions it supports; products carry the
Link SemVer and Core schema versions they were produced against (conventions.md §13).

**Deep-space data (RFC-0001).** No new product types are needed: deep-space contact plans, DSN
window catalogs, and **DTN / Bundle-Protocol** store-and-forward delivery use the existing
`ContactPlan`, contact-graph, and ground-station-catalog formats above. Products gain a `regime`
tag (per the [Core](core.md) Environment-API `regime` descriptor, [mission-model](mission-model.md)
§2.2) so consumers can distinguish a near-Earth (~1.3 s) plan from a minutes-to-tens-of-minutes
light-time deep-space plan, and the content-address key extends to cover the active regime.

---

## 6. Integration architecture

Link sits in the **World & environment** layer and integrates exclusively through
[Core](core.md) contracts (conventions.md §1.1 — no private side-channels):

- **Consumes** terrain occlusion (DEMs/horizon maps in an explicit planetary CRS) through the Core
  **`WorldProvider`** contract — an injected [Worlds](worlds.md) provider, **not** a dependency on the
  `astro-mine-worlds` package. **Consumes** SPICE ephemerides/frames through the shared
  **[`astro-mine-spice`](spice.md)** foundation (`astro_mine.spice`, [RFC-0002](../rfc/0002-shared-spice-foundation.md)),
  which realizes Core's `units`/`frames` vocabulary (conventions.md §5). **Consumes** node comms
  capabilities from [Fleet](fleet.md) SADF (relay orbiters and ground stations may be SADF assets
  themselves).
- **Provides** the comms model to [Sim](sim.md): a `ConnectivitySampler` and `DeliveryModel` so
  per-tick message delivery, latency, and bandwidth reflect real geometry. Link is registered as an
  **environment-model plugin** and contributes **comms observation masks** through the
  [Core](core.md) **Environment API** (the masks declared in core.md §3 — "explicit
  comms/observation masks"), so PettingZoo/Gymnasium views see partial observability for free.
- **Provides** contact-window, latency, and bandwidth **constraints** to [Allocate](allocate.md)
  (so task scheduling respects when an agent can receive an assignment or report a result) and to
  [Mind](mind.md) (so hierarchical planning reasons about comms blackouts). These are delivered as
  the **contact graph** and the latency/bandwidth time-series — both representations, see §11.
- **Provides** **Earth-link windows** and downlink/uplink latency to [Ops](ops.md) for
  operations scheduling and the delay-tolerant supervisory console (charter §8). [Ops](ops.md)/
  [Bridge](bridge.md) own the *actual* data plane (ROS 2/DDS, conventions.md §4); Link supplies the
  constraint model they obey, not the transport.
- **Bench/Hub:** [Bench](bench.md) pins a Link version + kernel/DEM set per comms-denied scenario;
  contact-plan products are shareable [Hub](hub.md) artifacts (content-addressed).

**Message flow (design loop):** Worlds DEM + SPICE → Link precompute → `ContactPlan` (object
store) → `ConnectivitySampler`/masks → Sim rollouts → Allocate/Mind consume constraints. **Service
contracts** are gRPC; the edge precompute API is REST/OpenAPI (conventions.md §3–4). Async
precompute jobs ride **NATS/JetStream** for lifecycle events (conventions.md §4).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — pure library; a researcher loads kernels + a DEM and computes a contact plan
     for one scenario on a laptop. This tier MUST always work.
  2. **Cloud** — the gRPC precompute service on **Kubernetes**; large epoch-window /
     many-node sweeps fan out via **Ray** or **Argo Workflows** (DAG of per-pair visibility jobs).
  3. **Operations/ground** — Link runs alongside [Ops](ops.md), recomputing forward-looking
     contact schedules as orbits/ephemerides update; products feed the ops planners and console.
- **Compute:** **CPU-bound**, not GPU. Geometry and link budgets are arithmetic and raycasts. A
  precompute worker is right-sized at a few vCPU and a few GB RAM; memory scales with epoch
  resolution × node-pairs. GPU is unnecessary except in a future ns-3/large-raster occlusion path.
- **Containerization:** OCI image with pinned CSPICE + GDAL; multi-arch. SPICE kernels and DEMs are
  mounted/streamed from the **S3-compatible object store** (MinIO/S3/GCS), not baked into images
  (conventions.md §5, §7).
- **Orchestration & scaling:** embarrassingly parallel across node-pairs and epoch chunks. The
  precompute service is stateless; state (plans) lives in object storage and a Postgres catalog.
  Caching is content-addressed so repeated scenarios are near-free.

---

## 8. Performance & scalability

- **Targets.** Compute a full contact plan for a reference lunar polar scenario — ~10²–10³ surface
  nodes + a small relay constellation + DSN, over a multi-day epoch window at ≤1 min resolution —
  in minutes on a single cloud worker, and serve a per-tick `connectivity(epoch)` query in
  sub-millisecond from a cached/indexed plan so it never bottlenecks [Sim](sim.md).
- **Bottlenecks.** (1) **Pairwise blow-up** — node-pair connectivity is O(N²) per epoch; (2)
  **terrain occlusion raycasting** against DEMs is the per-query hot spot; (3) **SPICE window
  searches** over long epoch ranges; (4) serializing dense latency/bandwidth cubes.
- **Mitigations.** Spatial/temporal pruning (skip pairs beyond max-range or below horizon a
  priori); **precompute horizon maps once in [Worlds](worlds.md)** and reduce occlusion to a cheap
  azimuth/elevation table lookup; vectorize budget math over pairs; chunk epoch windows for
  parallel Ray/Argo workers; cache content-addressed plans so design iterations reuse geometry that
  did not change. Hot kernels promotable to C++/Pybind11 only if profiling shows need
  (conventions.md §8).
- **Scaling strategy.** Horizontal over {node-pair partition × epoch chunk}; range-readable Zarr/
  Parquet so [Sim](sim.md) workers stream only the slices they need (conventions.md §8). The
  per-tick sampler is read-only against an indexed plan — bounded, back-pressure-free.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** the precompute service authenticates via OIDC and authorizes via RBAC/OPA;
  service-to-service is mTLS (conventions.md §9). The library path inherits the host's posture.
- **Supply chain:** signed OCI artifacts (Sigstore/cosign), SBOM, SLSA provenance
  (conventions.md §9). **SPICE kernels and DEMs are inputs with provenance**: their source and hash
  are recorded, and kernel coverage is validated before use — a wrong or truncated kernel silently
  changing visibility is a correctness-and-trust hazard, not just a bug.
- **Safety relevance.** Link is not a safety-enforcing component, but its outputs feed safety- and
  mission-critical decisions: a comms blackout window that Link reports incorrectly could cause a
  planner to assume an unsendable abort command will arrive. Therefore Link follows the
  **degrade-loudly** principle (§2.9): missing/partial inputs raise at the boundary;
  connectivity is never silently defaulted to "available." [Guard](guard.md) and [Ops](ops.md)
  treat Link windows as advisory constraints and keep independent floors.
- **Export control / dual use** (conventions.md §12, charter §10.5). Generic communications
  geometry, link budgets, and DTN modeling for *science/simulation* are firmly in the open commons.
  The sensitive edge is operational: precise, real-asset ground-station contact scheduling and
  high-fidelity link prediction tied to a live mission can become operational targeting/availability
  intelligence. Link tags such capabilities (e.g., "live-mission-link-prediction") via the Core
  capability vocabulary so they can be OPA-gated, and keeps any classified/restricted antenna or
  kernel data out of the open repo per `astro-mine/.github` EXPORT_CONTROL.md. The default open path
  uses public ephemerides and generic/parametric antenna models.

---

## 10. Observability & operability

- **Telemetry:** OpenTelemetry traces/metrics/logs in the service (conventions.md §10); a precompute
  job is traceable end-to-end, and a downstream replan in [Ops](ops.md) traces back through the Link
  query that produced its windows. Structured JSON logs aggregated with Loki; Prometheus/Grafana
  dashboards (plan compute time, cache hit-rate, pairs evaluated, window counts).
- **Diagnostics:** every connectivity product embeds the provenance block (kernel/DEM/config
  hashes) so a surprising "no contact" result is debuggable from the artifact alone.
- **Testing & validation** (conventions.md §11):
  - **Golden/determinism gates** — seeded/pinned scenarios compared to stored contact plans; CI
    fails on drift (the hard reproducibility requirement).
  - **External oracles** — ground-station pass times and orbiter visibility cross-checked against
    **GMAT/STK** and **Skyfield**; analytic spherical-body LOS cases checked in closed form.
  - **Property-based tests (Hypothesis)** — symmetry of LOS, monotonicity of rate with SNR,
    interval non-overlap invariants, light-time ≤ modeled latency.
  - **Link-budget regression** — against worked CCSDS examples within an explicit error budget.
  - **Contract tests** — Link proves it honors the Core Environment-API and message versions it
    claims (consumer-driven contract tests against [Core](core.md)).

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Visibility / geometry engine** | Hand-rolled vector math; **SPICE GF** (geometry finder); Orekit events | **SPICE GF via SpiceyPy** for frames/epochs/windows (charter §7); analytic fallback for spherical bodies; GMAT/STK/Skyfield as test oracles |
| **Terrain occlusion** | On-the-fly DEM raycast (DSK/COG); **precomputed horizon maps** from Worlds; analytic spherical horizon | **Precomputed horizon maps from [Worlds](worlds.md)** (cheap az/el lookup) + DSK/COG raycast fallback for fine geometry |
| **Link-budget fidelity** | Geometric visibility only; **parametric RF link budget** (gain/path-loss/SNR→rate); ns-3 packet-level sim | **Parametric link budget by default**; visibility-only as a fast mode; **ns-3 bridge as an optional later plugin** for packet-level studies |
| **DTN modeling depth** | Instantaneous-when-connected; **abstract store-and-forward** (contact-graph delivery); full **Bundle Protocol** fidelity | **Abstract store-and-forward over a CGR-style contact graph** in Phase 0–1; Bundle-Protocol-fidelity plugin later if a benchmark needs it |
| **Constraint representation to planners** | Boolean contact graph; continuous bandwidth/latency time-series; both | **Both** — contact graph for combinatorial [Allocate](allocate.md)/[Mind](mind.md), continuous latency/bandwidth cube for fidelity-sensitive consumers and [Sim](sim.md) |
| **Precompute vs on-demand** | Always precompute; always on-demand; hybrid | **Hybrid** — precompute + content-addressed cache for fixed scenarios; on-demand `ConnectivitySampler` for moving/parametric design loops |
| **Hot-kernel implementation** | Pure Python; **NumPy/Numba vectorized**; C++/Pybind11 | **NumPy/Numba first**; promote occlusion/visibility to **C++20/Pybind11** only if profiling demands (conventions.md §8) |
| **Ground-station catalog** | DSN-only; **DSN + ESTRACK + user-defined**; none | **DSN + ESTRACK + user-defined antennas** as content-addressed YAML catalogs |

**Open questions / research dependencies:**

- **Mask semantics in the Environment API.** Exact representation of comms observation masks for
  multi-agent, partially-observable, variable-timestep envs — co-designed with [Core](core.md) and
  [Sim](sim.md) (mirrors the open boundary in core.md §11).
- **DTN fidelity vs planner tractability.** How much store-and-forward realism planners can
  actually exploit before the contact graph becomes intractable for [Allocate](allocate.md) —
  resolved empirically against [Bench](bench.md) scenarios.
- **RF fidelity ceiling.** Whether parametric link budgets are sufficient for credible sim-to-real
  comms claims, or whether selected scenarios warrant the ns-3 bridge — tied to charter §8/§9.
- **Fading/availability uncertainty model.** How to express link availability under pointing error
  and (Mars) atmospheric/dust effects as first-class uncertainty (conventions.md §1.6).

**Deep-space comms (RFC-0001).** For deep space, the recommended choices above carry over with
regime tuning: **SPICE GF** handles small/irregular-body occultation (shared with
[Transit](transit.md)); the **parametric link budget** spans DSN ranges; and the **abstract
store-and-forward over a CGR-style contact graph** is the right default for **DTN / Bundle Protocol**
over intermittent, long-delay links, with the optional **Bundle-Protocol-fidelity** plugin reserved
for deep-space benchmarks where minutes-to-tens-of-minutes light-time makes delivery-time realism
load-bearing. The much larger latency drives the **delay-tolerant autonomy posture** that
[Ops](ops.md)/Guard consume; Link supplies the windows and modeled delivery times, not the policy.

---

## 12. Roadmap alignment

- **Phase 0 (MVP).** Geometric **LOS + terrain occlusion** (SPICE + Worlds horizon maps),
  **relay-orbiter and DSN contact windows**, a **parametric link budget** for rate/latency, and
  **contact-plan + comms-observation-mask** products wired through the [Core](core.md) Environment
  API into [Sim](sim.md). This is exactly enough to make the anchor **lunar polar water-ice
  prospecting** benchmark *comms-denied for real* — surface agents in/near PSRs losing line-of-sight
  and Earth contact — which is the property that makes the charter's coordination problems (§8, §9)
  reproducible. Determinism + content-addressed caching from day one.
- **Phase 1.** Richer **constellation geometry** and multi-hop reachability; **contact-graph /
  CGR** delivery model and the abstract store-and-forward `DeliveryModel`; full latency/bandwidth
  time-series for [Allocate](allocate.md)/[Mind](mind.md); **Earth-link windows** delivered to
  [Ops](ops.md) for delay-tolerant supervisory autonomy; ground-station catalog beyond DSN.
- **Later (Phase 2–3).** Optional **ns-3 packet-level** fidelity plugin and **Bundle-Protocol**
  fidelity; Mars atmospheric/dust link effects; live-mission link prediction (capability-gated per
  §9) for [Ops](ops.md) once operations cross to Earth analogs and beyond.
- **Phase 3 — deep-space comms (RFC-0001).** DSN contact scheduling with sparse Earth-link windows,
  minutes-to-tens-of-minutes light-time, **DTN / Bundle Protocol** store-and-forward, and
  small/irregular-body occultation for the `interplanetary_transit`/`proximity_orbit` regimes
  (consuming [Transit](transit.md), feeding the delay-tolerant posture in [Ops](ops.md)/Guard). The
  enabling **Core Environment-API `regime` hooks are reserved in Phase 1** ([mission-model](mission-model.md)
  §3), implementation in Phase 3; the lunar model stays the unchanged near-Earth default.
