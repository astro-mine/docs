# Astro-Mine Documentation

Documentation for the [Astro-Mine](https://github.com/astro-mine) platform — the
open-source commons for designing, simulating, and operating planetary robotic swarms for
exploration and in-situ resource utilization (ISRU).

> **Status:** Phases 0 and 1 shipped. The platform's packaging was then consolidated into **four
> distributions** — `astro-mine-platform` (the library), `astro-mine-cli` (the command line),
> `astro-mine-api` (REST) and `astro-mine-ui` (the front end) — and Phase 2 (operations bridge) is
> next. Repositories are private during incubation and flip public at the first public-benchmark
> milestone.

## Contents

- **[Guide](guide/README.md)** — task-oriented how-tos: how to *do* things with the platform, as opposed to how it is designed.
- **[Architecture](architecture/README.md)** — technology architecture for every component, and for
  each of the four distributions.
- **[Scenarios](scenarios/README.md)** — flagship use scenarios that drive requirements (lunar polar ice; asteroid mining).
- **[Roadmap](roadmap/README.md)** — detailed per-phase, per-component scope & requirements (planner-ready), derived from charter §10.
- **[Charter](charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md)** — product envisioning & vision (source of truth).
- **[Versioning & releases](VERSIONING.md)** — per-distribution SemVer, the frozen Core interface version, the content-addressed schema digest, and the private-incubation policy (no public PyPI yet).
- **[TPM](tpm/README.md)** — technical program-management working documents (planning & analysis, point-in-time).

## Checks

This tree is gated, on the charter's own principle (§9.4): *a process that cannot fail a bad change
is decoration; a check that fails the build is governance.* Applied to prose, that is a linter.

```sh
python3 scripts/check_docs.py                            # all four checks
python3 scripts/check_docs.py status                     # just one
python3 -m unittest discover -s scripts -t scripts       # test the checker itself
```

| Check | What fails |
|---|---|
| `links` | a relative link that does not resolve |
| `anchors` | a `#fragment` with no matching heading |
| `status` | prose that contradicts the declared status of the platform, or a claim that was corrected once and came back |
| `format` | trailing whitespace, CRLF, a missing final newline |

Two things about `status`, because they are the parts that need maintaining:

- **`SUBJECT_STATUS` in `scripts/check_docs.py` is the fact the prose is compared against.** When
  something ships, move it there first; every sentence still calling it unbuilt then fails, which is
  the point. The table is small enough to keep true — the prose is not.
- **A document that quotes a false claim in order to correct it is doing the right thing.** Excuse
  the line with `<!-- status-ok: why -->`, on it or immediately above. The reason is required: an
  exemption nobody had to justify is one nobody will revisit.

**No dependencies, by design** — the checker is standard library only and runs under a bare
`python3`, so validating the spec is never harder than editing it. External links are checked
[on a schedule](.github/workflows/external-links.yml) rather than on pull requests, so a
third-party outage cannot fail somebody's edit.

## See also

- [Organization profile & package map](https://github.com/astro-mine)
- [Governance](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)
- [Contributing guide](https://github.com/astro-mine/.github/blob/main/CONTRIBUTING.md)

## License

Apache-2.0 — see [LICENSE](LICENSE).
