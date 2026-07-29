# Scenarios: `ScenarioSpec` vs `Scenario`

Two different things are called a scenario. Confusing them is the most common mistake newcomers
make, and it produces confusing errors rather than obvious ones.

| | `ScenarioSpec` | `Scenario` |
|---|---|---|
| **Owned by** | `astro-mine bench` | `astro-mine sim` |
| **Names content by** | **pinned digests** | materialized, resolved content |
| **Answers** | "what is the benchmark?" | "what does the engine run?" |
| **Carries** | scenario id, content pins, metrics, seeds, held-out commitment | assets, providers, episode length, engine configuration |
| **You pass it to** | `astro-mine bench score/fetch/list`, `astro-mine sim run` | `astro-mine sim record --scenario-file` |
| **Needs content?** | pins it; does not contain it | contains what it needs |

## The bridge

`astro-mine sim run <scenario_id>` takes a **Bench `ScenarioSpec` id** and resolves it into a Sim
`Scenario` through `sim_scenario_from_spec`: it looks up each pinned digest in the content store and
rebuilds it into a live provider.

```bash
astro-mine sim run lunar-polar-ice-prospecting-sprint-v1 --seed 1001 --out run.mcap
```

`astro-mine sim record --scenario-file <path>` takes a **Sim `Scenario` JSON document** — already
materialized, self-contained, and needing no registry, no content, and no network. That is the path
the shipped reference scenario uses, and it is why it works offline with nothing downloaded:

```bash
astro-mine sim record --scenario-file <astro_mine/sim/reference/scenario.json> --out run.mcap
```

If you pass a Bench scenario **id** to `record`, or a Sim scenario **file** to `run`, you get an
error about the wrong kind of thing — this table is the answer.

Sim's own README carries a fuller comparison; read it there rather than from a copy that can drift.

## Why two, rather than one

Because they answer to different constituencies.

A benchmark must be **immutable and portable**: it names content by digest so that a result means
the same thing everywhere, and it must be readable by a package that has no engine installed —
Bench depends on Core and pydantic and nothing else ([narrow waist](narrow-waist.md)). It cannot
contain a world; it can only point at one.

An engine needs **materialized content**: actual terrain, an actual resource field, actual assets.
It cannot run a digest.

Collapsing them would either force Bench to depend on the engine, or force the benchmark
definition to embed hundreds of megabytes. The seam between them is where the entry-point discovery
happens, and it is deliberate.

## The scenario zoo

```bash
astro-mine bench list
```

```
lunar-polar-ice-endurance-v1
lunar-polar-ice-excavation-fidelity-v1
lunar-polar-ice-prospecting-sprint-v1
lunar-polar-ice-prospecting-v1
```

| Scenario | What it is for |
|---|---|
| `lunar-polar-ice-prospecting-v1` | **The anchor.** 43,200 ticks × 60 s — a 30-day lunar month. Nine pinned artifacts, seven metrics, public seeds 1001–1005. The default everywhere. |
| `…-prospecting-sprint-v1` | A short variant of the same setup — the one to use while you are still getting your environment right. |
| `…-endurance-v1` | Survival over the long horizon. |
| `…-excavation-fidelity-v1` | Granular contact fidelity, where the excavator's `tool` contact element matters. |

The zoo ships **in-package**, so `list` and fixture scoring work before you download anything. The
content those specs pin does not — that is [`astro-mine bench fetch`](../tutorials/01-score-the-anchor.md).
