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
| `source/backend/app/routers/**` — logic within an existing shape | Response shape unchanged ⇒ yellow. Shape changed ⇒ 🔴. **Never remove a `require_member` / `require_project_pm` call** — that is 🔴 regardless of shape. |
| `source/frontend/components/ProjectDashboard.vue` | UI only. Hiding or showing a control changes no permission; the server is the boundary (D3 §5b). |
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
| **Auth, JWT, hashing, or role logic** | Security-critical. Now well covered by `test_projects_and_roles.py`, but still 🔴. |
| **Weakening or removing a project-scope guard** | `require_member` / `require_project_pm` are the entire authorisation boundary (D3 §5b). Removing one silently reopens RISK-03. |
| **Reintroducing a global role** on `User` | The per-project model is deliberate (D7 / DEC-009). A global role would create two competing sources of authority. |
| **Making `/ai/decompose` call a real model** | D7 / DEC-003 — a deliberate open question (OQ-04), and a test asserts current behaviour. |
| **Deleting or rewriting `submission/**`** | Frozen coursework artefact — see §3. |
| **Rotating or hardcoding secrets; touching CORS** | RISK-02, RISK-05. |
| **Deploying** (the `ssh umi` + `docker compose` flow in `CLAUDE.md`) | Overwrites a live production host. Human-initiated only. |
| **`git push`, force-push, branch deletion, history rewriting** | Never without an explicit instruction. |
| **Deleting `source/backend/app/data/koshi.db`** | Committed binary; may hold data someone wants. |
| **Editing an existing Alembic revision** | Immutable once applied. Add a new revision instead (P12). |
| **Changing the migration backfill policy** | It decides who keeps access to what. See `0002`'s docstring. |

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
| **RISK-01** | **Unverified Google ID tokens.** `routers/auth.py` fell back to base64-decoding the JWT payload without verifying the signature, letting anyone forge a session for any email. | Low | Critical | ✅ **Closed 2026-08-28.** Gated behind `ALLOW_UNVERIFIED_GOOGLE_TOKENS`, default **off**, blocked entirely outside development, returning `401` otherwise. Covered by `test_unverified_google_token_rejected_when_flag_disabled`. The test suite opts in explicitly. |
| **RISK-02** | **Hardcoded JWT secret.** The same default lived in `config.py` *and* `docker-compose.yml`, in a public repo, so any token could be forged. | Low | Critical | ✅ **Closed for this checkout 2026-08-28.** Secret rotated to a fresh 256-bit value held in a gitignored `.env`; tokens signed with the published secret are now rejected. The default is an obvious placeholder, compose requires `JWT_SECRET` from the environment, and startup fails outside development if it is unchanged. ⚠️ **Any other deployment must rotate independently** — see the runbook in §7. |
| **RISK-03** | **No project-scoped authorisation.** Any authenticated user could read, mutate, or delete any task in any project. | Low | High | ✅ **Closed 2026-08-28.** `ProjectMember` is now the authorisation root; every project-scoped route calls `require_member` / `require_project_pm`. Non-members get `404` across project, task, sprint, AI and stats routes, asserted by four dedicated tests. |
| **RISK-04** | **Duplicated status-cycle logic** client and server (D4 §3.1). Divergence silently desynchronises the UI from persisted state. | Medium | Medium | Both implementations currently agree. Any edit must change both. |
| **RISK-05** | **`allow_origins=["*"]` with `allow_credentials=True`.** Invalid per the CORS spec and rejected by browsers; masks real origin policy. | Low | Medium | ✅ **Closed 2026-08-28.** Origins come from `CORS_ORIGINS`; `allow_credentials` is switched off automatically when the origin list is `*`, and `*` is rejected outside development. |
| **RISK-06** | **`dagSorter.ts` has no tests** yet holds the most intricate logic in the repo. An AI edit could silently corrupt ordering. | High | High | ⚠️ **Open.** D5 GAP-01 — highest-value fix available. |
| **RISK-07** | **Documentation contradicting code.** The retired SRS/URD/README made at least seven claims the code did not support (status order, key bindings, `/api/v1`, a non-existent test file, the LLM vendor). An agent trusting prose writes wrong code. | Low | High | ✅ **Closed 2026-08-28.** Stale documents deleted; `README.md` and `CLAUDE.md` rewritten against the code; D1–D8 are the single source. Conflicts preserved for the record in D7 / DEC-005. |
| **RISK-08** | **Dependency graph is server-side unresolvable** (D4 VIOLATION-01) — dependencies are `List[str]` but IDs are `int`. | **Certain** | High | ⚠️ **Open.** OQ-01, RED zone. |
| **RISK-09** | **Two lockfiles** (`pnpm-lock.yaml`, `package-lock.json`) with `Dockerfile` using `npm install` while docs say `pnpm`. Dev and prod can resolve different trees. | Medium | Medium | ⚠️ **Open.** D7 / DEC-007. |
| **RISK-10** | **No DB migrations.** Schema came from `create_all`, which never alters an existing table, so a column change silently did nothing to a deployed volume. | Low | High | ✅ **Closed 2026-08-28.** Alembic adopted with a pre-roles baseline (`0001`) and the roles migration (`0002`), both reversible. Outside development the app creates no schema and refuses to start unless the DB is at head. Covered by `test_migrations.py`, including upgrade of a populated legacy database. |
| **RISK-11** | **Seed data fires on an empty users table** in the lifespan hook, including a fixed password `koshi123` for `pm@tupm.qzz.io`. | Low | High | ✅ **Closed 2026-08-28.** Gated behind `SEED_DEMO_DATA`, and startup fails if it is enabled outside development. |
| **RISK-12** | **Tier-3 AI output is indistinguishable from real model output** to the caller. Users may act on canned text believing it is analysis. | High | Medium | Surface the tier in the response (e.g. a `source` field). |
| **RISK-13** | **No client/server reconciliation.** IndexedDB and SQLite diverge silently; last-write-wins. | High | Medium | ⚠️ **Open** (accepted for v1, D1 §4). **Partially reduced 2026-08-28:** the cache is now partitioned per project (`koshi_tasks_v2_p{id}`), so cross-project contamination is no longer possible. Divergence *within* a project remains unreconciled, and matters more now the app is genuinely multi-user. |
| **RISK-14** | **`_check_production_safety` is untested.** A refactor could disable the boot guard without any test failing. | Low | High | ✅ **Closed 2026-08-28.** `test_startup_safety.py` covers all four insecure defaults, the safe case, and the development exemption. |
| **RISK-15** | **Membership grants access to the whole project.** There is no per-task or per-field permission, and a `MEMBER` may edit or delete any task in a project they belong to. | Medium | Low | Accepted for v1. Revisit if larger teams need it (D1 OQ-05). |

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

