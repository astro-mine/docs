# File formats

The documents you author by hand, what each is for, who writes it, and a **real example that
validates**. Covers **UC-C9** (validate any Core-owned spec).

Every example path below is a file that exists in a repository. None were invented for this page,
and all of them pass `astro-mine-core validate`.

---

## One command checks them all

```bash
astro-mine-core kinds
```

```
action_batch    https://schemas.astro-mine.org/core/messages/v0.1/messages.schema.json
contact_plan    https://schemas.astro-mine.org/core/messages/v0.1/messages.schema.json
manifest        https://schemas.astro-mine.org/core/registry/v0.1/manifest.schema.json
mission         https://schemas.astro-mine.org/core/mission/v0.1/mission.schema.json
objective       https://schemas.astro-mine.org/core/objective/v0.1/objective.schema.json
plan            https://schemas.astro-mine.org/core/plan/v0.1/plan.schema.json
policy_package  https://schemas.astro-mine.org/core/policy/v0.1/policy_package.schema.json
run_provenance  https://schemas.astro-mine.org/core/provenance/v0.1/run_provenance.schema.json
sadf            https://schemas.astro-mine.org/sadf/v0.1/sadf.schema.json
```

```bash
astro-mine-core validate <file>...     # infers the kind from the document's $schema
astro-mine-core validate --kind sadf <file>
astro-mine validate <file>...          # the umbrella, routed to the owning component
```

Dispatch is on `$id`/`$schema`, so a document that identifies itself needs no `--kind`.

---

## Where the examples live

Two conventions coexist, for a reason worth knowing:

- **`examples/` in a repository** — browsable on GitHub, present in a clone, absent from an
  installed wheel. `astro-mine-core/examples/` holds **13 authored documents across 7 kinds** and is
  the main set.
- **Package data under `src/astro_mine/<comp>/reference/`** — reachable from an installed wheel via
  `importlib.resources`, which is why Guard's anchor SafetySpec moved there, and where Learn's
  `TrainConfig`, Sim's reference scenario, Mind's stacks, and Worlds' WorldSpec example live.

To reach package data:

```python
from importlib.resources import files
files("astro_mine.guard.reference").joinpath("safety_specs/anchor.safety.yaml").read_text()
```

---

## The nine Core-owned formats

### 1. SADF — Swarm Asset Description Format

**What:** a robot. Identity, frames, bodies with mass and inertia, capabilities, power, thermal,
sensors, comms, and multi-fidelity profiles. **Who authors it:** P4 Roboticist / Asset Author.
**Schema `$id`:** `https://schemas.astro-mine.org/sadf/v0.1/sadf.schema.json`

```
astro-mine-core/examples/assets/lunar-scout-rover.sadf.yaml
astro-mine-core/examples/assets/neo-sep-carrier.sadf.yaml
```

Plus **six shipped reference assets** as Fleet package data —
`astro_mine/fleet/library/{isru/isru-plant, logistics/hauler, manipulation/excavator,
orbital/lander, orbital/relay-orbiter, surface/prospecting-rover}.sadf.yaml` — which are the
anchor's fleet pins.

```bash
astro-mine-fleet new rover my-rover.sadf.yaml    # scaffold
astro-mine-fleet validate my-rover.sadf.yaml     # schema
astro-mine-fleet lint my-rover.sadf.yaml         # judgement
```

`capabilities` is the load-bearing field: Core's negotiation vocabulary, and how Mind and Allocate
decide who can be given which task. See [tutorial 04](../tutorials/04-author-an-asset.md).

### 2. ObjectiveSpec

**What:** what the mission is trying to achieve, in structured form — the input to a trade study or
a planner. **Who authors it:** P5 Mission Designer (usually through Studio's GUI rather than by
hand). **Schema `$id`:** `.../core/objective/v0.1/objective.schema.json`

```
astro-mine-core/examples/objectives/lunar-polar-ice-prospecting.objective.yaml
```

### 3. MissionSpec

**What:** an ordered set of phases, each in a regime (`launch_ascent`, `interplanetary_transit`,
`proximity_orbit`, `surface`, `ascent_return`, `earth_interface`). A single-`surface`-phase mission
is exactly today's campaign, which is why the schema is additive
([RFC-0001](../../rfc/0001-multi-regime-missions.md)). **Schema `$id`:**
`.../core/mission/v0.1/mission.schema.json`

```
astro-mine-core/examples/mission/lunar-surface-single-phase.mission.yaml
astro-mine-core/examples/mission/neo-sample-return-multiphase.mission.yaml
```

The multi-phase example is the shape Phase 3 fills in; the single-phase one is what runs today.

### 4. Plan / ContingentPlan

**What:** a plan as data — Core-owned so Mind, Guard, and Allocate exchange one representation
([RFC-0006](../../rfc/0006-plan-contingentplan.md)). **Schema `$id`:**
`.../core/plan/v0.1/plan.schema.json`

```
astro-mine-core/examples/plan/standing-control.plan.yaml
astro-mine-core/examples/plan/lunar-prospecting-contingent.plan.yaml
```

### 5. Plugin manifest

**What:** what a plugin is, what it registers, which Core interface versions it supports. Required
to publish a plugin to Hub. **Who authors it:** anyone extending the platform. **Schema `$id`:**
`.../core/registry/v0.1/manifest.schema.json`

```
astro-mine-core/examples/plugins/greedy-prospecting-baseline.manifest.yaml
astro-mine-core/examples/plugins/lunar-terramechanics-engine.manifest.yaml
```

