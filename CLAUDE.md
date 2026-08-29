# CLAUDE.md — Agent Instructions for Koshi

Guidance for AI agents working in this repository. **Read `documentation/` before editing code.**

## Before you touch anything

1. **[D6 §1](./documentation/D6-risks-delegation-policies.md)** — find your target file's autonomy
   zone (🟢 act / 🟡 act and report / 🔴 stop and ask). If 🔴, stop.
2. **[D8 §3](./documentation/D8-rtm.md)** — reverse-trace the file: what requirements it serves,
   what tests cover it (often: none).
3. **[D4](./documentation/D4-api-and-data-contracts.md)** — is this a contract change? If yes,
   follow the escalation path in D6 §2. Contract changes are never incidental.
4. **[D7](./documentation/D7-development-book.md)** — check whether the thing you're about to "fix"
   is already a recorded decision.
5. **[D5 §4](./documentation/D5-tests-and-acceptance.md)** — satisfy the Definition of Done before
   reporting completion.

## Verification gates

```bash
# Backend — must stay green
cd source/backend && pytest -q          # expect: 155 passed  (SQLite)

# The same suite against the engine that ships. Run this before anything that
# touches the schema, a constraint, or a dialect-specific migration — F-47
# survived four migrations because the tests ran on a different engine.
TEST_DATABASE_URL='mysql+pymysql://koshi:PW@127.0.0.1:3306/koshi_test?charset=utf8mb4' pytest -q

# Frontend
pnpm test                               # expect: 399 passed (vitest)
pnpm run build                          # vue-tsc -b && vite build
```

Vitest covers both stores, every pure module including the keyboard dispatcher, and thirteen
components. Component and keyboard tests opt into jsdom with a `// @vitest-environment jsdom`
docblock. Every non-trivial frontend module now has tests; what is left unverified is the AI
*cascade* (no test tells a real LLM answer from the deterministic fallback — D5 GAP-04) and the
IndexedDB round-trip, which is mocked everywhere.

Local stacks: `./scripts/dev-env.sh` once (writes per-machine secrets into a gitignored `./.env`),
then either

- **dev** — `docker compose -f docker-compose.dev.yml up -d --build` → `localhost:8080`.
  Seeded demo accounts, `ENVIRONMENT=development`, safety guard exempted.
- **production settings** — `./scripts/local-prod.sh up` → `localhost:8090`. Guard armed, no
  seeding, CORS pinned, own secret and volume. Use this to check anything security-related; the dev
  stack cannot tell you whether the production posture holds.

Both run at once. Every compose file declares an explicit top-level `name:` — without it they share
the directory-derived project name and `up` on one deletes the others (F-38).

## Standing rules

- **Verify, don't assume.** Read the implementation before describing behaviour. This documentation
  set exists because the previous docs confidently described behaviour the code did not have.
- **Scope discipline.** Fix what was asked. A drive-by fix of a known critical risk while doing
  something else is still a red-zone violation.
- **Test before touching untested logic.** Write the characterisation test first, confirm it passes against current
  behaviour, then change the code. A suite that has never failed proves nothing: seed a defect,
  confirm it is caught, revert. If a mutation seems to survive, check it actually ran — one that
  breaks template compilation reports "no tests", which reads as a false pass.
- **Never weaken a test to make it pass.** A failing test is a finding; report it. One test
  deliberately encodes a defect — see D5 §5.
- **Preserve the local-first ordering.** IndexedDB write precedes the network call, and neither
  blocks the render. Adding an `await` before render is an architecture violation, not a style
  choice (D3 §4.1).
- **Keep docs in the same commit.** A code change that invalidates D1–D8 without updating them is
  incomplete work.
- **Scope bulk edits** to `source/` and `documentation/`. Never `submission/`, `node_modules/`,
  `.venv/`, or `dist/`.
- **No secrets in source, and none in images.** The repo has a hardcoded-JWT-secret history; don't
  widen it. `source/backend/.dockerignore` is what keeps `.env` out of the published image — it
  exists because the image was shipping the signing key (F-32). Adding a file that holds anything
  you would not publish means updating that ignore list first.
- **A modal that batches store writes must check `taskStore.canMutate` itself.** The store refuses
  silently, so the modal otherwise reports success having written nothing (F-33).

Full policy set: [D6 §6](./documentation/D6-risks-delegation-policies.md).

## Invariants you must not break casually

**Status cycle** (`TODO → IN_PROGRESS → BLOCKED → DONE → TODO`) is implemented twice — in
`source/frontend/stores/taskStore.ts` and `source/backend/app/routers/tasks.py`. They must stay
identical. Changing the order is 🔴 RED.

**Kanban is exactly 4 columns**, navigation wraps via `(c ± 1 + 4) % 4`.

**Keyboard bindings** live in one file, `source/frontend/lib/keyboard.ts`, and are covered by
`keyboard.test.ts`. Changing one also means updating `ShortcutsHelpModal.vue`, `TaskTable.vue`'s
empty state, `README.md`, and D1 §3.1 — that set has drifted twice already (DEC-005, DEC-017).

**`data-task` / `data-selected` / `data-column` / `data-active-card`** on the board components are
test hooks. Keep them when restyling; class-based selectors were what they replaced.

**`types/task.ts` is a contract.** Any breaking change to `Task` requires bumping the IndexedDB key
version (`koshi_tasks_v2_p{projectId}`) — there is no migration code and stale values are read back
unvalidated.

**Alembic owns the schema.** Any ORM change needs a new migration — never edit an applied
revision, and never reintroduce `create_all` outside development. Outside development the app
refuses to start unless the database is at head.

