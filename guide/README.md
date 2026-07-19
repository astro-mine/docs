# Astro-Mine user guide

Task-oriented documentation: how to *do* things with the platform, as opposed to how it is
designed. The design lives in [`architecture/`](../architecture/), the requirements in
[`scenarios/`](../scenarios/), the plan in [`roadmap/`](../roadmap/), and accepted interface
changes in [`rfc/`](../rfc/).

## Contents

| | |
|---|---|
| [how-to/write-a-plugin.md](how-to/write-a-plugin.md) | Extend the platform: one recipe per extension surface |

## The rule this guide is held to

**Document what ships.** Every command and snippet here has been executed against the shipped
code, and the group names, constants, and file paths are quoted from source. A guide that
describes an aspiration reads exactly like a guide that describes a feature, which is worse than
having no guide at all — the reader cannot tell which one they are holding.

Where something is *not* built, or is built but not wired up, this guide says so and links to the
issue tracking it, rather than omitting it and leaving the reader to discover the gap themselves.
