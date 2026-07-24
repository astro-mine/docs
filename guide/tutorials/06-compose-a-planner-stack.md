# Tutorial 06 — compose a planner stack

**Persona:** P2 Planning / Autonomy Researcher
**Covers:** UC-E1 (compose a stack from a spec) · UC-E2 (validate a stack spec) · UC-E3 (run a
composed stack against the anchor) · UC-E4 (author a SafetySpec) · UC-E5 (validate/compile a
SafetySpec)
**Time:** ~30 minutes.

P2's success sentence: *"my CP-SAT alternative dropped in behind the same interface and I can prove
it's better."* This tutorial composes an autonomy stack from a spec, swaps a tier, attaches a safety
contract, and measures the result against the same benchmark everyone else uses.

---

## 1. What a stack is

Mind composes autonomy as a **three-tier spine plus a shield**:

| Tier | Answers |
|---|---|
| `mission` | what are we trying to achieve, and in what order? |
| `tamp` | task-and-motion planning — how do we do it, concretely? |
| `control` | what actuator commands realize that, this tick? |
| `shield` | is this action admissible, and what do we do if not? |

Each tier is filled by a **plugin**, resolved from the `astro_mine.mind.tier_plugins` entry-point
group. A stack spec is a document naming which plugin fills each tier, at which version. Swapping a
planner means editing one line, not forking anything.

## 2. See what ships

```bash
uv pip install ./astro-mine-mind ./astro-mine-guard
astro-mine-mind stacks
```

```
reference stacks (6) — load with astro_mine.mind.reference.load_stack_resource(<name>):
  lunar_prospecting.yaml
  lunar_prospecting_allocate.yaml
  lunar_prospecting_anchor.yaml
  lunar_prospecting_backends.yaml
  lunar_prospecting_bt.yaml
  lunar_prospecting_degrade.yaml

reference manifests (13) — tier/shield plugin descriptors:
  constraint_shield.yaml  control.yaml       greedy_allocator.yaml  mission.yaml
  mpc_control.yaml        ompl_tamp.yaml     onnx_control.yaml      pddl_mission.yaml
  pid_control.yaml        sampling_tamp.yaml shield.yaml            tamp.yaml
  up_mission.yaml
```

Six stacks, and each demonstrates one thing — **choose between them rather than reading all six**:

| Stack | What it demonstrates |
|---|---|
| `lunar_prospecting` | the base three-tier spine — start here |
| `lunar_prospecting_backends` | native engines behind the same tier interfaces |
| `lunar_prospecting_allocate` | region assignment delegated to Allocate |
| `lunar_prospecting_anchor` | the anchor wired to the real Guard shield |
| `lunar_prospecting_bt` | behavior-tree execution |
| `lunar_prospecting_degrade` | degrade-not-collapse under the shield |

## 3. Validate and compose (UC-E1, UC-E2)

```bash
astro-mine-mind validate lunar_prospecting.yaml
```

```
OK  lunar_prospecting.yaml: valid stack 'reference-lunar-prospecting' (3 tiers)
```

> A bare reference-stack name resolves against the shipped set — **including the `.yaml` suffix**,
> exactly as `astro-mine-mind stacks` prints it. `lunar_prospecting` without the suffix is read as a
> file path and fails with `cannot read file`.

**`validate` is schema plus registry.** It checks the document *and* that every plugin it names is
actually registered. A stack referencing a tier nobody installed fails here, not three layers deep
at runtime.

```bash
astro-mine-mind compose lunar_prospecting.yaml
```

```
stack: reference-lunar-prospecting
execution: composition
entry-point group: astro_mine.mind.tier_plugins
tiers (role -> plugin @ version):
  mission    mind.reference.mission @ 0.1.0
  tamp       mind.reference.tamp @ 0.1.0
  control    mind.reference.control @ 0.1.0
  shield     mind.reference.shield @ 0.1.0
core interface versions: env=0.1.0, messages=0.1.0, mission=0.1.0, objective=0.1.0, policy=0.1.0,
                         registry=0.1.0, resource_field=0.1.0, sadf=0.1.0, world_provider=0.1.0
```

`compose` resolves the whole stack and shows **which entry-point group each plugin came from** and
which Core interface versions it binds to. This is the command to run when something is not the
plugin you thought it was.

## 4. Swap a tier

Copy a stack, change the plugin named in one tier, re-validate:

```bash
python - <<'PY'
from astro_mine.mind.reference import load_stack_resource
open("my-stack.yaml", "w").write(load_stack_resource("lunar_prospecting.yaml"))
PY
# edit my-stack.yaml: point `tamp` at your plugin id
astro-mine-mind validate my-stack.yaml
astro-mine-mind compose my-stack.yaml
```

