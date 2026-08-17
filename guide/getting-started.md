# Getting started

The honest 10-minute path: from a clean machine to a result you can trust — and a clear account of
what that result is and is not.

Covers **UC-A1** (understand the platform), **UC-A2** (install), **UC-A3** (discover commands),
**UC-A4** (find the docs). Personas: **P1** Benchmark Researcher, **P6** Educator/Student.

---

## What Astro-Mine is

Astro-Mine is a platform for **designing, simulating, and benchmarking large heterogeneous robotic
swarms** — orbiters, landers, rovers, hoppers, excavators, haulers, ISRU plants — for exploration
and in-situ resource utilization on the Moon, Mars, and small bodies. The anchor problem it is
built around is **lunar polar water-ice prospecting**: a swarm that surveys permanently shadowed
regions, finds ice, digs it, hauls it, and turns it into stored water, under real illumination,
thermal, terrain, and comms constraints.

It is meant to become a **commons** — the shared simulation, benchmark, and orchestration substrate
for planetary-swarm robotics, the way ROS/Gazebo are for robotics and Gymnasium/MuJoCo are for RL.
That shapes every design decision: content is content-addressed and signed, runs are reproducible,
and every extension point is an entry point rather than a fork.

**Decide against it if:** you want a general-purpose robotics simulator (use Gazebo or MuJoCo), a
single-robot planning stack (use MoveIt or OMPL directly), a flight-qualified GNC toolchain
(Astro-Mine is explicitly design-time; operational maneuver targeting and guided EDL are out of
scope), or a finished product — this is an incubating platform whose repositories are still
private.

Architecturally it is a **thin, stable core with thick, swappable edges**: `astro_mine.core` owns
the asset format, the environment and policy APIs, the message schemas, and the plugin registry,
and everything else — worlds, resource fields, comms, simulation, autonomy, learning, benchmarking
— is a component that integrates only through those contracts. See
[concepts/narrow-waist.md](concepts/narrow-waist.md).

---

## Install

