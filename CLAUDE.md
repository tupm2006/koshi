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
cd source/backend && pytest -q          # expect: 38 passed

# Frontend
pnpm test                               # expect: 188 passed (vitest)
pnpm run build                          # vue-tsc -b && vite build
```

Vitest covers both stores, every pure module including the keyboard dispatcher, and seven
components. Component and keyboard tests opt into jsdom with a `// @vitest-environment jsdom`
docblock. **Untested:** `lib/gitParser.ts` and the six AI modals.

## Standing rules

- **Verify, don't assume.** Read the implementation before describing behaviour. This documentation
  set exists because the previous docs confidently described behaviour the code did not have.
- **Scope discipline.** Fix what was asked. A drive-by fix of a known critical risk while doing
  something else is still a red-zone violation.
- **Test before touching untested logic.** For any 🟡 file with no coverage — `lib/gitParser.ts`
  and the AI modals — write the characterisation test first, confirm it passes against current
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
- **No secrets in source.** The repo already has a hardcoded JWT secret problem; don't widen it.

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

## Deployment — human-initiated only

Do **not** run this yourself. It overwrites a live production host.

```bash
tar --exclude='.git' --exclude='node_modules' --exclude='dist' -czf - . \
  | ssh umi "tar -xzf - -C /home/tupm/docker/koshi" \
  && ssh umi "cd /home/tupm/docker/koshi && docker compose build && docker compose up -d"
```

## Authorship

Lead Architect & Developer: Phạm Minh Tú. Contributors: Phạm Văn Huynh, Đàm Đức Đôn.