If your plugin is not registered, `validate` says so. Writing and registering one is
[tutorial 08](08-write-a-plugin.md) — the `astro_mine.mind.tier_plugins` group, scaffolded by
`astro-mine plugin new tier`.

## 5. The safety contract (UC-E4, UC-E5)

A stack's `shield` tier enforces a **SafetySpec**: keep-out volumes, scalar bounds, temporal-logic
monitors, admissible modes and tasks, and a safe pose. Guard ships the anchor spec as **package
data**, so it is reachable from an installed wheel:

```
astro-mine-guard/src/astro_mine/guard/reference/safety_specs/anchor.safety.yaml
```

Pass `anchor` to any Guard subcommand to use it:

```bash
astro-mine-guard validate anchor
```

```
OK  safety_specs/anchor.safety.yaml: valid SafetySpec anchor-lunar-polar-v0 (sha256:e2a1737c6d05cb1b89f75d1dbcd5cb31be46fb9027a75bb1b0b0b642c8f1d0ee)
```

```bash
astro-mine-guard compile anchor
```

```
spec_id:       anchor-lunar-polar-v0
spec_hash:     sha256:e2a1737c6d05cb1b89f75d1dbcd5cb31be46fb9027a75bb1b0b0b642c8f1d0ee
compiled_hash: sha256:d2c0d90eaba138648d942cbf4b9ba2caef23727529ce7abc1b37f6610a938e2b
{"action_limits": {...}, "keep_out_terms": [...], "monitors": [...], "predicate_table": {...},
 "resource_bounds": {...}, "safe_pose": {...}, "scalar_bounds": [...]}
```

**Both hashes matter.** `spec_hash` identifies what you wrote; `compiled_hash` identifies the IR the
Rust safety core will actually execute. The compiled form is flat and bounded on purpose — a fixed
predicate table, a declared `resource_bounds` block (`predicate_slot_count`, `max_history_len`,
`worst_case_term_count`) — because a safety monitor with unbounded resource use is not a safety
monitor.

Reading the anchor spec's compiled output tells you what it enforces: three keep-out terms (a
30 m sphere around the lander, a PSR crater box, a slope half-space), six scalar bounds (energy
floor, power floor, thermal floor and ceiling, anchor torque, traverse speed ≤ 0.1 m/s), and two
temporal monitors over a 1,209,600-sample window — a 14-day lunar night — for SOC survival and
thermal survival.

```bash
astro-mine-guard falsify anchor      # seeded adversarial search on the anchor scenario
astro-mine-guard sign anchor         # sign the spec's content hash (offline dev signer)
```

`falsify` is the one to run before you trust a spec you wrote: it actively searches for a
counterexample rather than waiting for one.

Author your own with `astro-mine new safety my.safety.yaml`, then `validate` → `compile` →
`falsify` → `sign`.

## 6. Measure it (UC-E3)

**Mind does not run episodes, deliberately.** Stepping a stack needs a Core `Environment`, which is
Sim's job; Mind importing Sim would put an engine dependency behind the planning interface
([concepts/narrow-waist.md](../concepts/narrow-waist.md)). So composing is Mind's, executing is
Bench and Sim's:

```bash
python score_sim.py score lunar-polar-ice-prospecting-v1 --runner sim --seeds 1001 1002 1003 1004 1005
```

(the wrapper from [tutorial 02 §3](02-run-it-in-the-simulator.md), which furnishes SPICE).

That is the whole point of the exercise: your stack and the reference baseline are scored by the
**same** benchmark, over the same pinned content and the same seeds, producing scorecards whose
hashes differ only because the runs differ. *"I can prove it's better"* is a comparison of two
scorecards, and the pins are what make the comparison mean anything.

> **UC-E3 has no single command today.** There is no `astro-mine-mind run` — a Sim-backed one is
> tracked in [astro-mine-mind#25](https://github.com/astro-mine/astro-mine-mind/issues/25). Until it
> lands, the hop through Bench/Sim above is the path.

---

## 7. Where next

- **Write the tier or solver you wanted:** [08 — write a plugin](08-write-a-plugin.md).
- **Compare against learned policies:** [03 — train and publish a policy](03-train-and-publish-a-policy.md).
- **Every Mind and Guard flag:** [reference/cli.md](../reference/cli.md).
- **Why the seams are where they are:** [concepts/narrow-waist.md](../concepts/narrow-waist.md).
