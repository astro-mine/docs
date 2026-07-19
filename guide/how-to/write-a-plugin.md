# Write a plugin

Astro-Mine is a **thin, stable core with thick, swappable edges** ([charter §9.2](../../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md)).
Worlds, robots, sensors, planners, policies, solvers, metrics, and ISRU processes are all meant to
arrive as plugins — contributed, versioned, and replaced *without touching the core*. Reference
implementations ship as **replaceable examples, not privileged internals**
([conventions.md §1.3](../../architecture/conventions.md)).

This is the recipe for each extension surface. Every snippet below was executed against the shipped
code; the group names and constants are quoted from source, with the file that defines each.

---

## Which surface do I want?

| I have a new… | Surface | Mechanism |
|---|---|---|
| planner, controller, allocator, or safety shield for an autonomy stack | `astro_mine.mind.tier_plugins` | entry point |
| world, resource field, observation model, or comms model that must rebuild from a pulled bundle | `astro_mine.providers` | entry point |
| execution backend that scores a Bench scenario | `astro_mine.bench.runners` | entry point |
| solver backend for task allocation | `astro_mine.allocate.solvers` | entry point |
| MARL algorithm | `astro_mine.learn.algorithms` | entry point |
| training curriculum | `astro_mine.learn.curricula` | entry point |
| benchmark metric | Core `metric` manifest published to Hub | manifest |
| **kind of contract that none of the above expresses** | — | **[RFC](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)** |

That last row is the important one.

### When it is an RFC instead

