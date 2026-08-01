# Fidelity

**How accurate is the thing that just ran, and what did that accuracy cost?**

Astro-Mine makes fidelity an explicit, declared axis rather than an implicit property of whichever
code path you happened to take. Three places it shows up.

## 1. Asset fidelity profiles

A SADF asset declares multi-fidelity profiles, coarse to fine:

| Profile | What it models |
|---|---|
| `massmodel` | mass and inertia only — a point with properties |
| `kinematic` | frames and joints, no dynamics |
| `articulated` | the full articulated body |

```bash
astro-mine fleet fidelity <asset.sadf.yaml>          # list an asset's profiles
astro-mine fleet render <asset> --fidelity kinematic # pick the LOD for a preview
```

A run selects the coarsest profile that answers the question. A survey mission over 43,200 ticks
does not need articulated excavator dynamics; a granular-contact study does.

## 2. Engine tiers

Sim carries reference engines and native engines for the same physics. The reference engine is the
readable, portable definition of the model; a native engine is the fast implementation. Where both
exist, the platform's rule is **bit-exactness where it is claimed** — a native engine that
diverges from its reference is a bug, not a faster answer.

The `fixture` runner sits below all of this: it is not a fidelity tier, it is a recorded trace with
no physics at all. See [scenarios](scenarios.md) and
[tutorial 01 §4](../tutorials/01-score-the-anchor.md).

## 3. Surrogates

`astro_mine.surrogate` provides learned fast-physics tiers with **tracked error bounds**. A
surrogate is only usable if it can state how wrong it is; a fast model with unknown error is not a
fidelity tier, it is a guess.

Training exposes this as an explicit choice:

```bash
astro-mine learn --fidelity {sim_high,surrogate,gpu_vectorized} ...
```

- `sim_high` — the real engine. Slow, accurate.
- `surrogate` — a learned tier. Fast, with declared error bounds, subject to a validation threshold.
- `gpu_vectorized` — batched rollouts, optionally through a `--batched-world` factory (Sim's
  Brax/MJX tier or a JAX surrogate); falls back to a sequential CPU loop without one.

**The caveat travels with the artifact.** An exported `PolicyPackage` carries
`assumptions.surrogate_fidelity_caveats`. A policy trained on a surrogate and published without
recording that fact is making an unearned claim — and the consumer has no way to discover it.

## The honest-degradation rule

Across the platform, a lower-fidelity or unavailable path **says so visibly** rather than silently
substituting:

- A scorecard names its `runner`, and the CLI prints a banner when the fixture produced it.
- `astro-mine bench score --runner sim` **refuses** when a pinned provider did not rebuild, rather
  than scoring blind.
- `astro-mine fleet render` labels an inertia-equivalent proxy box as a proxy, per link, and stamps
  the output `lossy`.
- A console page whose backend is absent or whose capability is unmet **degrades visibly**, never
  blank.

The unifying idea: it is always acceptable to run something cheaper, and never acceptable to let a
reader believe they ran something more expensive.
