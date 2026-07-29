# CLI reference

Every shipped command, organized by **what you are trying to do** rather than by which component
owns it. Covers **UC-A3** (discover which command does what) and **UC-A4** (find the docs for my
task).

Verified against `--help` output at authoring time. Where a command does not exist, this page says
so rather than omitting it.

---

## One binary, one grammar

```
astro-mine <component> <verb> [options]
```

`astro-mine` is the **only** executable the platform installs (`conventions.md` §13, normative). It
comes from `astro-mine-cli`, which depends on `astro-mine-platform` — so `pip install astro-mine-cli`
gets you the command and every component behind it.

Thirteen names are components. Three are **routers**, which exist because they answer a question no
single component can: *who owns this?*

```bash
astro-mine                       # the components and the routers
astro-mine <component> --help    # that component's verbs — where the real help lives
astro-mine --version
```

**Top-level help does not list verbs, on purpose.** Rendering them would mean importing all thirteen
components to print a help screen. `astro-mine` imports **none**; dispatch imports exactly the one
module you named. You pay for the command you ran.

### The three routers

| Command | What it does |
|---|---|
| `astro-mine validate <file>...` | Validate an authored document. Routed to the component that owns its schema `$id`; the router owns no schema. `--json` for machine-readable output. |
| `astro-mine new [kind] [output]` | Scaffold an authored document. Each kind is written by the component owning that format. Omit the kind to list them. |
| `astro-mine plugin new <kind> <output>` | Scaffold a plugin package against a live extension group. |

`new` and `validate` are two ends of one contract: what `new` writes, `validate` accepts.

### Where a command is unavailable

Every component is always installed, so "component missing" is no longer a state you can reach. What
you can still hit is a surface that lives in **another distribution**, and the command says so rather
than failing obscurely:

```console
$ astro-mine studio serve
astro-mine studio serve needs the Studio REST surface (astro_mine.studio.api), which is not
included in astro-mine-platform.
```

