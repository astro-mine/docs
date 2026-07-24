# RFC 0011: the `astro-mine` umbrella CLI and command naming

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-23
- **Accepted:** 2026-07-23
- **Affects Core:** **no** — the umbrella is a discovery/dispatch/packaging concern, not a widening
  of the narrow waist. It introduces a **new top-level package** (`astro-mine-cli`, import
  `astro_mine.cli`) and a **cross-cutting naming convention** every component repo follows — the
  same bar [RFC-0002](0002-shared-spice-foundation.md) (Spice) and
  [RFC-0005](0005-seal-supply-chain-companion.md) (Seal) cleared — but it makes **no** change to
  `astro-mine-core`: no new enum, message, schema, or wire type, and `CORE_INTERFACE_VERSIONS`
  stays `0.1.0` (`VERSIONING.md §4`). If the chosen design forced a Core change, that would be a
  signal the design is wrong.

## Summary

The platform ships **ten console scripts** under **two naming schemes** and **no umbrella command**.
There is no discoverable front door: a user cannot type `astro-mine` and find their way. This RFC
adopts a thin, near-zero-dependency umbrella package — `astro-mine-cli`, exposing the single
console script **`astro-mine`** — that presents `astro-mine <verb>` as the discoverable entry while
every component CLI keeps working directly. The umbrella **discovers** subcommands from a Python
entry-point group (`astro_mine.cli`) — the platform's established extension mechanism — so a
component (or a third party) contributes a verb **without a PR to the umbrella**; and it degrades
**honestly** from a small, dependency-free manifest of first-party verbs, so `astro-mine train`
with `astro-mine-learn` absent names the fix instead of saying "unknown command." Naming is
standardized: direct binaries become `astro-mine-<package>`; the four bare names
(`fleet`/`worlds`/`link`/`prospect`) and the mis-nouned `astro-mine-train` are kept as **aliases for
one deprecation cycle**.

## Motivation

**G2.1** (gap report §6.1, §7, §8.1; UC-A3, Stage A). The platform's CLIs have grown organically
into an incoherent surface:

- **No front door.** Nothing named `astro-mine` exists. A new user has no discoverable entry point
  and no way to enumerate what the platform can do from the command line. The CLI is the product
  (gap report §8 principle 2); a product with no front door is undiscoverable.

- **Two naming schemes** (verified 2026-07-23 — ten console scripts):

  | Scheme | Commands |
  |---|---|
  | **bare** | `fleet` · `worlds` · `link` · `prospect` |
  | **prefixed** | `astro-mine-bench` · `astro-mine-cloud` (+ `astro-mine-cloud-harness`) · `astro-mine-hub` · `astro-mine-sim` · `astro-mine-studio` · `astro-mine-train` |

  All are argparse — at least that is uniform. But a user cannot guess whether the command is
  `fleet` or `astro-mine-fleet`.

- **Inconsistent in noun, not just prefix.** `astro-mine-learn` ships a binary called
  **`astro-mine-train`**. The package/command mapping is inconsistent in the *word*, not only the
  prefix — the one thing an umbrella must get right, because its whole value is that a user can
  guess the word.

- **The bare names are a land-grab.** `fleet`, `link`, and `prospect` are generic binaries planted
  on a user's `PATH`. That is an argument for the prefix independent of the umbrella.

