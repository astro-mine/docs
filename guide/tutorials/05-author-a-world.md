# Tutorial 05 — author a world

**Persona:** P3 Planetary Scientist / World Author
**Covers:** UC-C5 (author a WorldSpec) · UC-C7 (validate before an hours-long build) · UC-C6 (build
from real DEM data) · UC-G1 (publish)
**Time:** ~15 minutes for the synthetic path. The real-data path is hours of CPU and external
downloads.

A world in Astro-Mine is **declared, then built**. The declaration — a `WorldSpec` — is a small
YAML document. The build turns it into a content-addressed bundle: terrain, illumination, horizon
maps, PSR masks, thermal classes, regolith fields. This tutorial does the declaration honestly, the
synthetic build quickly, and states plainly what the real one costs.

---

## 1. Start from the shipped example

Worlds ships a copyable WorldSpec as package data:

```
astro-mine-worlds/src/astro_mine/worlds/spec/examples/synthetic_polar.world.yaml
```

It is deliberately **small and synthetic** — a 10 km × 10 km lunar south-polar basin at 20 m
resolution — and it needs neither the LOLA DEM nor SPICE kernels. Copy it, or scaffold a copy with
your own identity substituted:

```bash
astro-mine new world my.world.yaml --id my-basin --world-version 0.1.0
```

```
wrote my.world.yaml
```

The scaffold *is* the shipped example with your identity substituted, so it validates with no
hand-editing.

## 2. Understand the fields

```yaml
world_id: example-polar-basin
version: 0.1.0
description: A small synthetic lunar south-polar world.

crs:
  body: MOON
  body_fixed_frame: MOON_ME
  datum: null
  reference_radius_m: 1737400.0
  projection: >-
    +proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +x_0=0 +y_0=0
    +R=1737400.0 +units=m +no_defs

region:
  min_x_m: -5000.0
  min_y_m: -5000.0
  max_x_m:  5000.0
  max_y_m:  5000.0
  resolution_m: 20.0

source_dem:
  id: synthetic-polar-dem
  content_hash: null
  description: A synthetic illustrative DEM — replace with a real product and pin its content hash.

layers:
  regolith_prior: default_lunar
  illumination_backend: null
  illumination_n_azimuth: 72
  illumination_horizon_frame: grid
  illumination_max_radius_m: 8000.0
  illumination_abcorr: NONE
  psr_semantics: seasonal
  psr_start: '2025-01-01T00:00:00'
  psr_days: 365.0
  psr_step_hours: 12.0
  thermal_classes: [polar_lit, crater_floor]

reference_datetime: '2025-01-01T00:00:00Z'
```

**`crs` has no defaults, deliberately.** You state the body, the body-fixed frame, and the
reference radius explicitly. An implicit Earth datum on a lunar body is a defaulting bug, and the
loader rejects one outright rather than guessing ([RFC-0007](../../rfc/0007-units-frames-wire-schema.md),
LUNAR-TR-001). See [concepts/uncertainty.md](../concepts/uncertainty.md) for the same principle
applied to fields.

**Everything here is load-bearing on the hash.** `spec_hash` — and therefore `world_hash` — is
computed over exactly these bytes. Two worlds that declare the same thing hash the same; changing
any knob makes a *different world*, not a tweaked one. That is what lets a scenario pin a world by
digest and know it cannot drift ([concepts/content-addressing.md](../concepts/content-addressing.md)).

**The expensive knobs.** `resolution_m`, `illumination_n_azimuth`, `psr_days`, and
`psr_step_hours` set the build cost. The synthetic example uses 72 azimuths over 365 days at 12-hour
steps on a 500 × 500 grid. The anchor world uses far more, over a far larger region.

## 3. Validate before you build (UC-C7)

```bash
astro-mine-worlds validate my.world.yaml
```

```
OK  my.world.yaml: valid WorldSpec my-world (sha256:76e73535506be99a83c4e15581378088e0a8975dab3674c101def75aca11c9d2)
```

Or through the umbrella, which routes to the owning component:

```bash
astro-mine validate my.world.yaml
```

**Do this before every build.** A world build is minutes for the synthetic case and hours for a
real one; discovering a malformed CRS at the end of that is a bad day. The validator prints the
`spec_hash`, which is also how you check that two specs really are the same spec.

To see the schema itself:

```bash
astro-mine-worlds schema        # prints the published WorldSpec JSON Schema by its $id
```

## 4. Build it

Building is a **Python/script path**, not a CLI verb — `astro-mine-worlds` ships `validate`,
`schema`, and `publish`, and there is no `build` subcommand. Load the spec and drive the builder:

```python
from astro_mine.worlds.spec import WorldSpec

spec = WorldSpec.from_yaml("my.world.yaml")
print(spec.world_id, spec.spec_hash)
```

For the synthetic example this runs on one workstation in minutes and needs no external data, which
is the point of shipping it: you reach a real bundle before committing to the real thing.

## 5. The real-data path (UC-C6), honestly

Building the **anchor** world — Shackleton–de Gerlache — is a different undertaking:

- **The LOLA DEM** and PDS conditioning rasters (Diviner, LEND, M³). Not shipped; gigabytes;
  downloaded from PDS.
- **SPICE kernels** for the illumination geometry. Not shipped; obtained from
  [NAIF](https://naif.jpl.nasa.gov/naif/data.html).
- **Hours of CPU**, dominated by the per-cell horizon computation.

The anchor's own recipe is recorded in the scenario zoo's `pins.json` — the worked example of a
reproducible build, with the exact parameters (`--resolution-m 120`, `--n-azimuth 120`,
`--psr-days 365`, …) followed by `astro-mine-worlds publish`.

**The anchor world is not authorable as a static document**, and the shipped example says so in its
own comments: its region derives from the ingested DEM's grid, and its source is pinned by the
digest of a file the repository does not contain. That is not an oversight — a world built from real
data is defined by that data, and the spec records the pin rather than re-deriving the grid.

Worth knowing what the anchor's 0.4.0 build bought: a published horizon map, so resolving the world
takes ~3 s instead of re-deriving a 192-million-entry skyline on every load, and a spec-driven PSR
mask validated against the LOLA reference (PSR area fraction 0.1464 vs 0.1864 reference, |error|
0.0400, inside the published 0.0500 budget). The 0.1.0 world was at 0.1278 — an error of 0.0586,
**outside** that budget. This is what a world's provenance is supposed to tell you.

## 6. Publish it (UC-G1)

```bash
astro-mine-hub keygen --out ./keys
astro-mine-worlds publish <built-bundle> --registry ./myreg
```

The bundle is content-addressed and signed; consumers pull it by digest and re-verify fail-closed.
Once published, a scenario can pin it, and someone else's rover can drive on it — P3's success
sentence.

---

## 7. Where next

- **Put a swarm on your world:** [02 — run it in the simulator](../tutorials/02-run-it-in-the-simulator.md).
- **Author the robots:** [04 — author an asset](04-author-an-asset.md).
- **Contribute an illumination backend:** [08 — write a plugin](08-write-a-plugin.md) — the
  `astro_mine.field_models` group.
- **The format:** [reference/file-formats.md](../reference/file-formats.md).

**A related gap worth knowing:** resource priors — the other half of P3's world — are **Python
objects, not an authored file format**. `astro-mine-prospect publish` ships a prior bundle, but
there is no `prior.yaml` to write. Whether there should be is an open design question (G2.15), and
this guide will not invent a schema for it.
