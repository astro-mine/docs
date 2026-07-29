# Determinism & provenance

**A result is a claim. Provenance is what makes the claim checkable.**

## What determinism means here

Given the same scenario, the same seeds, the same content digests, and the same runner, a scored
run produces a **byte-identical scorecard**. You can check this yourself in one command, twice:

```bash
astro-mine bench score --seeds 1001 1002 | grep scorecard
astro-mine bench score --seeds 1001 1002 | grep scorecard
```

```
scorecard: sha256:b2547ddbdab91c6f16eda86c4759e9090ca65961126fdf92883bf647c57c7feb
scorecard: sha256:b2547ddbdab91c6f16eda86c4759e9090ca65961126fdf92883bf647c57c7feb
```

This is not a promise the platform asks you to trust — it is a property you can test, and the
repository's own reproducibility gates test it in CI.

## What a scorecard certifies

A `Scorecard` binds together, and hashes over:

| Field | Why it is in the hash |
|---|---|
| the metrics | the result itself |
| the scenario id | which benchmark |
| the seeds | which episodes |
| **the runner** | **what actually executed** |

That last one is why `runner` is a **required** field. `fixture/0.1.0` is a deterministic recorded
trace with no physics; `astro-mine-sim/0.1.0` is the engine. Both are legitimate; conflating them is
not. Because the runner is in the hash, a fixture result and a Sim result can never collide, and
"which one did you run?" is answerable from the artifact rather than from memory.

**What a scorecard does not certify:** that the numbers are good, that the policy generalizes, or
that the model of reality underneath is accurate. It certifies *this claim came from this
computation*.

## RunProvenance

For a run, the `RunProvenance` document records what produced it: seeds, input content digests,
code version, toolchain versions, environment lockfile, and — when a run happened under Cloud — the
image digest, the Core interface version, and the MLflow run id, injected as a `RunContext` and
folded into the artifact's provenance. That completes the chain from build time to run time.

An exported `PolicyPackage` carries the same idea for a trained artifact:

```json
"provenance": {
  "seed": 0,
  "code_version": "0.1.dev17",
  "toolchain_version": "torch==2.13.0+cpu;gymnasium==1.2.2;numpy==2.5.1",
  "env_lockfile": null,
  "input_hashes": []
}
```

alongside an `assumptions` block stating what the policy assumed about comms observability and
surrogate fidelity. A policy published without its assumptions is a number; with them it is a
contribution.

## Held-out seeds

The anchor's public seeds are `1001–1005`. The scenario also carries a **held-out seed commitment**
— a hash of seeds nobody can see, published in advance:

```
sha256:fee93327b5943041865348cc47b4b9db5bde955a9cd8c307ebeba18569ab5640
```

Leaderboard scoring runs against those. A policy tuned to the public five does not transfer, and
there is nothing to tune against a hash. The commitment is published *before* the seeds are used,
so the operator cannot choose them after seeing submissions either.

**What a held-out seed does and does not withhold.** It withholds the *episodes* — which is what stops
tuning to the ones you will be judged on. It does **not** withhold the sealed resource field: that is
realized per *scenario*, not per seed, so scoring a scenario's public seeds samples the same ground
truth the held-out ones will ([concepts/uncertainty.md](uncertainty.md#the-sealed-field-is-per-scenario-not-per-seed)).
Withholding the field is what hidden test scenarios are for, and the two mechanisms compose rather
than substitute.

## Reproducing someone else's result

Four things, all recorded, none guessable:

1. the **scenario id** — in the scorecard
2. the **seeds** — in the scorecard
3. the **runner** — in the scorecard, and in its hash
4. the **content** — pinned by digest in the scenario, fetched by digest, verified fail-closed

Match all four and you get their hash. If you get a different hash with the same inputs, that is a
bug worth reporting — which is exactly the property that makes the number meaningful.

## The constraint this comes from

**CX-REPRO** — determinism, provenance, content-addressing — is one of the platform's
non-negotiable constraints, alongside **CX-LOCAL** (works on one workstation, offline, no account,
no cluster). Both are stated normatively in `conventions.md` §11 and are why several things here
are more ceremonious than they would otherwise need to be.
