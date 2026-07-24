# Tutorial 02 — run it in the simulator

**Persona:** P1 Benchmark Researcher (also P6 Educator/Student) · **the real path**
**Covers:** UC-B4 (run the anchor on real physics and score it) · UC-B5 (prove determinism against
Sim) · UC-B6 (inspect a run) · UC-B7 (score your own policy) · UC-G6 (reproduce someone else's
result)
**Time:** ~30 minutes of setup, then ~10 minutes per anchor seed.

[Tutorial 01](01-score-the-anchor.md) ended with a fixture score. This one replaces it with real
physics: real terrain, real illumination, a real sealed resource field, a real contact plan. Same
command, one flag, an entirely different claim.

---

## 1. What a Sim-backed run needs that a fixture run does not

Three things, and the platform will stop you on each.

| | What | Why |
|---|---|---|
| **1. The runner** | `astro-mine-sim[bench]` | Registers `sim` into the `astro_mine.bench.runners` entry-point group. **Bench never imports Sim** — it discovers runners. |
| **2. The producers** | `astro-mine-worlds`, `astro-mine-prospect`, `astro-mine-link` | Content and code ship separately. The fetched bundles are data; these packages rebuild them into live providers through `astro_mine.providers`. |
| **3. SPICE kernels** | a furnished metakernel | The world resolves body-fixed frames through SPICE. **Nothing in the CLI furnishes them** — see §3. |

Plus the content itself, from [tutorial 01](01-score-the-anchor.md) §6:

```bash
astro-mine-bench fetch                 # ~461 MB, needs $GITHUB_TOKEN with read:packages
```

```bash
uv pip install "./astro-mine-sim[bench]" ./astro-mine-worlds ./astro-mine-prospect ./astro-mine-link
```

## 2. The refusal, and why it is the good outcome

Try scoring before the producers are installed:

```bash
astro-mine-bench score --runner sim --registry ~/.cache/astro-mine/hub-registry
```

```
refusing to score this scenario: 2 pinned input(s) resolved by digest but rebuilt no provider,
so this run is blind to them:
  - 'shackleton-de-gerlache-v1' (world_provider): install astro-mine-worlds — without it, no
    terrain, gravity or illumination — night windows cannot be measured, so `nights_survived`
    scores not-applicable
  - 'shackleton_water_ice_v1' (resource_field_backend): install astro-mine-prospect — without it,
    no sealed resource field — prospecting sensors render `valid=False`, so `discovery_latency`
    never trips and ISRU extraction sees no abundance
Content and code ship separately: `astro-mine-bench fetch` obtains the bundles; the producer
packages above rebuild them into live providers.
A scorecard is a claim about a run, and this run would not have modelled the content it pins.
Install the producers above, or pass `SimEpisodeRunner(allow_unresolved_content=True)` to score
anyway.
```

**Read this as integrity, not breakage.** The scenario pins a world by digest. Without
`astro-mine-worlds` the digest resolves — the bytes are right there — but nothing turns them into
terrain. A run like that would produce numbers, and those numbers would be a claim about content
that was never loaded. Bench refuses to make it.

`astro-mine-sim run` takes the other choice deliberately: it **warns and proceeds**, because
recording a partial run is a legitimate ask at the library tier, and a run that *was* blind records
that fact in its own provenance.

> **Known rough edge.** The refusal is correct but currently escapes as an unhandled `RuntimeError`
> traceback rather than a clean CLI error. The message is the last few lines. This is a defect, not
> a signal that you did something worse than you did.

## 3. SPICE: the gap in the command-line path

The world resolves frames like `MOON_ME` through SPICE, and **no Astro-Mine CLI furnishes a kernel
pool**. Run `astro-mine-bench score --runner sim` with everything else in place and you get:

```
SpiceGeometryError: cannot resolve position of 'SUN' relative to 'MOON' in frame 'MOON_ME' at
ET 0.0: SPICE(UNKNOWNFRAME) -- The string supplied to specify the reference frame was 'MOON_ME'.
This frame is not recognized.
```

