# CLI reference

Every shipped command, organized by **what you are trying to do** rather than by which repository
owns it. Covers **UC-A3** (discover which command does what) and **UC-A4** (find the docs for my
task).

Verified against `--help` output at authoring time. Where a command does not exist, this page says
so rather than omitting it.

---

## Naming: two schemes, one rule

**The rule** (`conventions.md` §13, normative; [RFC-0011](../../rfc/0011-umbrella-cli.md)):

- A component's direct console script is **`astro-mine-<package>`** — uniform prefix, named after
  its package. This removes the `PATH` land-grab of generic bare names.
- The discoverable surface above them is **`astro-mine <verb>`** — verb-first, because a user
  guesses the *action*. Component-scoped actions read as `astro-mine <component> <verb>`.
- The umbrella **discovers** verbs from the `astro_mine.cli` entry-point group. A component
  contributes a verb by declaring an entry point, **never by a PR to the umbrella**.

**What you will still find in the wild.** Four bare binaries — `fleet`, `worlds`, `link`,
`prospect` — and the mis-nouned `astro-mine-train` predate the rule. They are kept as **aliases for
one deprecation cycle and removed at the public-flip gate**. They work today, they print
deprecation warnings in some cases, and you should not write them down. New CLIs are born prefixed;
the alias surface only shrinks.

So if you find `fleet validate` in a blog post: it is the old name for `astro-mine-fleet validate`,
and it will stop working.

---

## The umbrella

```bash
astro-mine --help                # verbs available here, plus verbs whose component is missing
astro-mine <verb> --help         # a verb's own options
astro-mine --version
```

The umbrella's own three verbs:

| Command | What it does |
|---|---|
| `astro-mine validate <file>...` | Validate an authored document. Routed to the component that owns its format; the umbrella owns no schema. `--json` for machine-readable output. |
| `astro-mine new [kind] [output]` | Scaffold an authored document. Each kind is written by the component owning that format. Omit the kind to list them. |
| `astro-mine plugin new <kind> <output>` | Scaffold a plugin package against a live extension group. |

**It degrades honestly.** A verb whose component is not installed is still listed, with the
distribution that provides it:

```
Available from components that are not installed here:
  cloud     submit and manage cluster jobs [astro-mine-cloud]
  studio    the design studio (`studio serve`) [astro-mine-studio]
  train     train a policy and export it [astro-mine-learn]
```

Never a traceback, never "unknown command".

### Scaffold kinds

`astro-mine new <kind>` — authored documents:

| Kind | Document | Provided by |
|---|---|---|
| `asset` | a SADF asset | `astro-mine-fleet` |
| `safety` | a SafetySpec | `astro-mine-guard` |
| `stack` | an autonomy stack spec | `astro-mine-mind` |
| `world` | a WorldSpec | `astro-mine-worlds` |

`astro-mine plugin new <kind>` — plugin packages, one per live extension group:

| Kind | Entry-point group | Provided by |
|---|---|---|
| `algorithm` | `astro_mine.learn.algorithms` | `astro-mine-learn` |
| `curriculum` | `astro_mine.learn.curricula` | `astro-mine-learn` |
| `field-model` | `astro_mine.field_models` | `astro-mine-worlds` |
| `provider` | `astro_mine.providers` | `astro-mine-sim` |
| `runner` | `astro_mine.bench.runners` | `astro-mine-bench` |
| `solver` | `astro_mine.allocate.solvers` | `astro-mine-allocate` |
| `tier` | `astro_mine.mind.tier_plugins` | `astro-mine-mind` |
| `cli` | `astro_mine.cli` | `astro-mine-cli` |

What these scaffolds emit are the recipes in
[how-to/write-a-plugin.md](../how-to/write-a-plugin.md).

---

## Run and score a benchmark — `astro-mine-bench`

```
astro-mine-bench {score,fetch,submit,list,zoo-sync,zoo-search}
```

| Command | Flags | Notes |
|---|---|---|
| `list` | — | The scenario ids in the packaged zoo. |
| `score [scenario_id]` | `--seeds SEED...` · `--runner NAME` · `--registry PATH` · `--json` | Default scenario `lunar-polar-ice-prospecting-v1`; default runner **`fixture`** (a deterministic trace, not physics). `sim` needs `astro-mine-sim[bench]` + fetched content. The runner is recorded in the scorecard and its hash. |
| `fetch [scenario_id]` | `--registry PATH` · `--from REGISTRY` · `--trusted-key PATH` | Resolves the scenario's pins by digest, mirrors them locally, verifies fail-closed. Anchor ≈ **461 MB**; needs `$GITHUB_TOKEN` with `read:packages` while the org is private. Idempotent, then offline. `--from` defaults to `ghcr.io/astro-mine`. |
| `submit` | `--hub-ref REF` \| `--policy-ref MODULE:ATTR` \| `--job ID` · `--scenario-id ID` · `--to URL` · `--method` · `--author` · `--wait` · `--token-file` · `--json` | `--hub-ref` is the reproducible path. `--policy-ref` is local/dev and **not leaderboard-grade**. Token from `$ASTRO_MINE_BENCH_TOKEN`, never a flag. |
| `zoo-sync` | — | Seed the Postgres/pgvector catalog from the packaged zoo (operator task, P7). |
| `zoo-search` | — | Similarity-search the hosted scenario catalog. |

Tutorials: [01](../tutorials/01-score-the-anchor.md), [02](../tutorials/02-run-it-in-the-simulator.md).

## Simulate — `astro-mine-sim`

```
astro-mine-sim {run,record}
```

