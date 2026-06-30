# Astro-Mine-Spice — Technology Architecture

> Layer: **Commons backbone** (a *Core companion*) · Phase: **0** · Added by [RFC-0002](../rfc/0002-shared-spice-foundation.md) (accepted)
> The SPICE-backed realization of [Core](core.md)'s frame/time vocabulary: resolves names into
> positions, rotations, and topocentric geometry — and nothing more.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Spice` is the **single shared SPICE resolver** for the platform. [Core](core.md) defines
the frame/time *vocabulary* — `Epoch`, `ReferenceFrame`, `PlanetaryCRS`, and the `require_frame`/
`require_crs` fail-loud guards — but deliberately cannot host the *resolution* of those names into
geometry: `spiceypy`/`numpy` are exactly the heavy dependencies the narrow waist must never carry
([core.md](core.md) §2.3). Spice is that resolution, factored into a thin package
(`astro-mine-spice`, import `astro_mine.spice`) that every SPICE consumer depends on.

Concretely, given furnished NAIF kernels, Spice:

- manages the **SPICE kernel pool** — furnishing meta-kernels, clearing them, and a scoped
  `kernel_pool` context manager — failing loudly when coverage is missing;
- converts **Core epochs ↔ SPICE ET** and builds epoch ranges (`et`, `epoch_from_utc`, `epoch_range`);
- resolves **geometry primitives** — body-fixed/inertial **positions** (`body_position`, over
  `spkpos`) and **frame rotations** (`frame_transform`, over `pxform`) — in SI metres and a declared
  aberration correction;
- computes **topocentric site geometry** — a `Site` on a body surface, and the Sun/Earth/arbitrary-body
  elevation–azimuth–range tuples (`body_geometry`, `sun_geometry`, `earth_geometry`) that illumination
  (Worlds) and link visibility (Link) are built from;
- owns the body **reference radii** that are geometry rather than CRS/projection (e.g. `MOON_RADIUS_M`).

**The boundary (the invariant that keeps the waist thin).** Spice resolves Core's vocabulary into
positions, rotations, and topocentric scalars **and stops there**. It does **not** own:

- **window search** (`gfposc`/`gftfov` contact-window solving) — that stays in [Link](link.md) (LINK-02),
  driven *on top of* these primitives;
- **terrain occlusion** (horizon maps, `ray_intersect`) — that stays in [Worlds](worlds.md), exposed to
  consumers through the Core `WorldProvider` contract;
- **any physics, illumination, or comms interpretation** — that stays in the respective consumer.

**Explicitly out of scope.** Spice is not an astrodynamics engine (no propagation, no force models —
that is [Transit](transit.md)/[Sim](sim.md)), not a CRS/projection library (that is PROJ via
[Worlds](worlds.md)), and carries **no operational guidance** (generic geometry over public
ephemerides only — see §9).

**Primary users:** every SPICE consumer — [Worlds](worlds.md) (illumination/PSR) and [Link](link.md)
(LOS geometry) in Phase 0, and — as they adopt it — [Sim](sim.md)'s orbital engine, [Bridge](bridge.md)
(time/frame transforms), [Trajectory](trajectory.md), and [Transit](transit.md) (deep-space
ephemerides/frames).

**Charter alignment:** §7 designates **SPICE/NAIF** the astrodynamics standard; `conventions.md §1.7`
("interop, don't reinvent — bridge to … SPICE") sanctions naming the bridge plainly.

---

## 2. Architecture principles

1. **A thin Core companion, not an edge.** Spice depends only on `astro-mine-core` (frame/time *types*
   and guards) plus `spiceypy` and `numpy`. No GDAL/rasterio, no other `astro-mine-*` package. Core
   depends on it not at all; it depends on Core for vocabulary only.
2. **Resolve, don't interpret.** Spice turns names + epochs into numbers. The meaning of those numbers
   (is the link open? is the site lit? is the orbit stable?) belongs to the consumer.
3. **SI at the boundary.** SPICE works in kilometres; Spice converts to **metres** at its surface.
   Angles are degrees; epochs are Core `Epoch`s whose `tdb_seconds` is SPICE ET directly.
4. **One implementation ⇒ one set of conventions.** A single home for frame choices, aberration
   corrections, and the km↔m boundary means components compute Earth/Sun positions *identically* —
   the reproducibility argument *for* centralizing (`conventions.md §1.5`, §11).
5. **Fail loud at the kernel boundary.** A missing/incomplete kernel pool, an unknown frame, or an
   epoch outside coverage raises (`SpiceKernelError`/`SpiceGeometryError`) — never a guessed position.
   This is the upstream half of every consumer's "degrade, don't lie" contract.
6. **Stateless except the kernel pool.** The only state is SPICE's furnished pool; the `kernel_pool`
   context manager scopes it so tests and parallel workers don't leak kernels into each other.

---

## 3. Application architecture

Delivered **library-first** (importable, single-workstation usable per `conventions.md §1.4`); there
is no service wrapper — it is a dependency, not a process. Internal modules:

```
astro_mine.spice
├── _kernels.py    # kernel pool: load_metakernel / clear_kernels / kernel_pool (scoped) ; SpiceKernelError
├── _geometry.py   # body_position (spkpos), frame_transform (pxform), time helpers, Site topocentric geometry,
│                  #   body_geometry / sun_geometry / earth_geometry ; MOON_RADIUS_M ; SpiceGeometryError, DEFAULT_ABCORR
└── __init__.py    # facade: re-exports the public surface (and __version__)
```

### Key abstractions exposed

| Group | Names |
|---|---|
| Kernel pool (fail-loud) | `load_metakernel`, `kernel_pool`, `clear_kernels`, `SpiceKernelError` |
| Time | `et`, `epoch_from_utc`, `epoch_range` |
| Geometry primitives | `body_position` (`spkpos`), `frame_transform` (`pxform`), `SpiceGeometryError`, `DEFAULT_ABCORR` |
| Topocentric site geometry | `Site` (+ `Site.lunar_from_latlon`), `BodyGeometry`, `body_geometry`, `sun_geometry`, `earth_geometry` |
| Body constants | `MOON_RADIUS_M` (reference radii that are geometry, not CRS/projection) |

All positions are SI metres, angles degrees, frames are Core `ReferenceFrame`s resolved by name,
epochs are Core `Epoch`s.

### Key abstractions consumed

- **[Core](core.md)** `units`/`frames`: the `Epoch`, `ReferenceFrame`, `PlanetaryCRS` types and the
  `require_frame` fail-loud guard. This is Spice's *only* `astro-mine-*` dependency.
- **SPICE/NAIF** via **SpiceyPy** (CSPICE under the hood): `furnsh`/`unload`, `spkpos`, `pxform`,
  `str2et`, and the SPK/PCK/FK/LSK kernels a consumer furnishes.
- **NumPy** for vector math and epoch-range vectorization.

### Extension / plugin points

- **Additional body reference radii** as new bodies are modeled (small bodies in Phase 3).
- **Aberration-correction policy** — `DEFAULT_ABCORR` is the platform default; callers may override
  per query where a different correction is warranted (oracle cross-checks).

### Interaction patterns

A consumer furnishes a pinned, hashed meta-kernel once (`load_metakernel`, or the scoped
`kernel_pool` context manager), then calls `body_position`/`frame_transform`/`*_geometry` per epoch.
Worlds drives `sun_geometry`/`body_geometry` for illumination/PSR; Link drives `body_position`
(Earth/relay) for LOS and layers its own `gfposc` window search on top; Sim's orbital engine and
Transit consume the same primitives for ephemerides/frames.

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.12** (conventions.md §2). The public surface is fully typed; `spiceypy`
  ships no type information and is treated as an untyped boundary (per-consumer mypy override).
- **Geometry/astrodynamics:** **SPICE/NAIF** via **SpiceyPy** (CSPICE); no other geometry backend in
  the default path. **NumPy** for array math.
- **No heavy geospatial stack:** explicitly **no GDAL/rasterio/PROJ** — those belong to
  [Worlds](worlds.md). Keeping them out is the whole point of the package (a comms or orbital consumer
  must not transitively install raster libraries to position a body).
- **Config & schemas:** none of its own; it speaks Core's frame/time types.
- **Runtime model:** in-process importable library only — no FastAPI/gRPC surface.
- **Build/packaging:** Python wheel `astro-mine-spice` (import `astro_mine.spice`); SemVer,
  version-from-Git-tag; depends on a pinned `astro-mine-core` interface major version
  (conventions.md §7, §13). Native CSPICE ships inside the SpiceyPy manylinux wheel. NAIF **kernels are
  furnished by the consumer**, not bundled.

---

## 5. Data architecture

- **Inputs:** NAIF **kernels** — SPK (ephemerides), PCK (body orientation/radii), FK (frame defs), LSK
  (leap seconds), and optionally CK (pointing) / DSK (shapes). Consumers furnish them via a **pinned,
  content-hashed meta-kernel**; Spice validates coverage up front and fails loudly on a gap.
- **No store of its own:** Spice holds no datasets — only the live SPICE kernel pool (process state).
  Provenance (kernel source + hash) is recorded by the *consumer* in its products (conventions.md §5).
- **Units & frames:** positions in **SI metres** (converted from SPICE km at the boundary), angles in
  degrees, epochs are Core `Epoch`s (`tdb_seconds` = SPICE ET), frames are Core `ReferenceFrame`s
  resolved by name. No implicit Earth/WGS84 assumptions (conventions.md §5).

---

## 6. Integration architecture

Spice sits on the **Commons backbone** as a Core companion and integrates through plain package
dependencies (no service plane, no side-channels — conventions.md §1.1):

- **← [Core](core.md).** Depends on `astro-mine-core` for the frame/time types and `require_frame`
  guard. Core does **not** depend on Spice; the narrow waist stays free of heavy deps (core.md §2.3).
- **→ [Worlds](worlds.md).** Worlds resolves SPICE frames/epochs/Sun-Earth geometry through Spice
  (illumination/PSR, RM-P0-WORLDS-03); `worlds.crs` re-imports `MOON_RADIUS_M`. Replaces the former
  in-package `astro_mine.worlds.spice` (extracted on RFC-0002 acceptance).
- **→ [Link](link.md).** Link resolves Earth/relay body-fixed positions through Spice for LOS, then
  evaluates terrain occlusion via the Core `WorldProvider` contract — **no dependency on
  `astro-mine-worlds`** (RFC-0002).
- **→ [Sim](sim.md), [Bridge](bridge.md), [Trajectory](trajectory.md), [Transit](transit.md).** Sim's
  orbital engine (SIM-03, Phase 0), Bridge's time/frame transforms (Phase 2), and Trajectory/Transit
  (Phase 3) consume the same primitives when they next touch SPICE — additive, no rework (RFC-0002
  deferred cut-over).

**This is the seam fix.** By being the one package every consumer depends on, Spice eliminates both the
"re-derive a thin SPICE adapter per package" drift and the "depend on `astro-mine-worlds` just for
SPICE" edge→edge side-channel that `conventions.md §1.1` forbids.

---

## 7. Infrastructure & deployment

- **In-process library** — there is no cluster footprint; it is linked into whichever process imports a
  consumer (a research laptop, a Sim worker, a Cloud job).
- **Kernels at runtime:** consumers furnish a pinned meta-kernel; container images that need geometry
  pin a CSPICE build (via the SpiceyPy wheel) and mount/copy a content-addressed kernel set.
- **Distribution:** pinned downstream via a `uv` Git source + CI token during private incubation,
  identical to the `astro-mine-core` pattern (VERSIONING.md §5–7). Public PyPI wheel deferred to the
  public flip.

---

## 8. Performance & scalability

- `spkpos`/`pxform` calls are individually cheap; the dominant cost is **kernel furnishing** — so reuse
  the pool across queries and scope it with `kernel_pool` rather than re-furnishing per call.
- **Epoch ranges** vectorize through NumPy where SPICE allows; per-epoch loops are the fallback.
- "Measure before optimizing" (conventions.md §8): a native fast path is unwarranted until profiling of
  a real consumer (e.g. Link's per-tick visibility over hundreds of node-pairs) demands it — and even
  then the window-search hot loop lives in Link, not here.

---

## 9. Security, safety & compliance

- **No operational-targeting capability.** Generic SPICE geometry over **public ephemerides** is
  open-commons science; Spice carries no guided-EDL / maneuver-targeting surface and is **not** gated by
  the `operational_targeting` capability tag (conventions.md §12; mirrors worlds.md §9 and the
  [RFC-0001](../rfc/0001-multi-regime-missions.md) dual-use boundary).
- **Provenance:** kernels are pinned and content-hashed by consumers; the same kernel set + epoch +
  frame ⇒ identical geometry, which is what makes downstream products reproducible.
- **Supply chain:** SpiceyPy/CSPICE and NumPy are the only third-party runtime deps; pinned via
  `uv.lock` and covered by Dependabot (conventions.md §9).

---

## 10. Observability & operability

- **Fail-loud, structured errors:** `SpiceKernelError` (missing/incomplete pool, no coverage for an
  epoch) and `SpiceGeometryError` (unknown frame/body, resolution failure) name the offending
  kernel/frame/epoch so a consumer can surface a precise boundary failure rather than a silent default.
- **Coverage validation up front:** a furnished meta-kernel is checked for the epoch window it will be
  queried over, so gaps surface at setup, not mid-rollout.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **SPICE binding** | SpiceyPy (CSPICE); native CSPICE; pure-Python reimpl | **SpiceyPy** — the canonical, NAIF-aligned binding; CSPICE correctness, Python ergonomics (charter §7). |
| **Resolver scope** | Thin primitives only; full astrodynamics toolkit | **Thin primitives only** — propagation/force models are Transit/Sim; Spice resolves, it does not propagate. |
| **Cross-checks / oracles** | Trust SPICE; validate against Astropy/Skyfield/GMAT/STK | **SPICE canonical; others as oracles only** — written once here and trusted everywhere (conventions.md §11). |
| **Units boundary** | Expose km (SPICE-native); convert to SI metres | **SI metres at the boundary** — no km leaks past the package surface (conventions.md §5). |
| **Aberration default** | per-call; one platform default | **One `DEFAULT_ABCORR`**, overridable per call — singular convention, escape hatch for oracles. |

---

## 12. Roadmap alignment

Phase-0 deliverable, sequenced **before the Link MVP** (see [roadmap/phase-0](../roadmap/phase-0-commons-seed.md)):

- **RM-P0-SPICE-01** — extract `astro-mine-spice` near-verbatim from `astro_mine.worlds.spice`.
- **RM-P0-SPICE-02** — cut Worlds over (hard cut, delete the in-package module; oracle tests move).
- **RM-P0-SPICE-03** — distribution (Git-tag versioning, pinned downstream; no operational-targeting tag).

**Consumed by** RM-P0-WORLDS-02/03 (illumination/PSR) and RM-P0-LINK-01 (LOS geometry) in Phase 0.
**Deferred:** Sim's orbital engine (SIM-03, Phase 0), [Bridge](bridge.md) (Phase 2), and
[Trajectory](trajectory.md)/[Transit](transit.md) (Phase 3) adopt the foundation when they next touch
SPICE — additive, no rework ([RFC-0002](../rfc/0002-shared-spice-foundation.md) resolved decisions).
