# RFC 0002: A shared SPICE foundation package (`astro-mine-spice`)

- **Status:** draft
- **Author(s):** djankov
- **Created:** 2026-06-29
- **Affects Core:** no (depends on Core; no schema change) — but adds a new top-level package and updates a cross-cutting convention (`conventions.md §5`), so it goes through the RFC process per [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

Extract the SPICE-backed frame/time/geometry resolution that currently lives inside
`Astro-Mine-Worlds` (`astro_mine.worlds.spice`, shipped by RM-P0-WORLDS-02) into a new,
thin **commons-backbone** package, **`astro-mine-spice`** (import `astro_mine.spice`). It
depends only on `astro-mine-core` (the frame/time *types*) plus `spiceypy` and `numpy` —
no GDAL/rasterio. Every component that needs SPICE geometry — Worlds, Link, Sim's orbital
engine, and later Transit — then consumes **one** SPICE implementation through a shared
foundation, instead of either re-deriving thin SPICE adapters per package or depending on
the whole `Astro-Mine-Worlds` geospatial stack just to position a body.

## Motivation

The platform has an unresolved seam around SPICE, and it surfaces concretely at the first
non-Worlds SPICE consumer (RM-P0-LINK-01).

**Core deliberately cannot host SPICE.** `core.md §2.3` mandates *zero heavy dependencies*:
Core carries only the frame/time **types and conventions** — `Epoch`, `ReferenceFrame`,
`PlanetaryCRS`, the `require_frame`/`require_crs` fail-loud guards — and explicitly **defers
the name→geometry resolution** (kernels, `spkpos`, `pxform`) to elsewhere (`units` docstrings;
`core.md §2.3`).

**Today that resolution lives in Worlds.** RM-P0-WORLDS-02 built `astro_mine.worlds.spice`
and — intentionally — positions it as a shared service. Its own module docstrings say it is
*"the shared service illumination/PSR (RM-P0-WORLDS-03) **and Link (RM-P0-LINK-01) consume**,"*
that the raw primitives are *"a consumer drives over the furnished pool (e.g. **Link's own
`gfposc` window search**),"* and `Site` is *"the **shared Worlds↔Link** site type."* It even
ships `earth_geometry` — used nowhere inside Worlds — purely as the Link-facing twin of the
`sun_geometry` Worlds uses for illumination.

**But Worlds is the wrong home for a cross-component foundation.** Multiple non-Worlds
components need the same SPICE primitives:

- **Link** (RM-P0-LINK-01): Earth/relay body-fixed geometry for line-of-sight and (LINK-02)
  contact-window search.
- **Sim's orbital engine** (RM-P0-SIM-03: *"orbital (Basilisk/Orekit + SPICE)"*).
- **Transit** ([RFC-0001](0001-multi-regime-missions.md), Phase 3): interplanetary/free-space
  geometry.

Without a shared package, each of these has only two bad options:

1. **Re-derive a thin SPICE adapter per package.** Four-plus copies of `furnsh`/`spkpos`/
   `pxform`/topocentric-el-az wrappers drift apart — inconsistent aberration corrections,
   frame choices, and km↔m boundaries. Components then compute Earth/Sun positions *slightly
   differently*, which breaks cross-component reproducibility — a direct violation of the
   determinism tenet (`conventions.md §1.5`) — and multiplies the GMAT/STK/Skyfield
   oracle-validation burden N times over.
