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

### DEC-009 — Roles moved from the user to the (user, project) pair
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth) — requested by the maintainer

**Context.** `User.role` was a single global `PM | MEMBER` column chosen at registration. Three
things were wrong with it: a user had the same authority in every project; registration asked a
question a new user cannot meaningfully answer; and the column was nearly decorative, since only
`PATCH /users/{id}` ever consulted it (RISK-03 — nothing else checked anything).

**Decision.** Authorisation becomes relational. A new `project_members` join entity carries
`(project_id, user_id, role)` with a uniqueness constraint on the pair, and `User.role` is removed
entirely. Registration takes no role. Creating a project makes the creator its PM. A PM administers
membership and roles **within that project only**.

**Consequences by design:**
- The same account can be PM of one project and MEMBER of another, with nothing to reconcile.
- A brand-new account has zero authority anywhere until it creates or joins a project.
- `GET /projects` became the personal dashboard feed: it returns only the caller's projects,
  each annotated with `my_role`.
- `/stats/workload` gained a required `project_id`; workload is now per-project rather than global.
- `PATCH /users/{id}` became self-service; roles are no longer reachable through it.

**Alternatives considered.**
- *Keep `User.role` as a default and let projects override it.* Rejected — two sources of authority
  is exactly the ambiguity that made the old model useless. There would be no answer to "which one
  wins" that survives contact with a real permission check.
- *Add an Organisation tier above Project.* Rejected as premature; nothing in the requirements needs
  it, and it can be layered on later without changing the ProjectMember contract.
- *Model roles as permission flags rather than a two-value enum.* Rejected for v1 — no requirement
  distinguishes finer than "can administer" vs "can contribute" (D1 OQ-05 tracks revisiting this).

**404 rather than 403 for non-members.** A `403` confirms the resource exists. For a project the
caller has no right to know about, that is a disclosure, so unknown and forbidden are deliberately
indistinguishable. `403` is reserved for callers who *are* members but lack the PM role — at that
point there is nothing left to conceal and a precise error is more useful. This asymmetry is
asserted in the tests, so it cannot be "tidied up" into consistency by accident.

**Last-PM protection.** Demoting or removing the final PM of a project returns `400`. Without it a
project could be stranded with no one able to administer it and no recovery path short of direct DB
access.

**Schema migration.** `create_all` never alters an existing table (RISK-10), so an existing database
will **not** pick up `project_members`, nor drop `users.role`. For development the fix is to delete
`source/backend/data/koshi.db` and let it re-seed. A deployed database needs a real migration; this
is the clearest argument yet for adopting Alembic (RISK-10).

**Verification.** 17 new tests in `tests/test_projects_and_roles.py`; suite 6 → 23 passing. Verified
end to end against a running stack: a user registered with no role, created a project, became its
PM, added a second user as MEMBER, was refused a role change as that MEMBER (403), and the second
user held PM in their own project and MEMBER in the first simultaneously.

**Known gap.** Fixed during the same change: the IndexedDB cache used one shared key, which under a
multi-project model would let one project's board be read back as another's. Keys are now
partitioned per project (`koshi_tasks_v2_p{id}`) — see D4 §6 / INV-12. Divergence *within* a single
project is still unreconciled (RISK-13).

---

### DEC-010 — Insecure defaults became opt-in and boot-blocking
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth/config) — requested by the maintainer

**Context.** Four development conveniences were live in production code with no guard: an
unverified-Google-token fallback (RISK-01), a hardcoded JWT secret in both `config.py` and
`docker-compose.yml` (RISK-02), `allow_origins=["*"]` with `allow_credentials=True` (RISK-05), and
unconditional demo seeding with the known password `koshi123` (RISK-11).

**Decision.** Each becomes an explicit setting that is *off or safe by default*, and
`main.py::_check_production_safety()` refuses to start when `ENVIRONMENT` is not a development value
and any of them is still in force.

| Setting | Default | Outside development |
|:--|:--|:--|
| `ALLOW_UNVERIFIED_GOOGLE_TOKENS` | `false` | boot fails if true |
| `JWT_SECRET` | obvious dev placeholder | boot fails if unchanged |
| `CORS_ORIGINS` | `*` | boot fails if `*`; `allow_credentials` auto-disabled while `*` |
| `SEED_DEMO_DATA` | `true` | boot fails if true |

**Why fail closed at boot rather than warn.** A warning in a log nobody reads is how these got
shipped in the first place. Refusing to start is noticed immediately and cannot be ignored.

**Why the unverified-token path was kept at all.** `tests/test_auth.py` exercises Google sign-in
without network access to Google's public keys. Deleting the path would mean deleting that coverage.
It is enabled explicitly in `conftest.py` and nowhere else.

**Not fully resolved.** RISK-02 is *mitigated, not eliminated*: the secret still has a source-code
default rather than coming from a secret store, and any database seeded under the old published
secret should be treated as compromised — existing tokens remain forgeable by anyone who read the
public repo. Rotating it is a deployment action, not a code change.

**Verification.** `test_unverified_google_token_rejected_when_flag_disabled` asserts the `401`.
`test_startup_safety.py` covers the boot guard itself: each of the four insecure defaults blocks
startup, a fully safe production config starts, and development is exempt.

---

### DEC-011 — Alembic owns the schema; the app stops creating it
**Date:** 2026-08-28 · **Status:** Active · **Zone:** infrastructure · **Requested by the maintainer**

**Context.** RISK-10 had been open since the first audit and became blocking with DEC-009: that
change added `project_members` and dropped `users.role`, but `Base.metadata.create_all()` never
alters an existing table. A deployed database would have silently kept the old shape while the code
assumed the new one — the failure would have surfaced as confusing authorisation errors, not as a
clear schema error.

**Decision.** Adopt Alembic with two revisions, and make the environment decide who owns the schema.

| Revision | Contents |
|:--|:--|
| `0001_initial_schema` | The **pre-DEC-009** schema (global `users.role`, no `project_members`). |
| `0002_per_project_roles` | Creates `project_members`, backfills it, drops `users.role`. Reversible. |

Starting the baseline at the *old* schema is the point: an already-deployed database can be stamped
at `0001` and migrated forward, instead of being rebuilt. A baseline describing the current schema
would have offered no upgrade path at all — only a fresh install.

**Environment decides schema ownership** (D3 §5c):
- development → `create_all()`, for fast local iteration.
- otherwise → the app creates nothing and `_check_migrations_current()` refuses to start unless the
  database revision equals the code's head, printing the exact command to run.

**Backfill policy, and why it is permissive.** Before DEC-009 there was no project-scoped
authorisation: any authenticated user could touch any task in any project (RISK-03). The faithful
translation is that **every existing user becomes a member of every existing project** — that is the
access they already had. Owners and former global PMs become PMs; everyone else becomes MEMBER; an
ownerless project with no global PM promotes the lowest-id user so it is never left unadministered.

A migration must not silently revoke access people depend on. Tightening a roster is a judgement
call for whoever runs the upgrade, so it is documented as a required follow-up (D6 §7.2) rather than
guessed at here.

**Alternatives considered.**
- *Baseline at the current schema.* Rejected — no upgrade path for existing data, which is the only
  case that cannot be recovered by deleting the file.
- *Keep `create_all` everywhere and hand-write ALTERs.* Rejected — unversioned and unreversible.
- *Backfill only project owners as members.* Rejected — it would lock every other user out of
  projects they could previously use, turning an upgrade into an outage.

**Implementation note.** `migrations/env.py` takes the URL and metadata from `app.config` /
`app.database` rather than `alembic.ini`, so migrations always follow the app's configuration. An
explicitly supplied `sqlalchemy.url` still wins — without that the test-suite could not point a
migration run at a scratch database, which it does five times.

**Verification.** `test_migrations.py` (5 tests): single head; fresh upgrade produces the current
schema; a **populated legacy database** upgrades with roles backfilled correctly and nobody losing
access; an ownerless project still gets a PM; downgrade restores `users.role` from memberships.
Also exercised by hand end to end, including the boot guard refusing an unmigrated database.

---

### DEC-012 — JWT secret rotated; auth UI corrected
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Secret rotation.** The published default
(`koshi_super_secret_jwt_key_2026_academic_spec`) was replaced with a fresh 256-bit value generated
via `openssl rand -hex 32`, stored in `source/backend/.env`, which is gitignored. A tracked
`.env.example` documents every setting without carrying a value. Verified: a token signed with the
old published secret is now rejected. RISK-02 is closed **for this checkout only** — any other
deployment must rotate independently, and the runbook is D6 §7.1.

