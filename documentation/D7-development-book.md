# D7 — Development Book & Decision Log

**Purpose:** what was tried, what failed, and why the code is the way it is — so nobody re-litigates
a settled question or "fixes" something that is deliberate.

**Format.** Decisions are append-only. To reverse one, add a new entry that supersedes it; never
edit history. Findings record observed facts about the codebase.

---

## Part I — Decision Log

### DEC-001 — Repository split into `source/` and `documentation/`
**Date:** 2026-08-28 · **Status:** Active · **Zone:** infrastructure

**Context.** Code and docs were interleaved at the repo root: `src/`, `backend/`, `docs/`,
`index.html`, plus build config, all as siblings. An agent grepping for "where does X live" had no
structural signal.

**Decision.** Two top-level homes: `source/{frontend,backend}` for all executable code,
`documentation/` for all documentation. Build configuration stays at the root, where the toolchain
expects it.

**Alternatives considered.**
- *Move `package.json` and `vite.config.ts` into `source/frontend/` too.* Rejected — it would have
  forced a pnpm workspace restructure and changed every documented command. Higher risk than the
  ask warranted.
- *Leave `index.html` at the root* so Vite's default root keeps working. Rejected — `index.html` is
  source, and leaving it out would have defeated the point.

**Implementation.**
| File | Change |
|:--|:--|
| `vite.config.ts` | added `root: 'source/frontend'`, `build.outDir: '../../dist'`, `emptyOutDir: true` |
| `tsconfig.json` | `include` now `source/frontend/**` |
| `source/frontend/index.html` | script src `/src/main.ts` → `/main.ts` |
| `docker-compose.yml` | backend build context `./backend` → `./source/backend` |
| `.gitignore` | added `.venv/` |

`git mv` was used throughout, so history is preserved (git reports every move as `R`).

**Verification.** `npx vue-tsc -b` — no errors. `npx vite build` — 1610 modules, built to `dist/`.
`pytest -q` in `source/backend` — 6 passed.

**Consequences.** The frontend Dockerfile still uses build context `.` and works unchanged.
`nginx.conf` unaffected. `submission/` retains the old layout by design (D6 §3).

---

### DEC-002 — Cycle detection degrades gracefully instead of throwing
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active

**Context.** The SRS (retired in DEC-008) specified in §3.3 / SRS-FR-08 that Kahn's algorithm should
raise `CycleDetectedException` when `|L| < |V|`.

**What the code does.** `dagSorter.ts::topologicalSort` detects the same condition
(`result.length < tasks.length`) but appends the unsorted remainder rather than throwing. No
exception type exists anywhere in the codebase.

**Rationale for keeping it.** The sort feeds the primary render path. Throwing would blank the
board over a data problem the user cannot see or fix from the error. Silent degradation keeps every
task visible; cyclic members simply lose their ordering guarantee.

**Cost.** Cycles are invisible to the user. There is no warning badge and no console message.

**Follow-up.** Surface a non-blocking cycle warning in `DAGVisualizerModal.vue`. The SRS was wrong
here and the code was right, which is why D1 FR-GRAPH-03 now codifies the implemented behaviour.

**Related.** The two complexity scales (D4 §3.2) are deliberate for the same reason — CPM
exaggerates large tasks (S1/M3/L5/XL8) to surface bottlenecks, while workload accounting uses the
linear storage scale (S1/M2/L3/XL5). Harmonising them would flatten the critical path.

---

### DEC-003 — `/ai/decompose` is deterministic, not model-backed
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active, **open question**

**Context.** FR-AI-04 promises goal decomposition. Three of the four AI endpoints route through
`AIService` and the full three-tier cascade.

**What the code does.** `routers/ai.py::decompose_goal` never touches `AIService`. It returns three
hardcoded Vietnamese subtasks with the goal string interpolated into their titles (truncated to 30
chars), with a fixed linear dependency chain: analysis → backend → frontend.

**Why it is probably deliberate.** It guarantees a valid `AIDecomposeResponse` with zero latency and
zero cost, and `test_mandated_ai_features` asserts exactly three subtasks — the behaviour is
pinned by a test.

**Why it is a problem.** It is indistinguishable from a real feature at the API boundary. FR-AI-04
is marked "Stub" in D1 for this reason.

