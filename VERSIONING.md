# Astro-Mine — Versioning & Release Policy

> **Status:** Normative for every Astro-Mine distribution. Expands
> [`architecture/conventions.md`](architecture/conventions.md) §7.1 (the four distributions) and §13
> (naming & versioning). While the platform is in **private incubation**, the "incubation" rules here
> take precedence over any public-distribution language in the architecture docs.

## 1. Two version axes

Astro-Mine versions two different things on two independent axes. Conflating them is the most common
mistake, and it survived the consolidation intact — what changed is how many things sit on the second
axis.

| Axis | What it versions | Where it lives | Cadence |
|---|---|---|---|
| **Interface version** | a Core *contract* (`sadf`, `messages`, `objective`, `env`, `policy`, `registry`) | `astro_mine.core.compat.CORE_INTERFACE_VERSIONS` | only on a contract change — see §4 |
| **Distribution version** | a published artifact | each distribution's `pyproject.toml`/`package.json` | per integration milestone — see §3 |

A distribution's version may advance (it ships more capability) while the Core contract it speaks
stays fixed. They are decoupled by design (`conventions.md` §13: "interface versions are independent
of implementation versions").

**What the consolidation removed from this document.** Seventeen per-component SemVer lines, seventeen
Git tag series, a per-component milestone cut table, and a cross-repo dependency-pin matrix. A
component does not have a version. `astro_mine.sim` ships in `astro-mine-platform` and moves when it
moves; there is no separate `sim` distribution to pin, and therefore nothing to skew.

## 2. Distribution versions

There are four (`conventions.md` §7.1). Each uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`).

| Distribution | Version lives in | Moves when |
|---|---|---|
| `astro-mine-platform` | `pyproject.toml` (static) | the library gains capability — the common case |
| `astro-mine-cli` | `pyproject.toml` | the command surface or the dispatcher changes (§2.2) |
| `astro-mine-api` | `pyproject.toml` | a route set or a REST convention changes |
| `astro-mine-ui` | each package's `package.json` | that package changes (§2.3) |

- **Pre-1.0 for the whole private period.** Distributions stay in the `0.y.z` range — honest
  signalling that the API is unstable and may break. **`1.0.0` is reserved for the public-stability
  commitment** (§6), not for "it works."
- **Cadence:** bump the **minor** (`0.1 → 0.2`) at an integration milestone; bump the **patch** for
  fixes within one. Do **not** churn versions between milestones.

### 2.1 The platform's version, and one open inconsistency

The platform's version is **static** in `pyproject.toml`. It cannot be derived from a Git tag the way
the per-component packages were, because the build backend is **maturin** (Guard's Rust core has to be
compiled into the wheel — `architecture/platform.md` §4) and the `hatch-vcs` machinery went with
hatchling.

Two consequences, stated plainly because both are live:

- **A version bump is now an edit, not a tag.** The old scheme made "bump a version" and "cut a tag"
  the same act, which is what kept `pyproject.toml`, `__version__` and the tag from drifting. That
  guarantee is gone, so a release **MUST** bump the static version and cut the tag **in the same
  commit**, and CI **SHOULD** fail a tag whose name disagrees with the declared version. This is the
  weaker half of the scheme; treat it accordingly.

  That check exists now: `tests/platform/test_release_version.py`, landed with the platform's first
  tag (astro-mine-platform#33). It is a test rather than a workflow step, so it runs on a workstation
  — which mattered, because the org's Actions minutes were exhausted when it was written and a check
  living only in a workflow could not have been observed working before being relied on.
- **The CLI pins the platform at `branch = "main"`, and that is deliberate.** This paragraph used to
  say the opposite, and the two halves of this document and `conventions.md` disagreed with each
  other for as long as it did.

  The rev pin was right when it was written: the two repositories were one change split in half, and
  a floating pin could have resolved a platform that still installed files at the CLI's import path.
  **That hazard ended when the platform shipped zero console scripts** — the split is complete and
  cannot half-resolve. What remained was a pin whose reason had expired, and
  `conventions.md` §3.1 is normative against it: the CLI, API and front-end builds **MUST** run
  against the platform at `HEAD`, because "a downstream job that resolves its dependency from an old
  release cannot fail for any change, which makes a green board actively misleading rather than
  merely uninformative."

  That was not theoretical. When the pin finally moved (astro-mine-cli#36) it was **twenty commits
  stale**, and HEAD turned 576 green tests into 14 failures and 11 errors — including a scaffolder
  that had been minting unpublishable asset ids for as long as it had existed. Every one of those
  breaks had landed on the day its platform change did, under a green board.

  **A tag is the wrong pin here, and the platform now has one.** `v0.1.0` exists; this document used
  to instruct the CLI to move to it "as soon as the platform cuts one". That instruction is withdrawn
  for CI: a tag *is* a released pin, which is the thing §3.1 forbids for this build. A tag remains
  the right way for an end user to resolve a release. The floating pin is paired with a daily
  scheduled canary, because a floating pin is not a canary unless something runs it —
  `astro-mine-api` learned that when a platform break surfaced two days late on an unrelated pull
  request, and the CLI adopts the same shape rather than a second one.

  **Still open:** the CLI's own `hatch-vcs` version and the platform's static version are two
  different mechanisms, and should stop being.

### 2.2 The CLI tracks the platform, not any component

`astro-mine-cli` versions a **surface**: the `astro-mine` executable, its grammar, its exit-code and
`--json` conventions, and the contract a third-party verb satisfies.

- **A component adding, renaming, or removing a verb does not necessarily bump it** — but for a
  different reason than before. First-party verbs are now dispatched **statically** from a table in
  this distribution, so a first-party verb change *is* a change here. What still needs no release is a
  **third-party** verb: those are discovered from the `astro_mine.cli` entry-point group at runtime,
  which is the no-pull-request-to-extend guarantee (`architecture/cli.md` §6).
- **It bumps when its own behaviour changes:** the grammar, the dispatcher, the degradation contract,
  or the four-member protocol a third-party command satisfies.
- **That protocol is a cross-distribution compatibility surface — and is *not* a Core interface
  version.** Every third-party command binds to it structurally (`name`, `help`, `add_arguments`,
  `run`), so changing it breaks every outside command at once. It is nonetheless **not** in
  `CORE_INTERFACE_VERSIONS`: the CLI is not the narrow waist. Treat a breaking change to it with the
  same *discipline* as a contract change without borrowing Core's axis — bump the CLI's **minor**
  (pre-1.0, `0.y` minor is the breaking bump), and state the change in the tag annotation, since
  there are no GitHub Releases to carry notes (§5).
- Because the protocol is structural rather than imported, a mismatch surfaces at *dispatch* rather
  than at install: the CLI reports a non-conforming provider by name, entry point and missing member.
  That is a good error, not a substitute for announcing the change.

### 2.3 Front-end packages (npm)

`conventions.md` §2.1's front-end packages are npm packages, not wheels, so §2's mechanics need a
second expression:

- The version lives in **`package.json` `version`**, and follows the same SemVer and pre-1.0 rules.
- **They version per package, not per workspace.** The design system, the visualization library and
  the generated client each move at their own pace. Sharing a workspace does not make them one
  artifact. The workspace **root** is `private: true`, carries `0.0.0` permanently, and is not a
  package in the sense of this document.
- The **`packageManager`** field pins pnpm (`conventions.md` §2.1). It is a toolchain pin, not a
  package version, and it moves in one deliberate sweep.
- Front-end versions are hand-set — there is no `hatch-vcs` equivalent wired up — so a release
  **MUST** tag and bump in the same commit. Same weakness as §2.1, same discipline.
- **npm's release-age floor is a real release constraint.** A freshly published version can be
  refused by an install for a period after publication, including under `--frozen-lockfile`. Plan a
  contract change and its consumers accordingly, or link them in-workspace and publish once.

**None of them is published today, and that is a decision** (`architecture/ui.md` §8.2). All four
libraries carry `0.0.0`, build under the CI gates, and are consumed in-workspace as `workspace:*`;
`@astro-mine/console` is an application and was never going to be published. Their one class of
external consumer was the retired `<component>-ui` surface packages, so the mechanics above are the
policy for *when* a release happens rather than a description of a running release train — and every
row of it (hand-set version, tag-and-bump in one commit, the release-age floor) is a cost with nothing
currently on the other end. `publishConfig.registry` stays pinned to GitHub Packages in each manifest
regardless: a safety control, so the `@astro-mine` scope cannot resolve to npmjs.com even on a machine
holding a public-npm token. The same reasoning applies to the front end's OCI image, which is built
and verified in CI and pushed nowhere.

## 3. When versions are assigned — integration milestones

Versions are cut at the roadmap's **integration milestones** (`roadmap/`), giving stable pin targets
and reproducible Bench inputs without per-commit churn.

| Milestone | Typical cut |
|---|---|
| the consolidation | `astro-mine-platform 0.1.0` — the first single-wheel cut |
| the CLI's separation | `astro-mine-cli 0.1.0` — the grammar and the dispatcher |
| the API and UI standups | first `0.1.0` of each |
| later milestones (M2.1, …) | minor bumps as each distribution advances |

The old table listed a cut per component per milestone. Four rows is the whole table now, which is
most of the point.

## 4. The Core interface version is held at 0.1.0

**Policy (through Phase 2, likely into Phase 3):** `CORE_INTERFACE_VERSIONS` stays at **`0.1.0`** for
every interface. No minor or major bump — even as the additive multi-regime schema hooks
(`MissionSpec`, `regime`, `PhaseTransition`, propulsion/return SADF, `operational_targeting`) landed
in Phase 1. The **first interface bump happens at or after Phase 3.**

This is sound because the Core contract evolves under a strict **additive, append-only, never-break**
rule (`architecture/core.md`; `conventions.md` §3): proto fields are append-only, new fields are
additive (optional / default-valued), and `buf breaking` in CI **enforces** that every change is
wire-compatible. An old consumer and a newer Core therefore interoperate even though both still report
`0.1.0`.

**Consequence — version negotiation is a no-op while the version is frozen.**
`assert_core_compatible(...)` / `check_compatible(...)` (the `0.y` rule requires an *exact*-minor
match) return *compatible* for everything, because every party is `0.1.0`. Compatibility and
reproducibility are therefore guaranteed by **other** mechanisms, not by the version number:

1. **The distribution version + `uv.lock`** — the exact platform build a result was produced against.
   *Implemented, and simpler than it was:* this used to be a set of seventeen component revisions.
2. **Content-addressed schema digest** — the identity of the exact Core schema set, so a benchmark
   reproduces byte-for-byte. *Implemented — see §4.1.*
3. **`buf breaking` (proto) + the model-drift check (JSON Schema ↔ Pydantic)** — keep every change
   additive, which is what makes the frozen version safe. *Implemented.*
4. **Layering and consumer tests in one CI run** — a Core change runs every consumer's schema tests in
   the same job (`conventions.md` §3.1, §11). *Implemented, and structural now rather than a
   cross-repo canary that could not fail.*

The `compat` machinery still earns its place: it rejects unknown / misspelled interface names, and it
is the mechanism that will correctly refuse old consumers once the version is finally bumped.

### 4.1 The schema digest — the contract pin

**Core produces it.** `astro_mine.core.SCHEMA_DIGEST` is the content address of the exact schema set a
given Core carries — a `sha256:` digest over the canonical sources (the JSON Schemas, the Cap'n Proto
hot path, the units conformance vectors, and the `.proto` sources). It equals the published bundle's
`schema_digest` for the same commit, and the bundle is pullable from a registry by digest:

```python
from astro_mine.core import SCHEMA_DIGEST   # "sha256:…"
```

While the interface version is frozen, **this is the value that actually distinguishes one Core schema
set from another** — `__version__` and `CORE_INTERFACE_VERSIONS` cannot.

How a package *references* a Core schema — by absolute `$id`, resolved through
`astro_mine.core.schema_registry()` — is normative in
[`conventions.md` §3.1](architecture/conventions.md).

> **Note.** It is a *generated, committed constant*, not a runtime recompute, because the digest covers
> the `.proto` sources under `schemas/proto/` — which live at the platform root and are **not** in the
> wheel. An installed platform cannot see them, so it could not reproduce the digest from its own
> files; a filesystem walk relative to `__file__` would yield a plausible-but-wrong value in a wheel
> while looking correct in a source checkout. CI fails if the constant goes stale, and the bundle
> builder refuses to publish a bundle whose digest no package claims.

**Bench consumes it.** A `ScenarioSpec` pins the Core schema set by digest —
`ScenarioSpec.core_schema_digest` — alongside the interface versions and its content inputs. The pin
is *declarative* and folded into `spec_hash`, hence into `scenario_hash`: a scenario resolved against a
different Core contract is a **different task**, not silently the same one.

`resolve_scenario()` **verifies it and fails loud** — `IncompatibleCoreSchema` — when the pinned digest
disagrees with the installed Core's `SCHEMA_DIGEST`. This is precisely the check
`assert_core_compatible()` cannot perform: while the interface version is frozen it returns
*compatible* for every Core revision, so it cannot tell two schema sets apart. The digest can. The
resolved digest is recorded in run provenance (`Result`, `ProvenanceBundle`), so a leaderboard entry can
be audited against the exact contract it validated under.

The pin is **optional**, deliberately. A scenario may omit it — an older spec, or one authored against
a non-Python binding — and then its reproducibility rests on mechanism 1 alone: the `uv.lock` digest
pins the platform build. That is real, but it is an *environment* pin rather than a *contract* pin, it
is over-sensitive (any unrelated dependency bump changes it — and one wheel with a union dependency set
makes that *more* likely, not less), and it is unavailable to non-Python consumers, which have no
lockfile to appeal to but can assert they validated against a digest. **Pin the digest when you can.**

**Re-pinning.** When Core's schemas change its `SCHEMA_DIGEST` changes, and every scenario pinning the
old one stops resolving — loudly, by design. The fix is to re-author the scenario against the new
schemas under a **new `spec_version`**, never to edit a published spec in place
(`architecture/bench.md` §5: scenarios are immutable once published; old leaderboards remain valid for
their pinned spec).

## 5. Git tags vs. GitHub Releases

- **Git tags: required.** They are the pin target (§2.1) and the version's second witness. Every
  milestone cut is an annotated tag named `vMAJOR.MINOR.PATCH`, one series per distribution.
- **GitHub Release objects: deferred.** A full Release pays off when it carries published build
  artifacts and changelogs for external consumers — none of which exist during private,
  source-installed incubation. A plain tag is sufficient to pin against.
  - *Optional:* cut a single milestone Release on **`astro-mine-platform`** (e.g. "the consolidated
    platform, v0.1") with notes, to make the milestone legible — rather than a ceremonial Release per
    distribution.

## 6. What changes at the public flip (future)

When the org makes repositories public and stabilizes (per current intent, no earlier than the end of
Phase 2):

- **Publish the platform and the CLI wheels to a public index** via OIDC / Trusted Publishing, signed;
  switch the CLI from a Git source to a normal version range (e.g. `astro-mine-platform>=0.2,<0.3`).
  Publishing `astro-mine-cli` is the one that matters to a user: it is the install line every document
  quotes.
- **Publish the `@astro-mine/*` packages to public npm.** This is the open precondition for an outside
  party building on the design system or the visualization library
  (`architecture/ui.md` §8.2).
- Turn on **full GitHub Releases** with signed wheel assets + SLSA provenance + SBOMs (CX-SEC) — the
  supply chain applied to the distributions that implement it.
- Turn on **secret scanning, push protection and branch rulesets**, which are unavailable for private
  repositories on the current plan (`conventions.md` §9). Treating them as already on is how a gap gets
  inherited.
- Execute the **artifact-name migration** (`conventions.md` §13), which is deliberately gated here: it
  is a re-publish under new names, and it is far cheaper while no outside consumer holds the old ones.

## 7. Summary

- Two axes: **distribution version** (four of them, moving per milestone) vs **Core interface version**
  (held at `0.1.0`).
- Distributions stay **`0.y`**; a *component* has no version at all, which retires the whole per-repo
  pin matrix.
- **Tag and bump in the same commit.** The platform's version is static under maturin, so the tag no
  longer derives it — that is a real weakening, and the discipline replaces it (§2.1).
- **The CLI pins the platform at `main`, with a daily canary** — `conventions.md` §3.1 requires the
  downstream builds to run against `HEAD`, and a tag would be a released pin (§2.1). Not to be
  "fixed" back to a rev.
- **`astro-mine-cli` tracks the platform**, not any component; its command protocol is a
  cross-distribution surface coordinated like — but not versioned as — a Core interface (§2.2).
- **Tags always; full GitHub Releases deferred** to the public flip.
- With the interface version frozen, **lockfiles + content hashes + `buf breaking` + one CI run over
  every consumer** — not version negotiation — guarantee compatibility and reproducibility.

---

*See also:* [`architecture/conventions.md`](architecture/conventions.md) (§7.1 the four distributions,
§13 naming & versioning) · [`architecture/platform.md`](architecture/platform.md) (§4 build, §7
release) · [`architecture/cli.md`](architecture/cli.md) (the grammar and the command protocol) ·
[`architecture/core.md`](architecture/core.md) (§7 distribution, §11 versioning model) ·
[`roadmap/`](roadmap/) (integration milestones).