Kernels are not shipped with the platform — get them from
[NAIF](https://naif.jpl.nasa.gov/naif/data.html) and assemble a metakernel. Then furnish it
in-process before invoking the CLI's entry point:

```python
# score_sim.py
import sys
from astro_mine.spice import load_metakernel
load_metakernel("/path/to/metakernel.tm")

from astro_mine.bench.cli import main
sys.exit(main(sys.argv[1:]))
```

```bash
export ASTRO_MINE_HUB_REGISTRY=~/.cache/astro-mine/hub-registry
python score_sim.py score lunar-polar-ice-prospecting-v1 --runner sim --seeds 1001
```

This is a genuine hole: **the documented CLI path cannot be completed from a shell alone.** There is
no `--metakernel` flag on `score` or on `sim run`, and nothing reads a kernel path from the
environment. Everything below was produced through the four-line wrapper above.

## 4. Score it

Start on the sprint scenario — same machinery, minutes instead of tens of minutes:

```bash
python score_sim.py score lunar-polar-ice-prospecting-sprint-v1 --runner sim --seeds 1001
```

```
scenario:  lunar-polar-ice-prospecting-sprint-v1
runner:    astro-mine-sim/0.1.0
scorecard: sha256:2445f40a72ed2bea469519156ac8fb6593e5f5c6321f70238d3267bc875e4795

  information_gain             33483.6 nat          (up-better, n=1)
  psr_area_characterized           n/a m^2          (up-better, n=0)
  discovery_latency                  0 s            (down-better, n=1)
  comms_robustness                 n/a dimensionless (up-better, n=0)
```

Then the anchor itself — 43,200 ticks of 60 s, a 30-day lunar month:

```bash
python score_sim.py score lunar-polar-ice-prospecting-v1 --runner sim --seeds 1001
```

```
scenario:  lunar-polar-ice-prospecting-v1
runner:    astro-mine-sim/0.1.0
scorecard: sha256:5d31193541cd3f43a6bf409358a7662e0db12e05eb647e9522b176f82bb8bfa2

  water_mass                    47.612 kg           (up-better, n=1)
  energy_per_kg            2.53768e+06 J/kg         (down-better, n=1)
  information_gain             9000.68 nat          (up-better, n=1)
  psr_area_characterized    1.7975e+08 m^2          (up-better, n=1)
  nights_survived                    0 dimensionless (up-better, n=1)
  comms_robustness            0.429576 dimensionless (up-better, n=1)
  discovery_latency                  0 s            (down-better, n=1)
```

`runner: astro-mine-sim/0.1.0`, and a scorecard hash that is nothing like the fixture's. All seven
metrics scored.

## 5. Read it honestly

This is the part tutorial 01 could not teach, because the fixture has no story.

- **`water_mass = 47.612 kg`** — the swarm dug, hauled, delivered, and extracted. Extraction is
  coupled to delivered feedstock: the ISRU plant only produces water from regolith that was
  actually excavated and brought to it. A non-zero number here is earned.
- **`energy_per_kg = 2.54 × 10⁶ J/kg`** — enormous. That is the honest cost of the baseline's
  behavior, and it is the metric a better policy improves first.
- **`nights_survived = 0`** — the swarm did not come through a lunar night with margin intact.
  A real result, and a real target.
- **`discovery_latency = 0 s`** — read this one carefully. The scenario's discovery threshold is
  `0.0`, so the *first valid reading* trips it. It is not "instant discovery"; it is a threshold
  the `ScenarioSpec` schema cannot yet express meaningfully.
- **`n/a` on the sprint run** — `psr_area_characterized` and `comms_robustness` scored
  not-applicable with `n=0`: on that shorter episode no run produced a value they could be computed
  from. A `None` with a stated reason is honest. A `None` without one reads as breakage, which is
  why every one of them is explained here.

**What produced these numbers.** `--runner sim` scores a **capability-aware mode policy**
(`astro_mine.sim.bench._policy`). Each agent is held in a mode derived from its own SADF — its
capability tags say what it is for, its `power.loads_by_mode` says which modes it publishes a draw
for. On the anchor roster: rover → `prospect`, excavator → `excavate`, hauler → `drive_empty`,
relay-orbiter → `downlink`, lander → `idle`, ISRU plant → `idle`.

It does not plan, allocate, navigate, or react to anything it observes. It is a **replaceable
example — the conformance floor**, deliberately something a leaderboard can beat. Bench asks Sim for
it through the optional `DefaultPolicyProvider` seam, so the baseline is chosen by the runner that
resolved the content, not guessed by a CLI that cannot read a SADF document.

> **Do not trust `astro-mine-sim`'s README on this.** Its "The anchor baseline" section still
> explains why `water_mass` scores `0.0` and cites two issues that have since closed. Run the
> scorecard and read what it prints. Tracked in [docs#40](https://github.com/astro-mine/docs/issues/40).

## 6. Two scenario schemas, and why

You will meet two things called a scenario, and confusing them is the single most common trap here.

| | `ScenarioSpec` (Bench) | `Scenario` (Sim) |
|---|---|---|
| Owned by | `astro-mine-bench` | `astro-mine-sim` |
| Names content by | **pinned digests** | materialized, resolved content |
| Answers | "what is the benchmark?" | "what does the engine run?" |
| You use it with | `astro-mine-bench score/fetch/list` | `astro-mine-sim record` |

`astro-mine-sim run` takes a **Bench `ScenarioSpec` id** and resolves it into a Sim `Scenario`
through `sim_scenario_from_spec`. `astro-mine-sim record` takes a **Sim `Scenario` JSON file** and
needs no registry, no content, and no network. Sim's README carries the full comparison table —
read it there rather than from a copy that can drift.

## 7. Inspect the run (UC-B6)

Scoring gives you numbers. To see what happened, record the episode:

```bash
python sim_run.py run lunar-polar-ice-prospecting-sprint-v1 --seed 1001 --out anchor.mcap
```

```
06bfb73d54397f074b1930e943c7a7946e757c84519fa643be71338cdf811663
```

(`sim_run.py` is the same four-line wrapper as §3, calling `astro_mine.sim.__main__:main`.)

It prints the run's content hash and writes an [MCAP](https://mcap.dev/) log — 790 KB for the sprint
scenario. MCAP is a standard robotics log format, so any MCAP tool reads it; the platform's own
replay view is in the console ([console guide](../console.md), UC-B6).

The completely offline alternative, needing no content at all:

```bash
astro-mine-sim record --scenario-file <astro_mine/sim/reference/scenario.json> --out run.mcap
```

## 8. Prove it, and score your own policy

**Determinism (UC-B5, UC-G6).** Re-run any of the above with the same seeds and compare the
scorecard hash, exactly as in [tutorial 01](01-score-the-anchor.md) §7. The hash covers the runner,
so a Sim result and a fixture result can never be mistaken for one another. Reproducing someone
else's published result means: same scenario id, same seeds, same runner, same content digests —
all four are recorded in the scorecard, and the content is pinned, so there is nothing left to
guess.

**Your own policy (UC-B7).** The baseline is a `Policy` — swap in your own and score it the same
way. The path from a *trained* policy to a scored one is [tutorial 03](03-train-and-publish-a-policy.md).

---

## 9. Where next

- **Train something that beats it:** [03 — train and publish a policy](03-train-and-publish-a-policy.md).
- **Compose a planner instead of learning one:** [06 — compose a planner stack](06-compose-a-planner-stack.md).
- **See the run and the leaderboard in a GUI:** [the console guide](../console.md).
- **The ideas underneath:** [concepts/](../concepts/README.md) — fidelity, uncertainty, determinism
  & provenance.