**What you need:** Linux, macOS, or WSL2; **Python 3.12**; [`uv`](https://docs.astral.sh/uv/);
`git`; and a **Rust toolchain** if you build from source. A GPU is never required.

One line installs everything:

```bash
pip install astro-mine-cli
```

`astro-mine-cli` provides the `astro-mine` command and depends on `astro-mine-platform`, the single
distribution that ships **every** component — Core, Sim, Worlds, Fleet, Bench, Hub, Mind, Learn,
Guard and the rest — as `astro_mine.<component>`. There is nothing else to add, no component to
install separately, and no version to reconcile: you get the whole platform at one self-consistent
version. See [architecture/platform.md](../architecture/platform.md).

**The honest part.** During incubation the repositories are **private** and neither distribution is
on PyPI, so that line does not work for you yet. You install from source, which needs read access to
the org. Note that the public flip alone will not change this: it makes the source public, and
publishing to an index is a separate decision (`VERSIONING.md` §6.2). What the flip removes is the
need for org access:

```bash
git clone https://github.com/astro-mine/astro-mine-platform.git
git clone https://github.com/astro-mine/astro-mine-cli.git
uv venv --python 3.12 .venv
uv pip install ./astro-mine-platform ./astro-mine-cli
```

Building the platform compiles Guard's Rust safety core into the wheel, so the first install takes a
few minutes and needs `rustup` on the machine (`source ~/.cargo/env` first). If you cannot read the
org, you cannot install the platform; that resolves at the first public-benchmark milestone.

**Heavy optional stacks stay optional.** Everything the tutorials below do works from the base
install. Ray-based training, MuJoCo contact and the ONNX controller tier sit behind
component-prefixed extras — `astro-mine-platform[learn-rllib]`, `[sim-mujoco]`, `[mind-onnx]` — and
the local tier is guaranteed to work without any of them.

> **Python 3.12, pinned.** `uv venv` follows the machine default, which may be 3.13. Both
> repositories pin `.python-version` to 3.12; pass `--python 3.12` explicitly when you build an
> environment by hand.

---

## Minute one: a real run, no content, no account

Astro-Mine ships a **reference environment** as package data inside `astro_mine.sim`: a small
synthetic three-agent scenario that needs no downloaded content, no registry, no network, and no
token. It is the fastest way to see the simulator actually run.

```bash
python - <<'PY'
from importlib.resources import files
from astro_mine.sim.reference import REFERENCE_SCENARIO_FILE
print(files("astro_mine.sim.reference").joinpath(REFERENCE_SCENARIO_FILE))
PY
```

That prints the path to the shipped `scenario.json`. Record an episode from it:

```bash
astro-mine sim record --scenario-file <that path> --out run.mcap
```

It prints the run's content hash and writes an MCAP log:

```
54b31ce0bec091cf51d7e2c084cb59c88ec58b4d74025c8a83d4b04d9b467e8b
```

That is a complete, self-contained, offline simulation run. It is also *only* a synthetic
three-agent scenario — it is not the benchmark, and no score comes out of it.

> `REFERENCE_SCENARIO_FILE` is the **file name** (`scenario.json`), not a path. Resolve it through
> `importlib.resources.files("astro_mine.sim.reference")` as above; passing the constant directly
> to `--scenario-file` fails with `FileNotFoundError`.

The other zero-prerequisite path scores the benchmark against a **fixture** — see the next section
for what that means.

---

## The benchmark, in three commands

`astro_mine.bench` ships the scenario zoo in-package, so listing and scoring work before you
download anything.

```bash
astro-mine bench list
```

```
lunar-polar-ice-endurance-v1
lunar-polar-ice-excavation-fidelity-v1
lunar-polar-ice-prospecting-sprint-v1
lunar-polar-ice-prospecting-v1
```

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

**Read that last line before you read the numbers.** `runner: fixture/0.1.0` means no physics ran.
The fixture is a deterministic recorded trace: it exists so the scoring path, the metric
definitions, and the reproducibility gates can be exercised in CI and on a laptop with nothing
downloaded. Those seven numbers are real outputs of a real scoring pipeline over a **stand-in
episode**. They say nothing about how a swarm would actually perform.

The runner is not a footnote — it is a required field on the scorecard and it feeds the scorecard's
content hash. You can always tell which one produced a result.

---

## The real result: Sim-backed scoring

Running the anchor on real physics needs three things the fixture path does not.

**1. The content.** The anchor scenario pins nine artifacts by digest — one world bundle, six fleet
assets, one resource prior, one contact plan.

```bash
astro-mine bench fetch
```

> **Before you run this:** it downloads **~461 MB** (the world bundle is 99.6% of it), and while
> the org is private it needs `$GITHUB_TOKEN` with the **`read:packages`** scope to pull from
> `ghcr.io/astro-mine`. Without that token it fails with a registry authentication error. Re-running
> is idempotent, and once fetched the content works offline forever.

**2. The producers — already installed.** Content and code ship separately. The bundles are data;
turning them back into live terrain, illumination, resource fields, and comms needs the code that
built them — `astro_mine.worlds`, `astro_mine.prospect`, `astro_mine.link` — which Sim reaches
through the `astro_mine.providers` entry-point group rather than by importing them.

**You have all of them.** One wheel ships every component, so the step that used to be here — install
three more packages and a `[bench]` extra, from three more repositories — is gone. This was the single
largest source of confusion in this guide, and the consolidation deleted it rather than documenting it
better.

The mechanism that made that confusion legible is still there and still matters. Sim **refuses to
score** a scenario whose pinned content rebuilt no provider:

```
refusing to score this scenario: 1 pinned input(s) resolved by digest but rebuilt no provider,
so this run is blind to them:
  - 'some-third-party-field' (resource_field_backend): no provider registered — without it,
    no sealed resource field — prospecting sensors render `valid=False`, so `discovery_latency`
    never trips and ISRU extraction sees no abundance
A scorecard is a claim about a run, and this run would not have modelled the content it pins.
```

You will now only see this for **third-party** content whose provider package you have not installed —
which is exactly when you should see it. A scorecard is a claim. Refusing to make a claim about content
that was never loaded is integrity, not breakage.

**3. SPICE kernels.** The world resolves body-fixed frames through SPICE, so a Sim-backed run needs
a furnished kernel pool. Kernels are **not shipped** with the platform — obtain SPK/PCK/FK/LSK
kernels from [NAIF](https://naif.jpl.nasa.gov/naif/data.html) and list them in a metakernel (`.tm`).

```bash
export ASTRO_MINE_SPICE_METAKERNEL=/kernels/lunar.tm
```

The environment variable is what the **scoring** path uses, because `astro-mine bench score` hands
the Sim runner a content store and nothing else — Bench has no vocabulary for SPICE. `astro-mine sim
run` and `record` additionally take `--metakernel PATH`, which wins over the variable.

The pool is validated against the episode's epoch window when the run starts, so a kernel set that
stops short of a 30-day lunar month fails in the first second rather than partway through.

With all three in place, the same command reports a different runner and different numbers:

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

Different runner, different scorecard hash, different story — a swarm that stored 47.6 kg of water
at a very poor energy cost and did not survive a night. That is what the shipped baseline actually
does. It is a conformance floor, deliberately beatable.

---

## Discovering commands

There is one binary, and one grammar — `astro-mine <component> <verb>`:

```bash
astro-mine
```

It lists every component that owns commands, and the three routers that answer *who owns this?* for
you:

```
Components — `astro-mine <component> <verb>`:
  core      validate Core-authored formats; list them
  fleet     author, package and publish SADF assets
  worlds    author and publish world bundles
  ...
  studio    the design studio

Routers — these pick the owning component for you:
  validate  validate an authored document (routed to the format's owner)
  new       scaffold an authored document (routed to the format's owner)
  plugin    scaffold a plugin package (`plugin new <kind>`)

`astro-mine <component> --help` lists that component's verbs.
```

Top-level help deliberately does **not** list a component's verbs: rendering that would mean importing
all fourteen components to print a help screen, and `astro-mine` imports none. `astro-mine <component>
--help` is where the real help lives. See [reference/cli.md](reference/cli.md) for the complete
surface.

---

## Where to go next

| You are | Start here |
|---|---|
| **P1** Benchmark researcher | [01 — score the anchor](tutorials/01-score-the-anchor.md) → [02 — run it in the simulator](tutorials/02-run-it-in-the-simulator.md) → [03 — train and publish a policy](tutorials/03-train-and-publish-a-policy.md) |
| **P2** Planning / autonomy researcher | [06 — compose a planner stack](tutorials/06-compose-a-planner-stack.md) → [08 — write a plugin](tutorials/08-write-a-plugin.md) |
| **P3** Planetary scientist / world author | [05 — author a world](tutorials/05-author-a-world.md) |
| **P4** Roboticist / asset author | [04 — author an asset](tutorials/04-author-an-asset.md) |
| **P5** Mission designer | [07 — design a swarm in Studio](tutorials/07-design-a-swarm-in-studio.md) → [the console guide](console.md) |
| **P6** Educator / student | this page → [01 — score the anchor](tutorials/01-score-the-anchor.md) → [the console guide](console.md) |
| Extending the platform | [how-to/write-a-plugin.md](how-to/write-a-plugin.md) |
| Looking something up | [reference/cli.md](reference/cli.md) · [reference/file-formats.md](reference/file-formats.md) · [concepts/](concepts/README.md) |

---

## What you did and did not just do

If you followed this page end to end, you have:

- **Run a real simulation** — the reference environment, offline, three synthetic agents.
- **Scored the benchmark against a fixture** — a real scoring pipeline over a stand-in episode.
- **Possibly scored it against Sim** — real physics, real terrain and illumination, if you had the
  content, the producer packages, and a SPICE metakernel.

You have **not** trained anything, published anything, or seen the GUI. Those are tutorials 03, and
07 with the [console guide](console.md).
