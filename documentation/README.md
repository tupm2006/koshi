# Koshi Documentation

A navigation layer for humans and AI agents working on this codebase.
**Verified against the code on 2026-08-28.**

## Start here

Read in order. Each document answers one question.

| # | Document | Answers |
|:--|:--|:--|
| **D1** | [Requirements](./D1-requirements.md) | What must be achieved — scope, requirement register with IDs, non-goals, open questions. |
| **D2** | [Module Map](./D2-module-map.md) | Where things live — repo layout, per-file responsibilities, task→location lookup. |
| **D3** | [Architecture](./D3-architecture.md) | How components interact — topology, layering rules, the three critical flows, deployment. |
| **D4** | [API & Data Contracts](./D4-api-and-data-contracts.md) | Boundaries that must not be violated — HTTP surface, schemas, domain invariants, known violations. |
| **D5** | [Tests & Acceptance](./D5-tests-and-acceptance.md) | What correctness means — how to run the suites, per-requirement criteria, Definition of Done, coverage gaps. |
| **D6** | [Risks, Delegation & Policies](./D6-risks-delegation-policies.md) | Limits of AI autonomy — green/yellow/red zones, escalation path, risk register, standing policies. |
| **D7** | [Development Book & Decision Log](./D7-development-book.md) | What was tried, what failed, why the code is as it is — decisions, findings ledger, timeline. |
| **D8** | [RTM](./D8-rtm.md) | Traceability: requirement → work item → code → test, in both directions, plus impact analysis. |

## For an AI agent starting a task

1. **D6 §1** — find your target file's autonomy zone. If 🔴, stop and ask.
2. **D8 §3** — reverse-trace the file: what it serves and what verifies it.
3. **D4** — check whether your change touches a contract. If it does, D6 §2 applies.
4. **D7** — check whether the thing you are about to "fix" is a recorded decision.
5. **D5 §4** — satisfy the Definition of Done before reporting.

## Precedence when documents disagree

```
1. The code (verified by running it)
2. D1–D8            ← code-verified 2026-08-28
3. /README.md, /CLAUDE.md   ← summaries, rewritten to match D1–D8
```

`README.md` and `CLAUDE.md` at the repo root are deliberately summaries — an entry point and a set
of agent instructions. If either drifts from D1–D8, D1–D8 win.

## What happened to the old documentation

The previous specification set — `SRS.md`, `URD.md`, `architecture.md`, `codebase-map.md`,
`user-stories.md`, `BAO_CAO_KT1.md` — was **deleted** on 2026-08-28, not deprecated. It had drifted
from the code in seven confirmed places, including the status cycle order, the keyboard bindings,
the API prefix, and a test file that never existed. Salvageable material was absorbed into D1 and
D8 during authoring; what remained was incorrect residue that an agent could easily mistake for
authority.

The full conflict ledger is preserved in **[D7 / DEC-005](./D7-development-book.md)**, and the
rationale for deletion over deprecation in **DEC-008**. Git history retains the originals:
`git show 575bee7:docs/SRS.md`.

Note that `submission/nhom4/docs/` still contains copies of the retired specs. That is intentional —
`submission/` is a frozen coursework artefact (D6 §3), not live documentation.