That surface belongs to [`astro-mine-api`](../../architecture/api.md), which is not yet stood up.
(The hint the command prints after that line still names a retired distribution —
[astro-mine-cli#19](https://github.com/astro-mine/astro-mine-cli/issues/19).) An
unknown name is a plain error with the valid ones listed — never a traceback:

```console
$ astro-mine nosuch
astro-mine: error: unknown component or verb 'nosuch'; available: bench, cloud, core, fleet,
guard, hub, learn, link, mind, new, plugin, prospect, sim, studio, validate, worlds
```

### Names you may find in the wild

An earlier scheme gave every component its own `astro-mine-<component>` binary, with four bare names
(`fleet`, `worlds`, `link`, `prospect`) and the mis-nouned `astro-mine-train` kept as deprecated
aliases. **All of them are gone.** If you find `astro-mine-bench score` or `fleet validate` in a blog
post or an old transcript, the current spelling is `astro-mine bench score` and `astro-mine fleet
validate`.

### Scaffold kinds

`astro-mine new <kind>` — authored documents:

| Kind | Document | Provided by |
|---|---|---|
| `asset` | a SADF asset | `astro-mine fleet` |
| `safety` | a SafetySpec | `astro-mine guard` |
| `stack` | an autonomy stack spec | `astro-mine mind` |
| `world` | a WorldSpec | `astro-mine worlds` |

`astro-mine plugin new <kind>` — plugin packages, one per live extension group:

| Kind | Entry-point group | Provided by |
|---|---|---|
| `algorithm` | `astro_mine.learn.algorithms` | `astro-mine learn` |
| `curriculum` | `astro_mine.learn.curricula` | `astro-mine learn` |
| `field-model` | `astro_mine.field_models` | `astro-mine worlds` |
| `provider` | `astro_mine.providers` | `astro-mine sim` |
| `runner` | `astro_mine.bench.runners` | `astro-mine bench` |
| `solver` | `astro_mine.allocate.solvers` | `astro-mine allocate` |
| `tier` | `astro_mine.mind.tier_plugins` | `astro-mine mind` |
| `cli` | `astro_mine.cli` | `astro-mine-cli` |

What these scaffolds emit are the recipes in
[how-to/write-a-plugin.md](../how-to/write-a-plugin.md).

---

## Run and score a benchmark — `astro-mine bench`

```
astro-mine bench {score,fetch,submit,list,zoo-sync,zoo-search}
```

| Command | Flags | Notes |
|---|---|---|
| `list` | — | The scenario ids in the packaged zoo. |
| `score [scenario_id]` | `--seeds SEED...` · `--runner NAME` · `--registry PATH` · `--json` | Default scenario `lunar-polar-ice-prospecting-v1`; default runner **`fixture`** (a deterministic trace, not physics). `sim` needs fetched content. The runner is recorded in the scorecard and its hash. |
| `fetch [scenario_id]` | `--registry PATH` · `--from REGISTRY` · `--trusted-key PATH` | Resolves the scenario's pins by digest, mirrors them locally, verifies fail-closed. Anchor ≈ **461 MB**; needs `$GITHUB_TOKEN` with `read:packages` while the org is private. Idempotent, then offline. `--from` defaults to `ghcr.io/astro-mine`. |
| `submit` | `--hub-ref REF` \| `--policy-ref MODULE:ATTR` \| `--job ID` · `--scenario-id ID` · `--to URL` · `--method` · `--author` · `--wait` · `--token-file` · `--json` | `--hub-ref` is the reproducible path. `--policy-ref` is local/dev and **not leaderboard-grade**. Token from `$ASTRO_MINE_BENCH_TOKEN`, never a flag. |
| `zoo-sync` | — | Seed the Postgres/pgvector catalog from the packaged zoo (operator task, P7). |
| `zoo-search` | — | Similarity-search the hosted scenario catalog. |

Tutorials: [01](../tutorials/01-score-the-anchor.md), [02](../tutorials/02-run-it-in-the-simulator.md).

## Simulate — `astro-mine sim`

```
astro-mine sim {run,record}
```

| Command | Flags | Notes |
|---|---|---|
| `run <scenario_id>` | `--seed` · `--out` · `--registry PATH` · `--metakernel PATH` | Takes a **Bench `ScenarioSpec` id**, resolves it to a Sim `Scenario`, runs real physics, writes MCAP. Warns and proceeds on unresolved providers (unlike `bench score`, which refuses). |
| `record` | `--scenario-file PATH` · `--seed` · `--out` · `--metakernel PATH` | Takes a **Sim `Scenario` JSON document**. Self-contained: no registry, no content, no network — and no kernels. |

**SPICE kernels.** `--metakernel PATH` furnishes the pool, defaulting to
`$ASTRO_MINE_SPICE_METAKERNEL`. Kernels are not shipped — get them from
[NAIF](https://naif.jpl.nasa.gov/naif/data.html). The **environment variable is also what
`astro-mine bench score --runner sim` uses**: Bench hands the runner a content store and nothing
else, so the runner reads the variable itself rather than Bench growing a vocabulary for SPICE. The
pool is validated against the episode's epoch window at startup, so a short kernel set fails
immediately rather than mid-run. See
[tutorial 02 §3](../tutorials/02-run-it-in-the-simulator.md).

## Train — `astro-mine learn`

One command, no subcommands.

| Flag | Notes |
|---|---|
| `--env-factory MODULE:ATTR` | **Required.** Zero-arg factory yielding a `SwarmEnv` or the Core-typed `(Environment, {AgentId: Asset})` pair. Shipped example: `astro_mine.sim.reference:make_reference_env_and_assets`. |
| `--config-json PATH` | A `TrainConfig` JSON; overrides flags. Reference config: `astro_mine.learn.reference/train_config.json`. |
| `--algorithm` · `--seed` · `--iterations` · `--rollout-steps` · `--hidden-sizes` | Training knobs (comma-separated widths, e.g. `64,64`). |
| `--fidelity {sim_high,surrogate,gpu_vectorized}` | Rollout fidelity tier. |
| `--num-workers` · `--ray-address` · `--batched-world` | Scale-out. `1` = tier-1 in-process. |
| `--export DIR` | Export the trained policy into a content-addressed store: `<dir>/<hex>/{model.onnx,policy_package.json}`, one entry per agent. Needs the `[export]` extra. **Must be an absolute path** — a relative one fails after writing the ONNX. |
| `--export-format onnx` · `--export-version` | ONNX is the only cross-component policy artifact; version defaults to `0.1.0`. |
| `--output PATH` | Run report JSON (default stdout). |

`astro-mine learn` is the deprecated alias.

Tutorial: [03](../tutorials/03-train-and-publish-a-policy.md).

## Author assets — `astro-mine fleet`

The platform's exemplar CLI: a complete authoring lifecycle in 14 subcommands.

| Command | What it does |
|---|---|
| `new <kind> <output>` | Scaffold a minimal, valid SADF asset. `--id` · `--name` · `--asset-version` · `--force`. |
| `validate <path>` | Schema conformance for one document. |
| `lint <path>...` | Judgement checks across one or more documents. |
| `resolve <path>` | Emit the canonical JSON form. |
| `package <path>` | Content-addressed bundle. `--out` · `--oci` · `--sign` · `--key` · `--json`. |
| `verify` | Verify an OCI asset artifact's signature, and that it loads. |
| `publish <path>` | Publish signed to a Hub registry. `--registry` (local dir or remote) · `--sign` · `--key` · `--pub` (re-verify the round trip) · `--namespace` · `--publisher`. |
| `catalog` | List a registry as the robot menu. `--registry` · `--requires TAG[,TAG...]` · `--preview REFERENCE` · `--format` · `--materialize`. |
| `import <path>` | Import URDF/SDF into SADF + USD/glTF geometry. `-o` · `--assets-dir` · `--format {urdf,sdf}`. |
| `fidelity <path>` | List an asset's multi-fidelity profiles. |
| `families` | List parametric asset families and their parameters. |
| `resolve-family` | Resolve a family to a concrete SADF document. |
| `export <path>` | Export SADF to URDF/SDF (ROS) or a USD stage (Sim/Studio). |
| `render <path>` | Preview/thumbnail. `-o` · `--format {glb,usd}` · `--fidelity {massmodel,kinematic,articulated}`. |

Tutorial: [04](../tutorials/04-author-an-asset.md).

## Author worlds — `astro-mine worlds`

| Command | What it does |
|---|---|
| `validate <path>...` | Validate authored WorldSpec documents. `--json`. |
| `schema` | Print the published WorldSpec JSON Schema by its `$id`. |
| `publish` | Publish a built world bundle to a local OCI-layout registry. |

Building a world from a WorldSpec is a Python/script path, not a CLI verb. Tutorial:
[05](../tutorials/05-author-a-world.md).

## Author autonomy — `astro-mine mind`, `astro-mine guard`

```
astro-mine mind {validate,compose,stacks}
```

| Command | What it does |
|---|---|
| `stacks` | List the 6 reference stacks and 13 manifests Mind ships. |
| `validate <stack>` | Schema **plus registry** check — an unregistered plugin fails. |
| `compose <stack>` | Resolve to tier → plugin @ version, and the entry-point group each came from. |

A bare reference-stack name resolves against the shipped set, **including the `.yaml` suffix**:
`astro-mine mind compose lunar_prospecting.yaml`.

> **There is deliberately no `mind run`.** Stepping a stack needs a Core `Environment`, which is
> Sim's job, and the narrow waist forbids Mind importing it. Execute through Bench/Sim.
> A Sim-backed `astro-mine mind run` is tracked in
> tracked as an open Mind issue (the `mind run` verb's scope).

```
astro-mine guard {validate,compile,falsify,sign}
```

| Command | What it does |
|---|---|
| `validate <spec>...` | Validate SafetySpecs. |
| `compile <spec>` | Compile to the content-addressed IR (prints `spec_hash` and `compiled_hash`). |
| `falsify <spec>` | Seeded adversarial search for a counterexample: an unshielded control that must breach, then the same attack behind the shield. `--trials N` sweeps seeds `0..N-1`, `--seed` names one; `--horizon`/`--sample-period` size the rollout. |
| `sign <spec>` | Sign the spec's content hash (offline dev signer). |

Pass `anchor` as the spec to use the shipped reference spec — all four accept it. `falsify` needs no
scenario: its plant is synthetic, and the search derives its start and its attack from the spec's own
safe set, so it runs on a spec you wrote. Tutorial:
[06](../tutorials/06-compose-a-planner-stack.md).

## Validate anything Core owns — `astro-mine core`

| Command | What it does |
|---|---|
| `validate <file>...` | Validate one or more documents. `--kind KIND` to force a format; default is to infer from the document's `$schema`. `-` reads stdin. |
| `kinds` | List the known formats and their schema `$id`s. |

`--json` on the top-level command for machine-readable output. See
[file-formats.md](file-formats.md).

## Publish and fetch artifacts — `astro-mine hub`

| Command | Flags |
|---|---|
| `publish` | `--registry` · `--name` · `--version` · `--kind {policy,world,asset,surrogate,plugin,schema,design,campaign}` · `--manifest` · `--key` · `--layer` (repeatable) |
| `search` | Discover artifacts. |
| `resolve` | Resolve a reference to a pinned digest. |
| `pull` | Pull and re-verify. |
| `verify` | Re-verify an artifact's supply chain. |
| `keygen` | `--out DIR` — writes `cosign.key` / `cosign.pub` (ECDSA P-256). |

`--registry` accepts a local OCI-layout directory (`./reg`) or a remote (`ghcr.io/astro-mine`,
`http://localhost:5000`).

> **Inconsistency:** `publish --kind` is validated against the closed set above; `search --kind`
> accepts any string.

## Publish content — `astro-mine link`, `astro-mine prospect`

Both ship exactly one subcommand:

| Command | What it does |
|---|---|
| `astro-mine link publish` | Publish a ContactPlan to a local OCI-layout registry. |
| `astro-mine prospect publish` | Publish a belief-prior bundle to a local registry. |

## Design — `astro-mine studio`

| Command | Flags |
|---|---|
| `serve` | `--host` (default `127.0.0.1`) · `--port` (default `8000`) · `--registry` · `--trusted-key` · `--signing-key` · `--cache-dir` · `--ui-dir` · `--no-ui` · `--no-seed` |

Composes the backend, wires the Hub seams from a local registry, mounts the built UI, and seeds an
example study. Tutorial: [07](../tutorials/07-design-a-swarm-in-studio.md).

## Scale out — `astro-mine cloud`

| Command | What it does |
|---|---|
| `submit` | Submit a JobSpec through a backend. |
| `expand` | Preview a SweepSpec's expansion. |
| `compile` | Compile a JobSpec to an engine manifest. |
| `sweep` | Compile a SweepSpec to an Argo Workflow. |
| `workflow` | Compile a WorkflowSpec to an Argo Workflow. |
| `backends` | List registered backends. |

The in-container harness is not a command: it is `python -m astro_mine.cloud.submission.harness`,
invoked by the pod that Cloud creates rather than typed by a person
([cli.md](../../architecture/cli.md) §10). Cloud itself is always optional — every tutorial in this
guide runs on one workstation.

---

## Commands that do not exist

Named here so you do not go looking.

| You might expect | Reality |
|---|---|
| `astro-mine seal ...` | **Seal has no CLI yet.** An archetypal sign/verify tool with no shell surface; signing is reached through Hub and Fleet, or the Python API. Tracked as [astro-mine-cli#17](https://github.com/astro-mine/astro-mine-cli/issues/17). |
| `astro-mine allocate ...` | No CLI. Allocate is a library plus the `astro_mine.allocate.solvers` plugin group. |
| `astro-mine spice ...`, `astro-mine surrogate ...` | No CLI. Libraries only. |
| `astro-mine mind run` | Deliberately absent — see above. |
| A world **build** verb | Building a world bundle from a WorldSpec is a script/Python path. `astro-mine worlds` covers validate, schema, publish. |
| `astro-mine prospect` authoring verbs | Prospect priors are Python objects, not an authored file format. Only `publish` exists. |

`console` and `view` are TypeScript packages with no Python CLI — see the
[console guide](../console.md).