**Task ids: integers are canonical.** `TSK-n` is a derived display key (`TaskOut.key`), and the
only place the two representations convert is `taskKeyOf` / `serverIdOf` in `services/api.ts`.
Dependencies are `List[int]` and must resolve within the same project.

**Offline writes are gated.** A shared project (2+ members) is read-only while disconnected;
a personal one stays editable. `taskStore.canMutate` is the single gate — never bypass it.

**Localisation.** Any user-facing string goes in `lib/translations.ts` for **both** locales; the
English object is the source of truth and a missing key is a compile error.

**Three screens, no router.** `taskStore.appView` is `LANDING | BOARD | PROFILE`. A signed-out
visitor must never reach the board except via explicit guest mode.

**Uploads are an allowlist, and the client's filename never touches the filesystem.**
`services/uploads.py` generates `stored_name`; `filename` is a label. The stored content type comes
from our table, not the request — a browser sniffing an "image" into HTML would give the uploader
script execution on this origin. Widening `ALLOWED_TYPES` is 🔴 RED.

**`<img src>` cannot send a bearer token.** Anything behind auth is fetched through
`api.fetchBlob` and shown as an object URL — `AuthedMedia` for attachments, `AuthedAvatar` for
faces. Pointing an `<img>` straight at `/api/...` renders broken (F-45).

**Production is MySQL 8; a bare checkout is SQLite.** `DATABASE_URL` decides. Anything
dialect-specific in a migration must be gated on `bind.dialect.name` — MySQL cannot drop a column a
foreign key still references, and its ENUM is inline rather than a standalone type. Always
`utf8mb4`: MySQL's "utf8" is three bytes and silently truncates emoji and some Vietnamese.

**Uploads live on disk, not in the database.** A `mysqldump` is not a complete backup — the
`koshi-data` volume holds every attachment and avatar.

**SQLite ignores foreign keys unless told not to.** `enforce_foreign_keys()` is applied to the app
engine and the test engine, and deliberately NOT to Alembic's — `batch_alter_table` rebuilds tables
and enforcement turns that into a failure. Never register it on the `Engine` class.

**Never notify somebody about their own action.** It is the rule that decides whether the feed is
worth opening. `services/notify.py` is the only place notifications are created.

**A comment body is never rendered as markup.** `parseSegments` returns segments that the template
renders as Vue nodes; building an HTML string and using `v-html` would make every comment a
stored-XSS vector. 🔴 RED.

**Mentions are `@[Label](userId)` tokens in the body — no mentions table.** The id is what a mention
means, the label only what it looked like when written, so a rename resolves correctly. The regex
exists in `lib/mentions.ts` and `services/mentions.py`; change one, change both.

**Replies are one level deep.** Replying to a reply re-parents to its top-level ancestor, enforced in
the router because SQL cannot express it. You may only tag accepted members of the project.

**Avatars are visible to yourself and to people you share a project with**, because faces are
rendered on task cards. Anyone else gets 404, not 403. `POST /users/me/avatar` takes no user id, so
there is no request shape that aims it at somebody else's profile.

**Every affordance that writes must check `canMutate` or `isReadOnly` itself.** The store refuses
silently, so a control that does not check reports success having written nothing (F-33, F-43).

**Attachment URLs are not capabilities.** `download_attachment` re-checks membership on every
fetch; the id is a small integer anyone could guess.

**A task has assignees (plural), through `task_assignees`.** `Task.assignee_id` is gone (migration
0004). Everyone assigned must be an accepted member of the project.

**A PENDING membership grants nothing.** Adding somebody to a project creates an invitation;
`get_membership` returns None until they accept, so every existing guard inherits the rule. Only the
invitation endpoints may call `get_membership_row`. Widening what counts as a membership silently
grants access to everyone ever invited — 🔴 RED.

**`member_count` counts accepted members only.** It drives `isPersonalProject` and so the offline
write policy; counting invitations would flip a personal project read-only on the strength of
somebody who never replied.

**Deadline outranks priority** in board order (`lib/urgency.ts`). A LOW task due yesterday is a
broken promise; a CRITICAL one due next month is not. DONE is never urgent.

**Roles are per-project, never global.** `User` has no `role` column; authority lives on
`ProjectMember`. Every project-scoped route must call `require_member` or `require_project_pm` —
removing one silently reopens a closed critical vulnerability. The UI hiding a control is an
affordance, not a permission; the server is the only boundary.

## Repository layout

```
source/frontend/    Vue 3 SPA (Vite root — build config stays at repo root)
source/backend/     FastAPI service
documentation/      D1–D8 — the navigation layer
submission/         frozen coursework snapshot — read-only (D6 §3)
```

## Deployment

```bash
./scripts/deploy.sh <ssh-host> [remote-dir]      # ROTATE=1 to also rotate the JWT secret
```

The tar|ssh one-liner that used to be here **must not be used**. It excluded only `.git`,
`node_modules` and `dist`, so it shipped `.env` and `source/backend/.env` to production —
overwriting the live config with `ENVIRONMENT=development`, `SEED_DEMO_DATA=true` and
`CORS_ORIGINS=*`. The startup safety guard would not have objected, because it exempts development.
It also shipped developer databases over the production one. (F-37.)

`deploy.sh` excludes secrets, databases and virtualenvs, verifies afterwards that none landed,
generates the secret **on the remote** so none is ever transferred, backs up and migrates before
starting, and health-checks. Still a 🔴 red-zone action: it overwrites a live host, so run it
knowingly, not as a step in something else.

## Authorship

Lead Architect & Developer: Phạm Minh Tú. Contributors: Phạm Văn Huynh, Đàm Đức Đôn.
