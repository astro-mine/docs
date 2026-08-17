# Tutorial 08 — write a plugin

**Persona:** all of P1–P4
**Covers:** UC-H1 (learn how) · UC-H2 (scaffold) · UC-H3 (register a MARL algorithm) · UC-H4
(register a planner/shield tier) · UC-H5 (register a Bench metric) · UC-H6 (register a solver
backend) · UC-H7 (publish for others)
**Time:** ~20 minutes for the worked example.

This is how the commons compounds. A plugin is a **separate package** that declares an entry point;
the platform discovers it. **No PR to any Astro-Mine repository, ever.**

This tutorial walks one plugin end to end. The per-kind recipes live in
[how-to/write-a-plugin.md](../how-to/write-a-plugin.md) — that page is *"here is the snippet for
each kind"*; this one is *"here is you, writing one."* Read this first, then go there for your kind.

---

## 1. Pick your surface

| You want to change | Group | Scaffold |
|---|---|---|
| how an autonomy tier plans or shields | `astro_mine.mind.tier_plugins` | `astro-mine plugin new tier` |
| how tasks are allocated | `astro_mine.allocate.solvers` | `astro-mine plugin new solver` |
| how policies are learned | `astro_mine.learn.algorithms` | `astro-mine plugin new algorithm` |
| the training curriculum | `astro_mine.learn.curricula` | `astro-mine plugin new curriculum` |
| how content becomes a live provider | `astro_mine.providers` | `astro-mine plugin new provider` |
| how illumination is computed | `astro_mine.field_models` | `astro-mine plugin new field-model` |
| how Bench executes an episode | `astro_mine.bench.runners` | `astro-mine plugin new runner` |
| adding an `astro-mine <verb>` | `astro_mine.cli` | `astro-mine plugin new cli` |

A **Bench metric** is the exception: it is a Hub artifact resolved by a scenario's manifest, not an
entry point. Recipe in the how-to.