2. **Depend on `astro-mine-worlds` just for SPICE.** This drags the heavy GDAL/rasterio
   terrain stack (a declared hard dependency of Worlds) into a *comms* package and an
   *orbital* engine that touch no terrain, and creates an edge→edge dependency that
   `conventions.md §1.1` forbids (*"Components MUST NOT create private side-channels that
   bypass Core contracts"*).

**Why now.** LINK-01 is the first component to hit this. Deciding the seam once — before
Link, Sim's orbital engine, and Transit each solve it a different way — is far cheaper than
retrofitting three packages and reconciling three SPICE implementations later. The cost of
*not* doing it is paid immediately and repeatedly.

## Design

### The package

- **Name:** `astro-mine-spice` · **import:** `astro_mine.spice` · **dist:** `astro-mine-spice`
  (per `conventions.md §13`).
- **Layer:** **Commons backbone** — a *Core companion*. It is the SPICE-backed realization of
  Core's frame/time vocabulary that Core cannot host because of the heavy dependency. Naming
  the SPICE bridge plainly is sanctioned by `conventions.md §1.7` (*"Interop, don't reinvent…
  bridge to … SPICE"*) and the charter's §7 designation of SPICE/NAIF as the astrodynamics
  standard.
- **Dependencies:** `astro-mine-core` (frame/time types + fail-loud guards), `spiceypy`
  (CSPICE), `numpy`. **No** GDAL/rasterio, **no** other edge package.

### Public surface

Lifted near-verbatim from today's `astro_mine.worlds.spice` (so the extraction is a move, not
a rewrite):

| Group | Names |
|---|---|
| Kernel pool (fail-loud) | `load_metakernel`, `kernel_pool`, `clear_kernels`, `SpiceKernelError` |
| Time | `et`, `epoch_from_utc`, `epoch_range` |
| Geometry primitives | `body_position` (`spkpos`), `frame_transform` (`pxform`), `SpiceGeometryError`, `DEFAULT_ABCORR` |
| Topocentric site geometry | `Site` (+ `Site.lunar_from_latlon`), `BodyGeometry`, `body_geometry`, `sun_geometry`, `earth_geometry` |

All positions are SI metres (SPICE works in km; converted at the boundary), angles in degrees,
frames are Core `ReferenceFrame`s resolved by name, epochs are Core `Epoch`s (`tdb_seconds` is
SPICE ET directly).

### The boundary (the invariant that keeps the waist thin)

`astro-mine-spice` **resolves Core's vocabulary into positions, rotations, and topocentric
scalars — and stops there.** It does **not** own:

- **window search** (`gfposc`/`gftfov` contact-window solving) — stays in **Link** (LINK-02);
- **terrain occlusion** (horizon maps, `ray_intersect`) — stays in **Worlds**, exposed to
  consumers through the Core `WorldProvider` contract (`core.world`), exactly as today;
- **any physics, illumination, or comms interpretation** — stays in the respective consumer.

This is precisely the split Worlds' own docstrings already describe ("window search and terrain
occlusion live in the consumers, not here") — the RFC just moves the shared half to a package
every consumer can depend on cheaply.

### Migration

- **Worlds:** add `astro-mine-spice` to its dependencies; re-point its imports
  (`illumination/__init__.py`, `provider/__init__.py` import `Site`, `sun_geometry`,
  `epoch_range`, `DEFAULT_ABCORR`) from `astro_mine.worlds.spice` to `astro_mine.spice`. Because
  Worlds is pre-release (`0.0.0`) and we own every consumer during private incubation, do a
  **hard cut** — delete `astro_mine.worlds.spice` rather than leave a re-export shim — keeping
  the move clean. Worlds' SPICE oracle tests (`tests/test_spice_geometry.py`) move with the code
  to the new repo.
- **`MOON_RADIUS_M`:** `Site.lunar_from_latlon` currently reads `MOON_RADIUS_M` from
  `astro_mine.worlds.crs`. That body-radius constant moves into `astro_mine.spice` (it is
  geometry, not CRS/projection); `worlds.crs` re-imports it from there to keep its
  `PlanetaryCRS` datum definition in one place.
- **Link (RM-P0-LINK-01):** depends on `astro-mine-core` + `astro-mine-spice`. It computes
  Earth/relay body-fixed positions via `astro_mine.spice` (`body_position`/`earth_geometry`),
  then evaluates terrain occlusion through the injected Core `WorldProvider` contract — **no
  dependency on `astro-mine-worlds`.**
- **Sim / Transit:** cut over to `astro-mine-spice` when they next touch SPICE (Sim's orbital
  engine in Phase 0/1; Transit in Phase 3). Not required by this RFC, but they inherit the
  shared foundation for free.

### Determinism & validation

One implementation means one set of frame/aberration conventions across the platform, and the
GMAT/STK/Skyfield oracle cross-checks (`conventions.md §11`; LINK-05; WORLDS-02 §10) are written
**once** and trusted everywhere — instead of each component re-proving its own SPICE wrapper.
This is the reproducibility argument *for* centralizing, not against.

### Distribution & versioning

SemVer, version-from-Git-tag, pinned by downstream via a `uv` Git source + CI token during
private incubation — identical to the `astro-mine-core` pattern already used by Worlds
(`pyproject.toml [tool.uv.sources]`, `VERSIONING.md §5–7`). Carries **no operational-targeting
capability**: generic SPICE geometry over public ephemerides is open-commons science
(`conventions.md §12`; mirrors `worlds.md §9`).

### Documentation impact

On acceptance: add `astro-mine-spice` to the architecture vocabulary (`CLAUDE.md` layer table,
`architecture/system.md`); update `conventions.md §5` to name `astro-mine-spice` as the resolver
of the SPICE-backed frames/time/geometry that Core's `units` vocabulary defers to; reconcile
`worlds.md §6` and `link.md §2.2/§4/§6` to describe both packages consuming the shared
foundation; add a new `architecture/spice.md`; and add a short Phase-0 "SPICE foundation" entry
to `roadmap/phase-0-commons-seed.md` sequenced before the Link MVP.

## Impact on Core

**No Core schema change and no widening of the narrow waist.** `astro-mine-spice` *depends on*
Core; Core does not depend on it, and Core stays free of heavy dependencies (`core.md §2.3`
intact). If anything this **strengthens** `conventions.md §1.1`: components stop reaching into a
sibling edge's internals for SPICE and instead consume a declared shared foundation.

The one cross-cutting change is to `conventions.md §5`, which today says only that *"frames and
time are SPICE-backed."* It should name where that resolution lives (`astro-mine-spice`), so the
deferral from Core's `units` types to the resolver is explicit rather than folklore.

**Breaking change, but contained.** Deleting `astro_mine.worlds.spice` breaks Worlds' internal
import path. Worlds is `0.0.0` with no external consumers during private incubation and we own
the one in-repo caller graph, so this is a single coordinated PR, not a deprecation window.

## Alternatives considered

1. **Keep `worlds.spice` as the shared service; Link depends on Worlds.** This is what the
   Worlds code currently anticipates. Rejected: couples every SPICE consumer (Link, Sim, Transit)
   to Worlds' GDAL/rasterio terrain stack, and is the edge→edge side-channel `conventions.md §1.1`
   forbids. A comms package should not transitively install raster libraries to position Earth.
2. **Each component is its own SPICE client (re-derive thin adapters).** Aligns with a literal
   reading of `link.md §2.2/§4` ("Link uses SPICE/NAIF directly"). Rejected as the *default*:
   duplicated wrappers across four+ packages drift in frame/aberration conventions, breaking
   cross-component reproducibility (`conventions.md §1.5`) and multiplying oracle validation. (A
   component may still drive `spiceypy` directly for component-specific logic — e.g. Link's
   `gfposc` window search — *on top of* the shared primitives.)
3. **Put SPICE in Core.** Rejected outright: `spiceypy`+`numpy` are exactly the heavy weight Core
   must never carry (`core.md §2.3`); it would make Core un-importable in constrained/flight-adjacent
   contexts.
4. **Split Worlds into `worlds-core` + `worlds-spice` without a new top-level package.** Same code
   motion, but a new top-level package is cleaner under the one-repo-per-package convention
   (`conventions.md §13`) and makes the shared foundation discoverable to Sim/Transit, which have
   no reason to look inside Worlds.

## Unresolved questions

- **Final name.** `astro-mine-spice` (recommended, discoverable, honest about the foundation) vs.
  `astro-mine-frames` (impl-agnostic, but the package is intrinsically SPICE-bound — kernels, ET,
  `spkpos` — so the abstraction would oversell swappability).
- **Where body reference radii live.** `MOON_RADIUS_M` (and future per-body radii) in
  `astro_mine.spice` (recommended — it is geometry) vs. `astro_mine.core.units` (with the other
  frame/body constants).
- **Roadmap line.** Does this become a new `RM-P0-SPICE-*` track in the Phase-0 roadmap, sequenced
  before LINK-01 and refactoring the shipped WORLDS-02? Recommended: yes, a short foundation entry,
  tracked as issues post-acceptance (new repo · Worlds extraction · Link rewire).
- **Sim cut-over timing.** Cut Sim's orbital engine (SIM-03) over to `astro-mine-spice` in Phase 0
  alongside Worlds+Link, or defer until Sim next touches SPICE? (Deferring is safe; the foundation
  is additive.)
- **Migration tactic.** Hard cut of `astro_mine.worlds.spice` (recommended, pre-1.0) vs. a temporary
  re-export shim for one release.