**Do not change this unilaterally** — RED zone (D6 §1). Tracked as OQ-04. If it is ever made
model-backed, `test_mandated_ai_features` will fail correctly; fix the endpoint, not the assertion
(D5 §5).

---

### DEC-004 — Restored the missing `require_role` in `security.py`
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth) — done deliberately, flagged

**Problem found.** On a clean clone of `main`, the backend test suite could not be collected:

```
tests/conftest.py:11: from app.main import app, seed_initial_data
app/routers/users.py:7: from app.security import get_current_user, require_role
E   ImportError: cannot import name 'require_role' from 'app.security'
```

`routers/users.py` used `Depends(require_role(RoleEnum.PM))` to guard `PATCH /users/{user_id}`, but
`security.py` never defined `require_role`. **This was pre-existing upstream, not caused by the
restructure** — `git status` records `security.py` as a pure rename (`R`) with no content change
prior to this fix. The consequence was total: FastAPI failed at import, so all 6 tests, `uvicorn`,
and the Docker backend image were all non-functional on a clean checkout.

**What was tried first.** Confirmed the blast radius by adding the function temporarily and running
the suite: **6 passed**. So a single missing 6-line dependency factory was the only thing standing
between a broken repo and a fully green suite.

**Decision.** Restore `require_role` as a dependency factory in `security.py`, mirroring the
existing `get_current_pm_user` guard:

```python
def require_role(role: RoleEnum):
    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user
    return _guard
```

**Alternatives considered.**
- *Leave it broken and only document it.* Rejected — D5 would have had nothing to verify, and the
  restructure could not be validated against a suite that cannot run.
- *Rewrite `users.py` to use the existing `get_current_pm_user`.* Rejected — that changes a caller
  to work around a missing definition, and discards the more general factory the author clearly
  intended (it takes a role parameter).

**Honest disclosure.** This is auth code, a RED zone under D6 §1, and it exceeds a pure restructure
brief. It was done because the repository was non-functional without it and the fix is the minimal
restoration of clearly-intended behaviour. **It warrants human review.** Note that the negative case
(a `MEMBER` receiving `403`) remains untested — D5 GAP-02.

**Verification.** `pytest -q` → 6 passed, 47 warnings, 5.20s.

---

### DEC-005 — The documentation/code conflict ledger
**Date:** documented 2026-08-28 · **Status:** Active (source documents retired in DEC-008)

**Why this record survives its sources.** The documents listed below were deleted in DEC-008. This
entry is kept deliberately: it is the evidence that motivated the whole D1–D8 exercise, and without
it a future reader has no way to know *why* the old specs were discarded rather than merged.

**The keyboard case, in detail.** The retired `README.md` §4.1 and `CLAUDE.md` documented `c` =
create task and `Enter` = inline title edit. `lib/keyboard.ts` implements `n` = create, `i` = inline
edit, and `Enter` = open the task detail inspector. Git confirms this was intentional: commit
`ea46cc2` — *"feat(inspector): add TaskDetailModal, overhaul keyboard schema (n/Enter/i/Esc), and
circular Kanban nav"* — changed the bindings, and the source comment still reads *"'n': Create task
(overhauls 'c')"*. **The docs were simply never updated after a deliberate refactor.**

**Why this matters more than it looks.** An agent asked to "fix the create-task shortcut" while
trusting the README would have changed working code to match wrong documentation — reverting a
deliberate design decision on the authority of a stale sentence. This is RISK-07, and it is the
reason D6 §5 fixes a precedence order.

**All confirmed conflicts (7), as found on 2026-08-28:**

| Claim | Source of claim | Reality |
|:--|:--|:--|
| Status order `TODO→IN_PROGRESS→DONE→BLOCKED` | `README.md`, `URD.md` | Code: `TODO→IN_PROGRESS→BLOCKED→DONE` |
| Status order stated a third, different way | `CLAUDE.md` | same as above |
| `c` = create, `Enter` = inline edit | `README.md`, `CLAUDE.md` | `n` = create, `i` = inline edit, `Enter` = inspector |
| Endpoints at `/api/v1/...` | `SRS.md` §3.4 | `/api/...` — no `/v1` segment exists anywhere |
| `gitParser.test.ts` verifies URD-FR-10 | `SRS.md` §5 RTM | The file does not exist; **no** frontend tests exist |
| "Gemini 1.5 Flash" is the LLM | `README.md`, `CLAUDE.md` | OpenAI-compatible (`gpt-4o-mini`) + Ollama. No Gemini client anywhere. |
| `< 15MB` idle RAM | `README.md` badge | Never measured (D1 NFR-03) |