**Three UI defects fixed**, reported by the maintainer after testing DEC-009:

1. **The account panel showed a stranger's email.** `AuthModal` initialised its fields to the seeded
   demo credentials (`pm@tupm.qzz.io` / `koshi123`), so a user who had just registered saw those
   instead of their own account. Fields now start empty; the demo shortcuts are reduced to two
   labelled chips and only rendered under `import.meta.env.DEV`.

2. **The dashboard never opened for a new account.** `taskStore.isDashboardOpen` was set by `init()`,
   but `App.vue` held its own local `ref` of the same name — two independent pieces of state, so the
   store's value was never read. The local ref is gone; the store is the single source of truth.

3. **Signing in loaded no projects.** `AuthModal` called `syncWithBackend()` without
   `loadProjects()`, so `currentProjectId` stayed `null` and the board rendered empty with no route
   forward. This is the "nothing was usable" report.

**Root cause of 2 and 3 is the same:** the post-authentication sequence existed in two places
(boot and login) and they drifted. Both now funnel through a single `taskStore.onAuthenticated()`,
so the sequence cannot diverge again. A matching `logout()` clears session state and restores the
guest board.

**Also added:** an empty-state panel on the board when signed in with no project selected, and a
signed-in account panel showing the user, their current project and role, and a sign-out button —
there was previously no way to sign out at all.

**Verification.** Confirmed in-browser: registered a fresh account, was taken to the dashboard,
created a project, became its PM, and reopened the account panel to see the correct email. The
rotation was visible in the same session — the pre-rotation token was rejected and the app fell
back to the guest board.

**Gap.** These are frontend defects and the frontend still has no automated tests (D5 GAP-01 /
NFR-08). Nothing would catch a regression of any of the three. That remains the largest gap in the
project.

---

### DEC-013 — Vitest adopted; `dagSorter.ts` characterised
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Context.** D5 GAP-01 / RISK-06 had been the top-ranked gap since the first audit: the dependency
graph engine held the most intricate logic in the repository with zero automated coverage, and no
frontend test runner existed at all.

**Decision.** Add Vitest (config lives in `vite.config.ts`, `environment: 'node'` since `lib/` is
framework-free) and write **characterisation** tests — pinning what the code does today rather than
what an idealised spec says, per D6 P4/P5.

That distinction produced three assertions that would otherwise have looked like bugs to fix:

- **Cycle tolerance** rather than throwing (DEC-002) is asserted as correct behaviour.
- **The CPM weight scale** (S1/M3/L5/XL8) is pinned specifically, using a fixture where the storage
  scale (S1/M2/L3/XL5) would select a *different* winner. Harmonising the two scales — an obvious
  looking "cleanup" — now fails a test that explains why they differ (D4 §3.2).
- **A due date only breaks ties when both tasks have one**; a dated task does not sort ahead of an
  undated one. Labelled `QUIRK` so it reads as observed, not endorsed.

**Validating the tests.** All 28 passed on the first run, which for previously-untested code is a
warning sign rather than a success: a test that cannot fail proves nothing. Seven defects were
seeded into `dagSorter.ts` one at a time — removing the priority tie-break, inverting edge
direction, dropping the cycle remainder, including DONE tasks, swapping in the storage scale,
returning only the chain endpoint, ignoring the due-date tie-break — and every one was caught
(1–3 failures each). The source was then restored and confirmed byte-identical. This is now D6 P13.

**Found in the process — F-24.** `computeCriticalPath` memoises by task id alone, but
`getPathWeight`'s result also depends on the `visited` set that truncated the walk. On a **cyclic**
graph a node can be memoised from a truncated traversal and reused where the truncation would not
apply, so the same graph returns different answers depending on array order:

```
B <-> C  (cycle),  E depends on C
computeCriticalPath([B, C, E]) -> {B, C}
computeCriticalPath([E, B, C]) -> {B, C, E}
```

**Not fixed, deliberately.** The brief was to add tests; changing engine behaviour is a separate
decision (D6 P2), and the defect only manifests on graphs that are already invalid and already
degraded by DEC-002. It is pinned by a `KNOWN LIMITATION` test asserting both orders, so a future
fix fails loudly and forces the documentation to be updated rather than silently diverging.

The likely fix is to skip memoisation on any traversal that truncated at a visited node, at some
cost to the memo hit rate. That is a judgement call for the maintainer.

**Verification.** `pnpm test` → 28 passed. `pnpm test` is now part of the Definition of Done
(D5 §4).

**Gap unchanged in shape.** This covers one file. `taskStore.ts` — the widest-blast-radius module in
the repo, and where all three DEC-012 auth defects lived — is still untested (GAP-05, RISK-16). The
runner now exists, so it is unblocked.

---

### DEC-014 — Outstanding defects cleared; landing and profile pages added
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

Three separate asks: clear the open findings, add a landing page, and replace the
account popover with a real profile page.

#### Task identity unified (F-01, VIOLATION-01, RISK-08)

The longest-standing defect. `dependencies` was `List[str]` while `Task.id` was an integer, so a
dependency could never match a task: data round-tripped through the API and resolved to nothing.

**Decision.** The integer id is canonical everywhere. `dependencies` becomes `List[int]`;
`TaskOut` gains a derived `key` (`"TSK-12"`) as the display label. The server now **rejects**
dependency ids that do not resolve inside the same project, self-dependencies, and cross-project
references — silently storing junk is what let the defect survive this long. Legacy `"TSK-n"`
strings already in `dependencies_json` are coerced on read rather than left to poison the graph.

*Alternative rejected:* making the primary key a `TSK-n` string, matching `db/schema.sql`. That
would have required a table rebuild and a migration of every foreign key, to gain nothing the
derived `key` does not already provide.

On the client, conversion happens in exactly two functions — `taskKeyOf` / `serverIdOf` in
`services/api.ts` (INV-14). Scattering that translation is how the representations drifted apart.

`test_tasks.py` now asserts a dependency round-trips as a resolvable id, and covers the three
rejection cases. The pre-existing test that posted `"dependencies": ["TSK-1"]` was asserting the
broken contract; it was rewritten to create a real prerequisite (D6 P5 — the test encoded the bug).

#### Other findings closed

| Finding | Fix |
|:--|:--|
| **F-24** | `computeCriticalPath` cached results from truncated walks. Truncated results are now returned but never memoised, so cyclic graphs are order-independent. Its `KNOWN LIMITATION` test became a regression test. |
| **F-25** | `ApiClient.analyzeGitDiff` fabricated results and shadowed the real `parseGitDiff`. Deleted; `GitDiffModal` calls the parser directly, so secret/TODO detection actually runs. |
| **F-08** | `complexity_points` bounds now enforced on update, not only create. |
| **F-10** | The deterministic AI fallback selected its response by substring-matching the prompt, so rewording a prompt silently changed the fallback. It now takes an explicit `AIFeature` enum. |
| **F-11** | Tier 1 required `"openai"` in the URL, silently disabling it for every other compatible vendor even with a valid key. It now fires whenever a key is configured. |
| **F-16** | `acceptanceCriteria` / `dependsOnTitles` → snake_case, matching every other schema. |
| **F-18** | `datetime.utcnow()` replaced with a `utcnow()` helper returning naive UTC — aware datetimes would have broken comparisons against the naive columns. Warnings: 175 → 8. |
| **F-06, F-14, F-15** | Stale `db/schema.sql` and dead `svelte.config.js` deleted; the committed SQLite binary and build cache untracked. |
| **F-20** | UI labels corrected `c` → `n`. |
| **F-26 (DEC-007)** | `package-lock.json` removed; the Dockerfile now runs `pnpm install --frozen-lockfile` instead of `npm install` with no lockfile at all. |

**Two findings deliberately left open**, because they are decisions rather than defects:

- **F-09** — requiring `blocking_reason` when a task is `BLOCKED` conflicts directly with
  `POST /tasks/{id}/cycle-status`, which cycles *into* `BLOCKED` with no reason available.
  Enforcing it breaks that endpoint. Tracked as OQ-07.
- **FR-AI-04** — whether `/ai/decompose` should call a real model is a product question (OQ-04).

#### Landing page (FR-NAV-01..04)

An unauthenticated visitor previously landed on a board full of sample tasks with a small sign-in
popover, which implied the data was theirs and gave no sense of what the product was. `LandingPage.vue`
is now the default screen and where `logout()` returns.

