# Tutorial 03 — train and publish a policy

**Persona:** P1 Benchmark Researcher · **the Phase-1 flywheel**
**Covers:** UC-D1 (train on one workstation) · UC-D2 (export an ONNX PolicyPackage) · UC-D3
(evaluate honestly) · UC-D4 (train against the anchor) · UC-G1 (publish signed) · UC-G4 (submit) ·
UC-G5 (see your rank)
**Time:** the first training run takes under a minute. The anchor takes as long as you give it.

P1's whole success sentence: *"my policy is on the board by Friday."* This tutorial goes from a
clean environment to an ONNX policy artifact on a registry, submitted to a leaderboard, with the
caveats that make it a contribution to a commons rather than a number.

---

## 1. Start on the reference environment, not the anchor

The anchor is a **benchmark**: ~461 MB of content over a 43,200-tick lunar month. It is the wrong
tool for a first training run.

Sim ships a **reference environment** as package data — a small synthetic scenario, no content, no
registry, no network, milliseconds per episode — exposed as an importable factory:

```
astro_mine.sim.reference:make_reference_env_and_assets
```

It hands back the Core-typed `(Environment, {AgentId: Asset})` pair, which is what lets Learn derive
per-agent spaces from real SADF **without either package importing the other**. Learn stays
Sim-free; Sim never hears of Learn.

```bash
uv pip install "./astro-mine-learn[export]" ./astro-mine-sim
```

The `[export]` extra pulls the ONNX toolchain. Without it, training works and `--export` does not.

## 2. Train (UC-D1)

Learn ships a schema-validated reference `TrainConfig` as package data:

```python
from importlib.resources import files
print(files("astro_mine.learn.reference").joinpath("train_config.json"))
```

```json
{
  "seed": 0,
  "iterations": 2,
  "rollout_steps": 32,
  "hidden_sizes": [32, 32],
  "lr": 0.003,
  "gamma": 0.99,
  "gae_lambda": 0.95,
  "clip": 0.2,
  "update_epochs": 1,
  "entropy_coef": 0.0,
  "value_coef": 0.5,
  "use_rnn": false,
  "mixer": "qmix",
  "epsilon": 0.1,
  "fidelity": "sim_high",
  "num_workers": 1
}
```

Two iterations of 32 steps is a **smoke configuration** — it proves the pipeline, it does not train
anything. Raise `iterations` and `rollout_steps` once the path works end to end.

```bash
astro-mine-learn \
  --env-factory astro_mine.sim.reference:make_reference_env_and_assets \
  --config-json /path/to/train_config.json \
  --output train-report.json
```

> The binary is `astro-mine-learn`. `astro-mine-train` still works and prints a deprecation warning:
> it is a **mis-nouned legacy alias kept for one cycle**, removed at the public flip (RFC-0011 §5).

The run report carries the learning curve, throughput, and the produced policy's provenance:

```json
{
  "algorithm": "mappo",
  "learning_curve": [-0.06900187586882726, -0.06898980815469884],
  "config": { "...": "the resolved TrainConfig" },
  "provenance": { "...": "seed, code version, toolchain" }
}
```

**`StepResult.rewards` is empty by design.** Core v0.1 is *reward-free by default* — scoring is
Bench's job, and reward shaping is the consumer's. If you train against the environment as-is you
are training against a flat signal. Defining a reward is your first real modelling decision, not an
oversight in the platform.

## 3. Export the policy (UC-D2)

This is the commons' **unit of exchange**: an ONNX model plus a typed `PolicyPackage` describing how
to use it and what it assumes.

```bash
astro-mine-learn \
  --env-factory astro_mine.sim.reference:make_reference_env_and_assets \
  --config-json /path/to/train_config.json \
  --export /absolute/path/to/policies \
  --output train-report.json
```

```
exported excavator: sha256:d06cbbcd322ad9ec3f917468781e18729c9c3a074321e57a0f75ed4dbc894133 -> /abs/policies/d06cbbcd.../model.onnx
exported relay:     sha256:6f15c93ebf10788e3ee65d9dd6037617a793885b9e74a7482189bcd1f025576a -> /abs/policies/6f15c93e.../model.onnx
exported rover:     sha256:4b6345006f45abaab1928029223e8054a1ceaf62e4489022a049b54956340005 -> /abs/policies/4b634500.../model.onnx
```

One content-addressed entry **per agent kind**, each holding `model.onnx` and
`policy_package.json`. Before anything is written, an **ONNX-Runtime equivalence gate** runs: the
exported graph must reproduce the trained network's outputs. A model that does not survive the
round trip is not written.

> ⚠️ **`--export` must be an absolute path.** With a relative one the export writes `model.onnx`,
> then dies with `ValueError: relative path can't be expressed as a file URI` before writing
> `policy_package.json`, leaving a half-written entry. A defect, not intended behavior — pass an
> absolute path.

`--export-format onnx` is the only format (ONNX is the one cross-component policy artifact) and
`--export-version` stamps the SemVer on the package (default `0.1.0`).

## 4. What is in a PolicyPackage, and why it matters

