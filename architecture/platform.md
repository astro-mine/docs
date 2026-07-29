# Astro-Mine-Platform — the library distribution

> Distribution: **`astro-mine-platform`** (Python wheel) · Repository: `astro-mine-platform`
> Every component in [architecture/](README.md) ships here, as `astro_mine.<component>`.
> It is a **library**. It ships no commands, no web server, and no front end.
> Cross-cutting standards: see [conventions.md](conventions.md) (§7.1 is the distribution rule).

## 1. Purpose

One wheel carrying the whole Python platform. A user installs it — or, more often, installs
[`astro-mine-cli`](cli.md) and gets it — and holds every component at a single, self-consistent
version. There is no dependency matrix between components, no pin to choose, and no skew to
diagnose, because there is nothing to skew.

This is a **packaging** decision, not a design one. The component boundaries in this directory are
unchanged; what changed is that they no longer coincide with repository or release boundaries. The
per-component documents remain the design authority for the code under `astro_mine.<component>/`.

## 2. What is in it

The seventeen Python components that exist today:

| Layer | Components |
|---|---|
| Commons backbone | [Core](core.md) · [Spice](spice.md) · [Seal](seal.md) · [Bench](bench.md) · [Hub](hub.md) (client, index, registry) · [Cloud](cloud.md) |
| World & environment | [Worlds](worlds.md) · [Prospect](prospect.md) · [Link](link.md) |
| Assets | [Fleet](fleet.md) |
| Simulation | [Sim](sim.md) · [Surrogate](surrogate.md) |
| Autonomy & coordination | [Mind](mind.md) · [Learn](learn.md) · [Allocate](allocate.md) · [Guard](guard.md) |
| Design | [Studio](studio.md) (library and orchestration) |

Also in the wheel: Guard's Rust safety core as a compiled extension
(`astro_mine.guard._core`), every component's JSON Schemas and Protobuf sources, and the reference
content each component ships as package data (`src/astro_mine/<component>/reference/`).

**Not in it, deliberately:** the commands (→ [cli.md](cli.md)), the REST applications
(→ [api.md](api.md)), and the browser front end (→ [ui.md](ui.md)). Components whose design has a
REST or GUI face keep that face documented in their own doc; the code lives in the distribution that
owns that kind of surface.

[Ops](ops.md), [Bridge](bridge.md), [Transit](transit.md), [Trajectory](trajectory.md),
[Sizing](sizing.md) and [Ledger](ledger.md) are designed but not built (Phases 2–3). Each will land
as a subpackage here.

## 3. Layout

```
src/astro_mine/<component>/   the component packages
tests/<component>/            each component's suite, with its own default selection
schemas/                      Core's proto + JSON-Schema sources (path- and digest-coupled);
                              schemas/<component>/ for other owners' codegen sources
examples/                     runnable examples, grouped by kind (assets, worlds, plans, …)
rust/                         Guard's crate (PyO3 → astro_mine.guard._core)
scripts/                      test runner, codegen, schema-bundle builder, determinism gate
docs/components/<component>/  per-component source-tree notes; the design lives here in docs/
```

One rule explains most of it: any root-level directory that source, a script, or a committed digest
resolves by a **root-relative path** keeps its original name at the platform root. `schemas/`,
`examples/`, `embargo/`, `policy/`, `deploy/`, `docker/`, `platform/`, `validation/`, `validator/`,
`codegen/` are each owned by exactly one component and are anchored, not tidied — which is what let
path-resolving code and committed digests survive the move untouched.

## 4. Build & dependencies

- **Build backend: maturin.** A wheel has one backend, and Guard's is the constraint: its Rust
  trusted core must be compiled into the wheel, which is a safety requirement rather than packaging
  trivia. `python-source = "src"`, `manifest-path = "rust/Cargo.toml"`,
  `module-name = "astro_mine.guard._core"`. Building from source therefore needs a Rust toolchain.
  The crate's `panic = "abort"`, `lto`, and single-codegen-unit release profile are part of the
  safety argument and are not tuning knobs.
- **One base dependency set**, the union of what the components require. This is the honest cost of
  one wheel: installing it brings SPICE, PyTorch, OR-Tools, USD and GPyTorch whether or not a given
  user needs them. Tight pins that must not drift are preserved as-is — notably
  `gymnasium==1.2.2` (Ray exact-pins it), `ortools>=9.10,<9.11`, `protobuf>=7.35,<8`, and Torch via
  an explicit CPU index.
