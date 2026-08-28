# D6 — Risks, Delegation Map & Policies

**Purpose:** the limits of AI autonomy in this repository. Read this **before** editing.
**Audience:** AI coding agents first, human maintainers second.

---

## 1. Delegation map — autonomy by zone

Every path in the repository sits in exactly one zone.

### 🟢 GREEN — act autonomously

Change freely; the D5 §4 Definition of Done is sufficient.

| Path | Notes |
|:--|:--|
| `documentation/**` | Except: do not silently rewrite a D7 decision record; append a superseding entry instead. |
| `source/backend/tests/**` | Adding tests is always in scope. Deleting or weakening an assertion is 🟡. |
| `source/frontend/components/**` — styling, layout, copy | Must preserve the D4 §3.1 status order and INV-01. |
| Comments, docstrings, type annotations that add no behaviour | |
| New pure helpers in `source/frontend/lib/` | Keep them Vue-free and network-free (D3 §3). |

### 🟡 YELLOW — act, then report clearly

Proceed, but state what you did and why in your summary, and update the affected D-docs.

| Path / activity | Required care |
|:--|:--|
| `source/frontend/stores/taskStore.ts` | Widest blast radius in the repo. Preserve INV-02, INV-03. |
| `source/frontend/lib/dagSorter.ts` | ⚠️ **Zero test coverage** (D5 GAP-01). Write the test first, then change. |
| `source/frontend/lib/keyboard.ts` | Any binding change must also update `ShortcutsHelpModal.vue`, `README.md`, and D1 §3.1. |
| `source/backend/app/routers/**` — logic within an existing shape | Response shape unchanged ⇒ yellow. Shape changed ⇒ 🔴. |
| `source/backend/app/services/ai_service.py` — prompts | Prompts are Vietnamese; keep the language. Tier-3 branches on **substring matches in the prompt text** — editing prompt wording can silently break fallback routing. |
| Adding a dependency | Justify it; prefer zero-dependency solutions. |
| `vite.config.ts`, `tsconfig.json`, `Dockerfile`, `docker-compose.yml`, `nginx.conf` | Path-coupled after the restructure (D3 §6). Verify `pnpm run build` afterwards. |

### 🔴 RED — stop and ask a human first

Do **not** proceed on your own initiative, even if the change looks obviously correct.

| Activity | Why |
|:--|:--|
| **Unifying task identity** (int vs `TSK-n`) | D4 VIOLATION-01. Touches four contracts at once; product decision, not a refactor. Tracked as OQ-01. |
| **Changing the status cycle order** | D4 §3.1. Breaks kanban layout, lateral movement, and a passing test. Note the prose docs already disagree with the code — that is a documentation bug, *not* licence to change the code. |
| **Any change to a D4 contract** | Request/response shapes, DB columns, `types/task.ts`, JWT claims, the `koshi_tasks_v1` key. |
| **Auth, JWT, hashing, or role logic** | Security-critical and thinly tested (D5 GAP-02). |
| **Making `/ai/decompose` call a real model** | D7 / DEC-003 — a deliberate open question (OQ-04), and a test asserts current behaviour. |
| **Deleting or rewriting `submission/**`** | Frozen coursework artefact — see §3. |
| **Rotating or hardcoding secrets; touching CORS** | RISK-02, RISK-05. |
| **Deploying** (the `ssh umi` + `docker compose` flow in `CLAUDE.md`) | Overwrites a live production host. Human-initiated only. |
| **`git push`, force-push, branch deletion, history rewriting** | Never without an explicit instruction. |
| **Deleting `source/backend/app/data/koshi.db`** | Committed binary; may hold data someone wants. |

## 2. Escalation path for a contract change

1. Stop before editing.
2. State the contract (D4 §1 ID), every consumer, and the migration story — including the
   `koshi_tasks_v1` key bump if C4 is affected.
3. Present the options and a recommendation. **Wait for a decision.**
4. On approval: change the contract, every consumer, D4, D8, and add a D7 entry — one commit.

## 3. The `submission/` directory

`submission/` is a frozen snapshot of the project prepared for coursework submission (`nhom4`),
including its own copies of `src/`, `docs/`, `backend/`, `README.md`, and `nhom4.zip`. Its `docs/`
copy still holds the retired SRS/URD — that is expected; it is a frozen artefact, not live
documentation.

**Policy:** treat it as read-only build output.
- Never edit it to "keep it in sync" — it is a point-in-time artefact.
- Never let a repo-wide find-and-replace touch it. **Scope every bulk edit to `source/` and
  `documentation/`.**
- Regeneration is `scripts/package_submission.sh`, run deliberately by a human.
- It contains the *pre-restructure* layout. That is expected and correct.

## 4. Risk register