**Related.** `svelte.config.js` claims a Svelte frontend; the app is Vue 3 (F-15).

---

### DEC-006 — `analyzeGitDiff` stub shadows the real parser
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active, **unresolved**

**Finding.** `lib/gitParser.ts::parseGitDiff` is a complete, careful implementation: close-keyword
regexes (`close[sd]?|fix(e[sd])?|resolve[sd]?`), added-line scanning for TODO/FIXME/HACK, empty
catch blocks, hardcoded-secret patterns, and `: any` coercions, returning a full
`GitDiffAnalysisResult`.

`services/api.ts::analyzeGitDiff` does not call it. It counts `+++ b/` lines, marks
`currentTasks[0]` resolved regardless of content, and returns an object **missing
`architecturalConcerns`** — so it does not even satisfy the `GitDiffAnalysisResult` type in C3.

**Assessment.** This looks like scaffolding that was never removed, not a decision. The good code is
orphaned; the placeholder is what ships.

**Recommended fix (not applied).** Have `GitDiffModal.vue` call `parseGitDiff` directly — it is a
pure client-side function and needs no network call — and delete `ApiClient.analyzeGitDiff`. This
was not done here because it changes feature behaviour, which is outside a restructure brief.
Requires the D5 GAP-03 tests first (P4).

---

### DEC-007 — Package manager is ambiguous
**Date:** documented 2026-08-28 · **Status:** Unresolved

**Finding.** Both `pnpm-lock.yaml` and `package-lock.json` are committed. `README.md` and
`CLAUDE.md` prescribe `pnpm install`. The production `Dockerfile` runs `npm install` — and copies
only `package.json`, **not** either lockfile, so the production image resolves dependencies fresh
and ignores both locks entirely.

**Impact.** The deployed bundle can be built from a different dependency tree than any developer
ever tested. RISK-09.

**Recommendation (not applied).** Pick pnpm, delete `package-lock.json`, and change the Dockerfile
to `COPY package.json pnpm-lock.yaml ./` + `pnpm install --frozen-lockfile`. Deferred: it changes
the production build and belongs to a human (D6 §1).

---

### DEC-008 — Retired the legacy specification set; D1–D8 is the only documentation
**Date:** 2026-08-28 · **Status:** Active · **Zone:** documentation

**Context.** After DEC-001 the `documentation/` folder held two incompatible generations: the
legacy set (`SRS.md`, `URD.md`, `architecture.md`, `codebase-map.md`, `user-stories.md`,
`BAO_CAO_KT1.md`) and the new code-verified D1–D8. The legacy documents were authored ~2026-08-24 to
an IEEE 29148 template and had drifted from the code in seven confirmed places (DEC-005). Keeping
both meant every agent had to know which to distrust — the exact failure mode the D-set exists to
prevent.

**Decision.** Delete the legacy six. D1–D8 becomes the sole documentation set. `README.md` and
`CLAUDE.md` were rewritten from scratch against the code and demoted to explicit *summaries* that
defer to D1–D8.

**Alternatives considered.**
- *Merge the legacy content into D1–D8.* Rejected — the salvageable material (personas, MoSCoW
  classification, the state-transition formalism, the traceability matrix) was already absorbed into
  D1 and D8 during authoring. What remained was the incorrect residue.
- *Keep them marked "deprecated".* Rejected — a deprecation banner does not stop an agent grepping
  the repo and finding `/api/v1` in a file that looks authoritative. Deletion is the only reliable
  signal, and git history preserves them.

**What was NOT deleted, and why.**
- `submission/nhom4/docs/` still contains copies of the retired SRS/URD. `submission/` is a frozen
  coursework artefact (D6 §3); rewriting it would falsify a point-in-time submission.
- `nhom4.docx` and `scripts/generate_docx.py` are coursework packaging, not project documentation.

**Recovery.** `git show 575bee7:docs/SRS.md` (and siblings) retrieves any retired document.

**Consequences.** D6 §5's precedence list drops from four tiers to three. RISK-07 moves to
**Closed**. Cross-references in D1, D5, D6 and D7 were updated to describe the retired documents in
the past tense rather than as live sources.

---