Left alone, this worsens: **25.2/25.3/25.4** (this backlog) add Core, Guard, and Mind CLIs, and
without a decision they would be born under whichever scheme their author reached for. This RFC
decides the umbrella's *home and shape* and the naming rule **before** those land, so they are born
correct. It does **not** serialize them behind acceptance: each ships its component CLI under the
prefixed naming rule, and the umbrella dispatch above it is a thin call added once `astro-mine-cli`
exists (see [Traceability](#traceability)).

## Design

### 1. Home and shape — a thin dispatcher over an entry-point group

The umbrella is a **new top-level package, `astro-mine-cli`** (import `astro_mine.cli`), that ships
the single console script `astro-mine`. It has **near-zero dependencies** (argparse + stdlib
`importlib.metadata`; not even Core at runtime). It combines two mechanisms:

**(a) Discovery via a Python entry-point group — `astro_mine.cli`.** Each installed component
registers its subcommand(s) into this group. The umbrella *enumerates* the group with
`importlib.metadata.entry_points()` — which reads distribution metadata and does **not import** the
providers — to build `astro-mine --help` and to route a verb. It imports the target subcommand's
callable **lazily**, only when that verb actually runs, so import cost is paid per-invocation, never
per `--help`. This is the mechanism the platform already uses everywhere else
(`astro_mine.providers`, `astro_mine.field_models`, `astro_mine.mind.tier_plugins`, and Bench's
`astro_mine.bench.runners` from 21.1); the CLI is not special enough to invent a different one.
Because discovery is by entry point, **a component — or a third party — adds a verb without a PR to
the umbrella** (§3).

**(b) Honest degradation via a static first-party verb manifest.** Pure entry-point discovery cannot
name a fix for a *missing* first-party component: if `astro-mine-learn` is not installed, no `train`
entry point exists, and the umbrella would only be able to say "unknown command." So `astro-mine-cli`
ships a small, **dependency-free** manifest — plain strings, no imports — mapping the platform's own
verbs to their distributions (e.g. `train → astro-mine-learn`, `score → astro-mine-bench`). When a
known first-party verb has no registered provider, the umbrella prints the fix
(*"`astro-mine train` needs `astro-mine-learn` — `pip install astro-mine-learn`"*) instead of a bare
error. The manifest governs **only** the friendly hint for first-party verbs; third-party verbs are
still discovered dynamically and need no entry in it, so it does not reintroduce a
PR-to-extend chokepoint.

This shape is chosen because it is the only one that satisfies **all four** constraints
([Constraints](#constraints)): discoverable (enumerate the group cheaply), local-tier-safe
(near-zero deps; components stay independently installable), no-PR-to-extend (the entry-point group),
and degrade-honestly (the static manifest). The rejected options fail at least one; see
[Alternatives](#alternatives-considered).

### 2. The command surface

The discoverable surface is **verb-first** — a user guesses the action — sketched in gap report
§8.1:

```
astro-mine
├── fetch <scenario|artifact>        # populate the local registry from the published one (G1.2)
├── score <scenario> [--runner …]    # run + score a baseline (G1.1)
├── run   <scenario> [--out run.mcap]# a Sim-backed episode without Bench ceremony (G2.2)
├── list                             # scenarios in the zoo
├── validate <file>                  # dispatch on schema/kind (§6)
├── train … --export policy.onnx     # train + export a policy (G1.4)
├── submit <policy> --to <url>       # leaderboard submission (G2.14)
├── publish / search / pull / verify # artifact registry (delegates to hub)
├── studio serve                     # composed backend + mounted UI + seeded example (G2.3)
├── plugin new <kind>                # scaffold a plugin from template (§7; 22.5 / G2.8)
└── new asset|world|stack|safety     # scaffold an authored document
```

Where an action is inherently component-scoped, it reads as `astro-mine <component> <verb>`
(`astro-mine studio serve`). **Precedent already exists and validates the model:** Wave 24.4 shipped
`astro-mine-studio serve` as a subcommand *specifically* so the umbrella's `astro-mine studio serve`
is a thin dispatch into it, not a rewrite (its `pyproject.toml` says so). Every component CLI keeps
working when invoked directly; the umbrella is the discoverable entry, **not** a replacement (gap
report §8 principle 1).

### 3. The contribution contract — no PR to extend

A component contributes a subcommand by declaring an entry point in its own `pyproject.toml`:

```toml
[project.entry-points."astro_mine.cli"]
train = "astro_mine.learn.cli:umbrella"   # a Subcommand: name, help, add_arguments, run
```

The registered object is a small `Subcommand` protocol the umbrella defines (a name, a one-line
help, an `add_arguments(parser)` hook, and a `run(args) -> int`). The umbrella owns the top-level
parser, mounts each discovered subcommand under its verb, and dispatches. **No component imports
another, and no component imports the umbrella** (`conventions.md §1.1`): the umbrella depends on the
group *name*, not on any provider, exactly as Allocate's closed solver registry (G2.9) should have
and Mind's `tier_plugins` does. A third-party package that installs alongside and registers into
`astro_mine.cli` gains an `astro-mine <verb>` with no change to `astro-mine-cli` — the 22.5 / G2.8
lesson, not re-broken.

### 4. Degradation contract

When a user invokes a verb whose provider is not installed:

- **A known first-party verb** (in the manifest) → exit non-zero with a message that **names the
  fix**: `astro-mine train needs astro-mine-learn — pip install astro-mine-learn`. Never a
  traceback; never a blank "unknown command."
- **An unknown verb** → the standard argparse error listing the verbs that *are* available.

This is the CLI form of "degrade visibly, never blank" (gap report §8 principle 3) and mirrors the
component-level degradation the same backlog requires of `astro-mine-mind run` and
`astro-mine-guard falsify`.

### 5. Naming and aliases (normative)

Two layers, one rule each:

- **Direct component binaries are `astro-mine-<package>`.** The prefix wins uniformly: it removes
  the `PATH` land-grab and makes the package↔command mapping guessable. The four bare names
  (`fleet`, `worlds`, `link`, `prospect`) are renamed to `astro-mine-fleet`, …; and
  **`astro-mine-train` is renamed to `astro-mine-learn`** to match its package (resolving the
  noun inconsistency).
- **The umbrella surface is `astro-mine <verb>`** (verbs, §2), because the umbrella's value is
  guessing the *action*.

**Aliases and deprecation.** Every renamed binary keeps its old name as an **alias for one
deprecation cycle**: `fleet`/`worlds`/`link`/`prospect` and `astro-mine-train` continue to work, and
print a one-line deprecation notice to stderr pointing at the new name. **Removal milestone:** the
aliases are dropped at the **first public-benchmark milestone** (the public-flip gate; CLAUDE.md
"Org conventions") — i.e. before the platform is public, the transitional names are gone. The
alias surface only ever **shrinks**: every CLI added since this backlog began (`astro-mine-sim`,
`astro-mine-studio`) already took the prefix, and future ones must (§ normative rule), so no new
alias debt accrues.

### 6. `validate` dispatch ownership

`astro-mine validate <file>` is a **thin router**, not a validator:

- **Core owns Core-format dispatch.** Core's `astro-mine-core validate` (25.2) already dispatches on
  a document's schema `$id` through `schema_registry()` (RFC-0009) and exposes that dispatch as an
  **importable** function. `astro-mine validate` calls it for the Core-authored formats.
- **Each component owns its own checker**, federated under the one verb: `fleet validate` (SADF),
  `astro-mine-guard validate` (SafetySpec; 25.3), `astro-mine-mind validate` (stack spec; 25.4),
  and Worlds' `WorldSpec` (G2.11). Each registers a `validate`-capable subcommand or a validator
  the umbrella's `validate` consults.

The rule: **the format's owner owns its validator; the umbrella federates them; Core owns the
`$id`-keyed dispatch for Core formats.** No component reimplements another's checker (`compose, don't
fork`).

### 7. `plugin new` and `new`

`plugin new <kind>` (the 22.5 / G2.8 scaffold) and `new <asset|world|stack|safety>` live in the
**umbrella**, delegating to `fleet new` (the exemplar) and its generalization. Scaffolding is a
cross-component authoring concern with no natural single-component home, so the umbrella hosts it and
routes to the component that owns each artifact kind.

## Impact on Core

**None.** The umbrella is discovery + dispatch + packaging. It adds no schema, message, enum, or
wire type; it does not touch `astro-mine-core`. `CORE_INTERFACE_VERSIONS` stays **`0.1.0`**
(`VERSIONING.md §4`). Core gains, at most, a new *consumer* of its already-public
`astro-mine-core validate` dispatch (RFC-0009's `schema_registry()`), which is additive and requires
no Core change.

The one new artifact is a **new top-level package**, `astro-mine-cli` (repo `astro-mine-cli`,
import `astro_mine.cli`) — the reason this is an RFC rather than a plain issue, matching the
new-package precedent of Spice (RFC-0002) and Seal (RFC-0005). It is a *backbone* component in the
[system catalog](../architecture/system.md#4-component-catalog--role--runtime--data--talks-to).

## Alternatives considered

- **(a) One umbrella package depending on all components.** Discoverable and simple, but it **drags
  the entire platform into every install** — Ray, a Rust toolchain, CP-SAT, SPICE, Cap'n Proto — so
  `pip install astro-mine` to get `astro-mine score` also pulls `learn`, `guard`, and `allocate`.
  This violates **CX-LOCAL** (the local tier must stay light and independently installable).
  **Rejected.**

- **(b′) A thin dispatcher that shells out to installed `astro-mine-*` binaries (subprocess).** Near-
  zero deps and honest degradation, but it loses in-process composition, depends on the component
  binaries being on `PATH`, pays a subprocess launch per call, and cannot present a unified
  `--help`/error surface as cleanly. The chosen design keeps (b)'s lightness while dispatching
  **in-process via lazy import**. **Rejected in favor of the entry-point hybrid.**

- **(c) Pure entry-point discovery, no manifest.** This is the platform's established mechanism and
  is adopted for *discovery* (§1a). On its own, though, it **cannot name a fix for a missing
  first-party component** — an absent `astro-mine-learn` leaves no `train` entry point, so the
  umbrella could only say "unknown command." The static first-party manifest (§1b) is the minimal
  addition that fixes this without deps and without a PR-to-extend chokepoint. **Adopted, with the
  manifest.**

- **(d) No umbrella; fix naming only.** The null option. It leaves the platform with no discoverable
  front door — the primary gap (G2.1) — so it fails the motivation outright. The naming fixes it
  *would* make are subsumed here (§5). **Rejected.**

## Unresolved questions

- **The `Subcommand` protocol's exact shape** (argparse `add_arguments`/`run`, vs. a richer object)
  is an implementation detail settled when `astro-mine-cli` is built.
- **Shell completion** (bash/zsh/fish) for the discovered verb set is desirable and deferred to
  implementation.
- **Whether `astro-mine` should re-expose a component's *full* subcommand tree** (e.g.
  `astro-mine hub <anything hub supports>`) or only a curated verb set is deferred; the entry-point
  contract supports either.
- ~~The umbrella's own version/release cadence relative to components (it should track the platform,
  not any one component) is deferred to `VERSIONING.md`.~~ **Resolved 2026-07-23** in
  [`VERSIONING.md §2.2`](../VERSIONING.md): it tracks the platform; a component adding a verb never
  bumps it (discovery is dynamic); and the `Subcommand` contract is coordinated like — but
  deliberately not versioned as — a Core interface.

## Doc impact

- **`architecture/conventions.md §13`** — a **normative** CLI-naming subsection (direct binaries
  `astro-mine-<package>`; umbrella `astro-mine <verb>`; the `astro_mine.cli` contribution group;
  the alias/deprecation policy). This is where the rule binds future components.
- **`architecture/system.md §4`** — `astro-mine-cli` added to the component catalog (Backbone), with
  a footnote citing this RFC.
- **`guide/reference/cli.md`** — the CLI reference (26.6) documents the umbrella surface; a
  placeholder is reserved.
- **CLAUDE.md** (workspace) and the `rfc/` index — the accepted-RFC list gains `0011`.

## Traceability

- Gap **G2.1** (no umbrella CLI; inconsistent naming) — gap report §6.1, §7, §8.1.
- Use case **UC-A3**; Stage A. **CX-LOCAL**, **CX-GOV**.
- `conventions.md §13` (naming), `§7` (entry points); `system.md §4`; `VERSIONING.md §4`;
  `GOVERNANCE.md` (RFC process).
- Precedent: **RFC-0002** (Spice), **RFC-0005** (Seal) — new-package + cross-cutting-convention RFCs.
- Gates **25.2** (Core `validate`), **25.3** (Guard CLI), **25.4** (Mind CLI), **22.5**
  (`plugin new`); feeds **26.6** (CLI reference). Independent of **RFC-0010** (console) — a
  different surface.

### Constraints

- **CX-LOCAL** — the deciding constraint. A discoverable front door must not make the local tier
  heavier; the umbrella is near-zero-dependency and every component stays independently installable.
- **No PR-to-extend** — a component or third party contributes a subcommand by declaring an entry
  point, never by modifying the umbrella.
- **Degrade honestly** — a missing component produces a message that names the fix, never a
  traceback.
- **Additive** — existing component CLIs keep working directly; the umbrella is the discoverable
  entry, not a replacement.