**P9 — No secrets in source.** Never commit a key. The startup guard in `main.py` exists to catch
this class of mistake; never relax it to make a deployment "work".

**P11 — The server is the security boundary, never the UI.** Hiding a button is an affordance, not
a permission. Every rule enforced in a component must also be enforced in a router, and the router
check is the one that counts.

**P12 — Never edit an applied migration.** Once a revision may have run anywhere, it is immutable;
correct it with a new revision. Editing it silently desynchronises databases that already ran it.

**P10 — Bulk edits are scoped.** Any find-and-replace runs against `source/` and `documentation/`
only. Never `submission/`, `node_modules/`, `.venv/`, or `dist/`.

---

## 7. Operational runbooks

### 7.1 Rotating the JWT secret

Rotation **invalidates every existing session** — all users are signed out and must log in again.
There is no dual-key grace period; that is the intended blast radius when a secret is suspected
compromised.

```bash
# 1. Generate
openssl rand -hex 32

# 2. Set it wherever the deployment reads configuration (never in source control)
#    Local:  source/backend/.env        (gitignored)
#    Docker: JWT_SECRET=... docker compose up -d

# 3. Restart the API. Verify it did not fall back to the development default:
python -c "from app.config import settings; print(settings.JWT_SECRET == settings.DEV_JWT_SECRET)"
# must print False

# 4. Confirm old tokens are refused — any request with a pre-rotation bearer
#    token must now return 401.
```

**Rotate immediately if:** the secret ever appeared in source control, a log, or a screenshot; a
deployment ran with the published default; or someone with access to it leaves the project.

> The value `koshi_super_secret_jwt_key_2026_academic_spec` shipped in this repository's public
> history. **Any deployment that ever ran with it must be rotated**, and sessions issued under it
> treated as forgeable.

### 7.2 Applying migrations

```bash
cd source/backend
alembic current                 # where is this database?
alembic upgrade head            # migrate

# Database created before Alembic existed (no alembic_version table):
alembic stamp 0001_initial_schema && alembic upgrade head
```

Outside development the API refuses to start unless the database is at head, and names the command
to run. Back up before migrating: `0002` drops `users.role`, and its `downgrade` reconstructs that
column from memberships rather than restoring the original values.

**After running `0002` on real data, review each project's roster.** The backfill deliberately
preserves existing access — every user becomes a member of every project, because that is what they
already had — so it is more permissive than most teams want. Tightening it is a deliberate
follow-up, not something the migration should silently do.
