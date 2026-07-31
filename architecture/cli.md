# Astro-Mine-CLI — the command-line distribution

> Distribution: **`astro-mine-cli`** (Python wheel) · Repository: `astro-mine-cli`
> One executable, `astro-mine`, under one grammar: `astro-mine <component> <verb>`.
> Depends on [`astro-mine-platform`](platform.md); installing it installs the platform.
> Cross-cutting standards: see [conventions.md](conventions.md) §13 (CLI naming, normative).

## 1. Purpose

The platform's only command line, and the only executable any Astro-Mine distribution installs:

```console
$ pip install astro-mine-cli        # brings the platform with it
$ astro-mine <component> <verb> [options]
```

Everything the platform can do from a terminal is reached by naming the component that owns it and
then the action. Fourteen names are components; three are *routers*, which exist because they answer
a question no single component can — *who owns this?*

## 2. Why it is a separate distribution

It would be simpler to ship the commands inside the platform wheel. Two reasons not to, and they are
the reasons this document exists:

**The library stops having a user interface.** Argument parsing, help strings, output formatting and
exit-code policy are a different concern from resource fields and rigid-body physics. With them gone,
the platform's only boundary is its Python API, and "is this exported?" acquires a real answer — the
export audit for the move found exactly one function that had been reachable only through a command
handler.

**A surface decision is made once.** Help text, argument naming, exit-code conventions and `--json`
output shape are cross-cutting. They used to be decided thirteen times independently, which is how
the platform acquired three different addressing rules and seven verbs that could not be typed at
all.

## 3. Why it is not a zero-dependency dispatcher

The umbrella was originally built with **no** runtime dependencies — not even Core — federating every
first-party verb through the `astro_mine.cli` entry-point group. That design's rejected alternative
was "one umbrella package depending on all components", on the grounds that `pip install` for one
verb would drag Ray, CP-SAT, SPICE and a Rust toolchain onto the machine.

Consolidation dissolved the premise. The platform is one wheel already carrying all of it, so there
is no install this dependency makes heavier — the cost the original design refused to pay is now paid
by the platform simply existing. Meanwhile the indirection decoupled nothing: every component is
always present, so first-party federation was a metadata round-trip that hid which function ran.

What the original design actually protected — *you should not pay for what you did not run* — is kept
by a mechanism that still works (§5).

## 4. The grammar

```
astro-mine <component> <verb> [options]      # 13 components
astro-mine validate <file>...                # routed to the format's owner
astro-mine new <kind> <out>                  # scaffold an authored document
astro-mine plugin new <kind> <out>           # scaffold a plugin package
```

**Components:** `core` · `fleet` · `worlds` · `prospect` · `link` · `sim` · `bench` · `learn` ·
`mind` · `guard` · `hub` · `seal` · `cloud` · `studio`.