See [how-to/write-a-plugin.md](../how-to/write-a-plugin.md) and
[tutorial 08](../tutorials/08-write-a-plugin.md).

### 6. PolicyPackage

**What:** the commons' unit of exchange — an ONNX model plus its IO signature, its **assumptions**
(comms observability, surrogate-fidelity caveats, action bounds, determinism), and its provenance.
**Who authors it:** nobody by hand — `astro-mine-learn --export` writes it. **Schema `$id`:**
`.../core/policy/v0.1/policy_package.schema.json`

```
astro-mine-core/examples/policy/minimal.policy-package.yaml
astro-mine-core/examples/policy/greedy-prospecting-baseline.policy-package.yaml
```

The `assumptions` block is what makes a published policy honest; see
[tutorial 03 §4](../tutorials/03-train-and-publish-a-policy.md).

### 7. RunProvenance

**What:** what produced a result — seeds, content digests, code and toolchain versions, lockfiles.
The record that makes CX-REPRO checkable rather than aspirational. **Schema `$id`:**
`.../core/provenance/v0.1/run_provenance.schema.json`

```
astro-mine-core/examples/run-provenance/minimal.run-provenance.yaml
astro-mine-core/examples/run-provenance/full.run-provenance.yaml
```

### 8. Messages — `action_batch`, `contact_plan`

**What:** the on-the-wire vocabulary. `action_batch` is what a policy emits per tick;
`contact_plan` is the comms schedule Link publishes and Sim scores `comms_robustness` against.
Both live in one schema. **Schema `$id`:** `.../core/messages/v0.1/messages.schema.json`

Authored by hand mainly for tests and fixtures; normally produced by Link and by policies. The
anchor's own contact plan is a published artifact (`astro-mine.link.lunar-polar-relay-dsn`), not a
file you write.

### 9. Units, frames and time

**What:** not a standalone document but a **cross-cutting contract**
([RFC-0007](../../rfc/0007-units-frames-wire-schema.md)) that the other formats reference: every
physical quantity on the wire carries its unit, every position its frame, every epoch its time
scale. A CRS with an implicit Earth datum on a lunar body is rejected outright, not defaulted.

This is why WorldSpec makes you state `crs.body`, `body_fixed_frame`, and `reference_radius_m`
explicitly. It is the difference between a number and a measurement.

---

## Formats owned outside Core

### WorldSpec — `astro-mine-worlds`

**What:** the declaration of a world: CRS, region, resolution, illumination and PSR parameters,
regolith fields. `spec_hash` — and therefore `world_hash` — is computed over exactly these bytes,
so two worlds that declare the same thing hash the same.

```
astro-mine-worlds/src/astro_mine/worlds/spec/examples/synthetic_polar.world.yaml
```

A small synthetic lunar south-polar world, deliberately buildable **without the LOLA DEM or SPICE
kernels** — the one to copy.

```bash
astro-mine new world my.world.yaml               # scaffold
astro-mine-worlds validate my.world.yaml         # validate
astro-mine-worlds schema                         # print the published JSON Schema
```

The anchor world is *not* authorable as a static document: its region derives from an ingested DEM
grid pinned by a digest the repo does not contain. See
[tutorial 05](../tutorials/05-author-a-world.md).

### SafetySpec — `astro-mine-guard`

**What:** the safety contract — keep-out volumes, scalar bounds, temporal-logic monitors, admissible
modes and tasks, and a safe pose ([RFC-0004](../../rfc/0004-safetyspec-safety-contract.md)).
Compiles to a content-addressed IR the Rust safety core executes.

```
astro-mine-guard/src/astro_mine/guard/reference/safety_specs/anchor.safety.yaml
```

Package data, reachable from an installed wheel. Pass `anchor` to any Guard subcommand to use it:

```bash
astro-mine-guard validate anchor
astro-mine-guard compile anchor      # prints spec_hash and compiled_hash
astro-mine-guard falsify anchor
```

### Stack spec — `astro-mine-mind`

**What:** an autonomy stack as a document — which plugin fills each tier (mission, TAMP, control,
shield), at which version.

```
astro-mine-mind/src/astro_mine/mind/reference/stacks/lunar_prospecting.yaml
  (+ _allocate, _anchor, _backends, _bt, _degrade variants)
```

```bash
astro-mine-mind stacks
astro-mine-mind validate lunar_prospecting.yaml     # schema + registry
astro-mine-mind compose lunar_prospecting.yaml
```

### TrainConfig — `astro-mine-learn`

**What:** a training run's configuration, schema-validated, consumed by `--config-json`.

```
astro-mine-learn/src/astro_mine/learn/reference/train_config.json
```

### ScenarioSpec / Scenario

Two distinct things, both called "scenario" — see
[concepts/scenarios.md](../concepts/scenarios.md). `ScenarioSpec` (Bench) pins content by digest;
`Scenario` (Sim) is the materialized episode. The zoo's specs are package data in
`astro-mine-bench`; Sim's reference scenario is package data at
`astro_mine/sim/reference/scenario.json`.

---

## Not a file format: Prospect priors

Prospect's resource priors are **Python objects, not authored documents** — there is no `from_yaml`
anywhere in its source, and `SHACKLETON_CRS` / `SHACKLETON_PRIOR_GRID` are code in
`prospect/priors/catalog.py`.

This is a stated design question, not an oversight: whether a belief prior over a geospatial grid
*should* have a hand-authored file format is unresolved (gap **G2.15**). Until it is answered there
is nothing to document, and this page will not invent a schema for it. Publishing a prior bundle
works today (`astro-mine-prospect publish`); authoring one is Python.