Core's `PluginKind` vocabulary is **closed and Core-owned**
([`core/registry/enums.py`](https://github.com/astro-mine/astro-mine-core/blob/main/src/astro_mine/core/registry/enums.py)):

```
regime_engine · sensor_model · coupling_scheme · world_provider · body_pack · field_model
resource_field_backend · observation_model · prior_recipe · info_gain_objective · comms_model
asset · policy · metric · design · campaign
```

If your extension **implements one of these contracts**, ship a plugin — that is what this guide is
for, and no Core change is needed. If it needs a *new* kind, that is a **Core change and therefore
an RFC** ([GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)): every
addition to Core is a permanent liability, and the default answer to "should this go in Core?" is
no ([core.md §2](../../architecture/core.md)).

Note what is *not* on that list: several groups below (`bench.runners`, `allocate.solvers`,
`learn.algorithms`, `learn.curricula`) deliberately add nothing to Core. A Bench runner or a MARL
algorithm is a *host-local* extension point; what crosses the narrow waist is the artifact it
produces — a `policy`-kind manifest — not the machinery that produced it.

### In-process or out-of-process?

[conventions.md §7](../../architecture/conventions.md) draws the line: **in-process plugins use
Python entry points** — that is everything in this guide. **Untrusted or non-Python plugins run
out-of-process**, in a sandboxed container over gRPC. If you are consuming a plugin you do not
trust, the sandbox is the host's job, not the plugin's: Core itself **never executes plugin code**
([core.md §9](../../architecture/core.md)) — it describes, validates, and resolves, and the host
component decides what to run and how to contain it.

---

## The shape every recipe shares

1. **Implement the contract** — a Protocol or a small dataclass, defined by the host component.
2. **Advertise an entry point** in your `pyproject.toml` under the host's group.
3. **`pip install`** your package. Discovery is by installed metadata; nothing needs to be
   registered anywhere else, and the host never imports your package until something asks for it
   by name.
4. **Test it** (see [Testing your plugin](#testing-your-plugin)).
5. **Publish it** (see [Publishing](#publishing)).

Two things are worth knowing before the recipes:

**The entry-point *name* is not always the identity.** For some groups the name *is* the id a user
selects; for others the identity comes from the loaded object and the name is ignored. Each recipe
below says which. Getting this wrong is silent — your plugin loads and registers under a name you
did not expect.

**The manifest is your public face.** The entry point is only the in-process discovery mechanism.
What the platform indexes, negotiates against, and gates on is the Core
[`PluginManifest`](../../architecture/core.md) — kind, the Core interface versions you implement,
capability tags, inputs/outputs, determinism class, provenance, signature. See
[The manifest side](#the-manifest-side).

---

## Recipe: an autonomy tier (`astro_mine.mind.tier_plugins`)

**The hub.** Mind composes a three-tier stack — mission planner → per-agent TAMP → controller, plus
safety shields — from a declarative stack spec, and resolves every tier through this group. Two
other components already register into it: Allocate contributes `allocate.planner` and Guard
contributes `guard.shield`, each behind an optional `[mind]` extra, so neither base package depends
on Mind.

**Contract.** A **zero-argument provider** returning a
`TierPlugin(manifest=…, factory=…)` — a Core manifest plus a callable that builds the tier from a
params mapping. Defined in
[`mind/registry/registry.py`](https://github.com/astro-mine/astro-mine-mind/blob/main/src/astro_mine/mind/registry/registry.py)
(`ENTRY_POINT_GROUP`, line 44).

Requirements the registry enforces:

- the manifest's **kind must be `policy`** — true even for allocators and shields;
- it must pass Core's manifest gates (schema, interface versions, duplicate names);
- it should declare `attributes.tier` (`mission` / `tamp` / `control` / `shield` / `allocator`),
  which Mind's composer cross-checks against the role a stack spec binds it to;
- the factory's result is re-checked against the Core `Policy` contract after construction.

```toml
# pyproject.toml
[project.entry-points."astro_mine.mind.tier_plugins"]
"demo.control" = "demo_tier.plugin:demo_control_plugin"
```

```python
# demo_tier/plugin.py
from importlib import resources

from astro_mine.core.messages.model import ActionBatch
from astro_mine.core.registry import load_manifest
from astro_mine.mind.registry import TierPlugin


class DemoController:
    """A Core Policy: observations in, actions out."""

    def decide(self, observations, context) -> ActionBatch:
        return ActionBatch(actions=[])


def demo_control_plugin() -> TierPlugin:
    """The entry-point provider: a Core manifest + a factory."""
    text = resources.files("demo_tier").joinpath("manifest.yaml").read_text(encoding="utf-8")
    return TierPlugin(manifest=load_manifest(text).manifest, factory=lambda params: DemoController())
```

Ship the manifest as package data beside the module:

```yaml
# demo_tier/manifest.yaml
manifest_version: "0.1"
manifest:
  name: demo.control
  version: "0.1.0"
  kind: policy                 # required: `policy`, even for an allocator or a shield
  description: A third-party controller contributed as a Mind tier plugin.
  core_interfaces:
    policy: "0.1.0"
    messages: "0.1.0"
  determinism_class: bit_exact
  inputs: [Observation, ActionBatch]
  outputs: [ActionBatch]
  signature:
    scheme: unsigned           # sign it for real publication — see Publishing
  attributes:
    tier: control              # the role Mind's composer binds this to
```

**The entry-point name is the plugin name** used in a stack spec, and should match `manifest.name`.

```python
>>> from astro_mine.mind.registry import TierRegistry
>>> reg = TierRegistry.from_entry_points()
>>> sorted(m.name for m in reg.manifests)          # `manifests` is a property, not a method
[..., 'demo.control', ...]
>>> reg.manifest("demo.control").attributes["tier"]
'control'
>>> reg.instantiate("demo.control", {})
<DemoController ...>
```

**Best references to copy:** Guard's
[`guard/mind/plugin.py`](https://github.com/astro-mine/astro-mine-guard/blob/main/src/astro_mine/guard/mind/plugin.py)
is a one-liner over a package-data manifest — the cleanest shape. Allocate's
[`allocate/mind.py`](https://github.com/astro-mine/astro-mine-allocate/blob/main/src/astro_mine/allocate/mind.py)
builds its manifest programmatically and shows the cross-package pattern: the module that knows
*both* vocabularies lives on Allocate's side of the waist, the only side permitted to know both, so
there is still no `mind → allocate` dependency in either base package (RFC-0006).

---

## Recipe: a content provider (`astro_mine.providers`)

**The "rebuild from a pulled bundle" pattern.** Sim resolves a scenario's pinned content **by
digest** and must reconstruct a live provider from the pulled bytes *without importing the producer*.
Worlds, Prospect, and Link each self-register a factory here.

**Contract.** `(PluginManifest, {media_type: bytes}) -> provider` — a live Core provider (a
`WorldProvider`, a `ResourceField`, …). Consumed by
[`sim/runtime/content.py`](https://github.com/astro-mine/astro-mine-sim/blob/main/src/astro_mine/sim/runtime/content.py)
(`PROVIDER_ENTRY_POINT_GROUP`, line 103).

**The entry-point name is a Core `PluginKind` value** — this is the one group whose names come from
Core's vocabulary rather than being free-form. Your factory **must import only Core and your own
package**, never `astro_mine.sim`; that one-way dependency is the whole point
([conventions.md §1.1](../../architecture/conventions.md)).

```toml
[project.entry-points."astro_mine.providers"]
body_pack = "demo_provider.plugin:from_bundle"      # the name IS the PluginKind value
```

```python
# demo_provider/plugin.py
class DemoBodyPack:
    """A live Core provider rebuilt from bundle layers."""

    def __init__(self, manifest, layers):
        self.manifest = manifest
        self.layer_count = len(layers)


def from_bundle(manifest, layers):
    """(PluginManifest, {media_type: bytes}) -> provider."""
    return DemoBodyPack(manifest, layers)
```

```python
>>> from astro_mine.sim.runtime.content import _discover_factories
>>> sorted(_discover_factories())
['body_pack', ...]
```

---

## Recipe: a Bench runner (`astro_mine.bench.runners`)

**The best worked example of "contribute once, use everywhere" in the tree.** Bench must score
against real physics without ever importing Sim — it stays dependency-clean (`core` + `pydantic`).
So the Sim-backed runner lives in *Sim*, registers here, and Bench discovers it **by name**.

**Contract.** A `BenchRunnerProvider`: a `runner_id` property, `episode_runner(store)`, and
`harness_runner(store)`. Defined in
[`bench/baseline/_registry.py`](https://github.com/astro-mine/astro-mine-bench/blob/main/src/astro_mine/bench/baseline/_registry.py)
(`RUNNER_ENTRYPOINT_GROUP`, line 47). Note `store` is typed `object` precisely so Bench never names
a Sim type.

```toml
[project.entry-points."astro_mine.bench.runners"]
demo = "demo_runner.plugin:demo_runner_provider"    # the name IS the --runner id
```

```python
# demo_runner/plugin.py
from astro_mine.bench.baseline import fixture_runner_provider


class DemoRunnerProvider:
    runner_id = "demo"

    def episode_runner(self, store=None):
        return fixture_runner_provider.episode_runner(store)

    def harness_runner(self, store=None):
        return fixture_runner_provider.harness_runner(store)


demo_runner_provider = DemoRunnerProvider()
```

Once installed it is a first-class CLI option, and **the runner is recorded in the scorecard and
folded into its content hash**, so a third-party run is distinguishable by provenance rather than
only by its numbers:

```console
$ astro-mine-bench score --runner demo
scenario:  lunar-polar-ice-prospecting-v1
runner:    demo
scorecard: sha256:9cd21d94cd739af7ff7f46a559eb07f7a87b15b6dc301ac94d0fc05c160f866c
```

Built-ins are seeded in code and the group overlays on top, so `score` works from a raw checkout
with nothing installed. Discovery is **lazy and by name**: the group is scanned only on a built-in
miss, and an unknown runner gets an actionable install hint rather than a traceback.

---

## Recipe: a solver backend (`astro_mine.allocate.solvers`)

**Contract.** The `Solver` strategy — `solve(ir, budget, hints=None) -> Iterator[Incumbent]`:
lower the solver-neutral Allocation IR to your encoding, search within the budget, and yield
incumbents with **monotonically improving bounds**, the last carrying the terminal status. Defined
in
[`allocate/solvers/registry.py`](https://github.com/astro-mine/astro-mine-allocate/blob/main/src/astro_mine/allocate/solvers/registry.py)
(`SOLVER_ENTRY_POINT_GROUP`, line 61).

```toml
[project.entry-points."astro_mine.allocate.solvers"]
demo-solver = "demo_solver.plugin:DemoSolver"       # the name IS the backend id
```

```python
# demo_solver/plugin.py
from astro_mine.allocate.solvers.trivial import TrivialStubSolver


class DemoSolver:
    def __init__(self, *, task_kinds, durations=None):
        self._inner = TrivialStubSolver(task_kinds=task_kinds, durations=durations)

    def solve(self, ir, budget, *, hints=None):
        yield from self._inner.solve(ir, budget, hints=hints)
```

```python
>>> from astro_mine.allocate import known_backends, AllocationPlanner
>>> known_backends()
('cp-sat', 'demo-solver', 'trivial-stub')
>>> plan = AllocationPlanner(backend="demo-solver").solve(request)
>>> plan.provenance.backend
'demo-solver'
```

Three things this group guarantees, worth relying on:

- **Listing never imports.** `known_backends()` reads entry-point *names*; your dependency is
  imported only when someone resolves your id.
- **You may not shadow a built-in.** Advertising `cp-sat` is a hard error naming both claimants —
  which solver produced a plan is provenance, so an ambiguous id never resolves silently.
- **Your plan is re-checked.** Every feasible plan, from any backend, is independently verified
  against the IR — Allocate is not the safety authority ([allocate.md §9](../../architecture/allocate.md)),
  which is exactly what makes accepting a third-party solver safe.

---

## Recipe: a MARL algorithm (`astro_mine.learn.algorithms`)

**Contract.** A zero-argument callable returning an `Algorithm` — `act`/`learn`/checkpoint/`export`,
plus an `AlgorithmSpec`. Consumed by
[`learn/algos/registry.py`](https://github.com/astro-mine/astro-mine-learn/blob/main/src/astro_mine/learn/algos/registry.py)
(`ALGORITHM_ENTRY_POINT_GROUP`, line 47).

```toml
[project.entry-points."astro_mine.learn.algorithms"]
demo_algo = "demo_algorithm.plugin:build"
```

```python
# demo_algorithm/plugin.py
from astro_mine.learn.algos.ippo import IppoAlgorithm


def build():
    return IppoAlgorithm()
```

> **The entry-point name is ignored here.** The registry keys your algorithm by
> `algorithm.spec.capability_tag`, read off the loaded object. Installing the example above
> registers it as `marl.independent.ppo`, *not* as `demo_algo`. Set the tag deliberately.

```python
>>> from astro_mine.learn.algos.registry import AlgorithmRegistry
>>> AlgorithmRegistry().discover_entry_points()
['marl.independent.ppo']
```

This group adds **nothing to Core** — there is no `ALGORITHM` `PluginKind`. What crosses the waist
is the `policy`-kind artifact your training run produces (an ONNX `PolicyPackage` + typed sidecar),
which Mind, Guard, and Bench consume.

---

## Recipe: a curriculum (`astro_mine.learn.curricula`)

**Contract.** A zero-argument callable returning **either** a `CurriculumSpec` (a hand-authored
ladder) **or** a `CurriculumFactory` (an automatic curriculum) — both accepted, so a research
curriculum needs no adapter. Consumed by
[`learn/curriculum/registry.py`](https://github.com/astro-mine/astro-mine-learn/blob/main/src/astro_mine/learn/curriculum/registry.py)
(`CURRICULUM_ENTRY_POINT_GROUP`, line 42).

```toml
[project.entry-points."astro_mine.learn.curricula"]
demo_ladder = "demo_curriculum.plugin:build"
```

```python
# demo_curriculum/plugin.py
from astro_mine.learn.curriculum import comms_ladder


def build():
    return comms_ladder()
```

> **Naming depends on what you return.** A `CurriculumSpec` registers under **its own `spec.name`**
> and the entry-point name is ignored; a factory registers under the **entry-point name**. The
> example above returns a spec, so it registers as `comms_ladder`.

```python
>>> from astro_mine.learn.curriculum.registry import CurriculumRegistry
>>> CurriculumRegistry().discover_entry_points()
['comms_ladder']
```

---

## Recipe: a Bench metric (a Hub artifact, *not* an entry point)

Metrics are the one extension surface that is **not** an entry-point group. A metric plugin is a
Core `metric`-kind `PluginManifest` **published to Hub**, whose `attributes.entrypoint` carries a
`module:attribute` reference that Bench `importlib`-resolves at load time, after pulling and
verifying the artifact fail-closed.

```python
from astro_mine.bench.metrics import metric_manifest

manifest = metric_manifest(
    my_metric,
    name="acme/comms-uptime",          # a publisher may namespace it
    entrypoint="acme_metrics.uptime:COMMS_UPTIME",
)
# -> kind='metric', outputs=['comms_uptime'], attributes['entrypoint']=…
```

`outputs` declares the metric keys the plugin produces — that is what makes it discoverable by what
it *measures* rather than by name. Publish the manifest to Hub (below); Bench resolves it by
reference, verifies it, and overlays it onto its metric registry.

Why the difference: a metric is *content* a leaderboard entry depends on, so it has to be
content-addressed and verifiable, not merely installed. Entry points describe what is on this
machine; a Hub artifact describes something reproducible from a digest.

---

## The manifest side

Whichever mechanism you use, **the entry point is not your public interface** — the Core
`PluginManifest` is. It declares:

| Field | What it is for |
|---|---|
| `kind` | which Core contract this implements (the closed `PluginKind` vocabulary) |
| `core_interfaces` | the Core interface **versions** you implement; the host refuses incompatible loads |
| `capability_tags` | what you can do — consumers negotiate against declarations, never hard-coded types |
| `inputs` / `outputs` | what you consume and produce (a metric's `outputs` are its metric keys) |
| `determinism_class` | whether your results reproduce bit-exactly |
| `provenance` | inputs, seed, code version, toolchain, environment lockfile |
| `signature` | who vouches for these bytes |

Core **validates at the boundary and fails loud** — an invalid manifest is rejected with a precise
error, never silently coerced ([core.md §2](../../architecture/core.md)). And Core never runs your
code: it describes, validates, and resolves; the host component instantiates and, where you are
untrusted, sandboxes ([core.md §9](../../architecture/core.md)).

---

## Testing your plugin

You do **not** need to install anything to test discovery. Both patterns below are in-tree:

**Patch the registry's `entry_points` symbol** — the fastest, and what Learn's tests use. It works
because each registry imports `entry_points` into module scope:

```python
def test_my_plugin_is_discovered(monkeypatch):
    from astro_mine.learn.curriculum import registry as registry_mod

    class _EP:
        name = "demo_ladder"

        def load(self):
            return build            # your zero-arg provider

    monkeypatch.setattr(registry_mod, "entry_points", lambda *, group: [_EP()])
    assert "comms_ladder" in CurriculumRegistry().discover_entry_points()
```

**Assert against the really-installed distribution** — slower, but it is the only thing that proves
your `pyproject.toml` is right. Allocate's `tests/test_mind_entry_point.py` does this against the
real installed Mind:

```python
from importlib.metadata import entry_points

advertised = {ep.name: ep for ep in entry_points(group=ENTRY_POINT_GROUP)}
assert PLUGIN_NAME in advertised
plugin = advertised[PLUGIN_NAME].load()()
```

Use both: the patched form for behaviour, the installed form for packaging. A monkeypatch cannot
catch a typo in your entry-point declaration.

---

## Publishing

Local installation is enough for your own use. To share a plugin, publish it as a **signed,
content-addressed artifact** to Hub:

```bash
astro-mine-hub keygen  --out ./keys
astro-mine-hub publish --registry <registry> --name acme.my-plugin --version 1.0.0 \
    --kind plugin --manifest manifest.json --key ./keys/cosign.key --layer payload.bin
```

- **Signing is required.** `hub.md` §9 tiers artifacts as *open* (self-published, **signed**,
  unreviewed), *curated*, and *verified* — there is no tier for unsigned content, and Hub's
  admission gate refuses it. Keyed ECDSA works offline with no account, so this costs a local
  workflow nothing.
- **`--kind` is Hub's *container* vocabulary** (payload shape), a different axis from your
  manifest's `kind` (the Core interface). `plugin` is the deliberate generic container for a
  payload with no more specific shape. See [hub.md §2 principle 2](../../architecture/hub.md).
- **Verification is fail-closed at both ends** — at admission when you publish, and again in the
  client when anyone pulls. A consumer's `pull` re-verifies signature, SLSA provenance, and SBOM
  before returning bytes.

Everything up to this point works offline with no account
([conventions.md §7](../../architecture/conventions.md), tier 1). Publication is the last step, not
a prerequisite.

---

## Known gap: `astro_mine.field_models`

Worlds declares four entry points under `astro_mine.field_models`
(`horizon`, `raycast_cpu`, `raycast_gpu`, `surrogate`) — but **nothing reads that group**.
Illumination backends are selected by a string switch in `build_illumination_model`
(`worlds/illumination/_registry.py`), so a third-party field model advertised there would never be
discovered.

**Do not write a plugin against this group yet.** It is documented here rather than omitted so that
nobody spends an afternoon on an extension point that cannot load — the same failure mode that
[astro-mine-allocate#31](https://github.com/astro-mine/astro-mine-allocate/issues/31) fixed for
solver backends. Tracked in
[astro-mine-worlds#52](https://github.com/astro-mine/astro-mine-worlds/issues/52).

---

## See also

- [conventions.md §1](../../architecture/conventions.md) — the architecture tenets: narrow waist,
  contribute once/use everywhere, plugins over patches
- [conventions.md §7](../../architecture/conventions.md) — plugin transport and distribution
- [core.md](../../architecture/core.md) — the manifest, the registry, and what Core will not do
- [hub.md](../../architecture/hub.md) — publication, verification, and the trust tiers
- [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md) — the RFC process,
  for when a plugin is not enough
