# D1 — Requirements

**System:** Koshi (輿) Project Management Engine
**Status of this document:** Authoritative for *what must be true*. It does not describe *how*.
**Last verified against code:** 2026-08-28 (rev 2 — per-project roles)

> Reading order for an AI agent: **D1 (what) → D2 (where) → D3 (how it fits) → D4 (what must not break) → D5 (what proves it) → D6 (what you may not do) → D7 (what was already tried) → D8 (what a change touches).**

---

## 1. Problem statement

Mainstream issue trackers (Jira, Linear, ClickUp, Notion) impose network-round-trip latency on
every state mutation, require multi-field forms to create a unit of work, and bolt on LLM features
as free-text chat wrappers whose output cannot be trusted by downstream code.

Koshi targets a single team archetype — a small, keyboard-driven software team — and optimises for
**mutation velocity** and **schema-constrained AI output** rather than feature breadth.

## 2. Scope

**In scope.** Multi-project task tracking with a personal dashboard; four-state task lifecycle;
dependency graph and critical path; keyboard-first traversal in table and kanban views; local-first
persistence; JWT auth with **per-project** PM/MEMBER roles; four AI-assisted PM workflows with
deterministic fallback.

**Out of scope (v1).** Organisation/tenant objects above the project; real-time multi-user
collaboration or conflict resolution;
file attachments; time tracking / billing; notification delivery (email, Slack); mobile native apps;
migrations tooling (schema is created via `Base.metadata.create_all`).

## 3. Requirement register

Each requirement has a stable ID. **Never renumber these** — D8 and the test suite reference them.
Status reflects what is actually implemented in the code, not what is aspirational.

### 3.1 Functional — Interaction (FR-INT)

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-INT-01 | User can toggle Table ⇄ Kanban view with a single keystroke (`b`). | Must | Implemented |
| FR-INT-02 | Table view supports `j`/`k` (and `↓`/`↑`) row traversal, bounded to `[0, N-1]`. | Must | Implemented |
| FR-INT-03 | Kanban view supports 2D traversal: `h`/`l` across 4 columns, `j`/`k` within a column. | Must | Implemented |
| FR-INT-04 | `Space` advances the selected task one step through the status cycle. | Must | Implemented |
| FR-INT-05 | `Shift+H` / `Shift+L` move the selected task to the adjacent status column and focus follows the card. | Must | Implemented |
| FR-INT-06 | `1`–`4` set priority LOW / MEDIUM / HIGH / CRITICAL on the selected task. | Must | Implemented |
| FR-INT-07 | `n` opens the create-task modal; `i` begins inline title edit; `Enter` opens the task detail inspector. | Must | Implemented |
| FR-INT-08 | `d` / `Backspace` deletes the selected task. | Must | Implemented |
| FR-INT-09 | `/` focuses the search filter. | Must | Implemented |
| FR-INT-10 | Single-key hotkeys are suppressed while focus is inside an `<input>`, `<textarea>`, or `contenteditable`. | Must | Implemented |
| FR-INT-11 | `Escape`, bound in the **capture** phase at the app root, dismisses any modal, menu, inline edit, or search focus. | Must | Implemented |
| FR-INT-12 | `t` toggles light/dark theme with no transition animation. | Should | Implemented |
| FR-INT-13 | `?` opens the shortcuts help modal. | Should | Implemented |
| FR-INT-14 | Mobile viewports expose a docked bottom navigation bar. | Could | Implemented |