**Tension resolved deliberately.** FR-PERS-02 promises the app is usable with the backend
unreachable. Forcing everyone through authentication would have quietly broken that, so the landing
page carries an explicit *"Explore the demo board without an account"* option (FR-NAV-03). Guest
mode survives, but as a choice rather than the accidental default.

#### Profile page (FR-PROJ-09..11)

`ProfilePage.vue` replaces the popover: identity with avatar/initials and member-since, stat tiles,
**editable name and skills** with dirty-state save/discard, project memberships with the caller's
role in each (selecting one opens its board), and sign-out. `AuthModal.vue` is deleted — its login
half moved to the landing page and its account half became this page.

#### Navigation

Three screens driven by `taskStore.appView` (`LANDING | BOARD | PROFILE`). A router was rejected:
three screens, no deep links to preserve, and it would add a dependency plus URL state to keep in
sync with a store that already owns the session (D3 §5a). The cost is that screens are not
addressable — the reason to revisit if deep-linking is ever wanted.

**Verification.** Backend 34 → 38 tests; frontend 28; type-check and build clean. Verified live:
a dependency round-trips as `[6]` and resolves, bogus and self-referential ids are rejected, the
landing page renders for a signed-out visitor, sign-in reaches the board, the profile page shows
identity and memberships, and sign-out returns to the landing page.

**Gap.** The landing and profile pages are auth-adjacent and have **no automated tests** (GAP-10),
and `taskStore.ts` — which now also owns `appView`, guest mode and profile updates — is still
untested (GAP-05, RISK-16). That remains the largest gap in the project.

---

### DEC-015 — Guest mode dropped, offline narrowed, marketing site, localisation, store tests
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

#### Guest mode removed

A signed-out visitor previously got a board of sample tasks. That implied the data was theirs, and
kept a second persistence path (`koshi_tasks_v2_guest`, `INITIAL_TASKS`, `resetToDefault`) that
nothing else used. All of it is deleted: authentication is now required before any project data
loads, and `taskStore.test.ts` asserts `continueAsGuest` and `isGuestMode` no longer exist so they
cannot quietly return.

#### Offline writes narrowed to personal projects (FR-PERS-02 / FR-PERS-06)

FR-PERS-02 promised the whole app worked offline. That is only safe with one writer. There is no
reconciliation (RISK-13), so two members editing the same task offline would silently overwrite each
other on reconnect.

```
1 member  + offline -> writable   (nobody else can conflict)
2+ members + offline -> READ-ONLY
any        + online  -> writable
```

`taskStore.canMutate` is the single gate; `createTask`, `updateTask` and `deleteTask` all consult it.
The UI shows a red "read-only" badge plus an explanatory banner for a shared project, and an amber
"editing locally" badge for a personal one — the two states are genuinely different and were worth
distinguishing rather than showing one generic "offline" pill.

This narrows a published requirement rather than fixing a bug, so FR-PERS-02 was rewritten and
FR-PERS-06 added. RISK-13 drops from High to Medium: the remaining exposure is one user on two
devices, not two users on one project.

#### Landing page rebuilt as a marketing site (FR-MKT)

Sticky nav, hero, product preview, features, how-it-works, use cases, pricing, FAQ, closing CTA,
footer. Sign-in is a small control in the top-right; authentication moved into `AuthDialog.vue` so
the fold is product messaging rather than a form.

**Two things deliberately not fabricated:**

- **No testimonials.** Inventing quotes from users who do not exist is fabricated social proof. The
  "who it is for" section describes use cases instead. Now D6 P14.
- **No demo video.** No video file ships with the repo, so the player renders only when
  `VITE_DEMO_VIDEO_URL` is set. An empty frame that says so is honest; a fake play button is not.

**Pricing is placeholder.** The figures are plausible defaults, not commercial decisions, and are
flagged in D1 §3.5b and RISK-18. They must be replaced before the page is published.

#### Localisation: English + Vietnamese (FR-I18N)

Hand-rolled rather than `vue-i18n`, per D6's preference for zero-dependency solutions: two locales
and a fixed key set do not justify a runtime library.

The design point is that `Translations` is *derived from the English object*, so adding a key
without a Vietnamese counterpart is a **compile error**, not a string that silently falls back at
runtime. A test additionally asserts no locale has empty or stale keys, and that Vietnamese actually
differs from English on sampled copy — which catches a locale stubbed out by copying the English
file.

`detectLocale` resolves stored choice → browser language (primary subtag, so `vi-VN` counts) →
English, and is a pure function so it is testable without a browser.

#### Store tests (GAP-05 / RISK-16)

24 tests over `taskStore.ts`: the screen state machine, the offline write policy, project selection
and per-project cache partitioning, task id translation, the status cycle and filters. `idb-keyval`
and the API client are faked via `vi.hoisted()` — `vi.mock` factories are hoisted above the file
body, so anything they close over must be created there.

Validated the same way as DEC-013: eight defects seeded one at a time — making a shared project
writable offline, making a personal one read-only, removing each mutation guard, sending the user to
the board on logout, skipping the dashboard for a project-less account, unpartitioning the cache key,
and sending dependencies as raw display keys. **All eight were caught**, and the source was restored
byte-identical.

**Verification.** Frontend 28 → 61 tests; backend 38 unchanged; type-check and build clean. Verified
in-browser: the landing page renders with a small top-right sign-in, and switching to Vietnamese
translates the entire page including pricing and FAQ.

**Gap.** Every store and pure module is now covered, so the residual risk sits entirely in `.vue`
components, which still have no tests at all (GAP-10, RISK-17) — including `AuthDialog` and
`ProfilePage`, which handle credentials and account edits.

---

### DEC-016 — Component tests; the last untested layer
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Context.** With both stores and every pure module covered, `.vue` files were the only layer with
no automated verification at all (GAP-10 / RISK-17) — including the two that handle credentials and
account edits.

**Decision.** Add `@vue/test-utils` + `jsdom` and cover the four highest-risk components, in
descending order of what a defect would cost:

| Component | Tests | Focus |
|:--|--:|:--|
| `AuthDialog` | 16 | Sends exactly what was typed, no role field, failure surfaced rather than a silent non-login, password cleared on success but kept after a failure. |
| `ProfilePage` | 17 | Shows the signed-in account (not a stale one), dirty-state editing, email and role not editable, memberships, sign-out clears the session. |
| `ProjectDashboard` | 14 | PM affordances present, MEMBER restrictions absent, rejected actions surfaced. |
| `LandingPage` | 14 | Sections render, sign-in is in the nav not the hero, locale switching translates the whole page, and the two content commitments hold. |

**Environment.** Vitest stays on `node` by default; component files opt in with a
`// @vitest-environment jsdom` docblock, so the pure-module suites keep running without a DOM.
`test-setup.ts` supplies `matchMedia`, which jsdom does not implement and `themeStore` calls — a
harness gap, not something the component should have to defend against.

**Two content commitments are now asserted, not just intended.** `LandingPage.test.ts` fails if a
`<video>` element appears without `VITE_DEMO_VIDEO_URL`, and fails if the copy starts claiming
"trusted by", "loved by", "customers say" and similar. Those were decisions in DEC-015 that nothing
enforced; a future copy edit would have quietly undone them.

**Mutation testing — and two false passes.** Nine defects were seeded. Six failed immediately. The
other three needed investigation rather than being written off:

1. *Removing `v-if="isPM"` from the role select* reported "0 failed". The mutation made `v-else`
   invalid on the sibling, so the template failed to **compile** and Vitest reported "no tests" —
   which the measuring script counted as zero failures. Re-run as `v-if="true"`, it was caught.
2. *Removing the `isDirty` guard in `ProfilePage`* genuinely survived: the test only asserted the
   Save button was `disabled`, which does not exercise the handler a form can still reach via
   Enter. A test for the guard itself was added, and the mutation is now caught.
3. *Removing `.trim()` from the email* genuinely survived, and the test was **wrong rather than the
   code**: an `<input type="email">` applies the HTML value-sanitisation algorithm, so jsdom strips
   surrounding whitespace before the component ever sees it. The assertion could never have failed.
   It was rewritten to state what is actually true, with the reason in a comment, rather than left
   as a green test that verified nothing.

That third case is the point of P13. A suite that passes first time on untested code is a claim, not
evidence — and here the evidence showed one assertion was theatre. D6 P13 now also warns that a
mutation which breaks compilation reads as a false pass.

