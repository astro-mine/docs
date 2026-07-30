# Tutorial 01 — score the anchor

**Persona:** P1 Benchmark Researcher (also P6 Educator/Student) · **Phase 0**
**Covers:** UC-B1 (list scenarios) · UC-B2 (score offline, no account) · UC-B3 (obtain the anchor
content) · UC-B5 (prove determinism)
**Time:** ~15 minutes, plus a ~461 MB download if you do the content step.

You will list the benchmark scenarios, obtain the content the anchor pins, score the reference
baseline, read the scorecard, and prove the result reproduces. By the end you will be able to say
exactly **what ran** to produce your numbers — which is the whole point of this tutorial.

---

## 1. Install

```bash
pip install astro-mine-cli
```

One line, one version, everything ([getting-started](../getting-started.md) has the
install-from-source path you need until the public flip).

Bench is still **architecturally** light — it never imports the simulator, which is why `bench` and
`sim` can be swapped independently. What changed is that "light" no longer means "a smaller install":
one wheel carries every component. Bench ships the scenario zoo in-package, so the next two steps work
with nothing downloaded.

## 2. List the scenarios (UC-B1)

```bash
astro-mine bench list
```

```
lunar-polar-ice-endurance-v1
lunar-polar-ice-excavation-fidelity-v1
lunar-polar-ice-prospecting-sprint-v1
lunar-polar-ice-prospecting-v1
```

`lunar-polar-ice-prospecting-v1` is **the anchor** — the flagship lunar polar water-ice prospecting
scenario, 43,200 ticks of 60 s (a 30-day lunar month). It is the default for every Bench command.
`…-sprint-v1` is a short variant, useful while you are still setting things up.

## 3. Score it, right now (UC-B2)

```bash
astro-mine bench score
```

```
scenario:  lunar-polar-ice-prospecting-v1
runner:    fixture/0.1.0
scorecard: sha256:e6d16dfd6dc39bb9ab5f5e2c50fd1494419d1bf792494f6e8ff4ef6696df4ff6

  water_mass                   213.685 kg           (up-better, n=5)
  energy_per_kg                123.773 J/kg         (down-better, n=5)
  information_gain             2.69616 nat          (up-better, n=5)
  psr_area_characterized           180 m^2          (up-better, n=5)
  nights_survived                    1 dimensionless (up-better, n=5)
  comms_robustness                 0.5 dimensionless (up-better, n=5)
  discovery_latency              12600 s            (down-better, n=4)

scored with the reference runner — a deterministic trace fixture, not a physics engine. Use `--runner sim` for a Sim-backed run.
```

No account, no network, no content. That is intentional — but so is the last line.

---

## 4. The runner is the story

**`runner: fixture/0.1.0` means no physics ran.**

The `fixture` runner replays a deterministic recorded trace. It exists so the scoring pipeline, the
metric definitions, the sandbox, and the reproducibility gates can be exercised anywhere — in CI, on
a laptop, on a plane. The seven numbers above are genuine outputs of the real scoring code applied
to a **stand-in episode**. They are not a claim about how any swarm performs.

This distinction is structural, not editorial:

- `runner` is a **required field on every `Scorecard`** (`bench/metrics/_score.py`). There is no
  scorecard without one.
- It feeds the scorecard's **content hash**, so a fixture result and a Sim result can never collide.
- The CLI prints a banner whenever the reference fixture produced the card.
- The leaderboard renders the runner in the ranking row.

To check any scorecard, machine-readably:

```bash
astro-mine bench score --json | python -c 'import json,sys; print(json.load(sys.stdin)["runner"])'
```

```
fixture/0.1.0
```

If that says `fixture/0.1.0`, you scored the fixture. If it says `astro-mine-sim/0.1.0`, Sim
produced it. Never infer this from the numbers.

**When the fixture is the right tool:** regression tests, CI, determinism gates, teaching the
scoring model, and any time you are changing Bench itself. **When it is not:** any claim about
swarm performance, and any leaderboard submission.

Getting a Sim-backed score is [tutorial 02](02-run-it-in-the-simulator.md). Finish this one first —
everything here applies to both.

---

## 5. What the seven metrics mean

| Metric | Unit | Direction | What it measures |
|---|---|---|---|
| `water_mass` | kg | higher better | Water actually stored in the ISRU plant's gauge at episode end. The headline metric: non-zero only if regolith was dug, hauled, delivered, and extracted. |
| `energy_per_kg` | J/kg | lower better | Total swarm energy spent per kg of stored water — the efficiency counterpart. A swarm that produces a little water very expensively scores badly here. |
| `information_gain` | nat | higher better | Reduction in uncertainty about the resource field, against the belief the run maintained. Rewards *learning where the ice is*, not just digging. |
| `psr_area_characterized` | m² | higher better | Permanently-shadowed-region area brought below an uncertainty threshold. Survey coverage. |
| `nights_survived` | dimensionless | higher better | Lunar nights the swarm came through with power and thermal margin intact. Survival, not throughput. |
| `comms_robustness` | dimensionless | higher better | Fraction of the episode with a usable link, over the scenario's pinned contact plan. |
| `discovery_latency` | s | lower better | Time to the first valid detection above the scenario's discovery threshold. |

