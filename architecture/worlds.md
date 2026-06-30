# Astro-Mine-Worlds — Technology Architecture

> Layer: **World & environment models** · Phase: **0** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> Turns real mission data into simulatable celestial-body worlds — the physical
> substrate (terrain, gravity, illumination, thermal, regolith, dust) on which every
> scenario runs.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Worlds` builds **parameterized celestial-body environments** from real planetary
data and exposes them as the physical substrate every scenario runs on. A "world" is a
selectable, configurable, versioned bundle describing a *place* — e.g. the Shackleton crater
rim — at a chosen region, resolution, and epoch. Worlds provides:

- **Terrain** ingested from real Digital Elevation Models (LOLA, MOLA, HiRISE-derived DTMs) plus
  derived layers (slope, aspect, roughness, hillshade);
- **Gravity** (point-mass + spherical-harmonic field models, e.g. GRGM/GGM-class) and the
  body-fixed/inertial **frames, time, and Sun/Earth geometry** via SPICE/NAIF;
- **Illumination & shadowing** — solar incidence, horizon-limited line-of-sight to the Sun,
  and explicit detection of **permanently shadowed regions (PSRs)**;
- a **surface thermal model** driven by illumination, slope/aspect, and regolith thermophysics;
- **regolith / terramechanics parameter fields** (bulk density, cohesion, friction angle,
  bearing, thermal inertia) as *inputs* consumed by [Sim](sim.md);
- a **dust environment model** (mobilization/adhesion parameters, optical loading);
- **level-of-detail tiling** (heightfield tiles + 3D Tiles) for streaming to [View](view.md).

**What it explicitly does NOT do.** Worlds is a *data and field-model* component, not a
physics engine and not a resource model:

- **No dynamics integration.** Worlds *parameterizes* gravity and terramechanics; it does not
  propagate orbits or simulate wheel/soil contact — that is [Sim](sim.md).
- **No resource fields.** What is *in* the ground (water ice, mineral grade) belongs to
  [Prospect](prospect.md); Worlds only provides the spatial substrate Prospect georeferences
  against.
- **No comms modelling.** [Link](link.md) computes line-of-sight/relay geometry; Worlds only
  supplies the terrain horizon/occlusion service it queries.
- **No rendering.** Worlds emits geometry tiles; [View](view.md) renders them.
- **No new transport, schema, or auth machinery** — those are owned by [Core](core.md) and
  fixed by [conventions.md](conventions.md).

**Small & irregular bodies (RFC-0001).** [RFC-0001](../rfc/0001-multi-regime-missions.md)
generalizes a single-world campaign into a [Mission](mission-model.md) of phases across regimes;
Worlds is extended to model the *body* end of that — small / irregular bodies (asteroids, NEOs,
small moons) for the `surface` and `proximity_orbit` regimes. Worlds remains strictly "on/at a
body" (surface and near-surface/proximity); the **free-space interplanetary medium between bodies
is [Transit](transit.md)**, a separate environment component — Worlds is *not* stretched to
represent free space. Small-body support replaces three Phase-0 simplifications: full 3-D shape
models in place of ~2.5-D heightfields, irregular non-central gravity in place of a constant
central field, and cohesion-dominated **microgravity regolith** parameters. As ever, Worlds owns
the spatial parameter fields; [Sim](sim.md) owns the constitutive/contact physics (including the
new microgravity-contact regime). This lands in Phase 3 (see §12).

**Primary users:** planetary scientists (curate/validate worlds from PDS data) and simulation
builders (select and configure a world for a scenario). Indirectly, *every* component, because
every scenario stands on a world.

**Charter alignment:** §5.1 (Worlds component), §7 "Planetary data" (GDAL ingest of USGS
Astrogeology / PDS — LOLA, MOLA, HiRISE) and "Astrodynamics and geometry" (SPICE/NAIF),
§8 (sim-to-real for terramechanics; decision-making under deep uncertainty), §11 Phase 0
(ships with Core/Sim/Fleet/Bench for the lunar-polar reference scenario), §13 (anchor scenario:
lunar polar water-ice prospecting in comms-denied PSRs).

---

## 2. Architecture principles

1. **Real data in, simulatable world out.** The job is to convert authoritative planetary
   datasets (PDS/USGS) into reproducible, georeferenced field models — not to invent terrain.
   Synthetic/procedural worlds are a clearly-flagged secondary mode, never the default.
2. **Planetary CRS is mandatory, Earth assumptions are forbidden.** Every spatial value carries
   an explicit body-fixed frame, datum (reference radius/geoid), and projection, resolved via
   SPICE + PROJ. No implicit WGS84 (conventions.md §5). A `+R=...` planetary projection string
   is part of every layer's metadata.
3. **A world is a versioned, content-addressed bundle.** Same inputs ⇒ same world hash. Worlds
   are reproducible artifacts (conventions.md §1.5, §5 provenance), distributable via
   [Hub](hub.md), so a benchmark on "Shackleton v3" is exactly reproducible.
4. **Time- and geometry-explicit.** Illumination, thermal, and Sun/Earth geometry are functions
   of epoch (TDB/ET). A world references an SPICE meta-kernel; queries take an epoch. Nothing
   is silently "noon."
5. **Cloud-native, range-readable, chunked.** Terrain and field layers are COG/Zarr so a sim
   worker streams only the tiles/chunks it touches (conventions.md §5, §8). Worlds must serve a
   1 km² patch at full resolution without materializing the whole DEM.
6. **Parameters here, physics there.** Worlds exposes *terramechanics and thermal parameter
   fields*; the constitutive models that consume them live in [Sim](sim.md). The boundary is the
   [Core](core.md) Environment API, not a private channel.
7. **Multi-fidelity by construction.** Every world ships an LOD pyramid; illumination and thermal
   have a fidelity dial (precomputed coarse → on-demand fine). Consumers pick fidelity per task
   (conventions.md §8).
8. **Uncertainty is carried, not erased.** DEM vertical error, interpolation/void-fill flags,
   and regolith-parameter priors travel with the data as companion layers, so downstream
   sim-to-real claims can be honest (charter §8, §12).
9. **Library first, service second.** Worlds is importable on a workstation (open a world, query
   a tile, evaluate illumination) before it is a tile/field service (conventions.md §1.4).

---

## 3. Application architecture

Worlds is a Python library with native acceleration for the heavy geometric kernels
(horizon/ray-cast illumination), plus an optional read-only field/tile service.

```
astro_mine.worlds
├── ingest/         # PDS/USGS fetch, GDAL warp/reproject, void-fill, COG/Zarr writers
│   ├── pds/        #   PDS4/PDS3 + USGS Astrogeology source adapters
│   └── stac/       #   STAC catalog build/query for source & derived datasets
├── crs/            # planetary CRS/frame/datum registry; PROJ + SPICE frame resolution
├── ephemeris/      # SPICE meta-kernel mgmt; Sun/Earth geometry, body frames, epochs
├── terrain/        # DEM model: heightfield + (optional) mesh/SDF; derived layers; LOD
├── gravity/        # point-mass + spherical-harmonic gravity field evaluation
├── illumination/   # horizon maps, ray-cast/GPU shadowing, solar incidence, PSR detection
├── thermal/        # surface thermal model (1-D thermophysical), thermal-inertia fields
├── regolith/       # terramechanics + dust parameter fields (Sim inputs)
├── world/          # WorldSpec: composes layers; resolves config; versions/hashes the bundle
├── tiles/          # 3D Tiles / heightfield tiling for View; LOD pyramid generation
├── api/            # Core Environment-API world provider; gRPC/FastAPI field+tile service
└── registry/       # Core plugin manifest: body/world-pack registration & discovery
```

### Key abstractions exposed

- **`WorldSpec`** — the declarative description of a world: body, region (CRS-tagged bounding
  geometry), source datasets (by STAC item + content hash), resolution/LOD, epoch range, and
  the enabled field models (illumination/thermal/regolith/dust) with their parameters. Authored
  as **YAML validated by JSON Schema** (conventions.md §3), with a canonical Protobuf wire form.
  A `WorldSpec` plus its resolved inputs hashes to a content-addressed world ID.
- **World provider for the Environment API** — Worlds implements the [Core](core.md) Environment
  API's *world/terrain* surface: given a position + epoch, return ground elevation/normal,
  surface frame, local gravity vector, illumination state, surface temperature, and the regolith
  parameter tuple at that point. This is the contract [Sim](sim.md) consumes.
- **`IlluminationModel`** — `sun_visibility(point, epoch) -> (lit | penumbra | shadow, solar_flux)`
  and `psr_mask(region, epoch_window) -> raster`. Backed by horizon maps and/or ray casting.
- **`TerrainModel`** — `sample(xy) -> (z, normal, slope, aspect)`; `ray_intersect(origin, dir)`
  for line-of-sight (the service [Link](link.md) queries for occlusion); tile/mesh export.
- **`RegolithField`** — `params(xy) -> {bulk_density, cohesion, friction_angle, bearing,
  thermal_inertia, …}` with companion uncertainty. Pure data; constitutive law lives in Sim.

### Extension / plugin points

Worlds is itself a host of plugins discovered through the [Core](core.md) registry
(conventions.md §1.3):

- **Body packs** — a new celestial body (Mars, Enceladus, an asteroid) is a plugin contributing
  its frames, gravity model, reference radius/geoid, and default thermophysics. "Support a new
  world" means writing a package, never patching Worlds (charter §10.2). Under
  [RFC-0001](../rfc/0001-multi-regime-missions.md), **small-body gravity packs** (polyhedral /
  mascon, with a harmonic far-field) are additional registry content that pairs with the surface
  body-pack — the same plugin mechanism, now carrying a 3-D shape model, a non-central gravity
  representation, and a body rotation/tumbling state alongside the surface fields.
- **Source adapters** — new dataset providers/instruments under `ingest/`.
- **Field models** — alternative illumination, thermal, or dust implementations registered
  against the same abstract interface and selected in `WorldSpec`.

### Interaction patterns

- **In-process library** (default tier): open a `WorldSpec`, query terrain/illumination/regolith
  directly — the path [Sim](sim.md) uses when co-located with the world.
- **Read-only field/tile service** (cloud tier): gRPC for sim workers (streaming tile/field
  reads), REST/OpenAPI + 3D-Tiles HTTP for [View](view.md), STAC API for catalog browse.
- **Batch precompute**: `Argo`/`Ray` jobs build LOD pyramids, horizon maps, and PSR masks once,
  then publish the immutable world bundle to [Hub](hub.md).

---

## 4. Application programming & runtime platforms

Aligned with conventions.md §2:

- **Language:** **Python 3.11+** for ingest, CRS/ephemeris, orchestration, and the public API
  (type-hinted, `mypy`/`pyright`). **C++20** (Pybind11) for the hot geometric kernels —
  horizon/ray-cast illumination and mesh/tile generation. **CUDA** for the GPU illumination
  path. **Rust** is optional for the content-addressed world-bundle packing/verification tool.
- **Geospatial stack:** **GDAL/rasterio** (warp, reproject, COG I/O), **PROJ** (planetary
  projections), **Zarr** (chunked N-D field layers) with **xarray** for labelled access,
  **rio-tiler/titiler** for dynamic tiling, **pystac/stac-fastapi** for cataloging,
  **shapely/geopandas** for region geometry.
- **Astrodynamics & geometry:** **SpiceyPy** (CSPICE bindings) for ephemerides, body-fixed
  frames, epochs (TDB/ET), and Sun/Earth geometry — the charter's §7 standard.
- **Numerics:** NumPy/SciPy; **Numba**/CuPy where a Python kernel must be fast but not C++.
  Spherical-harmonic gravity via an established library (e.g. `pyshtools`-style evaluation).
- **Geometry/tiles:** USD and glTF for mesh interchange (conventions.md §3); **3D Tiles** output
  for [View](view.md)'s Cesium renderer (charter §7).
- **Service layer:** **FastAPI** (REST/OpenAPI 3.1, STAC API) + **gRPC** for service-to-service
  (conventions.md §3, §4). Recorded provenance via standard tooling.
- **Runtime model:** importable library first; the service is a stateless deployment of the same
  library reading immutable bundles from object storage (conventions.md §1.4, §8).
- **Build/packaging:** Python wheel `astro-mine-worlds` (Pybind11 native extension, manylinux);
  OCI image for the service; **world bundles are OCI artifacts** in the registry, discovered via
  [Hub](hub.md) (conventions.md §7). SemVer for the package; content hashes for bundles.

---

## 5. Data architecture

Worlds is one of the platform's principal **data producers** (conventions.md §5).

| Data | Format / store | Notes |
|---|---|---|
| Source DEMs / rasters (LOLA, MOLA, HiRISE) | **COG** via **GDAL**, cataloged with **STAC** | Reprojected to the body CRS on ingest; originals referenced by content hash |
| Derived terrain layers (slope, aspect, roughness, hillshade) | **COG** | Computed from the DEM; tagged with producing code version |
| Field models (illumination, thermal, gravity, regolith, dust) | **Zarr** (chunked, range-readable); **HDF5** for interop | The N-D physical fields consumed by [Sim](sim.md)/[Prospect](prospect.md) |
| Horizon maps / PSR masks | **Zarr** + **COG** | Precomputed per body region; PSR mask is epoch-window-derived |
| Terrain tiles for View | **3D Tiles** (glTF tilesets) + quantized-mesh/heightfield | LOD pyramid; served over HTTP |
| World bundle (the deliverable) | **OCI artifact**, **content-addressed** object store (MinIO/S3) | Manifest + STAC catalog + layers; the distributable unit |
| World/source catalog & metadata | **PostgreSQL + PostGIS** | Spatial index of worlds, regions, datasets; backs the STAC API |

- **Owned:** `WorldSpec` schema; the world-bundle manifest; derived terrain/illumination/thermal/
  regolith/dust layers; horizon maps and PSR masks; 3D-Tiles tilesets.
- **Consumed:** PDS4/PDS3 + USGS Astrogeology datasets (charter §7); SPICE kernels (SPK/PCK/FK/
  LSK) from NAIF; gravity-field coefficient sets. For small bodies (RFC-0001): published 3-D
  **shape models** and small-body **gravity packs** (polyhedral/mascon + harmonic far-field) plus
  rotation/tumbling state, carried as body-pack registry content (§3).
- **Schemas:** `WorldSpec` and the world manifest are **JSON Schema + Pydantic v2**
  (conventions.md §3), versioned and owned by Worlds; the Environment-API world surface is a
  [Core](core.md)-owned Protobuf contract. Every layer carries explicit CRS, datum, units, and
  epoch metadata.
- **CRS/frames/time:** body-fixed frames, datum, and projection resolved via **SPICE + PROJ**;
  epochs in **TDB/ET** (conventions.md §5). The CRS is a first-class, validated field — ingest
  fails loudly on a missing or Earth-defaulted CRS.
- **Provenance:** every derived artifact records source content hashes, producing code version,
  environment lockfile, SPICE kernel set, and any seed (conventions.md §5). A world ID is the
  hash of its `WorldSpec` + resolved inputs.
- **Lifecycle & versioning:** worlds are immutable once published; updates produce a new
  content-addressed version. Source rasters keep COG overviews; field Zarr arrays keep a
  consolidated metadata index. SemVer on the package, content hash on the bundle.

---

## 6. Integration architecture

Worlds plugs into the platform exclusively through [Core](core.md) contracts
(conventions.md §1.1, no private side-channels):

- **→ [Sim](sim.md) (primary consumer).** Worlds implements the **[Core](core.md) Environment
  API** world/terrain surface: Sim queries ground geometry, surface frame, local gravity,
  illumination/solar flux, surface temperature, and the **regolith terramechanics parameter
  tuple** per point/epoch. The split is deliberate: *Worlds supplies the parameter fields; Sim
  runs the wheel/soil and contact constitutive models that consume them.* In-process when
  co-located; gRPC field streaming when sharded.
- **→ [Prospect](prospect.md).** Worlds is the **spatial substrate** Prospect's resource fields
  are georeferenced against (same CRS, same grid). Prospect adds *what is in the ground*; Worlds
  owns *where the ground is and what it is like*.
- **→ [Link](link.md).** Worlds exposes the **terrain occlusion / line-of-sight** service
  (`ray_intersect`, horizon maps) that Link uses to compute inter-agent and Earth-link
  visibility — the same horizon machinery that drives PSR detection. Link consumes this through the
  Core **`WorldProvider`** contract (`core.world`), not a direct dependency on Worlds; the SPICE
  ephemeris half of Link's geometry comes from [Spice](spice.md), not from here ([RFC-0002](../rfc/0002-shared-spice-foundation.md)).
- **→ [View](view.md).** Worlds streams **3D Tiles** (LOD terrain) and raster overlays to View's
  Cesium/3D-Tiles renderer over HTTP.
- **↔ [Core](core.md).** Worlds depends on `astro-mine-core` for the Environment-API contract,
  the plugin manifest/registry, units/frames/time conventions, and message schemas; body/world
  packs register via the Core manifest.
- **← [Spice](spice.md).** Worlds resolves SPICE-backed frames, epochs, and Sun/Earth geometry
  through the shared **`astro-mine-spice`** foundation (`astro_mine.spice`,
  [RFC-0002](../rfc/0002-shared-spice-foundation.md)) instead of embedding its own SPICE adapter — the
  illumination/PSR machinery (RM-P0-WORLDS-03) drives `sun_geometry`/`body_geometry` from it, and
  `worlds.crs` re-imports the body reference radius (`MOON_RADIUS_M`) from there. This replaces the
  former in-package `astro_mine.worlds.spice` module (extracted on acceptance of RFC-0002).
- **→ [Hub](hub.md).** World bundles are published, versioned, and discovered as content-addressed
  OCI artifacts via Hub (charter §6, §10.3).
- **→ [Bench](bench.md).** Bench pins a specific world version (and Core interface version) per
  scenario so leaderboard results are exactly reproducible (conventions.md §1.5).

**Message flows / transport:** gRPC for service-to-service field/tile reads; REST/OpenAPI +
STAC API + 3D-Tiles HTTP at the edge; NATS/JetStream events on ingest/publish completion
(conventions.md §4). High-rate per-tick field reads use the chunked Zarr/COG path rather than
message passing — workers stream the slices they need (conventions.md §8).

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — `pip install astro-mine-worlds`; open a small world bundle and query it on a
     workstation. *This tier MUST work* (clone-and-run-in-an-afternoon, charter §13).
  2. **Cloud** — the stateless field/tile + STAC service on **Kubernetes**, reading immutable
     bundles from S3-compatible storage; **Argo Workflows**/**Ray** for batch precompute
     (LOD pyramids, horizon maps, PSR masks, thermal time-series).
- **Compute profile:**
  - **Ingest/precompute (CPU-heavy):** GDAL warp/reproject and thermal time-stepping are
    CPU/IO-bound; scale horizontally across regions/tiles. Generous RAM for large DEM windows;
    fast local scratch for COG/Zarr writes.
  - **Illumination (GPU-accelerated):** horizon/ray-cast shadowing over large regions and long
    epoch windows is the GPU workload; a single GPU node precomputes horizon maps and PSR masks,
    or serves on-demand fine illumination. CPU fallback for small/local use.
  - **Field/tile service (light):** stateless, memory-light, scales out behind a load balancer;
    state lives in object storage + PostGIS.
- **Containerization & orchestration:** OCI images, pinned bases (with the pinned GDAL/PROJ/SPICE
  toolchain — a notable supply-chain surface); **NVIDIA GPU Operator** (MIG sharing) for the
  illumination service; horizontal pod autoscaling on the read service.
- **Scaling:** worlds are partitioned by **region and LOD tile**, so both precompute and serving
  fan out naturally. Object storage + CDN-friendly COG/3D-Tiles handle read scale.

---

## 8. Performance & scalability

- **Targets (Phase-0 indicative):** open a world and serve a full-resolution ~1 km² terrain
  patch in well under a second on a workstation; per-point Environment-API queries (elevation,
  normal, illumination, regolith tuple) at interactive rates for an in-process Sim loop;
  precompute a Shackleton-region horizon map / PSR mask within a single batch job; tile a region
  to 3D Tiles fast enough that [View](view.md) streams smoothly.
- **Bottlenecks & mitigations:**
  - *Illumination over large regions/long epoch windows* — the dominant cost. Mitigate with
    **precomputed horizon maps** (per-azimuth horizon elevation) so per-epoch sun visibility is
    an O(1) lookup, and **GPU ray casting** for the fine on-demand path. PSR masks are computed
    once over an epoch window and cached.
  - *DEM I/O at scale* — mitigated by COG overviews + Zarr chunking and range reads, so workers
    fetch only touched tiles (conventions.md §8).
  - *Per-tick field sampling in tight sim loops* — co-locate Worlds in-process with Sim and use
    tile-local caches; fall back to streaming gRPC only when sharded.
  - *Thermal time-series* — precompute representative diurnal/seasonal curves per terrain class;
    interpolate at query time rather than integrating live.
- **Multi-fidelity:** LOD pyramids for terrain; coarse precomputed vs fine on-demand illumination
  and thermal — the fidelity dial consumers choose per task (conventions.md §8).
- **Scaling strategy:** horizontal across regions/tiles for precompute; stateless read service
  behind a load balancer; immutable content-addressed bundles cache cleanly.

---

## 9. Security, safety & compliance

- **AuthN/Z:** the field/tile/STAC service uses platform OIDC + RBAC via **OPA**
  (conventions.md §9); service-to-service **mTLS**. Most world data is open commons; private/
  embargoed source datasets are gated by policy.
- **Isolation:** body packs and field-model plugins are untrusted code — loaded via the Core
  registry and run in-process only when signed/trusted; otherwise **out-of-process (gRPC +
  sandboxed container, seccomp/gVisor)**, the forward path toward WASM (conventions.md §7, §9).
- **Supply chain:** signed bundles and images (**Sigstore/cosign**), **SLSA** provenance,
  **SBOM** (Syft/CycloneDX). The pinned **GDAL/PROJ/SPICE** native toolchain is a deliberate,
  scanned dependency surface (conventions.md §9).
- **Export control / dual-use:** publicly released PDS/USGS planetary terrain and standard SPICE
  kernels are **open science** — squarely in the open commons (charter §12, conventions.md §12).
  Worlds carries **no operational targeting capability**, so its EAR/ITAR posture is low-risk;
  the dual-use partition lives downstream in [Bridge](bridge.md)/[Ops](ops.md). Worlds still
  honors capability tags so an unusually sensitive dataset can be partitioned via the standard
  mechanism.
- **Safety:** Worlds is not on a real-time control path, but the **PSR mask, illumination, and
  slope/bearing fields it produces feed safety-relevant decisions** (energy survival, keep-out,
  trafficability) in [Guard](guard.md)/[Allocate](allocate.md). Therefore data correctness is a
  first-class safety concern: validated CRS/datum, carried vertical/parameter uncertainty, and
  golden-test regression against published illumination/PSR references.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** in the service — traces across ingest → reproject → precompute
  → publish, and across a field/tile read; metrics (query latency, tile cache hit rate, precompute
  job duration, GPU utilization); structured JSON logs to **Loki**; **Prometheus + Grafana**
  dashboards (conventions.md §10). Standard liveness/readiness; per-service SLOs.
- **Testing & validation:**
  - **Unit/integration:** `pytest`; **Hypothesis** property tests for CRS round-trips, frame
    transforms, and tiling invariants (e.g. reproject-then-inverse is identity within tolerance).
  - **Geometric validation:** SPICE-backed Sun/Earth geometry checked against NAIF reference
    cases; horizon/illumination/PSR results regression-tested against **published lunar
    illumination and PSR datasets** (e.g. LOLA-derived PSR catalogs) with explicit error budgets
    (conventions.md §11).
  - **Determinism gates:** the same `WorldSpec` + pinned toolchain + kernels must produce the
    same world hash; CI fails on non-reproducibility (conventions.md §11, §1.5).
  - **Contract tests:** consumer-driven tests prove Worlds honors the [Core](core.md)
    Environment-API version it claims (conventions.md §11).
  - **Geospatial sanity CI:** every ingested layer is asserted to carry a valid planetary CRS,
    datum, and units before publish — an Earth/WGS84 default is a hard CI failure.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Terrain representation** | Heightfield/raster grid (DEM); triangle mesh; implicit/SDF | **Heightfield grid as the canonical form** (matches DEM source, COG/Zarr-native, cheap LOD); generate **triangle/3D-Tiles meshes** for View and **local mesh patches** for contact-rich Sim regions on demand. SDF only as an optional accelerator for ray queries. **Small / irregular bodies (RFC-0001) break the heightfield assumption** — they require a full 3-D closed-surface shape model (mesh/SDF), not a 2.5-D DEM, carried by the small-body pack. |
| **Illumination / shadowing** | Precomputed per-azimuth horizon maps; on-demand CPU ray casting; GPU shadow rendering/ray casting | **Precomputed horizon maps as the default** (O(1) per-epoch sun visibility, drives PSR masks) **+ GPU ray casting for the fine on-demand path**; CPU ray casting as the portable fallback. |
| **Regolith / terramechanics split** | All terramechanics in Worlds; all in Sim; **parameter fields here, constitutive models in Sim** | **Parameter fields in Worlds, constitutive models in [Sim](sim.md)** — Worlds owns the spatial *what-it-is-like* data; Sim owns the *how-it-behaves* physics, joined at the Core Environment API. |
| **CRS / frame handling** | Roll-our-own planetary CRS; **PROJ planetary CRS + SPICE frames**; GDAL defaults | **PROJ (planetary `+R`/geoid) for projections + SPICE for body-fixed/inertial frames, epochs, and Sun/Earth geometry**; explicit CRS on every layer (conventions.md §5). |
| **Field-layer store** | Zarr; HDF5; NetCDF; GeoTIFF only | **Zarr (cloud-native, chunked) primary; COG for 2-D rasters; HDF5 for interop** (conventions.md §5). |
| **Terrain tiles for View** | 3D Tiles (Cesium); quantized-mesh; custom | **3D Tiles** (+ quantized-mesh/heightfield), matching [View](view.md)'s Cesium renderer (charter §7). |
| **Thermal model fidelity** | Static map; 1-D thermophysical (per-class precomputed); full 3-D FEM | **1-D thermophysical model, precomputed per terrain class** and interpolated; full 3-D deferred — out of Phase-0 scope. |
| **Gravity model** | Point-mass only; **point-mass + spherical harmonics**; polyhedral (small bodies) | **Point-mass + spherical harmonics** for the Moon/Mars; **polyhedral / mascon** added via small-body packs (RFC-0001, Phase 3) for irregular non-central fields, with a harmonic far-field. |
| **Ingest cataloging** | Ad-hoc paths; **STAC**; custom DB only | **STAC** for both source and derived datasets, backed by PostGIS (conventions.md §5). |

**Open questions / research dependencies:**

- **Regolith parameterization taxonomy** — which terramechanics parameters, in which units, with
  what uncertainty representation, form the stable Worlds→Sim tuple? Co-design with
  [Sim](sim.md); ties to charter §8 (sim-to-real for planetary terramechanics).
- **PSR-mask epoch semantics** — "permanently" shadowed is defined over an epoch window; what
  standard window and tolerance does Bench fix for the reference scenario? Resolve with
  [Bench](bench.md).
- **Illumination penumbra fidelity** — sharp horizon vs finite-solar-disk soft shadows; how much
  penumbra fidelity does energy-survival planning ([Guard](guard.md)/[Allocate](allocate.md))
  actually need?
- **DEM void-fill & uncertainty** — standard void-fill and how DEM vertical error propagates into
  illumination/PSR/trafficability uncertainty (charter §8, §12).
- **Surrogate illumination** — could a learned surrogate replace ray casting for very large
  swarm-scale queries, with tracked error? Co-design with [Surrogate](surrogate.md).
- **Microgravity regolith taxonomy (RFC-0001)** — which cohesion-dominated parameters (and
  body rotation/tumbling state) form the stable small-body Worlds→[Sim](sim.md) tuple for the
  microgravity-contact regime, distinct from the gravity-dominated lunar/Martian set? Co-design
  with Sim; the boundary with the free-space medium is [Transit](transit.md).

---

## 12. Roadmap alignment

- **Phase 0 (now) — MVP.** Worlds ships with [Core](core.md)/[Sim](sim.md)/[Fleet](fleet.md)/
  [Bench](bench.md) for the **lunar polar water-ice reference scenario** (charter §11, §13):
  - ingest LOLA DEM for the Shackleton/south-polar region → COG/Zarr with explicit planetary CRS;
  - SPICE-backed lunar frames, epochs, and Sun/Earth geometry;
  - point-mass + low-order spherical-harmonic lunar gravity;
  - **precomputed horizon maps, solar illumination, and PSR masks** (the comms-/sun-denied core
    of the anchor scenario);
  - a first-cut surface **thermal** model and a **regolith terramechanics parameter field**
    consumable by Sim via the Environment API;
  - **3D-Tiles** export for [View](view.md);
  - the `WorldSpec` schema, content-addressed world bundle, and STAC catalog, publishable to
    [Hub](hub.md).
  Goal: a researcher can select "Shackleton vN" and run/score a baseline in an afternoon.
- **Phase 1+ — later.** Mars worlds (MOLA/HiRISE) and Martian frames; richer dust model; finer
  GPU on-demand illumination and learned illumination surrogates; additional body packs as
  plugins (charter §10.2); deeper thermal fidelity.
- **Phase 3 — ecosystem.** New environments (asteroids via polyhedral gravity, icy moons like
  Enceladus/Europa) arrive purely as community **body packs** — "support a new world" stays a
  package, never a Worlds core change (charter §10.2, §11).
  - **Multi-regime missions (RFC-0001).** The small / irregular-body extension — 3-D shape models,
    polyhedral/mascon non-central gravity, body rotation/tumbling, and microgravity-regolith
    fields for the `surface` and `proximity_orbit` regimes — lands here, alongside
    [Transit](transit.md) and the new mission-architecture components. The additive
    [Core](core.md) schema hooks it relies on (`MissionSpec`/`regime`/`PhaseTransition`) are
    *reserved in Phase 1* per the [mission-model](mission-model.md), so the Phase-0 narrow waist
    is not retrofitted later.