> ℹ️ These bindings were changed deliberately in commit `ea46cc2` ("overhaul keyboard schema
> (n/Enter/i/Esc)"); the older docs were never updated and have since been retired. The
> authoritative list is `source/frontend/lib/keyboard.ts`. See D7 / DEC-005.

### 3.2 Functional — Domain model (FR-DOM)

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-DOM-01 | A task has exactly one status drawn from `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`. | Must | Implemented |
| FR-DOM-02 | Status cycling is a total, cyclic function over the ordered 4-set (see D4 §3.1). | Must | Implemented |
| FR-DOM-03 | A task has exactly one priority from `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. | Must | Implemented |
| FR-DOM-04 | A task carries a complexity weight (S/M/L/XL, stored as integer points). | Must | Implemented |
| FR-DOM-05 | A task may declare dependencies on other tasks, forming a directed graph. | Must | Implemented |
| FR-DOM-06 | A task may carry an ordered list of acceptance criteria. | Should | Implemented |
| FR-DOM-07 | A task in `BLOCKED` status should carry a human-readable `blocking_reason`. | Should | **Not enforced** — the field is nullable and no validation requires it. |
| FR-DOM-08 | Tasks belong to a project; optionally to a sprint; optionally assigned to one user. | Must | Implemented |
| FR-DOM-09 | Tasks accept threaded comments authored by a user. | Should | Implemented |

### 3.3 Functional — Graph engine (FR-GRAPH)

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-GRAPH-01 | Tasks are topologically ordered so a dependency always precedes its dependents. | Must | Implemented |
| FR-GRAPH-02 | Ties in the topological order break deterministically by priority, then due date, then creation time. | Must | Implemented |
| FR-GRAPH-03 | A dependency cycle must not crash or drop tasks; cyclic members are appended after the acyclic prefix. | Must | Implemented |
| FR-GRAPH-04 | The system computes a maximal-weight dependency chain over non-`DONE` tasks and flags its members as the critical path. | Should | Implemented |
| FR-GRAPH-05 | The critical path is viewable as a graph (`v`). | Should | Implemented |

> ⚠️ FR-GRAPH-03 codifies graceful degradation. The retired SRS specified raising a
> `CycleDetectedException`; no such exception ever existed in the code. The requirement now matches
> the implementation. See D7 / DEC-002.

### 3.4 Functional — Persistence & sync (FR-PERS)

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-PERS-01 | Every mutation is committed to client IndexedDB before any network call. | Must | Implemented |
| FR-PERS-02 | The app is fully usable (read + write) with the backend unreachable. | Must | Implemented |
| FR-PERS-03 | Backend unavailability is surfaced as a passive badge, never a blocking dialog. | Must | Implemented |
| FR-PERS-04 | The JWT is persisted in `localStorage` under `koshi_jwt_token` and re-attached on boot. | Must | Implemented |
| FR-PERS-05 | The full task set can be exported and re-imported as JSON. | Could | Implemented |

### 3.5 Functional — Identity & access (FR-AUTH)

**Roles are per-project, never global.** An account has no role of its own; it holds a role in each
project it belongs to, and may be `PM` of one project while being `MEMBER` of another.

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-AUTH-01 | Users register and log in with email + password; passwords are bcrypt-hashed. | Must | Implemented |
| FR-AUTH-02 | Registration takes **no role**. A new account has zero memberships and therefore no authority anywhere. | Must | Implemented |
| FR-AUTH-03 | Users may authenticate with a Google ID token, with the signature verified. | Should | Implemented |
| FR-AUTH-04 | Every route except `/api/auth/*` and `/api/health` requires a valid HS256 bearer token. | Must | Implemented |
| FR-AUTH-05 | Creating a project makes the creator its `PM`. | Must | Implemented |
| FR-AUTH-06 | A project `PM` may add members, remove members, and change any member's role **in that project**. | Must | Implemented |
| FR-AUTH-07 | A `MEMBER` may read the project and its tasks but may not alter membership, roles, or sprints. | Must | Implemented |
| FR-AUTH-08 | The last `PM` of a project cannot be demoted or removed, so a project is never left unadministered. | Should | Implemented |
| FR-AUTH-09 | Every project-scoped endpoint refuses non-members. Non-membership returns `404`, not `403`, so project existence is not disclosed. | Must | Implemented |
| FR-AUTH-10 | A user may edit only their own profile; roles are not editable through the profile endpoint. | Must | Implemented |

### 3.6 Functional — Projects & dashboard (FR-PROJ)

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-PROJ-01 | Any authenticated user may create a project from their personal dashboard. | Must | Implemented |
| FR-PROJ-02 | The dashboard lists only the projects the caller belongs to, each annotated with the caller's role in it. | Must | Implemented |
| FR-PROJ-03 | The user may switch the active project; the board reloads for that project. | Must | Implemented |
| FR-PROJ-04 | A PM may add an existing user to a project by email, choosing their role. | Must | Implemented |
| FR-PROJ-05 | The member roster shows each member's role and their in-project workload (active tasks, WIP points). | Should | Implemented |
| FR-PROJ-06 | Role-changing controls are hidden from non-PMs, and independently refused by the server. | Must | Implemented |
| FR-PROJ-07 | A PM may delete a project they administer. | Could | Implemented |
| FR-PROJ-08 | An account with no projects is shown the dashboard on load so it can create its first one. | Should | Implemented |

### 3.7 Functional — AI workflows (FR-AI)

All AI endpoints must return **schema-valid structured output** or fail closed to a deterministic
generator. No endpoint may return free-form text where a schema is declared.

| ID | Requirement | Priority | Status |
|:--|:--|:--|:--|
| FR-AI-01 | Weekly progress summary aggregating status, blockers, and priorities for a project. | Must | Implemented (LLM-backed, text output) |
| FR-AI-02 | Meeting-minutes extraction: raw transcript → `main_topics`, `action_items`, `key_decisions`. | Must | Implemented (LLM-backed, JSON) |
| FR-AI-03 | Assignment recommendation from member skills and in-flight complexity points. | Must | Implemented (LLM-backed, JSON) |
| FR-AI-04 | Goal decomposition: a goal string → a dependency-linked subtask list. | Should | **Stub** — returns three hardcoded Vietnamese subtasks; the LLM is never called. See D7 / DEC-003. |
| FR-AI-05 | Git diff analysis: unified diff → resolved task IDs + architectural concerns. | Should | **Split brain** — a real parser exists client-side but the API client shadows it with a stub. See D7 / DEC-006. |
| FR-AI-06 | Every AI call degrades through a three-tier cascade and never returns a 5xx due to LLM unavailability. | Must | Implemented |
| FR-AI-07 | Team workload statistics: per-member active task count, complexity points, overload flag. | Must | Implemented |
| FR-AI-08 | Overdue task listing with days-overdue computation. | Should | Implemented |

### 3.8 Non-functional (NFR)

| ID | Requirement | Target | Status |
|:--|:--|:--|:--|
| NFR-01 | Local state mutation commits to the DOM within one frame. | < 16 ms | Implemented; **unverified** (no perf harness) |
| NFR-02 | No CSS transitions or animations on state change. | 0 ms | Implemented |
| NFR-03 | Idle client memory footprint. | < 15 MB | **Unverified** — claim originates in `README.md`, never measured. |
| NFR-04 | Text contrast meets WCAG AA. | ≥ 4.5:1 | Implemented; **unverified** (no audit tooling) |
| NFR-05 | Theme initialises before first paint (no FOUC). | — | Implemented via synchronous `<head>` script |
| NFR-06 | AI tier-1 timeout 10 s; tier-2 timeout 4 s; tier-3 is synchronous. | — | Implemented |
| NFR-07 | Backend test suite passes on a clean checkout. | 100% | Implemented (29/29) — was broken until D7 / DEC-004 |
| NFR-08 | Frontend has automated tests. | — | **Not met** — zero frontend tests exist. See D5 §6. |
| NFR-09 | The service refuses to start in a non-development environment while any insecure default is in force. | — | Implemented & tested — `main.py::_check_production_safety` |

## 4. Explicit non-goals

- Koshi does **not** attempt correctness under concurrent multi-user edits to the same task.
  Last-write-wins is accepted.
- Koshi does **not** guarantee that IndexedDB state and server state converge. Reconciliation is
  best-effort and one-directional at load time.
- The AI tier-3 fallback is **not** intelligent. It is a canned-response generator whose sole job is
  to keep response schemas valid when no model is reachable.

## 5. Open questions

| ID | Question | Blocks |
|:--|:--|:--|
| OQ-01 | Should task IDs be integers (server truth) or `TSK-n` strings (client truth)? See D4 §2.1. | FR-DOM-05, FR-AI-05 |
| OQ-02 | Should `blocking_reason` become mandatory when status is `BLOCKED`? | FR-DOM-07 |
| OQ-05 | Should a project support more than two roles (e.g. a read-only VIEWER)? | FR-AUTH-06 |
| OQ-06 | Should adding a member send an invitation, rather than requiring the account to exist already? | FR-PROJ-04 |
| ~~OQ-03~~ | ~~Is unverified Google token decoding acceptable outside test environments?~~ **Resolved 2026-08-28:** no. It is now opt-in via `ALLOW_UNVERIFIED_GOOGLE_TOKENS`, off by default, and blocked outside development. | — |
| OQ-04 | Should FR-AI-04 call a real model, or is deterministic decomposition the intended product? | FR-AI-04 |