**Verification.** Frontend 61 → 122 tests; backend 38 unchanged; type-check and build clean.

**Gap.** Coverage is no longer absent anywhere, but it is uneven: the **board interaction layer** —
`lib/keyboard.ts`, `TaskTable`, `KanbanBoard`, `TaskDetailModal` — is still manual-only, and that is
all fourteen FR-INT requirements (GAP-12). `lib/keyboard.ts` is the obvious next target: a pure
function over a store that is already covered, needing no DOM.

---

### DEC-017 — Keyboard dispatcher and board views tested
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Context.** GAP-12 was the last concentration of untested behaviour: `lib/keyboard.ts` carried all
fourteen FR-INT requirements on manual verification alone, and the three board components rendered
the data users actually work with.

**Coverage added (66 tests).**

| Target | Tests | Focus |
|:--|--:|:--|
| `lib/keyboard.ts` | 38 | All fourteen bindings, `isInputActive`, the typing guard, deference to the detail modal, `preventDefault` behaviour, mount/unmount lifecycle. |
| `TaskTable` + `KanbanBoard` | 15 | Rendering from the selected project, filters, selection tracking, column placement by status, per-column counts. |
| `TaskDetailModal` | 13 | Its own keyboard mode, edit buffers, blank-title refusal, task switching, and that the offline write gate applies here too. |

**Stable test hooks added to production markup.** Selection was expressed only through Tailwind
classes, so a test would have had to assert on `ring-indigo-500` — which breaks on any restyle.
`data-task`, `data-selected`, `data-column` and `data-active-card` were added instead: three
attributes that say what they mean and survive a redesign. A deliberate, small change to production
code in service of testability.

**Three things the tests found:**

1. **`isInputActive` did not return a boolean.** It is declared `: boolean` but ended with
   `target.isContentEditable`, which is `undefined` on an element where the property is not
   implemented — so the function returned `undefined`, not `false`. Real browsers always define it,
   so this never misbehaved in production, but the function did not honour its own signature.
   Changed to `=== true`.

2. **F-20 had a remnant.** `TaskTable`'s empty state still told users to *"Press `c`"* — the binding
   retired in DEC-005 and fixed in DEC-014 everywhere except here. A test now asserts the `<kbd>`
   reads `n`, so the next drift fails a build instead of misleading a user.

3. **`TaskTable` renders two inputs while editing**, not one, because it emits separate desktop and
   mobile layouts and CSS decides which is visible. Not a defect, but the test asserts the real
   number with the reason stated rather than the tidy one — a test that quietly expected 1 would
   have been wrong about the component.

**Mutation testing.** Ten defects seeded: rebinding create back to `c`, swapping `Enter`/`i`,
dropping the typing guard, deleting on Cmd+Backspace, letting `h`/`l` work in table view, ignoring
`unmount`, highlighting every table row, ignoring the kanban status filter, closing the inspector
while editing, and allowing a blank title. **All ten were caught** (1–6 failures each). The
measuring script now also distinguishes a compile-breaking mutation from a genuine survivor, after
that produced a false pass in DEC-016.

**Verification.** Frontend 122 → 188 tests; backend 38 unchanged; type-check and build clean.

**Gap.** What is left is small and known: `lib/gitParser.ts` (GAP-03) and the six AI modals
(GAP-13). `gitParser` is the better target — a pure function, security-adjacent since it scans
diffs for hardcoded secrets, and the subject of a test file the retired SRS claimed existed and
never did.

---

## Part II — Findings ledger

Observations that are not yet decisions. Each should become a decision or a work item.