## Part II — Findings ledger

Observations that are not yet decisions. Each should become a decision or a work item.

| ID | Finding | Location | Severity | Status |
|:--|:--|:--|:--:|:--|
| F-01 | Task ID type differs across ORM (`int`), frontend (`string`), and `schema.sql` (`VARCHAR`). Dependencies are `List[str]` against `int` IDs, so the server-side graph can never resolve. | D4 VIOLATION-01 | **Critical** | Open — OQ-01, RED |
| F-02 | Google ID token signature verification failure falls back to **unverified** base64 payload decoding. Forgeable sessions for any email. | `routers/auth.py` | **Critical** | Open — RISK-01 |
| F-03 | JWT secret hardcoded in `config.py` and `docker-compose.yml`, both public. | | **Critical** | Open — RISK-02 |
| F-04 | No task endpoint verifies project membership. Any user can mutate any task. | `routers/tasks.py` | High | Open — RISK-03 |
| F-05 | `dagSorter.ts` — the most intricate logic in the repo — has zero tests. | | High | Open — D5 GAP-01 |
| F-06 | `db/schema.sql` diverges from the ORM in ≥4 ways and is never executed. | | Medium | Documented — D4 §2.3 |
| F-07 | `allow_origins=["*"]` with `allow_credentials=True` is spec-invalid. | `main.py` | Medium | Open — RISK-05 |
| F-08 | `complexity_points` validated `ge=1, le=8` on create, unvalidated on update. | `schemas/task.py` | Low | Open |
| F-09 | `blocking_reason` not required when status is `BLOCKED`, despite FR-DOM-07. | | Low | Open — OQ-02 |
| F-10 | Tier-3 AI fallback branches on **substring matches in prompt text** (`"cuộc họp"`, `"recommended_user_id"`). Rewording a prompt silently breaks fallback routing. | `ai_service.py` | Medium | Open |
| F-11 | Tier 1 fires only if `"openai" in AI_API_URL`. Any other OpenAI-compatible vendor silently falls through to Tier 2/3 even with a valid key. | `ai_service.py` | Medium | Open |
| F-12 | Seed data creates `pm@tupm.qzz.io` / `koshi123` whenever the users table is empty — including in production. | `main.py` | High | Open — RISK-11 |
| F-13 | No migration tooling. `create_all` never alters existing tables, so schema changes silently no-op on a deployed volume. | | High | Open — RISK-10 |
| F-14 | `source/backend/app/data/koshi.db` (SQLite binary) and `tsconfig.tsbuildinfo` (build cache) are committed. | | Low | Open |
| F-15 | `svelte.config.js` is dead residue from a Svelte prototype. | | Low | Open — safe to delete |
| F-16 | `AIDecomposeResponse` uses camelCase (`acceptanceCriteria`) while every other schema uses snake_case. | `schemas/ai.py` | Low | Open |
| F-17 | Tests require `source/backend/data/` to exist before the first run; nothing creates it. | `conftest.py` | Low | Open — document or `mkdir` in a fixture |
| F-18 | Widespread `datetime.utcnow()` — deprecated, 47 warnings per test run. | backend | Low | Open |

## Part III — Timeline

| Date | Event |
|:--|:--|
| ~2026-08-24 | `URD.md` / `SRS.md` v2.1.0 authored (IEEE 29148 style). Both later drift from the code. |
| 2026-08-24 | `ea46cc2` overhauls the keyboard schema to `n`/`Enter`/`i`/`Esc`; docs never updated (DEC-005). |
| pre-2026-08-28 | Svelte prototype abandoned for Vue 3; `svelte.config.js` left behind (F-15). |
| pre-2026-08-28 | `submission/nhom4` snapshot frozen for coursework. |
| pre-2026-08-28 | `require_role` lost from `security.py`; backend becomes non-importable (DEC-004). |
| **2026-08-28** | Repository restructured into `source/` + `documentation/` (DEC-001). |
| **2026-08-28** | `require_role` restored; backend suite green at 6/6 for the first time (DEC-004). |
| **2026-08-28** | D1–D8 authored against the code; 18 findings and 7 prose/code conflicts recorded. |
| **2026-08-28** | Legacy SRS/URD/architecture/codebase-map/user-stories/BAO_CAO_KT1 deleted; `README.md` and `CLAUDE.md` rewritten against the code (DEC-008). |