A metric can score **not applicable** (`n/a`, printed with `n=0`). That is a statement, not a
failure: it means no run produced a value the metric could be computed from — usually because the
content or the provider it depends on was absent. Tutorial 02 shows this happening for real and
explains each case.

Note `n=` on each row: how many seeds contributed. `discovery_latency` above shows `n=4` out of five
seeds — on one seed nothing tripped the threshold, so that seed contributes no value rather than a
fabricated one.

---

## 6. The nine pins, and why they are digests (UC-B3)

The anchor scenario does not name its content — it **pins** it, by content hash:

| Pin | Id | Version |
|---|---|---|
| world | `shackleton-de-gerlache-v1` | 0.4.0 |
| fleet | `astro-mine.fleet.prospecting-rover` | 0.1.0 |
| fleet | `astro-mine.fleet.excavator` | **0.2.0** |
| fleet | `astro-mine.fleet.hauler` | 0.1.0 |
| fleet | `astro-mine.fleet.isru-plant` | **0.2.0** |
| fleet | `astro-mine.fleet.lander` | 0.1.0 |
| fleet | `astro-mine.fleet.relay-orbiter` | 0.1.0 |
| prospect | `shackleton_water_ice_v1` | 1.0.0 |
| link | `astro-mine.link.lunar-polar-relay-dsn` | 0.3.0 |

Each carries a `sha256:` digest and a description recording *why that version*. The excavator moved
to 0.2.0 when it gained a `tool` contact element, without which no library asset reaches the
granular contact ladder. The ISRU plant moved to 0.2.0 when it gained a `water_gauge` — before
that, Bench could not tell a full tank from a swarm that produced nothing, because `water_mass` is
scored by matching a reading's species and unit.

That is what content-addressing buys you: **the scenario cannot drift underneath your result.** A
digest names one exact byte sequence. If someone republishes "the anchor world" with a different PSR
mask, it is a different digest and therefore a different scenario — your score stays comparable to
itself and to everyone else's. See
[concepts/content-addressing.md](../concepts/content-addressing.md).

To obtain them:

```bash
astro-mine bench fetch
```

> **Read this before you run it.** It pulls **~461 MB** — the world bundle is 99.6% of that — from
> `ghcr.io/astro-mine`. While the org is private it needs `$GITHUB_TOKEN` carrying the
> **`read:packages`** scope; without it you get a registry authentication failure. Re-running is
> idempotent, and once fetched everything works offline.

```
usage: astro-mine bench fetch [-h] [--registry PATH] [--from REGISTRY]
                              [--trusted-key PATH] [scenario_id]
```

`--registry` is where it writes (default `$ASTRO_MINE_HUB_REGISTRY`, else
`~/.cache/astro-mine/hub-registry`). Every artifact is verified fail-closed on arrival: content is
checked by digest, and a signature must be present, intact, and bound to the artifact. Pass
`--trusted-key` to additionally pin *whose* signature you accept.

You do not need this step to finish tutorial 01 — the fixture runner ignores the content store
entirely. You need it for tutorial 02.

---

## 7. Prove it reproduces (UC-B5, CX-REPRO)

Determinism is not something this platform asks you to take on faith. Score twice and compare the
scorecard hash:

```bash
astro-mine bench score --seeds 1001 1002 | grep scorecard
astro-mine bench score --seeds 1001 1002 | grep scorecard
```

```
scorecard: sha256:b2547ddbdab91c6f16eda86c4759e9090ca65961126fdf92883bf647c57c7feb
scorecard: sha256:b2547ddbdab91c6f16eda86c4759e9090ca65961126fdf92883bf647c57c7feb
```

Identical. The hash covers the metrics, the scenario, the seeds, **and the runner** — so it
fingerprints the whole claim, not just its numbers. Two people reporting the same hash ran the same
thing; two people reporting the same numbers under different hashes did not.

**Seeds.** The anchor's public seed set is `1001, 1002, 1003, 1004, 1005`, and `score` uses all five
by default. The scenario also carries a **held-out seed commitment** —
`sha256:fee93327b5943041865348cc47b4b9db5bde955a9cd8c307ebeba18569ab5640` — a hash published in
advance of seeds nobody can see. Leaderboard scoring uses those, so a policy that overfits the
public five is caught by construction. You cannot tune against a hash.

---

## 8. What you have, and what is next

You can now list scenarios, score one offline, read a scorecard, tell which runner produced it, and
prove your result reproduces. You have **not** run any physics.

- **The real thing:** [02 — run it in the simulator](02-run-it-in-the-simulator.md).
- **Score your own policy instead of the baseline:** also tutorial 02 (UC-B7).
- **Look a command up:** [reference/cli.md](../reference/cli.md).
- **Understand the model:** [concepts/](../concepts/README.md) — content-addressing, determinism &
  provenance, and the two scenario schemas.