| ID | Finding | Location | Severity | Status |
|:--|:--|:--|:--:|:--|
| F-01 | Task ID type differed across layers; dependencies were `List[str]` against `int` ids, so the server-side graph could never resolve. | D4 §2.1 | Critical | ✅ Closed — DEC-014 |
| F-02 | Google ID token signature verification failure fell back to **unverified** base64 payload decoding. | `routers/auth.py` | Critical | ✅ Closed — DEC-010 |
| F-03 | JWT secret hardcoded in `config.py` and `docker-compose.yml`, both public. | | Critical | ⚠️ Mitigated — DEC-010. **Rotate any deployed secret**; old tokens stay forgeable. |
| F-04 | No task endpoint verified project membership. Any user could mutate any task. | `routers/tasks.py` | High | ✅ Closed — DEC-009 |
| F-05 | `dagSorter.ts` — the most intricate logic in the repo — has zero tests. | | High | ✅ Closed — DEC-013 (28 tests, mutation-verified) |
| F-06 | `db/schema.sql` diverged from the ORM and was never executed. | | Medium | ✅ Closed — DEC-014 (deleted; Alembic owns the schema) |
| F-07 | `allow_origins=["*"]` with `allow_credentials=True` is spec-invalid. | `main.py` | Medium | ✅ Closed — DEC-010 |
| F-08 | `complexity_points` validated on create, unvalidated on update. | `schemas/task.py` | Low | ✅ Closed — DEC-014 |
| F-09 | `blocking_reason` not required when status is `BLOCKED`. | | Low | ⚠️ **Open by decision** — conflicts with `cycle-status`, which enters `BLOCKED` with no reason. OQ-07. |
| F-10 | Tier-3 AI fallback branched on substring matches in prompt text. | `ai_service.py` | Medium | ✅ Closed — DEC-014 (explicit `AIFeature` enum) |
| F-11 | Tier 1 required `"openai"` in the URL, silently disabling it for other compatible vendors. | `ai_service.py` | Medium | ✅ Closed — DEC-014 |
| F-12 | Seed data creates `pm@tupm.qzz.io` / `koshi123` whenever the users table is empty. | `main.py` | High | ✅ Closed — DEC-010 (gated by `SEED_DEMO_DATA`) |
| F-13 | No migration tooling. `create_all` never alters existing tables, so schema changes silently no-op on a deployed volume. | | High | ✅ Closed — DEC-011 (Alembic, with an upgrade path for pre-existing databases) |
| F-14 | SQLite binary and build cache were committed. | | Low | ✅ Closed — DEC-014 (untracked + gitignored) |
| F-15 | `svelte.config.js` was dead residue from a Svelte prototype. | | Low | ✅ Closed — DEC-014 (deleted) |
| F-16 | `AIDecomposeResponse` used camelCase while every other schema used snake_case. | `schemas/ai.py` | Low | ✅ Closed — DEC-014 |
| ~~F-17~~ | ~~Tests require `source/backend/data/` to exist before the first run.~~ **Incorrect when written** — `app/database.py` creates the sqlite directory itself. Corrected in D5 §1. | `database.py` | — | Withdrawn |
| F-18 | Widespread deprecated `datetime.utcnow()`. | backend | Low | ✅ Closed — DEC-014 (warnings 175 → 8) |
| F-19 | `AuthModal.vue` quick-login buttons were labelled "PM" / "Member", implying global roles. | `AuthModal.vue` | Low | ✅ Closed — DEC-012 (relabelled `pm@` / `dev@`, dev-only) |
| F-20 | UI tooltips said `c` for create task; the binding is `n`. | `App.vue`, `MobileBottomNav.vue`, `TaskTable.vue` | Low | ✅ Closed — DEC-014, with a remnant in `TaskTable`'s empty state found and fixed by DEC-017 |
| F-21 | The post-auth sequence was duplicated between boot and login and drifted, leaving a signed-in user with no projects loaded. | `taskStore.ts`, `AuthModal.vue` | High | ✅ Closed — DEC-012 (single `onAuthenticated`) |
| F-22 | `App.vue` shadowed `taskStore.isDashboardOpen` with a local ref, making the store field dead state. | `App.vue` | Medium | ✅ Closed — DEC-012 |
| F-24 | `computeCriticalPath` memoised results from truncated walks, so cyclic graphs were order-dependent. | `lib/dagSorter.ts` | Medium | ✅ Closed — DEC-014 (truncated results never cached) |
| F-25 | `ApiClient.analyzeGitDiff` fabricated results and shadowed the real `parseGitDiff`. | `services/api.ts` | Medium | ✅ Closed — DEC-014 |
| F-26 | Dockerfile ran `npm install` copying neither lockfile, so the image resolved an untested dependency tree. | `Dockerfile` | Medium | ✅ Closed — DEC-014 |
| F-27 | `isInputActive` is declared `: boolean` but returned `undefined` when `isContentEditable` was not implemented. Harmless in real browsers; a signature violation regardless. | `lib/keyboard.ts` | Low | ✅ Closed — DEC-017 |
| F-28 | `TaskTable` renders two edit inputs (desktop + mobile layouts) for a single edited row. Not a defect; recorded so a future test does not assume one. | `TaskTable.vue` | Low | Documented — DEC-017 |
| F-29 | `parseGitDiff` never populates `blockedTaskIds`; the field is always `[]` and `GitDiffModal`'s loop over it is dead code. The type promises `{id, reason}[]`. | `lib/gitParser.ts` | Low | Open — documented, see OQ-08 |
| F-30 | A BLOCKED task was auto-resolved when any word from its title appeared *as a substring* anywhere in the diff, so a task blocked on "store" was resolved by any diff touching `taskStore.ts` — and the modal then offered to write DONE. | `lib/gitParser.ts` | High | ✅ Closed — DEC-018 (whole-word match). Residual heuristic risk: OQ-08 |
| F-31 | The frontend Dockerfile ran `corepack enable` with no pinned pnpm, so the build fetched whatever pnpm was newest — which now requires a newer Node than the `node:20` base image. The image could not be built at all. | `Dockerfile`, `package.json` | High | ✅ Closed — DEC-018 (`packageManager` pin + `node:22`) |
| F-32 | The backend had no `.dockerignore` behind `COPY . .`, so the image shipped `.env` (the rotated JWT secret), `data/koshi.db` (a developer database with bcrypt hashes) and the host `.venv`. The database copy also seeded the runtime volume, so `alembic upgrade head` ran against a pre-existing schema and the container refused to start. | `source/backend/Dockerfile` | **Critical** | ✅ Closed — DEC-018 |
| F-33 | `AIDecomposerModal` and `GitDiffModal` reported "Inserted!" / "Applied to Tasks!" and closed after writing nothing, because every store write is a no-op on a read-only project (INV-15). The user was told their work was saved when it was not. | `AIDecomposerModal.vue`, `GitDiffModal.vue` | High | ✅ Closed — DEC-018 |
| F-34 | `WeeklySummaryModal` returned early with no project selected without clearing `isLoading`, so it span forever and hid its own error message behind the spinner. | `WeeklySummaryModal.vue` | Medium | ✅ Closed — DEC-018 |
| F-35 | The AI cascade was unobservable: every tier returned a bare `str`, so nothing — not the tests, not the logs, not the API response — could tell a real model answer from the deterministic fallback. A deployment with a revoked key served canned Vietnamese text and looked healthy. | `services/ai_service.py` | Medium | ✅ Closed — DEC-019 (`AITier` + a warning log) |
| F-36 | `docker-compose.dev.yml` fell back to a shared constant `JWT_SECRET` when none was set, so a token minted on one developer's machine verified on another's. Found while verifying the RISK-19 rotation: the container kept accepting a pre-rotation token. | `docker-compose.dev.yml` | Medium | ✅ Closed — DEC-019 (no default; `scripts/dev-env.sh` writes a per-machine value) |
| F-37 | The documented deploy command (`tar --exclude=.git --exclude=node_modules --exclude=dist \| ssh umi ...`) excluded no secrets, so deploying shipped the developer's `.env` and `source/backend/.env` over production's — putting the live host into `ENVIRONMENT=development` with `SEED_DEMO_DATA=true` and `CORS_ORIGINS=*`, which the startup guard exempts. It also shipped three developer SQLite databases and a host `.venv`. | `CLAUDE.md`, now `scripts/deploy.sh` | **Critical** | ✅ Closed — DEC-020 |
| F-38 | Three compose files in one directory all defaulted to project name `koshi` (from the directory), so `up` on one treated the others' containers as orphans and removed them. Bringing up the local production stack destroyed the running dev stack. | `docker-compose*.yml` | Medium | ✅ Closed — DEC-021 (explicit top-level `name:`) |
| F-39 | The "image contains no secret" check ran via `docker compose run`, which **mounts the data volume** — so it inspected image *plus* volume. It reported the runtime database as a leak, and worse, it passed on an empty volume, which is exactly when reassurance is least warranted. Written by me in DEC-020 and DEC-019. | `scripts/deploy.sh`, `scripts/local-prod.sh` | Medium | ✅ Closed — DEC-021 (`docker run` against the image, nothing mounted) |
| F-40 | `POST /tasks/{id}/comments` checked only that the task existed — no `require_member` — so any authenticated user could post into any project they had never been invited to. Dormant only because no UI had ever called the endpoint. | `routers/tasks.py` | **High** | ✅ Closed — DEC-023 |
| F-41 | The inspector's assignee selector was a hardcoded list of four team members storing strings (`"tupm"`, `"dev"`) that matched no user id, so choosing one assigned nobody. | `TaskDetailModal.vue` | Medium | ✅ Closed — DEC-023 (real project roster) |
| F-42 | `CommentThread.post()` set the "these files did not upload" message *before* `load()`, whose first act is to clear `errorMsg` — so a failed upload reported nothing and the user believed their evidence had attached. | `CommentThread.vue` | Medium | ✅ Closed — DEC-023 |
| F-43 | The task inspector had no visible way to start editing — only the `i` shortcut and clicking the title text, neither of which announces itself. Users discovered editing by clicking the description field. Entering edit mode on a read-only project was also possible, where every write is then silently refused. | `TaskDetailModal.vue` | Medium | ✅ Closed — DEC-024 |
| F-44 | The avatar replace path read the outgoing filename back *after* committing the new one, so the comparison always matched and the previous file was never unlinked. | `routers/users.py` | Low | ✅ Closed — DEC-024 |
| F-23 | Deleting the SQLite file under a running uvicorn leaves it writing to a deleted inode ("attempt to write a readonly database"). Restart the process, do not just replace the file. | operational | Low | Open — documented here |

### DEC-018 — gitParser and the AI modals tested; a secret-leaking image found

**Date:** 2026-08-28 · **Closes:** D5 GAP-03, GAP-13 · **Tests:** frontend 188 → 260

**What was asked.** Finish the last two documented coverage gaps, and bring the stack up under
Docker on this machine.

**What the tests found.** GAP-13 was filed as low value — "each modal is a thin shell over an
endpoint already covered server-side". That was wrong in one specific way. The two modals that
*write* to the board are not thin shells: they translate an AI result into a batch of store
mutations, and neither checked whether the store would accept them. On a shared project offline
every write is a no-op (INV-15), so both modals ran their loop, wrote nothing, flashed a success
message and closed (F-33). This is the failure mode the offline policy exists to prevent — a user
believing their work is saved — reintroduced one layer above the gate. The lesson generalises:
*a component that batches store writes needs the same gate the store has, because the store's
refusal is silent.*

`gitParser.ts` (GAP-03) held a worse one. Its BLOCKED-task heuristic resolved a task when any word
longer than three characters from its title appeared **as a substring** of the diff. A task blocked
on "Migrate the store" was therefore resolved by any diff mentioning `taskStore` — and
`GitDiffModal` then offered to mark it DONE. Narrowed to a whole-word match (F-30). The heuristic
itself remains: see OQ-08.

**What Docker found.** Neither image was usable.

The frontend image could not be built: `corepack enable` with no pinned pnpm version fetches the
newest release, which now requires a newer Node than `node:20` provides (F-31). Fixed by adding
`packageManager: pnpm@10.18.3` to `package.json` — so corepack resolves the pnpm the lockfile was
actually written by — and moving the builder to `node:22`.

The backend image was worse. `COPY . .` with no `.dockerignore` had been shipping `.env` — the
rotated JWT secret, the one thing D6 §7.1 says must never enter source control or an image —
together with a developer's `data/koshi.db` (real user rows and bcrypt hashes) and the host
`.venv`. Anyone able to pull the image or `exec` into a container could read the signing key and
forge sessions for any account (F-32). It also broke startup: Docker seeds a fresh named volume
from the image's directory contents, so `/app/data/koshi.db` arrived pre-populated at the old
pre-`ProjectMember` schema and `alembic upgrade head` failed on `table users already exists`.

This had been true of the **production** compose file all along, not only the new dev one. The
secret must be treated as exposed to anyone who has held that image, and rotated again before the
next deploy. Recorded as RISK-19.

**Local stack.** `docker-compose.dev.yml`, separate from the deployment file rather than an
override of it: the deployment file expects an external `proxy-net`, a real secret and a reverse
proxy, which is the right shape for the server and the wrong one for a laptop. The dev backend runs
`alembic upgrade head` before serving even though development mode would happily `create_all()` —
otherwise the migrations are never exercised until a production deploy, which is exactly when you
do not want to find out they are broken. Both migrations now run clean from an empty database, and
login through nginx returns a token.