| Command | Flags | Notes |
|---|---|---|
| `run <scenario_id>` | `--seed` · `--out` · `--registry PATH` | Takes a **Bench `ScenarioSpec` id**, resolves it to a Sim `Scenario`, runs real physics, writes MCAP. Warns and proceeds on unresolved providers (unlike `bench score`, which refuses). |
| `record` | `--scenario-file PATH` · `--seed` · `--out` | Takes a **Sim `Scenario` JSON document**. Self-contained: no registry, no content, no network. |

> **Gap:** neither subcommand furnishes a SPICE kernel pool, and there is no `--metakernel` flag, so
> a Sim-backed anchor run cannot be driven from a shell alone. See
> [tutorial 02 §3](../tutorials/02-run-it-in-the-simulator.md) for the wrapper that works.

## Train — `astro-mine-learn`

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

`astro-mine-train` is the deprecated alias.

Tutorial: [03](../tutorials/03-train-and-publish-a-policy.md).

## Author assets — `astro-mine-fleet`

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

## Author worlds — `astro-mine-worlds`

| Command | What it does |
|---|---|
| `validate <path>...` | Validate authored WorldSpec documents. `--json`. |
| `schema` | Print the published WorldSpec JSON Schema by its `$id`. |
| `publish` | Publish a built world bundle to a local OCI-layout registry. |

Building a world from a WorldSpec is a Python/script path, not a CLI verb. Tutorial:
[05](../tutorials/05-author-a-world.md).

## Author autonomy — `astro-mine-mind`, `astro-mine-guard`

```
astro-mine-mind {validate,compose,stacks}
```

| Command | What it does |
|---|---|
| `stacks` | List the 6 reference stacks and 13 manifests Mind ships. |
| `validate <stack>` | Schema **plus registry** check — an unregistered plugin fails. |
| `compose <stack>` | Resolve to tier → plugin @ version, and the entry-point group each came from. |

A bare reference-stack name resolves against the shipped set, **including the `.yaml` suffix**:
`astro-mine-mind compose lunar_prospecting.yaml`.

> **There is deliberately no `mind run`.** Stepping a stack needs a Core `Environment`, which is
> Sim's job, and the narrow waist forbids Mind importing it. Execute through Bench/Sim.
> A Sim-backed `astro-mine-mind run` is tracked in
> [astro-mine-mind#25](https://github.com/astro-mine/astro-mine-mind/issues/25).

```
astro-mine-guard {validate,compile,falsify,sign}
```

| Command | What it does |
|---|---|
| `validate <spec>...` | Validate SafetySpecs. |
| `compile <spec>` | Compile to the content-addressed IR (prints `spec_hash` and `compiled_hash`). |
| `falsify <spec>` | Seeded adversarial search on the anchor scenario. |
| `sign <spec>` | Sign the spec's content hash (offline dev signer). |

Pass `anchor` as the spec to use the shipped reference spec. Tutorial:
[06](../tutorials/06-compose-a-planner-stack.md).

## Validate anything Core owns — `astro-mine-core`

| Command | What it does |
|---|---|
| `validate <file>...` | Validate one or more documents. `--kind KIND` to force a format; default is to infer from the document's `$schema`. `-` reads stdin. |
| `kinds` | List the known formats and their schema `$id`s. |

`--json` on the top-level command for machine-readable output. See
[file-formats.md](file-formats.md).

## Publish and fetch artifacts — `astro-mine-hub`

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

## Publish content — `astro-mine-link`, `astro-mine-prospect`

Both ship exactly one subcommand:

| Command | What it does |
|---|---|
| `astro-mine-link publish` | Publish a ContactPlan to a local OCI-layout registry. |
| `astro-mine-prospect publish` | Publish a belief-prior bundle to a local registry. |

## Design — `astro-mine-studio`

| Command | Flags |
|---|---|
| `serve` | `--host` (default `127.0.0.1`) · `--port` (default `8000`) · `--registry` · `--trusted-key` · `--signing-key` · `--cache-dir` · `--ui-dir` · `--no-ui` · `--no-seed` |

Composes the backend, wires the Hub seams from a local registry, mounts the built UI, and seeds an
example study. Tutorial: [07](../tutorials/07-design-a-swarm-in-studio.md).

## Scale out — `astro-mine-cloud`

| Command | What it does |
|---|---|
| `submit` | Submit a JobSpec through a backend. |
| `expand` | Preview a SweepSpec's expansion. |
| `compile` | Compile a JobSpec to an engine manifest. |
| `sweep` | Compile a SweepSpec to an Argo Workflow. |
| `workflow` | Compile a WorkflowSpec to an Argo Workflow. |
| `backends` | List registered backends. |

`astro-mine-cloud-harness` is the in-container harness entry point. Cloud is always optional —
every tutorial in this guide runs on one workstation.

---

## Commands that do not exist

Named here so you do not go looking.

| You might expect | Reality |
|---|---|
| `astro-mine-seal ...` | **Seal has no CLI.** An archetypal sign/verify tool with no shell surface; signing is reached through Hub and Fleet, or the Python API. |
| `astro-mine-allocate ...` | No CLI. Allocate is a library plus the `astro_mine.allocate.solvers` plugin group. |
| `astro-mine-spice ...`, `astro-mine-surrogate ...` | No CLI. Libraries only. |
| `astro-mine-mind run` | Deliberately absent — see above. |
| A world **build** verb | Building a world bundle from a WorldSpec is a script/Python path. `astro-mine-worlds` covers validate, schema, publish. |
| `astro-mine-prospect` authoring verbs | Prospect priors are Python objects, not an authored file format. Only `publish` exists. |

`console` and `view` are TypeScript packages with no Python CLI — see the
[console guide](../console.md).