If your change does not fit any of these, it may belong in Core — which means a
change to a **Core contract**, not a plugin. The how-to's
[*"When it is a Core change instead"*](../how-to/write-a-plugin.md#when-it-is-a-core-change-instead)
section is the test.

## 2. Scaffold it (UC-H2)

We will write an allocation solver (UC-H6).

```bash
astro-mine plugin new solver ./my-solver
```

```
wrote my-solver/pyproject.toml
wrote my-solver/src/my_solver/__init__.py

Install it and the id becomes selectable:
  pip install -e my-solver
  # then: AllocationPlanner(backend='demo-solver')
```

Every component is always installed, so `plugin new` can never fail for a missing owner — the
degradation path that used to be documented here is unreachable. The scaffold's job is now only to
write a package that registers correctly.

## 3. Read what it generated

The `pyproject.toml` is the whole registration mechanism:

```toml
[project]
name = "my-solver"
version = "0.1.0"
requires-python = ">=3.12"
# Note what is NOT here: astro-mine-cli. The CLI loads this package; it is not a dependency of it.
dependencies = ["astro-mine-platform"]

[project.entry-points."astro_mine.allocate.solvers"]
demo-solver = "my_solver:demo_solver"
```

Three things worth noticing:

- **The entry-point name is the backend id**, and it is recorded in a plan's `provenance.backend`.
  Which solver produced a plan is provenance, which is why your id may not shadow a built-in.
- **You depend on the platform, not on the CLI.** `astro-mine-cli` loads your package; it is not a
  dependency of it. Reversing that would make every plugin drag a command surface in.
- **You depend on `astro-mine-platform`, the whole wheel, and there is no smaller thing to depend
  on.** Every component ships in it ([conventions.md](../../architecture/conventions.md) §7.1), so
  there is no `astro-mine-allocate` to name — a plugin extends a component but installs a
  distribution. The scaffold emitted the retired per-component name until
  [astro-mine-cli#18](https://github.com/astro-mine/astro-mine-cli/issues/18) closed on 2026-07-30;
  this page told you to patch it by hand for longer than the defect existed.
- **Nothing else is registered anywhere.** There is no central list to add yourself to.

The generated module starts from the shipped stub, so it produces valid output from the first
commit:

```python
class DemoSolver:
    """Delegates to the shipped stub, so it produces valid streaming plans from the first commit.

    Replace `solve` with your own encoding. Starting from the stub means the plumbing — the
    registry, provenance, the independent re-check — is proven before you introduce a search that
    can fail for a reason of its own.
    """
```

and documents the contract you are implementing:

> **The contract** is `solve(ir, budget, *, hints=None) -> Iterator[Incumbent]`: lower the
> solver-neutral Allocation IR to your encoding, search within the budget, and **yield incumbents
> with monotonically improving bounds**, the last carrying the terminal status. Streaming is the
> point — yielding one final answer works and throws away the anytime behaviour the IR was designed
> for.
>
> **Your plan is re-checked.** Every feasible plan, from any backend, is independently verified
> against the IR before it is used: Allocate is not the safety authority. That is what makes an open
> solver seam reasonable — a plausible-but-wrong plan is caught rather than trusted.

That last paragraph generalizes: **open seams are safe because the platform re-checks, not because
it trusts you.**

## 4. Install it and watch it appear

```bash
uv pip install -e ./my-solver
```

```
Installed 1 package in 0.56ms
 + my-solver==0.1.0
```

```bash
python -c "from astro_mine.allocate.solvers.registry import available_backends; print(available_backends())"
```

```
('cp-sat', 'demo-solver', 'trivial-stub')
```

**That is the whole mechanism.** Your solver sits alongside the built-ins, discovered through the
same entry-point lookup they are — no special case, no registration call, and no Astro-Mine
repository was modified.

## 5. Write the real thing

Now replace the stub's `solve` with your encoding, keeping the streaming contract. Test it the way
the how-to's *"Testing your plugin"* section describes: the platform's own conformance expectations
for your group are what your tests should assert, and a plugin that passes them behaves
interchangeably with a built-in.

Then measure it. For a solver that means composing a stack that uses it and scoring against the
same benchmark ([tutorial 06](06-compose-a-planner-stack.md) §6) — the comparison that makes
*"and I can prove it's better"* a fact rather than an assertion.

## 6. Add the manifest

To publish, your plugin needs a **Core plugin manifest**: what it is, what it registers, which Core
interface versions it supports.

Real examples to copy — either works as-is:

```bash
cp astro-mine-platform/examples/plugins/greedy-prospecting-baseline.manifest.yaml \
   my-plugin.manifest.yaml
# the other example: lunar-terramechanics-engine.manifest.yaml
astro-mine core kinds       # `manifest` -> .../core/registry/v0.1/manifest.schema.json
astro-mine core validate my-plugin.manifest.yaml
```

```
OK  my-plugin.manifest.yaml: valid manifest
```

Edit `name`, `version` and `description` to yours. **Keep `name`/`version` in step with the
`--name`/`--version` you publish under**: the catalog indexes the *manifest's* pair, so a mismatch
publishes under one name and is found under the other.

Both on-disk shapes are accepted, YAML or JSON: a **manifest document** (`manifest_version` + a
`manifest:` mapping — what the examples above are, and what `astro-mine core validate` blesses) or a
bare `PluginManifest`. `hub publish` used to require the bare JSON form only, so the shipped examples
validated and then could not be published; that is fixed
(tracked as an open Hub issue).

### Which `kind` does a solver declare?

`kind` is required and drawn from Core's **closed** `PluginKind` vocabulary, and there is no `solver`
in it — by design. `astro_mine.allocate.solvers` *"deliberately adds nothing to Core"*: what crosses
the narrow waist is the allocation artifact, not the machinery that searched for it.

**Declare `kind: policy`.** That is the rule the tier recipe already states — *"the manifest's kind
must be `policy` — true even for allocators and shields"* — and a solver sits one level below an
allocator, as the backend an allocator's search runs on. Its only consumer is a `policy`-kind
allocator, so `policy` names what the plugin participates in rather than asserting a Core interface
it does not implement. Nothing resolves a solver *through the registry*; the entry point is the whole
registration.

If the platform ever wants solvers distinguished in the catalog, that is a new `PluginKind` and
therefore a **Core change**, not a value to pick per plugin — and Core's bar is a named consumer,
an additive change, and green consumer tests
([how changes are governed](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md#how-changes-are-governed)).

The how-to's *"The manifest side"* section covers the fields.

## 7. Publish it (UC-H7)

```bash
astro-mine hub keygen --out ./keys
astro-mine hub publish \
  --registry ./myreg \
  --name my-solver --version 0.1.0 --kind plugin \
  --manifest ./my-plugin.manifest.yaml \
  --key ./keys/cosign.key
```

```
sha256:ffecc1fa7809e635cf1daf0c51a6d0a579db6501429bcea000bc88cbec0a5e26
```

> **`--kind` appears twice here, meaning two different things, and both are right.** The flag is
> **Hub's container vocabulary** — the shape of the payload, where `plugin` is the deliberate generic
> container for a payload with no more specific shape. Your manifest's own `kind:` is the **Core
> interface** the plugin declares against (`policy`, above). Container ≠ contract; they are separate
> axes and do not map onto each other. See the how-to's
> [*Publishing*](../how-to/write-a-plugin.md#publishing) section and
> [hub.md §2 principle 2](../../architecture/hub.md).

Signed, content-addressed, discoverable by digest — the same pipeline as every other artifact
([concepts/content-addressing.md](../concepts/content-addressing.md)).

Then confirm it is findable, which is the point of the step:

```bash
astro-mine hub search --registry ./myreg --text my-solver
```

**Do not skip this step.** A plugin nobody can find is not a contribution to a commons; it is a
local patch that happens to be well-structured. `astro-mine hub search` is how someone else finds
it, and a digest is how they depend on it without you promising never to change it.

---

## 8. The kinds, and where their recipes are

Every one of these is live today. [how-to/write-a-plugin.md](../how-to/write-a-plugin.md) has the
recipe for each — this tutorial deliberately does not duplicate them, because duplicated recipes
drift apart.

| UC | Kind | Group |
|---|---|---|
| UC-H3 | MARL algorithm | `astro_mine.learn.algorithms` |
| — | training curriculum | `astro_mine.learn.curricula` |
| UC-H4 | autonomy tier / shield | `astro_mine.mind.tier_plugins` — the hub; Allocate and Guard both register here |
| UC-H5 | Bench metric | a Hub artifact, **not** an entry point |
| UC-H6 | solver backend | `astro_mine.allocate.solvers` |
| — | content provider | `astro_mine.providers` |
| — | illumination field model | `astro_mine.field_models` |
| — | Bench runner | `astro_mine.bench.runners` |
| — | CLI verb | `astro_mine.cli` |

## 9. Where next

- **Use your plugin in a stack:** [06 — compose a planner stack](06-compose-a-planner-stack.md).
- **The per-kind recipes:** [how-to/write-a-plugin.md](../how-to/write-a-plugin.md).
- **Why the seams are entry points:** [concepts/narrow-waist.md](../concepts/narrow-waist.md).
- **The manifest format:** [reference/file-formats.md](../reference/file-formats.md).
