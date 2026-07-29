# Astro-Mine-UI — the front-end distribution

> Distribution: **`@astro-mine/*`** (npm packages) · Repository: `astro-mine-ui`
> The console shell, its surface contract, the design system, the visualization library, and every
> per-component surface — one workspace, one baseline, one build.
> Talks to [`astro-mine-api`](api.md) over HTTP. Cross-cutting standards:
> see [conventions.md](conventions.md) §2.1 (the front-end baseline, normative) and §13 (naming).
>
> **Status: not yet stood up.** Every package here exists, ships and is published; they are spread
> across four repositories (`astro-mine-console`, `astro-mine-view`, and the `ui/` trees of Hub,
> Studio and Bench). The design below — one workspace — is the target, and the move is tracked in the
> [roadmap](../roadmap/README.md).

## 1. Purpose

**One GUI, not an app per component.** The console is the platform's single front door: a shell that
composes per-component *surfaces* over a small, stable contract, so one application spans every
component without any component importing another. The design detail is
[console.md](console.md); this document is about the distribution — what ships, how it is layered, and
what the workspace boundary is for.

## 2. What is in it

| Package | Kind | What it is |
|---|---|---|
| `@astro-mine/surface` | contract | Types only, zero runtime dependencies. What a *surface* is: its namespace, routes, slots, and the host capabilities it may use. |
| `@astro-mine/ui` | design system | Tokens, primitives, accessibility, light/dark, the honesty components, and the chart layer (visx + `d3-scale`). |
| `@astro-mine/view` | library | Visualization: the Cesium globe, MCAP replay, timeline, and frame helpers. |
| `@astro-mine/console` | application | The shell — navigation, routing, the inspector, and build-time surface composition. Private and unpublished; it is deployed, not consumed. |
| `@astro-mine/<component>-ui` | surfaces | One per component with a GUI face: `hub-ui`, `bench-ui`, `studio-ui` today. |

## 3. Layering is the product

```
surface  ←  ui, view  ←  <component>-ui surfaces  ←  console
```

Dependencies point **one way only**, and that is asserted by a layering check rather than by review:

- `surface` depends on nothing. A surface package can implement the contract without pulling in the
  design system, and the contract can be read without running anything.
- `ui` and `view` depend on `surface` (and on React as a peer) and **not on each other**: geometry,
  tiles and frame helpers are View's, and the design system does not re-implement them.
- A `<component>-ui` surface depends on `surface`, `ui`, and — if it draws a globe — `view`. It MUST
  NOT depend on another surface. Two surfaces that need the same thing means the thing belongs in
  `ui` or `view`.
- `console` depends on all of them and is depended on by nothing.

The `-ui` suffix is not decoration: it is what the layering check keys on to tell a surface from a
library (`conventions.md` §13).

## 4. Why one repository

The packages are already one system — they share a baseline, a build, a design system, and a
layering rule — but they were spread across four repositories, and the cost showed up in three
predictable places:

- **A contract change needed a publish to test.** Adding a slot to `@astro-mine/surface` meant
  publishing it before any surface in another repository could try it, and npm's release-age floor
  made even a `--frozen-lockfile` install wait. In one workspace it is a local change.
- **The layering rule could only be enforced on the packages that happened to be co-located.** The
  check lived in the console repository and could not see the surfaces it was about; the surfaces
  were composed at build time from published versions.
- **Defects found by the first real surface were invisible to the others.** The first surface to use
  a hook found three shell and design-system bugs that the remaining surfaces then hit in turn,
  because nothing in either repository ran the other's code.

One workspace also makes the honest statement about coupling: these packages version together in
practice, so they should version together in fact.

## 5. Layout

```
packages/surface/            @astro-mine/surface   the contract
packages/ui/                 @astro-mine/ui        design system + chart layer
packages/view/               @astro-mine/view      Cesium globe, MCAP replay, timeline
packages/<component>-ui/     one per surface
apps/console/                @astro-mine/console   the shell (private)
scripts/check-layering.mjs   the dependency-direction check
e2e/                         Playwright, against built artifacts
```

The workspace root is `private: true` and unpublished; only the packages it ships carry the
`@astro-mine` scope (`conventions.md` §13).

## 6. Build, test & publish

The baseline is normative and lives in [conventions.md](conventions.md) §2.1 — TypeScript 5.5, React
18.3, Node ≥ 20.19, pnpm pinned in the workspace root, Vite 8 (library mode for packages, app mode for
the console), Vitest 4 + Testing Library for units, Playwright against the **built** artifact, ESLint
and Prettier. Three lanes gate the build: units, browser tests, and an automated accessibility lane.
Where design tokens ship, their properties are checked rather than claimed — contrast conformance
across every theme and mode, colour-vision separation for chart palettes, generated artifacts matching
their source.

**Publishing:** the libraries publish to a private npm registry (GitHub Packages) during incubation,
which is why installing them needs a `read:packages` token; the console is deployed as a built
application and publishes nothing. Cesium ships binary assets that the console build copies rather
than fetches, so the app has no external CDN dependency at runtime.

**Two environment notes worth writing down, because both look like product defects and are not.**
Playwright cannot launch a browser in this workspace's WSL environment (a missing system library), so a
red browser lane there is environmental — units, typecheck, lint and build are the local truth, and CI
is the arbiter for the browser lane. And `jsdom` does not implement every `File` method, so a surface
reading an uploaded file must use an API `jsdom` has.

## 7. Interfaces

- **Inward:** [`astro-mine-api`](api.md) over HTTP, at runtime. No package here imports Python or
  knows the platform's internals; a surface renders capability a component already exposes
  (`conventions.md` §2).
- **Outward:** the `Surface` contract, which is also the third-party extension point — an outside
  package can ship a surface for its own component. The contract is types-only and versioned
  deliberately for exactly that reason.
- **Core vocabulary on the wire.** A surface consumes Core schemas by their published `$id` and does
  not re-declare their shapes (`conventions.md` §3.1). It also inherits Core's frame and unit rules:
  a value with no unit is a bug upstream, and the design system renders a value with no uncertainty
  bound as an open mark rather than as a zero-length error bar, so honesty is structural rather than
  remembered.

## 8. What this distribution must not do

1. **No component owns an app.** A component contributes a *surface*; the shell is the only
   application. This is the rule the whole design exists to enforce.
2. **No surface imports another surface** (§3).
3. **No platform capability originates here.** A front end that needs a new behaviour needs it in the
   platform, and then in the API — not in a component wearing the wrong clothes
   (`conventions.md` §2).
4. **No second data-fetching stack.** The baseline ships none deliberately; the loading / error /
   empty discipline lives in the design system's `AsyncState` (`conventions.md` §2.1).

## 9. Roadmap alignment

The console, the contract, the design system, the visualization library and three surfaces ship.
Standing up this repository is the second distribution-level task after the consolidation: move the
five package trees into one workspace, extend the layering check to cover the surfaces it was always
about, and replace build-time composition from published versions with workspace links. Surfaces for
the remaining components, and the full operations viewer, are Phase 2. See the
[roadmap](../roadmap/README.md) and, for the user-facing view, the
[console guide](../guide/console.md).