**Rejected: "fixing" F-29 by populating `blockedTaskIds`.** Nothing in the parser detects a
*newly* blocked task, so filling the field would mean inventing a heuristic for it. Writing BLOCKED
is destructive and the existing heuristics are already too loose. Left dead and documented; the
field should probably be removed from the contract instead (OQ-08).

**Verification.** frontend 260 passed, backend 38 passed, `tsc --noEmit` clean, build clean.
14 seeded mutations across the parser and the modals: 13 caught, 1 surviving and recorded in
D5 §5 rather than hidden — the blank-diff guard in `handleAnalyze` is unreachable behind a
`:disabled` button, so no component test can reach it.

### DEC-019 — The AI cascade made observable; the leaked secret rotated

**Date:** 2026-08-28 · **Closes:** D5 GAP-04, most of RISK-19 · **Tests:** backend 38 → 64

**The problem GAP-04 named.** Every AI test asserted response *shape*. The deterministic fallback
returns exactly the right shape — that is its entire purpose — so the suite could not distinguish a
working AI deployment from one whose API key had been revoked six months earlier. Every test would
stay green while every user received canned Vietnamese text instead of analysis.

**Why this could not be fixed with tests alone.** The cascade had no notion of which tier answered.
All three return a bare `str`; the caller cannot tell them apart, and neither could a test. So the
first change was to make provenance exist: `_call_llm` now returns `(text, AITier)`.

`AITier` is deliberately **not** in any HTTP response — that would be a D4 contract change, and D4
changes are never made as a side effect of writing tests. It exists for two consumers: the tests,
and a `logger.warning("AI DEGRADED: ...")` on every tier-3 answer. That log line is currently the
*only* signal an operator would get that AI is dead, which is worth stating plainly rather than
treating as solved.

**What the tests mock.** `httpx.AsyncClient.post`, not `AIService` methods. Patching the class under
test would have proved only that the mock works — it would not have noticed the URL, the auth
header, the model name or the payload drifting. Mocking at the transport boundary means the tests
also pin that tier 1 sends `Bearer <key>` and `temperature: 0.2`, and that tier 2 sends
`stream: false` (streaming would return chunks the parser cannot read).

One assertion is about restraint rather than function: with no API key configured, tier 1 must not
be *attempted*, not merely fail. A deployment that forgot its key should not be posting prompts to
an unauthenticated endpoint.

**A mutation that survived, and the test that was wrong.** Removing the `res.status_code == 200`
check from tier 1 did not fail the suite. The parametrised 401/429/500/503 test sends an empty body,
so the mutant fell through on a `KeyError` from the missing `choices` — the right outcome for the
wrong reason. A gateway or quota error can return a perfectly well-formed payload with a non-200
code, so a test was added for exactly that. The lesson repeats DEC-016: a passing test is not
evidence until you know *which* line made it pass.

**RISK-19.** The secret was rotated, both images rebuilt from scratch with `--no-cache`, and the old
image IDs deleted. The new backend image was then checked directly rather than assumed:

```
docker run --rm --entrypoint sh koshi-koshi-backend -c 'test -f /app/.env && echo LEAKED || echo clean'
→ clean       (also: no data/koshi.db, no .venv)
```

**Verifying the rotation is what caught F-36.** After rotating, a pre-rotation bearer token was
replayed against the running container and came back **200**. The secret in `source/backend/.env`
had rotated, but the container never reads that file — it took `JWT_SECRET` from
`docker-compose.dev.yml`, which fell back to a hardcoded `dev_only_not_a_real_secret`. A constant
shared by every checkout is the same failure as the original leak, one directory over. The fallback
is gone; `scripts/dev-env.sh` now writes a per-machine random value into a gitignored root `.env`.
Replaying the same token after the fix returns **401**.

This is why the runbook (D6 §7.1) gained two steps it did not have: verify the *image*, not just the
config, and destroy the old images — rotation does not un-publish an image that contains the old key.

**Not done, and not mine to do.** The production host still runs the old image with the old secret.
Deployment is human-initiated by policy (D6 §3), so RISK-19 stays open until someone deploys and
purges the registry copies. Until then every session on that host should be treated as forgeable.

**Verification.** backend 64 passed, frontend 260 passed, `tsc --noEmit` clean, build clean.
10 seeded mutations against the cascade, all caught after the status-code test was added.

### DEC-020 — The deploy command was the last instance of the leak it was meant to fix

**Date:** 2026-08-28 · **Closes:** F-37 · **RISK-19:** still open, see below

**Context.** The repository owner explicitly authorised running the production deploy, including
generating the JWT secret, overriding the human-initiated-only policy in D6 §3. That authorisation
is recorded here because it was a deliberate exception, not a lapse.

**The deploy did not happen, for a plain reason:** `umi` does not resolve from this machine and
there are no SSH keys on it. This checkout belongs to a contributor, not to the host's owner. No
amount of permission substitutes for a route to the host.

**What the attempt found instead.** Before deploying, the command was inspected rather than run —
and it was the single worst remaining instance of the problem RISK-19 describes:

```
tar --exclude='.git' --exclude='node_modules' --exclude='dist' -czf - . | ssh umi ...
```

Three exclusions. Listing what that tarball actually contains:

```
./.env                                   ← the root secret
./source/backend/.env                    ← ENVIRONMENT=development, SEED_DEMO_DATA=true, CORS_ORIGINS=*
./source/backend/data/koshi.db           ← a developer database
./source/backend/app/data/koshi.db
./submission/nhom4/backend/app/data/koshi.db
./source/backend/.venv/bin/python        ← a host virtualenv
```

So running the documented deploy would have overwritten the production configuration with
development settings. Not merely leaking a secret — **disabling the protection against leaking
it**: `_check_production_safety` exempts `ENVIRONMENT=development`, so the host would have booted
happily, seeded `pm@tupm.qzz.io` / `koshi123`, accepted any origin, and raised nothing.

Had the deploy been runnable, it would have made production materially worse while appearing to fix
it. That is worth stating flatly: the inability to connect was the only thing standing between the
authorisation and the damage.

**`scripts/deploy.sh`.** Exclusions are now an explicit list covering `.env*`, `*.db`, `.venv`,
caches and build metadata — and, because an exclude list is only as good as its last edit, the
script *verifies* afterwards that no `.env` landed rather than trusting it. The secret is generated
on the remote with `openssl rand -hex 32` into a `chmod 600` file and never crosses the wire; it is
never passed as an argument, where it would appear in the remote process list. Rotation is opt-in
(`ROTATE=1`), because signing every user out should be a decision, not a side effect of shipping.

The script also does two things the one-liner never did. It backs up and runs
`alembic upgrade head` in a one-off container **before** `up -d` — the production compose file
deliberately does not run migrations, so that a forgotten one fails loudly, which also means
nothing was running them at all. And it refuses to start if the working tree is dirty, so what is
deployed corresponds to a commit somebody can point at.

**Rejected: making the production compose run migrations automatically,** matching
`docker-compose.dev.yml`. It would have been fewer moving parts, but it converts the "refuse to
start on a stale schema" guard into "migrate silently on every restart" — a container restart at
3am would then apply a schema change nobody was watching. Migrations stay an explicit deploy step.

**RISK-19 remains open.** The production host still runs the pre-fix image with the pre-rotation
secret. Everything that can be done from here is done; what remains needs someone with SSH access
to run `ROTATE=1 ./scripts/deploy.sh <host>`.

### DEC-021 — A production instance on the development machine

**Date:** 2026-08-28 · **Closes:** nothing in D5; adds a deployable target

**Why.** The `umi` host belongs to a third party and is unreachable from this checkout, so RISK-19's
remaining step cannot be performed here. The owner asked instead for a separate instance on this
machine. The useful version of that request is not "the dev stack on another port" — it is an
instance where the **production settings are actually in force**, because those are the settings
nobody has ever exercised locally.

`docker-compose.prod-local.yml` runs with `ENVIRONMENT=production` (so `_check_production_safety` is
armed rather than exempted), `SEED_DEMO_DATA=false` (no `koshi123` accounts), `CORS_ORIGINS` pinned
to its own origin, its own secret, and its own volume. The only concessions to being on a laptop are
that ports are published to localhost instead of joining Caddy's `proxy-net`, and there is no TLS
because there is no domain. Nothing about the security posture is relaxed.