```json
{
  "policy_package_version": "0.1",
  "policy_package": {
    "name": "mappo.rover",
    "version": "0.1.0",
    "onnx_model": {
      "digest": "sha256:4b6345006f45abaab1928029223e8054a1ceaf62e4489022a049b54956340005",
      "opset": 17,
      "uri": "file:///abs/policies/4b634500.../model.onnx"
    },
    "io_signature": {
      "inputs": [{"name": "obs", "dtype": "float32", "shape": [-1, 13]}],
      "observation_space": {"flat_dim": 13, "comms_dim": 0, "recurrent": false},
      "action_space": {"outputs": [
        {"name": "kind", "kind": "discrete", "dim": 2},
        {"name": "mode", "kind": "discrete", "dim": 2},
        {"name": "goto", "kind": "box", "dim": 3}]}
    },
    "assumptions": {
      "deterministic": true,
      "comms_observability": null,
      "surrogate_fidelity_caveats": [],
      "action_bounds": {"goto": {"dim": 3, "low": -1.0, "high": 1.0}}
    },
    "provenance": {
      "seed": 0,
      "code_version": "0.1.dev17",
      "toolchain_version": "torch==2.13.0+cpu;gymnasium==1.2.2;numpy==2.5.1",
      "env_lockfile": null,
      "input_hashes": []
    },
    "core_interfaces": {"env": "0.1.0", "messages": "0.1.0", "policy": "0.1.0", "sadf": "0.1.0"}
  }
}
```

**`assumptions` is the honest part, and it is not optional.**

- `comms_observability` — what the policy assumed it could see. A policy trained with perfect
  comms will behave differently under a real contact plan, and a consumer needs to know that
  before, not after.
- `surrogate_fidelity_caveats` — if you trained on a surrogate fidelity tier, this records the
  error bounds you accepted. Empty here because this run used `sim_high`.
- `io_signature` — what it consumes and emits, so another component can bind to it without reading
  your training code.
- `provenance` — seed, code version, toolchain versions. This is what makes a third party able to
  reproduce you.

A policy published without its caveats is a number, not a contribution.

## 5. Evaluate honestly (UC-D3)

Before publishing, score it the way [tutorial 02](02-run-it-in-the-simulator.md) scores the
baseline, and do it across **seeds**, not one:

```bash
python score_sim.py score lunar-polar-ice-prospecting-v1 --runner sim --seeds 1001 1002 1003 1004 1005
```

Report the seed sweep, not your best seed. The anchor's public seeds are `1001–1005`; the
leaderboard scores against **held-out seeds** whose commitment hash ships in the scenario, so a
policy tuned to the public five will not survive the transfer. That is the design working.

**Training against the anchor (UC-D4)** means pointing `--env-factory` at a Sim-backed factory over
the fetched anchor content rather than the reference environment — the same command, a heavier
world, and the SPICE prerequisite from [tutorial 02](02-run-it-in-the-simulator.md) §3.

**Scale-out (UC-D5)** is optional and never a prerequisite: `--num-workers` for vectorized rollouts,
`--ray-address` for a Ray cluster, `astro-mine-cloud submit` to wrap the same entry point in a
KubeRay job. The training entry point does not change — *"the same code with a different executor,
never a fork."* **Experiment tracking (UC-D6)** is MLflow, third-party and optional.

## 6. Publish it (UC-G1)

```bash
astro-mine-hub keygen --out ./keys
astro-mine-hub publish \
  --registry ./myreg \
  --name mappo-rover --version 0.1.0 --kind policy \
  --manifest ./manifest.json \
  --layer /abs/policies/4b634500.../model.onnx \
  --layer /abs/policies/4b634500.../policy_package.json \
  --key ./keys/cosign.key
```

`--kind` is a closed set — `policy, world, asset, surrogate, plugin, schema, design, campaign` —
and `--manifest` is a Core plugin manifest describing the artifact. The registry can be a local
OCI-layout directory (as here) or a remote (`ghcr.io/astro-mine`). Publishing is always signed;
admission re-verifies.

## 7. Submit it (UC-G4, UC-G5)

```bash
export ASTRO_MINE_BENCH_TOKEN=<your leaderboard token>
astro-mine-bench submit \
  --hub-ref sha256:4b6345006f45abaab1928029223e8054a1ceaf62e4489022a049b54956340005 \
  --scenario-id lunar-polar-ice-prospecting-v1 \
  --to https://leaderboard.example \
  --method "MAPPO, 32x32, reward v3" --author "your name" \
  --wait
```

- **`--hub-ref` is the path a real submission takes.** The artifact is referenced by digest and
  verified fail-closed, so the entry is reproducible by anyone.
- **`--policy-ref module:attr` is the local/dev path.** It runs sandboxed like any submission, but
  nothing pins what the reference resolves to — it is explicitly **not leaderboard-grade**.
- The bearer token comes from `$ASTRO_MINE_BENCH_TOKEN` or `--token-file`, **never a flag**.
  Identity comes from the token alone.
- `--wait` polls to a terminal status and prints the resulting submission and rank.

Your entry renders with the runner that produced it. Reading the board is account-free — see the
[console guide](../console.md) for the leaderboard surface (UC-G5).

---

## 8. The flywheel

That is the loop the commons runs on: **train → export with honest assumptions → publish by digest
→ submit → someone else pulls your digest and reproduces you.** Every step is content-addressed and
signed, which is what makes the last one possible.

- **Score a stack instead of a learned policy:** [06 — compose a planner stack](06-compose-a-planner-stack.md).
- **Register your algorithm so others can use it:** [08 — write a plugin](08-write-a-plugin.md).
- **Every flag:** [reference/cli.md](../reference/cli.md).
- **The PolicyPackage format:** [reference/file-formats.md](../reference/file-formats.md).