- **Extras are `<component>-<extra>`** (`learn-rllib`, `sim-mujoco`, `mind-onnx`,
  `bench-leaderboard`, …) because bare extra names collided across components — there were three
  `recording`s. Heavy optional stacks live behind them: Ray, MuJoCo, ONNX runtimes, JAX, MLflow,
  cluster clients.
- **Tier 1 must stay light enough to work.** The local tier is the property consolidation had to
  preserve: no service, no account, no extra. Adding a base dependency is a decision against that
  tier and should be argued as one (`conventions.md` §7.1).
- **No internal pins.** The `astro-mine-*` cross-pins and the whole Git-source pin matrix are gone
  with the repositories they coordinated.

Four `python -m` entry points remain, because each is invoked by other code rather than typed by a
person: the Cloud in-pod harness, the Sim container entrypoint, Bench's per-seed eval worker, and
Studio's orchestration worker. They are plumbing, not a command surface.

## 5. Interfaces

- **Inward:** none. The platform depends on no other Astro-Mine distribution. It is the base of the
  dependency graph, and the reason the CLI, API and front end can each be replaced without touching
  it.
- **Outward, to code:** the Python API of each component. This is now the platform's *only* public
  boundary, which is the main thing the split bought — "is this exported?" has a real answer, and the
  export audit that accompanied the CLI's removal found exactly one function that had been reachable
  only through a command handler.
- **Outward, to third parties:** the plugin and command entry-point groups. A third-party package
  registers a world, asset, planner, solver, validator, scaffold, or CLI verb by declaring an entry
  point in its own metadata (`conventions.md` §7.2, §13). The platform itself registers into none of
  the four CLI groups — its entries used to shadow the component names at the top level.

## 6. Testing & CI

Each component arrived with its own default pytest selection, and a single rootdir has a single
`addopts`, so the selections are re-applied by a runner rather than merged:

```bash
python scripts/test.py              # every component, each with its own default selection
python scripts/test.py core sim     # a subset
```

CI names the marker expression per component. Opt-in lanes (`sim`, `cluster`, `integration`,
`postgres`, `minio`, `nats`, `mlflow`, `docker`, `gpu`, `realdata`, `scale`) are marker-gated and
self-skip. Whole-platform coverage runs via `scripts/coverage_sweep.sh` against a 95% gate.

Two properties the single tree makes CI responsible for, since no package boundary enforces them any
more (`conventions.md` §11):

- **Layering.** No component imports another's private modules; no component imports the CLI or API
  distribution; Core imports nothing above its declared dependency floor.
- **Cross-component compatibility.** A change to a Core schema runs every consumer's schema tests in
  the same job. This is stronger than the cross-repo canary it replaced, which resolved Core from a
  stale release and could not fail.

## 7. Release

One version for the whole distribution, one tag, one wheel — see [VERSIONING.md](../VERSIONING.md).
The per-component versions and the `hatch-vcs` machinery that derived them are gone; a component
does not have a version of its own to bump, and the Core *interface* version remains a separate
axis, still frozen.

## 8. Boundaries — what this distribution must not do

1. **No console scripts.** A command belongs in [`astro-mine-cli`](cli.md). A capability reachable
   only by running a command is a capability the library failed to export.
2. **No web framework.** A component MUST NOT ship a FastAPI application; REST surfaces are route
   modules in [`astro-mine-api`](api.md) over the component's public API. gRPC services are
   different and stay here — they serve a component's own contract at high rate and are not a web
   edge.
3. **No cross-component private imports.** Sharing a distribution is not permission to couple
   (`conventions.md` §1, §3.1).
4. **No heavy module-scope imports.** One wheel makes an eager top-level import everyone's problem.
5. **No component knows its distribution name.** Code that asked `importlib.metadata` about "my
   package" was asking a question whose answer changed; capability detection is by import or entry
   point, not by distribution.

## 9. Provenance of this distribution

The wheel is a **consolidation, not a rewrite**: the eighteen component repositories were copied
mechanically, and import paths, public APIs, schemas and their `$id`s, entry-point groups,
configuration and environment-variable semantics, and algorithms are unchanged. Two departures were
deliberate — the CLI moved out entirely, and the REST and TypeScript surfaces were not migrated. The
migration contract, the complete list of places code had to be edited, and the execution log live in
the repository's own `docs/CONSOLIDATION_PLAN.md`, which is a historical record and is not
maintained as current documentation.

## 10. Roadmap alignment

Phases 0 and 1 are built and ship here. The immediate distribution-level work is standing up
[`astro-mine-api`](api.md) and [`astro-mine-ui`](ui.md) as their own repositories, and retiring the
eighteen component repositories once nothing references them. Phase-2 and Phase-3 components land as
new subpackages. See the [roadmap](../roadmap/README.md).