| ID | Risk | Likelihood | Impact | Mitigation / status |
|:--|:--|:--:|:--:|:--|
| **RISK-01** | **Unverified Google ID tokens.** `routers/auth.py` catches signature-verification failure and falls back to base64-decoding the JWT payload *without verifying the signature*. Anyone can forge a token for any email and receive a valid session. | High | **Critical** | ⚠️ **Open.** Intended as a sandbox convenience; it is live in production code with no environment guard. Gate on an explicit `ALLOW_UNVERIFIED_OAUTH` flag defaulting to off. OQ-03. |
| **RISK-02** | **Hardcoded JWT secret.** The same default lives in `config.py` *and* `docker-compose.yml`. It is in the public repo, so any token can be forged. | High | **Critical** | ⚠️ **Open.** Must come from a secret store; remove the default. |
| **RISK-03** | **No project-scoped authorisation.** Any authenticated user can read, mutate, or delete any task in any project. Only `PATCH /users/{id}` checks a role. | High | High | ⚠️ **Open.** Add ownership/membership checks. D5 GAP-02. |
| **RISK-04** | **Duplicated status-cycle logic** client and server (D4 §3.1). Divergence silently desynchronises the UI from persisted state. | Medium | Medium | Both implementations currently agree. Any edit must change both. |
| **RISK-05** | **`allow_origins=["*"]` with `allow_credentials=True`.** Invalid per the CORS spec and rejected by browsers; masks real origin policy. | Medium | Medium | ⚠️ **Open.** Pin to known origins. |
| **RISK-06** | **`dagSorter.ts` has no tests** yet holds the most intricate logic in the repo. An AI edit could silently corrupt ordering. | High | High | ⚠️ **Open.** D5 GAP-01 — highest-value fix available. |
| **RISK-07** | **Documentation contradicting code.** The retired SRS/URD/README made at least seven claims the code did not support (status order, key bindings, `/api/v1`, a non-existent test file, the LLM vendor). An agent trusting prose writes wrong code. | Low | High | ✅ **Closed 2026-08-28.** Stale documents deleted; `README.md` and `CLAUDE.md` rewritten against the code; D1–D8 are the single source. Conflicts preserved for the record in D7 / DEC-005. |
| **RISK-08** | **Dependency graph is server-side unresolvable** (D4 VIOLATION-01) — dependencies are `List[str]` but IDs are `int`. | **Certain** | High | ⚠️ **Open.** OQ-01, RED zone. |
| **RISK-09** | **Two lockfiles** (`pnpm-lock.yaml`, `package-lock.json`) with `Dockerfile` using `npm install` while docs say `pnpm`. Dev and prod can resolve different trees. | Medium | Medium | ⚠️ **Open.** D7 / DEC-007. |
| **RISK-10** | **No DB migrations.** Schema comes from `create_all`, which never alters an existing table. A column change silently does nothing to a deployed volume. | Medium | High | ⚠️ **Open.** Adopt Alembic before any production schema change. |
| **RISK-11** | **Seed data fires on an empty users table** in the lifespan hook, including a fixed password `koshi123` for `pm@tupm.qzz.io`. | Medium | High | ⚠️ **Open.** Disable seeding outside development. |
| **RISK-12** | **Tier-3 AI output is indistinguishable from real model output** to the caller. Users may act on canned text believing it is analysis. | High | Medium | Surface the tier in the response (e.g. a `source` field). |
| **RISK-13** | **No client/server reconciliation.** IndexedDB and SQLite diverge silently. | High | Medium | Accepted for v1 (D1 §4). Revisit before multi-user use. |

## 5. Documentation precedence

When sources conflict, trust in this order:

```
1. The code (verified by running it)
2. D1–D8 in documentation/   ← code-verified 2026-08-28
3. README.md, CLAUDE.md      ← summaries; rewritten 2026-08-28 to match D1–D8
```

There is no longer a fourth tier: the stale SRS/URD/architecture/codebase-map documents were
deleted in DEC-008 rather than left to mislead. `README.md` and `CLAUDE.md` are deliberately
summaries — if either drifts from D1–D8, D1–D8 win.

**Never resolve a conflict by editing code to match prose.** Fix the prose, or escalate.

## 6. Standing policies for AI agents

**P1 — Verify, do not assume.** Read the implementation before describing behaviour. This
documentation set exists because four documents in this repo confidently describe behaviour the
code does not have.

**P2 — Scope discipline.** Fix what was asked. A drive-by fix of RISK-01 or VIOLATION-01 while doing
something else is a RED-zone violation regardless of how correct the fix is.

**P3 — Contracts are not refactors.** See §2.

**P4 — Test before touching untested logic.** For any 🟡 file with no coverage — `dagSorter.ts`
above all — write the characterisation test first, confirm it passes against current behaviour,
then change the code.

**P5 — Never weaken a test to make it pass.** A failing test is a finding. Report it. The one test
that encodes a defect is flagged in D5 §5.

**P6 — Report honestly.** If a change is partial, blocked, or unverified, say so plainly. Never
report a suite as passing without running it.

**P7 — Keep the docs in the same commit.** A code change that invalidates D1–D8 without updating
them is incomplete work (D5 §4).

**P8 — Preserve the local-first ordering.** IndexedDB write precedes the network call, and neither
blocks the render (INV-03, D3 §4.1). Introducing an `await` before render is an architecture
violation, not a style choice.

**P9 — No secrets in source.** Never commit a key, and never widen the existing hardcoded-secret
problem.

**P10 — Bulk edits are scoped.** Any find-and-replace runs against `source/` and `documentation/`
only. Never `submission/`, `node_modules/`, `.venv/`, or `dist/`.