**The posture is asserted, not assumed.** `scripts/local-prod.sh` queries the running container's
settings and fails if `ENVIRONMENT` is a development alias, the secret is the dev default,
`SEED_DEMO_DATA` is on, CORS is a wildcard, or unverified Google tokens are accepted. A future edit
that quietly relaxes one of those breaks the start, rather than producing a "production" instance
that is nothing of the sort.

**Two defects found by doing it, both mine.**

`up` on the new stack **deleted the running dev stack** (F-38). Compose derives the project name
from the directory when none is given, so all three files were project `koshi`; bringing up one
made the others' containers look like orphans. Each file now declares an explicit `name:`. The
symptom was loud, but the same mechanism against the *deployment* file on a shared host would not
have been.

The image-cleanliness check I wrote in DEC-019/020 was wrong (F-39). `docker compose run` mounts the
data volume, so it was inspecting image *plus* volume: it flagged the legitimate runtime database as
a leak on the second run, and — the part that matters — it had **passed on the first run only
because the volume was empty**. A check that passes for the wrong reason is worse than no check,
because it is quoted as evidence. Both scripts now inspect the image directly via `docker run` with
nothing mounted, resolving the name with `config --images` rather than `images -q` (which lists only
images of existing containers, and so returns nothing immediately after a `down`).

**Verified end to end** against the running instance: registration returns a user object with no
`role` field (roles are per-project); the creator gets `my_role: PM` on their own project; a task
cycles `TODO → IN_PROGRESS → BLOCKED → DONE → TODO` in the documented order (INV-01); an unknown
dependency id is rejected with 400; a non-member reading the project gets **404, not 403**
(existence non-disclosure); the AI weekly summary returns tier-3 output with no key configured; and
the seeded demo password that works on the dev stack is refused here with 401. The smoke-test data
was then destroyed, so the instance is empty and awaiting its first real signup.

### DEC-022 — Deadlines at creation, a PM view, and invitations that must be accepted

**Date:** 2026-08-28 · **Tests:** backend 64 → 80, frontend 260 → 292 · **Migration:** 0003

Four changes from using the app: no deadline field when creating a task, no
deadline-driven ordering, no way for a PM to assign work as they create it, and
"adding a member" silently conscripting somebody into a project.

**Deadlines.** `due_date` and `assignee_id` already existed on the server and in
`TaskOut` — only the create form never offered them, so setting a deadline meant
create → open detail → open description. Both are now on the form. `<input
type="date">` yields `YYYY-MM-DD` with no time, pinned to **23:59:59 local**: a
task due "the 30th" is not late at 00:01 on the 30th.

**Ordering** lives in `lib/urgency.ts`, a pure module, because a getter that
reaches into Pinia, IndexedDB and the API client cannot be tested for a
comparison. `now` is a parameter everywhere; "is this overdue?" is nothing but
boundaries, and a function that reads the clock internally cannot be tested at
one. Days are counted as **calendar days, not 24-hour blocks** — at 23:00,
something due 09:00 tomorrow is one day away, because that is what a person
reading a calendar means.

The ordering rule is deliberate: **deadline outranks priority.** A LOW task due
yesterday is a broken promise; a CRITICAL one due next month is not yet a
problem. Priority states importance, a deadline states time, and only one of
them runs out. DONE tasks are never urgent regardless of how overdue — leaving
finished work burning red at the top is how a board stops being read.

**PM vs member** is a difference of *default attention*, not of permission.
`taskStore.scope` opens a PM on ALL (their job is the project) and a member on
MINE (theirs is their queue); both can switch. The assignee selector on the
create form appears only for a PM, showing each member's current load so work
can be spread rather than stacked. Hiding it is an affordance — the server
refuses a non-PM's attempt regardless (D6 P11).

**Invitations** were the real work. `add_member` used to be unilateral: a PM
typed an email and that person was in a project they had never heard of.

Modelled as `ProjectMember.status` rather than a separate Invitation table,
which keeps the authorisation root single — still exactly one row to consult,
and exactly one place deciding what it means. `get_membership` now returns None
for a non-ACCEPTED row, so **every** existing guard inherits the rule without
being touched. `get_membership_row` exposes the raw row for the invitation
endpoints alone.

That indirection is the whole design, and `test_invitations.py` checks it
against every project-scoped surface at once — project, roster, tasks, sprints,
stats, AI — because one endpoint resolving the raw row would silently undo it.
A pending invitation returns **404, not 403**: replying must not confirm the
project exists either.

Two smaller judgements. `member_count` counts ACCEPTED only, or an unanswered
invitation would make a personal project look shared and flip it read-only
offline (INV-15) on the strength of somebody who never replied. And a DECLINED
row is kept rather than deleted, so the PM sees an answer instead of an
invitation that vanished — and can re-invite, since otherwise one mis-click
locks a person out of a project permanently.

**The migration backfills ACCEPTED**, which is the only safe choice: those
people have access today, and defaulting them to PENDING would revoke it from
every existing member of every project. The `downgrade` deletes PENDING and
DECLINED rows *before* dropping the column — otherwise downgrading would
promote every unanswered invitation into a real membership, silently widening
access.

**Found while building.** Four existing tests failed immediately, correctly:
they added a member and used the access straight away. The fixture now accepts
the invitation, and `project_with_pending_invite` was added for the flow itself.
A locally-created task was dropping `assigneeId` — it was sent to the server but
not kept in the local object, so a task you had just assigned to yourself
vanished from your own "My tasks" view until the next sync. Local-first means
the local copy is complete (INV-03). And `ProjectDashboard.test.ts`'s member
fixture predated `status`, so every member rendered as having declined; the
fixture now mirrors the server default.

**Verified end to end** against the local production instance: invited user gets
404 on the project, sees the invitation with the project name and inviter,
`member_count` stays 1 while pending, accepting grants access and returns the
project, and a PM-created task carries both its deadline and its assignee.

### DEC-023 — Collaboration: several assignees, discussion, and proof of completion

**Date:** 2026-08-29 · **Tests:** backend 80 → 107, frontend 292 → 323 · **Migration:** 0004

**One instance, not three.** Ports 5173 (Vite dev server), 8080 (docker dev) and 8090 (local
production) were all running, and the first two shared a backend — so "it works on 8080" said
nothing about the production configuration. Only 8090 is kept.

**Assignees became plural.** `tasks.assignee_id` is now the `task_assignees` join table: the same
attributive-to-relational move 0002 made for roles, for the same reason. The column could represent
exactly one fact and the fact is not always one; the workaround — duplicating a task so two people
can own it — loses that it is one piece of work. Backfill copies every existing assignment across.

Every assignee must be an **accepted** member of the project. Assigning to a pending invitation
would produce work its owner cannot open, and would confirm a user id exists for a project they
cannot see.

**Filtering** is now ALL / MINE / one named person, for everyone. Not a PM-only control: knowing
what a teammate is carrying is how you know who to ask, and it reveals nothing "All tasks" does not.
MINE resolves to the signed-in user at read time rather than storing an id, so it stays correct if
the session changes underneath it.

**Comments and evidence share one thread.** Evidence is a comment that happens to justify a
transition; two feeds would mean reading two places to follow one task. `kind` changes the label,
not the plumbing. The inspector is the home — it is already the per-task view.

The evidence prompt opens from the store on **any** path a task reaches DONE by, so no caller has
to remember to ask, and it is **never a gate**: the transition is already committed, skipping is
one click, and offline it does not appear at all because there is nowhere to upload to. A modal
that could strand a task in IN_PROGRESS because an upload failed would cost more than the evidence
is worth.

The thread is server-only and says so offline. A conversation cannot be reconciled by
last-write-wins the way a task field can, so rather than invent a merge strategy it declines.

**Uploads.** The rules are narrow because this is the one place a user hands us bytes we later hand
to another user's browser:

- An **allowlist** of image and video types, not a blocklist. Unknown is refused.
- The client's filename **never touches the filesystem** — `stored_name` is generated. That is what
  makes traversal impossible rather than merely filtered; the test uploads
  `../../../../etc/passwd.png` and asserts the stored label is `passwd.png`.
- The stored content type comes from **our table**, not the request. A browser sniffing an
  "image/png" upload into HTML would give the uploader script execution on this origin. Served with
  `nosniff` and a sandbox CSP.
- The size limit is enforced **while streaming**. Trusting `Content-Length`, or measuring after
  reading, both let a large upload exhaust memory before the check runs. A partial file is removed.
