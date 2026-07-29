# The narrow waist

**A thin, stable Core with thick, swappable edges.**

`astro_mine.core` owns a small, slow-changing set of contracts:

- **SADF** — the asset format
- the **Environment** and **Policy** APIs
- **message schemas** — `ActionBatch`, `ContactPlan`, `ObjectiveSpec`, `Plan`, `MissionSpec`,
  `PolicyPackage`, `RunProvenance`
- the **plugin registry** and its manifest

Everything else — worlds, resource fields, comms, simulation, surrogates, autonomy, learning,
allocation, safety, benchmarking, the registry, the console — is a component that integrates
**only** through those contracts. Core is deliberately dependency-light: no crypto (that is
`astro_mine.seal`), no SPICE (that is `astro_mine.spice`), no geospatial stack, no engine.

## Why it is worth the friction

A commons has to let strangers replace parts of it without coordinating with anyone. That is only
possible if the seams are few, named, and stable. The cost is real: you sometimes need two packages
where one would do, and some obvious-looking shortcuts are forbidden. The benefit is that a solver
someone wrote last week can be dropped behind the same interface as CP-SAT and measured on the same
benchmark, with no PR to any Astro-Mine repository.

## Three consequences you will actually hit

**Bench never imports Sim.** Bench depends on Core and pydantic and nothing else. It discovers
runners through the `astro_mine.bench.runners` entry-point group; Sim registers one.

This is the clearest case of the waist doing work you can check. Bench and Sim now ship in the *same
wheel*, so nothing in the packaging stops Bench from importing Sim — and it still does not. A layering
test asserts the import graph, which is a stronger guarantee than the old one: two separate
distributions merely made the coupling inconvenient, and inconvenient is not the same as absent.
The payoff is unchanged — you can swap the runner without touching Bench, and a third party can
register their own.

**Mind has no `run`.** Composing an autonomy stack is Mind's job. *Stepping* one needs a Core
`Environment` — which Sim provides — and Mind importing Sim would put an engine dependency behind
the planning interface. So Mind composes; Bench and Sim execute. This looks like a missing feature
until you try to swap the engine, at which point it is the whole point.

**Content and code ship separately.** A world bundle is data. Turning it back into terrain,
illumination, and gravity needs `astro_mine.worlds`, reached through the `astro_mine.providers`
group. That is why fetching content is not enough to run a scenario, and why Sim refuses to score
a run whose pinned providers did not rebuild.

## The live extension points

Every one is an entry-point group. Registering into one requires no change to any Astro-Mine repo.

| Group | You are extending |
|---|---|
| `astro_mine.cli` | the umbrella CLI — a new `astro-mine <verb>` |
| `astro_mine.providers` | content providers — worlds, resource fields, comms models |
| `astro_mine.bench.runners` | how Bench executes an episode |
| `astro_mine.mind.tier_plugins` | an autonomy tier — mission, TAMP, control, shield |
| `astro_mine.allocate.solvers` | an allocation backend |
| `astro_mine.learn.algorithms` | a MARL algorithm |
| `astro_mine.learn.curricula` | a training curriculum |
| `astro_mine.field_models` | an illumination backend |

Recipes: [how-to/write-a-plugin.md](../how-to/write-a-plugin.md). Narrative:
[tutorial 08](../tutorials/08-write-a-plugin.md).

## The rule, stated normatively

`conventions.md` §1.1: components integrate through Core contracts, **never through private
side-channels**. In the console the same rule reads: a surface never imports another surface.

Where a capability is heavy but genuinely shared, it becomes a **Core companion** rather than
entering Core: `astro_mine.spice` for frames, time, and geometry
([Spice](../../architecture/spice.md)); `astro_mine.seal` for signing and SBOM
([Seal](../../architecture/seal.md)). Thin waist, thick edges, and a named
place for the things that are neither.
