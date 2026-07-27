# Uncertainty

**Prospecting is inference under uncertainty. The platform models that, and refuses to render it as
certainty.**

## Belief vs sealed ground truth

The anchor scenario has two resource fields, and keeping them apart is the whole design:

- **The belief prior** — `shackleton_water_ice_v1`, a probabilistic field over water-ice abundance
  derived from public LOLA / Diviner / LEND / M³ datasets. This is published, pinned by digest, and
  visible to everyone.
- **The sealed ground truth** — a fixed, seeded realization **for a scenario** (`prospect.md`:109),
  drawn from that prior once. It is what sensors read against. It is never published and never
  visible to a policy.

A prospecting swarm therefore does what a real one does: it starts with a prior, takes noisy
readings, and updates a posterior. Two of the anchor's metrics score exactly that —
`information_gain` (how much uncertainty the run removed) and `psr_area_characterized` (how much
area it brought below an uncertainty threshold). A policy that drives straight to the richest cell
of the *prior* is not prospecting; it is guessing well.

### The sealed field is per scenario, not per seed

**Sealing is per scenario.** Two runs of the same scenario at different seeds read against the *same*
sealed field: the realization rides in the pinned bundle, and nothing on the `astro-mine-bench score
--runner sim` path re-realizes it per episode. So a seed sweep over one scenario measures the
policy's sensitivity to *its own* stochasticity, not to where the ice is — and the honest expectation
for a scenario-independent metric like `information_gain` is **low or zero dispersion across seeds**,
which reads as a broken harness if you were told to expect the field to move.

That is a property worth knowing before you design an evaluation, because it means **held-out seeds
alone do not stop memorization.** What does, per `bench.md` §9, is the combination:

| Mechanism | What it withholds |
|---|---|
| **Hidden test scenarios** | the field itself — a scenario you have never scored has a sealed realization you have never sampled |
| **Embargoed specs** | the scenario definition, until the evaluation closes |
| **Held-out seeds** | the specific episodes, so a policy cannot be tuned to the ones it will be judged on |

Held-out seeds are the weakest of the three on their own and the guide previously rested the whole
anti-gaming argument on them. Report a seed sweep because it exposes variance you would otherwise
average away ([tutorial 03 §5](../tutorials/03-train-and-publish-a-policy.md)) — not because the
world changes underneath it.

## Sensors return validity, not just values

A reading carries whether it is valid. Without a resource-field provider installed, prospecting
sensors render `valid=False` — and the effect propagates honestly: `discovery_latency` never trips,
and ISRU extraction sees no abundance. The run does not quietly score zeros as though the swarm
looked and found nothing. That is why `astro-mine-bench score --runner sim` refuses rather than
scoring blind ([tutorial 02 §2](../tutorials/02-run-it-in-the-simulator.md)).

## Not-applicable is a result

A metric can score `n/a` with `n=0`. That is a statement — *no run produced a value this metric
could be computed from* — and it is strictly better than a fabricated `0.0`. A `None` with a stated
reason is honest; a `None` without one reads as breakage, which is why every one in this guide's
worked examples is explained where it appears.

The same applies per seed: `discovery_latency` scoring `n=4` across five seeds means one seed never
tripped the threshold and contributes nothing, rather than contributing a made-up number that would
drag the mean.

## Rendering uncertainty honestly

The rule for every visual surface: **no false-precision heatmaps.** A belief field is drawn with its
uncertainty, not as a crisp answer. A Pareto front in Studio is drawn with the uncertainty attached
to each candidate — P5's output has to survive a design review, and a front rendered as though its
points were exact licenses a claim the analysis does not support.

Concretely, when you read a Pareto front ([tutorial 07](../tutorials/07-design-a-swarm-in-studio.md)):

- it tells you which designs are **not dominated** under the modelled assumptions
- it does **not** tell you which is best — that needs preferences the model does not hold
- and overlapping uncertainty between two candidates means the ranking between them is **not
  resolved**, however far apart their centres sit

## Where this is normative

`conventions.md` and the console's `Surface` contract both carry the honesty requirement: stand-ins
and degraded states are visibly labelled, and uncertainty is rendered as uncertainty. See
[fidelity](fidelity.md) for the same principle applied to model accuracy.