- Membership is checked **before a byte is written**, and again on every download. An attachment URL
  is not a capability — the id is a small integer anyone could guess.

**Three defects found, all pre-existing or mine.** `POST /comments` had no `require_member` at all
(F-40) — the one route in the codebase that had escaped the rule D6 states, dormant because no UI
called it. The inspector's assignee selector was a hardcoded list of four names storing strings that
matched no user id, so it had never assigned anyone (F-41). And my own `CommentThread.post()` set
the "these files did not upload" message before `load()`, whose first act is to clear it — so a
failed upload reported success (F-42). The test for it failed for the right reason on the first run.

**A test narrowed rather than deleted.** `TaskDetailModal`'s "renders no edit fields until edit mode"
started failing because the modal now hosts a comment composer, whose textarea is not an edit field
for the task. Scoped to exclude `#comment-draft` with the reason stated, rather than dropped.

**Verified end to end** on the local production instance: a task assigned to two people appears
under both filters; a member's comment is readable by the PM; evidence uploads and renders; and the
same file returns 200 to a member, 401 anonymous, 404 to a non-member, while a `.sh` is refused 400.

### DEC-024 — A visible Edit button, and profile pictures

**Date:** 2026-08-29 · **Tests:** backend 107 → 117, frontend 323 → 334 · **Migration:** 0005

**F-43 was a discoverability failure, not a missing feature.** Editing a task already worked three
ways — press `i`, click the title, click the description — and none of them announced itself. The
footer showed a `i Edit` keycap, but a keycap is a hint, not a button. The user found the
description field by accident and reasonably concluded that was the only way in.

The fix is an explicit `Edit` button in the inspector header, which becomes `Done` while editing.
The row actions in `TaskTable` had the same shape — `opacity-0 group-hover:opacity-100`, invisible
on touch and to anyone navigating by keyboard — so they now also show on the selected row.

Entering edit mode on a **read-only** project was possible, and every keystroke was then silently
discarded by the store: the F-33 shape once more. `enterEditMode` now refuses, and the button is
disabled with the reason in its tooltip. That is the third instance of the same bug class, which is
why it is now a standing rule in `CLAUDE.md` rather than a note on one component: *the store
refuses silently, so any control that writes must check `canMutate` itself.*

**Avatars** reuse the attachment writer with a narrower allowlist — images only, 2 MB — so there is
one place that decides what a stored file may be. Video is excluded deliberately: a profile picture
is re-fetched by every board that renders a card.

`POST /users/me/avatar` takes **no user id**. That is structural rather than a check somebody could
forget to write: there is no request shape that aims it at another profile. A test asserts the
absence of `/users/{id}/avatar` as a write route, so a future signature change is noticed.

Reading is narrower than "any authenticated user": **yourself, or anyone you share a project with**,
which is exactly where the app renders a face. Everyone else gets 404 rather than 403 — the reply
must not confirm the account exists. `avatar_file` is a separate column from `avatar_url` because
the served URL carries a cache-busting segment and cannot double as the filesystem name without the
two meanings drifting.

**F-44, mine.** The replace path read the outgoing filename back from the database *after*
committing the new one, so the comparison always matched and the old file was never removed — every
change would have leaked a file. Found by the test asserting the directory does not grow.

**The user's data was live during this work.** The local production instance had two real accounts
by the time migration 0005 ran; it was applied to that database rather than a reset one, and both
rows survived with `avatar_file` added. Worth recording because the instinct after a schema change
is to reset the volume, and here that would have destroyed somebody's actual project.

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
| **2026-08-28** | Roles moved from `User` to `ProjectMember`; personal dashboard added; RISK-03 closed (DEC-009). |
| **2026-08-28** | Insecure defaults gated and made boot-blocking; RISK-01/05/11/14 closed, RISK-02 mitigated (DEC-010). Suite 6 → 29. |
| **2026-08-28** | Alembic adopted with an upgrade path for pre-existing databases; RISK-10 closed (DEC-011). |
| **2026-08-28** | JWT secret rotated; three auth-UI defects fixed; RISK-02 closed for this checkout (DEC-012). Suite → 34. |
| **2026-08-28** | Vitest adopted; `dagSorter.ts` characterised with 28 mutation-verified tests; GAP-01/RISK-06 closed, F-24 found (DEC-013). |
| **2026-08-28** | Task identity unified and 11 further findings closed; landing + profile pages added (DEC-014). Backend suite → 38. |
| **2026-08-28** | Guest mode removed; offline writes narrowed to personal projects; marketing landing page; en/vi localisation; store tests (DEC-015). Frontend suite → 61. |
| **2026-08-28** | Component tests for the four highest-risk `.vue` files; GAP-10/RISK-17 closed; two false-pass tests corrected (DEC-016). Frontend suite → 122. |
| **2026-08-28** | Keyboard dispatcher and board views tested; GAP-12 closed; F-20 remnant and F-27 found (DEC-017). Frontend suite → 188. |
| **2026-08-28** | `gitParser` and the AI modals tested; GAP-03/GAP-13 closed. Docker images found to be unbuildable (F-31) and to ship the JWT secret (F-32); local stack added (DEC-018). Frontend suite → 260. |
| **2026-08-28** | AI cascade made observable and tested by tier; GAP-04 closed. Secret rotated and images rebuilt clean; a shared dev-secret fallback found and removed (DEC-019). Backend suite → 64. |
| **2026-08-28** | Deploy authorised by the owner but unreachable from this machine; inspecting the documented command found it shipped developer secrets and dev settings over production (F-37). Replaced with `scripts/deploy.sh` (DEC-020). |
| **2026-08-28** | Production-configured instance stood up locally on :8090 and verified end to end; compose project-name collision (F-38) and a false-passing image check (F-39) found and fixed (DEC-021). |
| **2026-08-28** | Deadlines on the create form, deadline-first board ordering, PM/member default scope, and membership invitations requiring acceptance (DEC-022, migration 0003). Backend → 80, frontend → 292. |
| **2026-08-29** | Multiple assignees, per-member filtering, comments, completion evidence with uploads, assignee avatars (DEC-023, migration 0004). An unguarded comment endpoint found (F-40). Backend → 107, frontend → 323. |
| **2026-08-29** | Explicit Edit button; profile picture upload (DEC-024, migration 0005). Read-only edit mode closed — third instance of the silent-refusal class. Backend → 117, frontend → 334. |

## Part IV — Open questions

Questions the code cannot answer for itself. Each needs a human decision, and each is referenced
from the finding or decision that raised it.

- **OQ-04** — should `/ai/decompose` keep returning hardcoded subtasks? (product)
- **OQ-07** — should `blocking_reason` be mandatory on BLOCKED, given `cycle-status` enters BLOCKED
  with no reason? (product; see F-09)

### OQ-08 — Should the Git diff analyser guess at all?

`parseGitDiff` has two ways to resolve a task. One is explicit and correct: `closes #TSK-12` in the
commit message. The other resolves any **BLOCKED** task whose title shares a word with the diff,
with no closing keyword required — and `GitDiffModal` offers to write DONE for both without
distinguishing them.

F-30 narrowed this from substring to whole-word matching, which removes the worst false positives
but not the category. A task blocked on "Migrate the store" is still resolved by an unrelated diff
that happens to say "store". The failure is silent and destructive: work marked DONE that is not.

Three options, in order of preference:

1. **Drop the heuristic.** Resolve only on an explicit closing keyword. Loses a feature nobody has
   asked for; makes the output trustworthy.
2. **Keep it but separate it in the UI.** Two lists — "closes, per the commit message" and
   "possibly related" — with only the first selected by default.
3. **Leave as is.** Only defensible if the modal stops being one click from a bulk status write.

Related: F-29 — `blockedTaskIds` is in the contract, always empty, and read by dead code. Whichever
option is chosen, that field should go.

**Also unresolved:** the secret scanner's coverage. It matches `keyword = "literal"` only, so it
misses the JSON/YAML colon form (`"api_key": "..."`), `Authorization: Bearer ...`, and any name
where the keyword is not immediately adjacent to the `=` — including `JWT_SECRET_VALUE = "..."`.
`gitParser.test.ts` pins each of these as a known miss. A clean report from this scanner is not
evidence that a diff is free of credentials, and D6 §7.1 should not be read as if it were.

**Owner:** product. **Blocking:** nothing; the modal is usable and now honest about read-only
projects.