`seal` is the newest and the only one added after the move: the component whose entire purpose is
to be run from a shell was the one that shipped no shell surface. It signs, verifies and describes
**loose files** — anything addressed by a registry reference is `hub`'s. `seal verify` and `hub
verify` therefore both stand and are not duplicates: Hub resolves a published artifact and runs the
whole verify-twice policy against a registry, Seal checks one detached signature over one file.
They share one implementation, because Hub's supply chain calls Seal's verifier.

**The three routers.** `validate` dispatches a document to whichever component owns its schema
`$id` — four components own an authored format (`core`, `guard`, `mind`, `worlds`), and a collision
between two claimants is an error rather than a coin flip. `new` writes one of four authored-document
kinds (`asset`, `world`, `stack`, `safety`), each templated by the component that owns the format and
validated by that component's own loader. `plugin new` writes a package against a live extension
group — seven kinds today (`tier`, `provider`, `field-model`, `runner`, `solver`, `algorithm`,
`curriculum`); the eighth group is `astro_mine.cli` itself.

`new` and `validate` are two ends of one contract: what `new` writes, `validate` accepts. A scaffold
that emits a document its owner's validator rejects is a defect in the pair, not in either half.

## 5. Laziness — you pay for the command you ran

`astro-mine --help` imports **no** component. The listing comes from a static table of plain strings,
and dispatch imports exactly one module: the one the user named.

That is what the two-phase parse buys. Phase one parses only *which* component; everything after it
is `argparse.REMAINDER`. Phase two imports that component's module and lets it parse its own tail. A
single-phase parser would have to call every component's `add_arguments` to build the tree, importing
all fourteen to render a help screen.

The cost is that top-level `--help` cannot show a component's verbs; `astro-mine <component> --help`
is where the real help lives. That is the trade, and it is the right way round: the top level is read
once, a component's help is read repeatedly.

## 6. Two sources, one shape

**First-party commands are dispatched statically.** **Third-party commands are discovered** from the
entry-point groups, because that is the no-pull-request-to-extend guarantee and consolidation does
not touch it. Both are wrapped so the dispatcher cannot tell them apart.

Four groups stay live for third parties:

| Group | Extends |
|---|---|
| `astro_mine.cli` | a new top-level name |
| `astro_mine.cli.validators` | `astro-mine validate` |
| `astro_mine.cli.scaffolds` | `astro-mine new` |
| `astro_mine.cli.plugin_scaffolds` | `astro-mine plugin new` |

The platform registers into **none** of them: its entries used to shadow the component names at the
top level. A third-party entry point that claims a name the platform owns is **reported, not
silently honoured** — named by package, version and entry point — because a shadowed `fleet` that
quietly does something else is the worst failure this surface can have.

## 7. The thin-wrapper rule (normative)

A command module MAY declare argparse arguments, read a `Namespace`, call a platform function, format
output, and map a result to an exit status.

It MUST NOT implement domain logic, define a schema or data model, hold state between invocations, or
import a platform private (`_`-prefixed) name.

Anything a command needs that the platform does not export is a **platform change**. This is not
style: `astro-mine fleet package` and Fleet's own packaging manifest must produce byte-identical
canonical JSON, and they only do that by calling the same exported function.

## 8. Parser parity

A committed fixture records all **50 verbs and 189 arguments** as the platform's own binaries
declared them, captured before any code moved: option strings, defaults, `nargs`, `choices`,
`required`, help text. A test asserts the current parsers still match.

Regenerating that fixture to make the test pass is not a fix. The fixture *is* the old behaviour, and
the old behaviour is the requirement; a verb that genuinely must change is a separate change with its
own justification, and the fixture moves in that commit.

A component that was **never** a binary is excluded by name rather than back-filled — a fixture of
what the binaries declared cannot describe a group that never was one, and back-filling would turn
the contract into a mirror of the current code. `seal` is the first such exclusion. The exclusion set
is asserted exactly, so a *ported* component silently dropping out of the fixture still fails.

## 9. Honest degradation

A verb whose backing capability is absent MUST report what is missing and how to get it — never a
traceback, never "unknown command" — and MUST exit **non-zero**. The case that survives
consolidation is a surface in another distribution: `astro-mine studio serve` reaches the Studio
REST application, which lives in [`astro-mine-api`](api.md), so the command names where the surface
lives rather than failing obscurely. That is also why `studio` keeps its group.

**A good message is not a success.** The status is a separate claim from the text, and it is the
one every script reads. `serve` is imperative: explaining why it could not serve is the right
behaviour, but exit 0 asserts that a server is running. `astro-mine studio serve && open
http://localhost:8000` opened a dead port for as long as that was the status. A helpful message
makes this *more* dangerous, not less — the command looks like it worked.

Where the capability lives in another distribution, the status is **1**, not 2. Exit 2 is reserved
for a usage error — *"I typed this wrong"* — and is kept distinct from the 1-and-up range a command
uses for its own failures. Such a verb was invoked correctly; the installation is incomplete.
Answering it with 2 points the reader at their command line instead of at their environment.

That split governs every failure a command reports, not only an absent capability, and it is what a
script branching on the status is entitled to read:

- **1** — the command was invoked correctly and could not complete: a missing optional extra, an
  unreadable file, content that did not resolve, a runner that refused to score.
- **2** — the user named something that does not exist or cannot be parsed, or supplied nothing
  where something was required: an unknown scenario id, an unregistered `--runner`, a malformed
  flag value, a store named by neither a flag nor its environment fallback. `argparse` already
  produces this status for free on a genuine parse error.

**When the hint cannot resolve, omit it.** "How to get it" assumes something to get. Where the
capability ships in a distribution that does not yet exist, the honest message names that
distribution and the roadmap item that stands it up, and says no released distribution provides it
— an install hint that resolves to nothing is worse than none, because pip's "no matching
distribution" reads as a broken environment rather than a stale message.

## 10. What is deliberately not a verb

Two platform entry points are not exposed here, because neither is typed by a person and both are
invoked as `python -m` by machinery that already depends on them: Bench's per-seed `eval-worker`
(Cloud fans it out) and Sim's container entrypoint. They stay in the platform, where their callers
look for them (`platform.md` §4).

## 11. What this distribution must not do

1. **No second executable.** One binary, one grammar. The prefixed per-component binaries
   (`astro-mine-<component>`) and the bare legacy aliases (`fleet`, `worlds`, `link`, `prospect`, and
   the mis-nouned `astro-mine-train`) are gone and MUST NOT come back (`conventions.md` §13).
2. **No domain logic** (§7).
3. **No eager imports** (§5).
4. **No component may depend on it.** The dependency runs one way; a layering test asserts it
   (`conventions.md` §11).

## 12. Roadmap alignment

The CLI ships. Known gaps are tracked as issues rather than described here as design — notably that
the `astro_mine.cli` group has no `plugin new` scaffold of its own (structurally impossible under the
old design, merely unwritten under this one). Seal's missing verbs were the other one, closed by
`astro-mine seal` (§4). See the
[roadmap](../roadmap/README.md) and the [CLI reference](../guide/reference/cli.md) for the
user-facing surface.
