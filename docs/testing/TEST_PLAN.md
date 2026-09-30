# KOSHI PROJECT MANAGEMENT ENGINE
# COMPREHENSIVE AUTOMATION TEST PLAN & QUALITY ASSURANCE STRATEGY

**Document ID:** KOSHI-QA-TESTPLAN-2026-V1.2  
**Target System:** KOSHI Local-First Project Management System  
**QA Team & Authorship:** Nhóm 04 (ICTU) — Phạm Minh Tú, Phạm Văn Huynh, Đàm Đức Đôn  
**Standard Compliance:** ISO/IEC/IEEE 29148:2018, ISO/IEC/IEEE 29119 (Software Testing)  
**Date:** September 30, 2026  
**Status:** V1.2 APPROVED FOR PHASE 1 IMPLEMENTATION

---

## 1. PHẠM VI KIỂM THỬ (SCOPE OF TESTING)

Kế hoạch này bao phủ toàn diện toàn bộ vòng đời kiểm thử tự động cho hệ thống KOSHI theo mô hình kim tự tháp (Test Pyramid), bao gồm:

### 1.1. Frontend Scope (`source_code/frontend/`)
- **Algorithmic Engines & Utilities:**
  - `dagSorter.ts`: Kahn topological sort, cycle handling, critical path calculation theo trọng số complexity & priority, kiểm tra thuật toán $O(V+E)$ trên $\ge 1000$ nodes (ngưỡng an toàn 1.0s).
  - `keyboard.ts`: Vim navigation dispatcher 2D (`h`/`j`/`k`/`l`, `H`/`L`, arrows), shortcut actions (`Space`, `Enter`, `i`, `d`/`Backspace`, `c`/`n`, `1-4`, `/`, `a`, `g`, `v`, `t`, `?`), capture-phase `Escape` listener, focus guards (`!isInputActive()`), modifier key preservation.
  - `gitParser.ts`: Unified Git Diff parsing, extraction of ticket IDs (`TSK-X`), blocker resolution, architectural concern heuristic detection.
  - `aiDecomposer.ts`: Schema-constrained deterministic subtask graph decomposition.
- **State Management & Persistence:**
  - `taskStore.ts`: Invariant 4-step status cycle (`TODO` $\to$ `IN_PROGRESS` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`), optimistic mutations, IndexedDB (`idb-keyval`) hydration/persistence, search/filter (status, priority, sprint, critical path), priority governance (request, approve, reject), conflict resolution, JSON import/export lossless roundtrip.
  - `themeStore.ts`: Theme state toggling (0ms transition freeze, dark class).
  - `i18nStore.ts`: Locale state management and translation dictionary integrity.
- **Component & UI Integration:**
  - View presentation: `TaskTable.vue` (0-jitter active border, DONE styling), `KanbanBoard.vue` (2D grid, active ring), `TaskCard.vue`, `MobileBottomNav.vue`.
  - Modals đầy đủ: `CreateTaskModal.vue`, `TaskDetailModal.vue`, `ShortcutsHelpModal.vue`, `ProjectMembersModal.vue`, `DAGVisualizerModal.vue`, `AIDecomposerModal.vue`, `WeeklySummaryModal.vue`, `MeetingMinutesModal.vue`, `WorkloadAssignModal.vue`, `GitDiffModal.vue`, `AuthModal.vue`.
  - Application Root: `App.vue` (Escape capture phase, view routing).
- **End-to-End (E2E) User Workflows (Playwright):**
  - Full keyboard-only workflows (no mouse).
  - 4-step status cyclic progression via Space and lateral Shift+H/L.
  - Multi-view switching (`b`) and theme persistence (`t`).
  - Offline-first resilience: network disconnect $\to$ optimistic mutation $\to$ reload $\to$ network reconnect $\to$ background synchronization.
  - Responsive layout and touch gestures on mobile viewports.
- **Non-Functional Testing:**
  - Project `perf` riêng biệt: Action latency budget ($< 50\text{ms}$), optimistic mutation budget ($< 16\text{ms}$), idle JS Heap memory footprint ($< 15\text{MB}$) đo qua $\ge 50$ mẫu.
  - Accessibility audit via `@axe-core/playwright` (thiết lập baseline, chống hồi quy).
  - Visual regression testing (snapshot testing cho Light/Dark themes trên Chromium môi trường Linux/Docker cố định).

### 1.2. Backend Scope (`source_code/backend/`)
- **API Endpoints:**
  - Authentication: `/api/auth/register`, `/api/auth/login`, `/api/auth/google`, `/api/auth/me`.
  - Tasks: `GET`, `POST`, `GET /{id}`, `PUT/PATCH /{id}`, `DELETE /{id}`, `POST /{id}/cycle-status`, `POST /{id}/comments`, `request-priority`, `approve-priority`, `reject-priority`.
  - Projects & Members: `GET /api/projects`, `POST /api/projects`, `/api/projects/{id}/members`, RBAC enforcement.
  - Sprints & Stats: `GET /api/sprints`, `POST /api/sprints`, `/api/sprints/{id}/stats`.
  - AI Services: `/api/v1/ai/weekly-summary`, `/api/v1/ai/meeting-minutes`, `/api/v1/ai/recommend-assignment`, `/api/v1/ai/decompose`.
- **Database & Integrity:**
  - SQLite WAL mode, foreign keys (`PRAGMA foreign_keys = ON`), cascading deletes on task dependencies and project members.
  - In-memory SQLite session isolation per test.
- **Security & Resilience:**
  - Token validation (JWT HS256, expiration, invalid signatures).
  - RBAC & BOLA/IDOR prevention (`verify_project_membership`).
  - Input validation (Pydantic schema constraints, 422 Unprocessable Entity).
  - SQL injection and XSS sanitation.
  - AI Mock boundary: Full mocking of external LLMs (OpenAI/Ollama), schema adherence, fallback tier transitions, prompt injection resistance.

---

## 2. NGOÀI PHẠM VI (OUT OF SCOPE)
- Stress/load testing vượt quá 10,000 concurrent users trên single SQLite node.
- Live external network calls (OpenAI API key, Google OAuth server) — 100% mocked.
- Thiết bị di động vật lý (chỉ dùng Playwright viewport & touch emulation).
- Đo RAM tiến trình hệ điều hành (Resident Set Size) — chỉ đo JS Heap memory của runtime qua Chrome DevTools Protocol.

---

## 3. ĐÁNH GIÁ RỦI RO & BIỆN PHÁP GIẢM THIỂU (RISKS & MITIGATIONS)

| ID | Rủi ro (Risk) | Khả năng | Mức độ | Biện pháp giảm thiểu (Mitigation Strategy) |
| :--- | :--- | :---: | :---: | :--- |
| **R-01** | **Spec Conflict: Shortcut Tạo Task** (`c` vs `n`) | Cao | Cao | Test theo đặc tả `c`, đánh dấu `xfail`, ghi vào `BUG_REPORT.md` loại "Spec conflict". Đồng thời test phím `n` để không nghẽn E2E. |
| **R-02** | **Spec Conflict: Trọng số Critical Path** (S=1, M=2, L=3, XL=5 vs S=1, M=3, L=5, XL=8 kèm priority) | Cao | Trung bình | Test theo đặc tả chuẩn, đánh dấu `xfail`, ghi `BUG_REPORT.md` loại "Spec conflict". Viết test bảo vệ hàm hiện tại chống hồi quy. |
| **R-03** | **Code Bug: Thiếu Rollback khi API lỗi trong `taskStore.ts`** | Cao | Cao | Test hành vi rollback, đánh dấu `xfail`, ghi vào `BUG_REPORT.md` loại "Code bug". Tuyệt đối không sửa code sản phẩm. |
| **R-04** | **Flaky do Test Timing/Performance trên CI** | Cao | Cao | Tách hoàn toàn test timing và memory sang project riêng `perf`. Dùng p95 qua $\ge 50$ mẫu và áp dụng hệ số nới 1.5x trên CI. Không đưa vào suite kiểm tra ổn định chức năng (3 lần chạy sạch). |
| **R-05** | **Ô nhiễm dữ liệu giữa các test backend** | Trung bình | Cao | Sử dụng in-memory SQLite (`sqlite:///:memory:`) với transaction rollback cô lập trong `conftest.py`. |
| **R-06** | **Thiếu IndexedDB trong jsdom** | Cao | Trung bình | Cấu hình `fake-indexeddb/auto` trong Vitest setup file. |
| **R-07** | **LLM API không ổn định** | Cao | Cao | Mock 100% tại `httpx.AsyncClient` hoặc `AIService._call_llm`. |

---

## 4. MÔ HÌNH KIM TỰ THÁP KIỂM THỬ (TEST PYRAMID ARCHITECTURE)

```
                     / \
                    /   \
                   / E2E \          ~10-15% (Playwright)
                  /-------\         - Core User Workflows, Vim Nav, Offline Sync
                 /         \
                / Component \       ~25-30% (@vue/test-utils + jsdom)
               /   & API     \      - Vue Modals/Boards, FastAPI Routers, RBAC
              /---------------\
             /      Unit       \    ~55-60% (Vitest + pytest)
            /   (Logic/Store)   \   - DAG, Keyboard, TaskStore, AI Heuristics
           /---------------------\
```

---

## 5. MA TRẬN TRUY VẾT YÊU CẦU & TEST CASES (RTM) - ĐỒNG BỘ 100% VỚI MỤC 6 & MỤC 9

| Requirement ID | Nguồn đặc tả | Mô tả yêu cầu | Test Case ID | Tầng kiểm thử | File thực thi chuẩn hóa |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **URD-FR-01** | URD §3.1 / SRS-FR-01 | Toggle Table / Kanban qua phím `b` | `TC-KB-01`, `TC-STORE-06`, `TC-E2E-02` | Unit / E2E | `keyboard.test.ts`, `taskStore.test.ts`, `navigation.spec.ts` |
| **URD-FR-02a** | URD §3.1 / US-01 | Vim navigation Table (`j`/`k`, arrows, clamped) | `TC-KB-02`, `TC-STORE-07`, `TC-COMP-TABLE-01` | Unit / Comp | `keyboard.test.ts`, `taskStore.test.ts`, `TaskTable.test.ts` |
| **URD-FR-02b** | URD §3.1 / SRS-FR-01 | Vim 2D Kanban (`h`/`j`/`k`/`l`, bounds clamp) | `TC-KB-03`, `TC-STORE-08`, `TC-COMP-KANBAN-01` | Unit / Comp | `keyboard.test.ts`, `taskStore.test.ts`, `KanbanBoard.test.ts` |
| **URD-FR-02c** | URD §3.1 / Core Rule 1 | Status cycle 4 bước (`TODO` $\to$ `IN_PROG` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`) | `TC-STORE-01`, `TC-KB-04`, `TC-API-TASK-03`, `TC-E2E-03` | Unit / API / E2E | `taskStore.test.ts`, `keyboard.test.ts`, `test_tasks_api.py`, `task-lifecycle.spec.ts` |
| **URD-FR-02d** | URD §3.1 / US-02 | Dịch cột Kanban `Shift+H` / `Shift+L` kèm focus retention & wrap-around | `TC-KB-05`, `TC-STORE-09`, `TC-E2E-02` | Unit / E2E | `keyboard.test.ts`, `taskStore.test.ts`, `navigation.spec.ts` |
| **URD-FR-02e** | URD §3.1 / Core Rule 3 | Priority hotkeys `1`-`4` (`LOW`, `MED`, `HIGH`, `CRITICAL`) | `TC-KB-06`, `TC-STORE-03` | Unit | `keyboard.test.ts`, `taskStore.test.ts` |
| **URD-FR-02f** | URD §3.1 / US-03 | Inline title edit vs Detail Modal với `Enter` & `i` | `TC-KB-07a`, `TC-KB-07b`, `TC-COMP-MODAL-DETAIL`, `TC-E2E-01` | Unit / Comp / E2E | `keyboard.test.ts`, `Modals.test.ts`, `task-lifecycle.spec.ts` |
| **URD-FR-02g** | URD §3.1 / SRS-FR-01 | Delete selected task (`d` / `Backspace`, modifier guard) | `TC-KB-08`, `TC-STORE-02` | Unit | `keyboard.test.ts`, `taskStore.test.ts` |
| **URD-FR-02h** | URD §3.1 / Core Rule 3 | Shortcut tạo task `c` mở Create Task Modal | `TC-KB-09`, `TC-COMP-MODAL-CREATE`, `TC-E2E-01` | Unit / Comp / E2E | `keyboard.test.ts`, `Modals.test.ts`, `task-lifecycle.spec.ts` |
| **URD-FR-02i** | URD §3.1 / Core Rule 3 | Search focus với `/` | `TC-KB-10`, `TC-STORE-11`, `TC-E2E-04` | Unit / E2E | `keyboard.test.ts`, `taskStore.test.ts`, `search-modal.spec.ts` |
| **URD-FR-03** | URD §3.1 / SRS-FR-03 | Capture-phase global `Escape` dismiss modals/edit/search | `TC-KB-11`, `TC-COMP-APP-ESC`, `TC-COMP-MODAL-A11Y`, `TC-E2E-04` | Unit / Comp / E2E | `keyboard.test.ts`, `App.test.ts`, `Modals.test.ts`, `search-modal.spec.ts` |
| **URD-FR-04** | URD §3.1 / Core Rule 5 | Local-first IndexedDB persistence, Optimistic Rollback & sync | `TC-STORE-04`, `TC-STORE-05`, `TC-STORE-10`, `TC-E2E-06` | Unit / E2E | `taskStore.test.ts`, `offline-first.spec.ts` |
| **URD-FR-05** | URD §3.1 / SRS-FR-05,07 | Theme toggling `t`, 0ms transition freeze, contrast AA | `TC-THEME-01`, `TC-E2E-05`, `TC-A11Y-01` | Unit / E2E / NFR | `themeStore.test.ts`, `theme-toggle.spec.ts`, `a11y.spec.ts` |
| **URD-FR-06** | URD §3.2 / SRS-FR-08,09 | Topological DAG, Kahn cycle detection, Critical Path Flame | `TC-DAG-01` $\to$ `08`, `TC-SRV-DAG-01`, `TC-COMP-FLAME-01`, `TC-COMP-MODAL-DAG`, `TC-E2E-07` | Unit / Srv / Comp / E2E | `dagSorter.test.ts`, `test_dag_cpm.py`, `TaskTable.test.ts`, `Modals.test.ts`, `dag-visualizer.spec.ts` |
| **URD-FR-07** | URD §3.2 / SRS-FR-11 / US-05 | AI Weekly Progress Summary | `TC-SRV-AI-01`, `TC-API-AI-01`, `TC-COMP-MODAL-SUMMARY` | Service / API / Comp | `test_ai_cascade.py`, `test_ai_api.py`, `Modals.test.ts` |
| **URD-FR-08** | URD §3.2 / SRS-FR-12 / US-06 | AI Meeting Minutes Extraction | `TC-SRV-AI-02`, `TC-API-AI-02`, `TC-COMP-MODAL-MINUTES` | Service / API / Comp | `test_ai_cascade.py`, `test_ai_api.py`, `Modals.test.ts` |
| **URD-FR-09** | URD §3.2 / SRS-FR-13 | AI Workload & Smart Assignment Recommendation | `TC-SRV-AI-03`, `TC-API-AI-03`, `TC-COMP-MODAL-WORKLOAD` | Service / API / Comp | `test_ai_cascade.py`, `test_ai_api.py`, `Modals.test.ts` |
| **URD-FR-10** | URD §3.2 / SRS-FR-01 | Git Diff Ticket Synchronizer AST Parser | `TC-DIFF-01` $\to$ `05`, `TC-COMP-MODAL-DIFF` | Unit / Comp | `gitParser.test.ts`, `Modals.test.ts` |
| **URD-FR-11** | URD §3.3 / Core Rule 4 | Lossless JSON Import / Export roundtrip | `TC-IO-01` $\to$ `04`, `TC-E2E-08` | Unit / E2E | `jsonIO.test.ts`, `import-export.spec.ts` |
| **URD-FR-12** | URD §3.3 / SRS-FR-01 | Mobile Touch gestures & Bottom Nav | `TC-COMP-MOB-01`, `TC-E2E-09` | Component / E2E | `MobileNav.test.ts`, `mobile-touch.spec.ts` |
| **SRS-FR-02** | SRS §3.1 | Input focus guards (`!isInputActive()`) | `TC-KB-12` | Unit | `keyboard.test.ts` |
| **SRS-FR-04** | SRS §3.2 | Zero-jitter permanent `border-l-2` in TaskTable | `TC-COMP-TABLE-01` | Component | `TaskTable.test.ts` |
| **SRS-FR-06** | SRS §3.2 | Inset ring selection in Kanban | `TC-COMP-KANBAN-01` | Component | `KanbanBoard.test.ts` |
| **SRS-FR-10** | SRS §3.4 | Cascading 3-Tier AI Architecture (Cloud $\to$ Ollama $\to$ Fallback) | `TC-SRV-AI-CASCADE-01` $\to$ `04` | Service Unit | `test_ai_cascade.py`, `test_ai_schemas.py` |
| **SRS-FR-AI-DEC**| SRS §3.4 / README §3.1 | Deterministic Goal Decomposer | `TC-DECOMP-01` $\to$ `04`, `TC-API-AI-04` | Unit / API | `aiDecomposer.test.ts`, `test_ai_api.py` |
| **SRS-FR-I18N** | SRS §3.1 | Locale Translation Integrity | `TC-I18N-01` | Unit | `i18nStore.test.ts` |
| **SRS-FR-PROJ** | SRS §2.1 | Projects & Member Management RBAC | `TC-API-PROJ-01` $\to$ `03`, `TC-COMP-MODAL-MEMBERS` | API / Comp | `test_projects_api.py`, `Modals.test.ts` |
| **SRS-FR-SPRINT**| SRS §2.1 | Sprints & Sprint Stats | `TC-API-SPRINT-01` $\to$ `03` | API | `test_sprints_api.py` |
| **SRS-FR-COMMS** | SRS §2.1 | Task Comments Endpoint | `TC-API-TASK-05` | API | `test_tasks_api.py` |
| **SRS-NFR-01** | SRS §4 / Core Rule 5 | Performance budget: Mutation $< 16\text{ms}$, Action $< 50\text{ms}$ ($\ge 50$ samples) | `TC-PERF-01`, `TC-PERF-02`, `TC-PERF-03` | Non-Functional (perf) | `performance.spec.ts` |
| **SRS-NFR-01b**| README §1 / Badge | Idle JS Heap Memory $< 15\text{MB}$ ($\ge 50$ samples) | `TC-PERF-04` | Non-Functional (perf) | `performance.spec.ts` |
| **SRS-NFR-04** | SRS §4 | Security: JWT Bearer, Current User, Project BOLA isolation, Sanitization | `TC-API-AUTH-01` $\to$ `05`, `TC-SEC-01` $\to$ `03` | Security / API | `test_auth_api.py`, `test_rbac_security.py`, `test_sanitization.py` |

---

## 6. CHI TIẾT TEST CASES THEO TỪNG FILE & PHÂN HỆ

### 6.1. Unit Tests (Frontend)

- **`tests/unit/dagSorter.test.ts`:**
  - `TC-DAG-01`: Empty task array returns empty result and empty critical path.
  - `TC-DAG-02`: Single task node handled properly without crash.
  - `TC-DAG-03`: Linear dependency chain ($A \to B \to C$) correctly topologically ordered.
  - `TC-DAG-04`: Diamond dependency graph ($A \to B, C \to D$) with deterministic resolution.
  - `TC-DAG-05`: Disconnected components properly ordered by priority weight and due date.
  - `TC-DAG-06`: Self-loop ($A \to A$) and mutual cycle ($A \to B \to A$) do not cause infinite recursion.
  - `TC-DAG-07`: Critical path calculation: test theo trọng số spec chuẩn ($S=1, M=2, L=3, XL=5$) vs logic code hiện tại (`{XL:8, L:5, M:3, S:1} * priorityWeight`). Đánh dấu `xfail` cho test spec chuẩn và ghi vào `BUG_REPORT.md` (Spec conflict).
  - `TC-DAG-08`: Sanity algorithmic complexity test: Đồ thị $\ge 1000$ nodes chạy dưới ngưỡng an toàn $1.0\text{s}$ (đo latency chính xác chuyển sang `performance.spec.ts`).

- **`tests/unit/taskStore.test.ts`:**
  - `TC-STORE-01`: 4-step status cycle completes full rotation (`TODO` $\to$ `IN_PROGRESS` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`).
  - `TC-STORE-02`: CRUD operations (Create with compact ID, Read, Update, Delete with dependency cleanup).
  - `TC-STORE-03`: Priority mutation (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and comparator sorting.
  - `TC-STORE-04`: IndexedDB hydration on initialization and persistence on mutation.
  - `TC-STORE-05`: Optimistic updates và cơ chế rollback khi API fail (đánh dấu `xfail` do code hiện bắt `.catch(() => {})` mà chưa revert; ghi vào `BUG_REPORT.md` loại Code bug).
  - `TC-STORE-06`: Toggle view mode state (`TABLE` $\leftrightarrow$ `KANBAN`).
  - `TC-STORE-07`: Table navigation: `selectTask`, `selectNext`, `selectPrev` với clamping $[0, N-1]$.
  - `TC-STORE-08`: Kanban cursor navigation: `moveKanbanCursor` 2D (trái, phải, lên, xuống, column clamp).
  - `TC-STORE-09`: Lateral column shift: `shiftActiveKanbanTask` trái/phải với circular wrap-around và focus retention.
  - `TC-STORE-10`: Sync conflict resolution: kiểm tra quy tắc "newer `updatedAt` wins" khi gộp dữ liệu server và local.
  - `TC-STORE-11`: Multi-dimensional filtering (search query, status enum, priority enum, sprint backlog, critical path only).

- **`tests/unit/keyboard.test.ts`:**
  - `TC-KB-01`: `b` triggers view mode toggle between `TABLE` and `KANBAN`.
  - `TC-KB-02`: `j`/`k` / Down/Up traverses rows clamped to $[0, N-1]$ in Table mode.
  - `TC-KB-03`: `h`/`l` executes in Kanban view; ignored in Table view.
  - `TC-KB-04`: `Space` cycles status of selected active task.
  - `TC-KB-05`: `Shift+H` / `Shift+L` shifts column with wrap-around and focus retention.
  - `TC-KB-06`: `1-4` assigns priority to active task.
  - `TC-KB-07a`: `Enter` mở TaskDetailModal theo US-03 và code thực tế (PASS).
  - `TC-KB-07b`: `Enter` kích hoạt inline title edit theo README/URD-FR-02 (đánh dấu `xfail` do code map `Enter` mở modal và dùng `i` cho inline edit; ghi `BUG_REPORT.md` loại Spec conflict).
  - `TC-KB-08`: `d`/`Backspace` deletes task, blocked when `Ctrl` or `Meta` is pressed.
  - `TC-KB-09`: `c` opens quick task creation modal (đánh dấu `xfail` do code map `n`; ghi `BUG_REPORT.md` loại Spec conflict). Đồng thời test phím `n` mở modal.
  - `TC-KB-10`: `/` focuses search bar.
  - `TC-KB-11`: `Escape` closes modals, cancels edit, blurs inputs.
  - `TC-KB-12`: All single-character hotkeys ignored when typing in `input`, `textarea`, `select`, or `contenteditable`.

- **`tests/unit/aiDecomposer.test.ts`:**
  - `TC-DECOMP-01`: Decompose auth/login goals returns structured subtasks with dependencies and acceptance criteria.
  - `TC-DECOMP-02`: Decompose api/backend/db goals returns valid schema and correct DAG relations.
  - `TC-DECOMP-03`: Decompose ui/frontend goals returns valid schema.
  - `TC-DECOMP-04`: Arbitrary text goals decomposed sequentially without schema violations.

- **`tests/unit/themeStore.test.ts` & `tests/unit/i18nStore.test.ts`:**
  - `TC-THEME-01`: Toggle theme updates dark class and injects 0ms transition freeze style.
  - `TC-I18N-01`: Translation dictionary completeness (VI/EN) and reactive locale switching.

- **`tests/unit/gitParser.test.ts` & `tests/unit/jsonIO.test.ts`:**
  - `TC-DIFF-01`: Valid diff with `closes #TSK-101` marks task resolved.
  - `TC-DIFF-02`: Empty diff or invalid format handles gracefully without throwing.
  - `TC-DIFF-03`: Large diff ($> 10,000$ lines) parsed under sanity threshold $1.0\text{s}$.
  - `TC-DIFF-04`: Sensitive data scan flags hardcoded secrets, empty catch blocks, unsafe `any`.
  - `TC-DIFF-05`: Cross-reference BLOCKED tasks with keywords in commit diff.
  - `TC-IO-01`: Lossless JSON roundtrip (`tasks` $\to$ export $\to$ import $\to$ deep equal).
  - `TC-IO-02`: Rejection of corrupted JSON or non-array payloads.
  - `TC-IO-03`: Preservation of Vietnamese Unicode characters (`Tiếng Việt có dấu, ký tự đặc biệt`).
  - `TC-IO-04`: Retain task schema invariants upon import.

---

### 6.2. Component Tests (`source_code/frontend/tests/component/`)

- **`TaskTable.test.ts`:**
  - `TC-COMP-TABLE-01`: Renders active row with permanent `border-l-2` without horizontal layout displacement.
  - `TC-COMP-FLAME-01`: Tasks on critical path render visual `Flame` icon badge.
  - `TC-COMP-DONE-01`: Tasks in DONE status render with line-through and standard contrast (no opacity-50).

- **`KanbanBoard.test.ts`:**
  - `TC-COMP-KANBAN-01`: Renders 4 columns with inset rings (`ring-2 ring-inset`) on selected cards.
  - `TC-COMP-KANBAN-02`: Empty column state rendering.

- **`Modals.test.ts` (Bao phủ đầy đủ tất cả modal):**
  - `TC-COMP-MODAL-CREATE`: `CreateTaskModal.vue` validation, submit, close.
  - `TC-COMP-MODAL-DETAIL`: `TaskDetailModal.vue` view/edit fields, status update, priority proposal.
  - `TC-COMP-MODAL-DAG`: `DAGVisualizerModal.vue` renders critical path nodes and edges.
  - `TC-COMP-MODAL-SUMMARY`: `WeeklySummaryModal.vue` renders summary sections, copy button.
  - `TC-COMP-MODAL-MINUTES`: `MeetingMinutesModal.vue` renders topics, action items, decisions.
  - `TC-COMP-MODAL-WORKLOAD`: `WorkloadAssignModal.vue` renders recommendation and workload points.
  - `TC-COMP-MODAL-DIFF`: `GitDiffModal.vue` renders resolved tickets and architectural concerns.
  - `TC-COMP-MODAL-HELP`: `ShortcutsHelpModal.vue` renders keyboard reference table.
  - `TC-COMP-MODAL-MEMBERS`: `ProjectMembersModal.vue` lists members and permits role manipulation.
  - `TC-COMP-MODAL-AUTH`: `AuthModal.vue` handles email/password and Google OAuth tabs.
  - `TC-COMP-MODAL-A11Y`: Modal dialogs enforce role="dialog", aria-modal="true", and focus trap.

- **`App.test.ts`:**
  - `TC-COMP-APP-ESC`: Root capture-phase `Escape` dismisses open modals and blurs search.

- **`MobileNav.test.ts`:**
  - `TC-COMP-MOB-01`: `MobileBottomNav.vue` renders navigation icons and triggers view toggle.

---

### 6.3. Backend & API Tests (`source_code/backend/tests/`)

- **Authentication (`tests/api/test_auth_api.py`):**
  - `TC-API-AUTH-01`: Register new user with hashed password (bcrypt).
  - `TC-API-AUTH-02`: Login returns valid JWT Bearer token.
  - `TC-API-AUTH-03`: Google OAuth login with mock/verified tokens.
  - `TC-API-AUTH-04`: Cross-project isolation: non-member access returns `403 Forbidden` (BOLA/IDOR).
  - `TC-API-AUTH-05`: `GET /api/auth/me` returns current user profile, role, and skills.

- **Tasks (`tests/api/test_tasks_api.py`):**
  - `TC-API-TASK-01`: Full CRUD on `/api/tasks`.
  - `TC-API-TASK-02`: Priority governance (Member requests $\to$ PM approves/rejects; Member direct edit rejected with 403).
  - `TC-API-TASK-03`: Cycle status endpoint advances `TODO` $\to$ `IN_PROGRESS` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`.
  - `TC-API-TASK-04`: Dependency cascading deletion when task is removed.
  - `TC-API-TASK-05`: `POST /api/tasks/{id}/comments` adds task comment and retrieves list.

- **Projects & Members (`tests/api/test_projects_api.py`):**
  - `TC-API-PROJ-01`: Create & list projects (scoped to owner/members).
  - `TC-API-PROJ-02`: Project member addition, removal, and role updates (OWNER, PM, MEMBER, VIEWER).
  - `TC-API-PROJ-03`: RBAC enforcement: VIEWER cannot mutate project/tasks.

- **Sprints & Stats (`tests/api/test_sprints_api.py`):**
  - `TC-API-SPRINT-01`: Create sprint with start/end date and goal.
  - `TC-API-SPRINT-02`: List sprints belonging to project.
  - `TC-API-SPRINT-03`: `GET /api/sprints/{id}/stats` computes total tasks, completed points, velocity, blockers.

- **AI Services (`tests/api/test_ai_api.py` & `tests/services/`):**
  - `TC-API-AI-01`: `POST /api/v1/ai/weekly-summary` produces structured markdown summary.
  - `TC-API-AI-02`: `POST /api/v1/ai/meeting-minutes` produces JSON (`main_topics`, `action_items`, `key_decisions`).
  - `TC-API-AI-03`: `POST /api/v1/ai/recommend-assignment` returns optimal assignee based on workload.
  - `TC-API-AI-04`: `POST /api/v1/ai/decompose` breaks goal down into sequential DAG subtasks.
  - `TC-SRV-AI-01`: `AIService.generate_weekly_summary` service logic.
  - `TC-SRV-AI-02`: `AIService.extract_meeting_minutes` service logic.
  - `TC-SRV-AI-03`: `AIService.recommend_task_assignment` cost function evaluation.
  - `TC-SRV-AI-CASCADE-01`: Tier 1 Cloud LLM execution (mock 200 response).
  - `TC-SRV-AI-CASCADE-02`: Fallback from Tier 1 failure to Tier 2 Ollama.
  - `TC-SRV-AI-CASCADE-03`: Fallback from Tier 2 failure to Tier 3 Deterministic engine.
  - `TC-SRV-AI-CASCADE-04`: Unparseable LLM output caught and returns deterministic fallback JSON.

- **DAG Engine Backend (`tests/services/test_dag_cpm.py`):**
  - `TC-SRV-DAG-01`: Backend task dependency graph cycle detection and critical path derivation.

- **Security & Sanitization (`tests/security/test_rbac_security.py`, `tests/security/test_sanitization.py`):**
  - `TC-SEC-01`: SQL Injection payloads in title/description safely parameterized.
  - `TC-SEC-02`: XSS payloads in task title escaped in response.
  - `TC-SEC-03`: Secrets not leaked in exception responses or logs.

---

### 6.4. E2E Tests (`source_code/frontend/e2e/specs/`)

- `TC-E2E-01`: Create task with `c`/`n`, edit title with `Enter`/`i`, cycle status with `Space`, delete with `d`.
- `TC-E2E-02`: 2D navigation `h`/`j`/`k`/`l`, lateral shift `Shift+H`/`L`, view toggle `b`.
- `TC-E2E-03`: Complete 4-step status cyclic progression via UI.
- `TC-E2E-04`: Search `/`, trigger AI modals (`a`), Git Diff (`g`), DAG (`v`), Help (`?`), dismiss with `Escape`.
- `TC-E2E-05`: Theme switch `t`, verify 0ms transition freeze and persistence after reload.
- `TC-E2E-06`: Offline-first:
  - Khởi chạy backend uvicorn test trên port chuyên dụng (`8001`), SQLite test DB tạm.
  - Vite frontend cấu hình `VITE_API_URL` trỏ tới port `8001`.
  - Ngắt mạng qua `page.context().setOffline(true)`.
  - Thực hiện tạo task và sửa status trên UI.
  - Reload trang $\to$ verify dữ liệu vẫn tồn tại từ IndexedDB.
  - Phục hồi mạng qua `page.context().setOffline(false)`.
  - Kích hoạt sync (qua sự kiện `online` / `taskStore.syncWithBackend()`).
  - Xác minh dữ liệu: Truy vấn trực tiếp API backend `GET /api/tasks` để chứng minh task đã được đồng bộ lên SQLite server.
- `TC-E2E-07`: DAG Visualizer: Verify critical path rendering and cycle prevention alerts.
- `TC-E2E-08`: Lossless JSON import and export via UI (`import-export.spec.ts`).
- `TC-E2E-09`: Responsive layout and touch gestures on mobile viewport (375x667).

---

### 6.5. Non-Functional Tests (Project `perf` & A11y)

- **`performance.spec.ts` (Nằm trong project riêng `perf`):**
  - `TC-PERF-01`: Action latency measurement: Đo thời gian từ keydown đến DOM update, lấy giá trị $p95$ qua $\ge 50$ mẫu. Ngân sách: $< 50\text{ms}$ (CI cho phép hệ số nới $1.5\times < 75\text{ms}$).
  - `TC-PERF-02`: Optimistic mutation latency: Đo thời gian commit state Pinia/DOM, lấy $p95$ qua $\ge 50$ mẫu. Ngân sách: $< 16\text{ms}$ (CI cho phép hệ số nới $1.5\times < 24\text{ms}$).
  - `TC-PERF-03`: DOM scale test với 500, 2000, 5000 tasks không gây rò rỉ bộ nhớ hoặc đơ UI.
  - `TC-PERF-04`: Đo Idle JS Heap Memory qua Chrome DevTools Protocol (`Performance.getMetrics` $\to$ `JSHeapUsedSize`). Đo baseline trước (lấy trung bình $\ge 50$ mẫu sau khi GC idle). Ngân sách: $< 15\text{MB}$ JS Heap (CI nới $1.5\times < 22.5\text{MB}$). Nếu baseline hiện tại vượt quá 15MB, ghi nhận vào `BUG_REPORT.md` loại Code bug/Performance.
- **`a11y.spec.ts`:**
  - `TC-A11Y-01`: Quét baseline axe-core ban đầu trên Table, Kanban, Modals. Ghi nhận vi phạm hiện có vào `BUG_REPORT.md`. Assert không phát sinh thêm violation mới so với baseline.
- **Visual Regression:**
  - `TC-VISUAL-01`: Snapshot testing cho Light/Dark mode trên Chromium trong môi trường container Linux/Docker cố định.
- **Stability Gate:**
  - `TC-STABILITY-01`: Chạy 3 lần liên tiếp functional test suite (loại trừ project `perf`) đạt kết quả pass nhất quán 100%.

---

## 7. TIÊU CHÍ PASS / FAIL (PASS / FAIL CRITERIA)

### 7.1. Tiêu chí PASS (Acceptance Criteria)
1. **100% Deterministic:** Không có test nào phụ thuộc vào sleep cứng hoặc thứ tự chạy ngẫu nhiên.
2. **Zero Unhandled Flakiness:** Bộ test suite chức năng chạy 3 lần liên tiếp đạt kết quả nhất quán 100%.
3. **No Product Code Mutation:** Không can thiệp sửa mã nguồn sản phẩm chỉ để test pass. Mọi bug phát hiện phải đánh dấu `test.fail` hoặc `pytest.mark.xfail` và lập tài liệu trong `BUG_REPORT.md`.
4. **Mock Isolation:** 100% network calls tới external LLMs và Google OAuth được mock hoàn toàn trong test runs.
5. **Traceability:** Mỗi test case đều có tag ánh xạ `@US-XX` hoặc `@REQ-XX`.
6. **A11y Baseline Gate:** Không phát sinh violation mới vượt qua baseline đã ghi nhận.
7. **Offline-First Synchronized:** Dữ liệu tạo offline được verify xuất hiện đúng trong cơ sở dữ liệu server sau khi bật lại kết nối.

### 7.2. Tiêu chí FAIL
- Bất kỳ assertion chức năng nào bị vỡ mà không phải do bug đã biết được ghi nhận trong `BUG_REPORT.md`.
- Bất kỳ rò rỉ dữ liệu hoặc deadlock SQLite trong quá trình chạy song song.
- Test timing/memory trong project `perf` vượt ngưỡng đã nhân hệ số nới trên CI.

---

## 8. TIÊU CHÍ COVERAGE (COVERAGE CRITERIA)

| Phân hệ / File kiểm thử | Tiêu chí Line Coverage | Tiêu chí Branch Coverage |
| :--- | :---: | :---: |
| `dagSorter.ts` | $\ge 90\%$ | $\ge 85\%$ |
| `taskStore.ts` | $\ge 85\%$ | $\ge 80\%$ |
| `keyboard.ts` | $\ge 90\%$ | $\ge 85\%$ |
| `gitParser.ts` | $\ge 85\%$ | $\ge 80\%$ |
| `aiDecomposer.ts` | $\ge 85\%$ | $\ge 80\%$ |
| Backend Core (`tasks.py`, `auth.py`, `ai_service.py`) | $\ge 80\%$ | $\ge 75\%$ |
| Toàn bộ Backend Routers & Services | $\ge 80\%$ | $\ge 70\%$ |

---

## 9. CẤU TRÚC THƯ MỤC KIỂM THỬ MỤC TIÊU

```
source_code/
├── frontend/
│   ├── tests/
│   │   ├── setup.ts
│   │   ├── unit/
│   │   │   ├── dagSorter.test.ts
│   │   │   ├── taskStore.test.ts
│   │   │   ├── keyboard.test.ts
│   │   │   ├── gitParser.test.ts
│   │   │   ├── aiDecomposer.test.ts
│   │   │   ├── themeStore.test.ts
│   │   │   ├── i18nStore.test.ts
│   │   │   └── jsonIO.test.ts
│   │   └── component/
│   │       ├── App.test.ts
│   │       ├── TaskTable.test.ts
│   │       ├── KanbanBoard.test.ts
│   │       ├── Modals.test.ts
│   │       └── MobileNav.test.ts
│   └── e2e/
│       ├── fixtures/
│       │   └── test-fixtures.ts
│       ├── pages/
│       │   ├── BasePage.ts
│       │   ├── TablePage.ts
│       │   ├── KanbanPage.ts
│       │   └── ModalPage.ts
│       └── specs/
│           ├── navigation.spec.ts
│           ├── task-lifecycle.spec.ts
│           ├── offline-first.spec.ts
│           ├── dag-visualizer.spec.ts
│           ├── search-modal.spec.ts
│           ├── theme-toggle.spec.ts
│           ├── import-export.spec.ts
│           ├── mobile-touch.spec.ts
│           ├── a11y.spec.ts
│           └── performance.spec.ts
├── backend/
│   └── tests/
│       ├── conftest.py
│       ├── api/
│       │   ├── test_auth_api.py
│       │   ├── test_tasks_api.py
│       │   ├── test_projects_api.py
│       │   ├── test_sprints_api.py
│       │   └── test_ai_api.py
│       ├── services/
│       │   ├── test_ai_cascade.py
│       │   ├── test_ai_schemas.py
│       │   └── test_dag_cpm.py
│       └── security/
│           ├── test_rbac_security.py
│           └── test_sanitization.py
docs/
└── testing/
    ├── TEST_PLAN.md
    ├── TEST_CASES.md
    ├── BUG_REPORT.md
    └── README.md
.github/
└── workflows/
    └── test.yml
```

---

## 10. KẾ HOẠCH TRIỂN KHAI THEO CÁC PHASE

- **Phase 0:** Khảo sát, hoàn thiện `TEST_PLAN.md` (V1.2), lập bảng `BUG_REPORT.md`.
- **Phase 1:** Thiết lập hạ tầng test: Vitest + jsdom + fake-indexeddb, Playwright (tách project `perf`), pytest + httpx, scripts `package.json`, GitHub Actions workflow `test.yml`.
- **Phase 2:** Triển khai toàn bộ Unit tests độc lập (frontend & logic).
- **Phase 3:** Triển khai Component tests với `@vue/test-utils` (bao gồm tất cả modals và App).
- **Phase 4:** Triển khai Backend API & Security tests (100% mock AI/OAuth, CRUD projects, sprints, comments, /me).
- **Phase 5:** Triển khai Playwright E2E tests (Page Object Model, uvicorn test backend cô lập cho offline sync).
- **Phase 6:** Triển khai Non-Functional tests (Project `perf`, JS Heap Memory $<15\text{MB}$, Axe baseline scan, Visual snapshots Chromium Docker, 3x Stability).

---

## 11. GIẢ ĐỊNH & CÂU HỎI MỞ (ASSUMPTIONS & OPEN QUESTIONS)

### 11.1. Các giả định kỹ thuật (Technical Assumptions)
1. **[ASSUMPTION-01] Vòng lặp Shift+H/L (Circular Wrap-Around):**  
   - *Nguồn gốc:* Dựa trên code thực tế tại `taskStore.ts` dòng 491-493 (`(currIdx + 1) % 4` và `(currIdx - 1 + 4) % 4`) và `user_story.md` US-02 ("wraps to TODO (Column 0)").  
   - *Tình trạng đặc tả:* URD-FR-02 chỉ ghi "lateral column shifting with synchronous focus retention".  
   - *Quyết định:* QA xác định đây là ASSUMPTION suy ra từ code kết hợp US-02.

2. **[ASSUMPTION-02] Chiến lược giải quyết xung đột đồng bộ (Conflict Resolution):**  
   - *Nguồn gốc:* Dựa trên code thực tế tại `taskStore.ts` dòng 387 (`if (local && local.updatedAt > sTask.updatedAt) merged.push(local)`).  
   - *Tình trạng đặc tả:* URD.md và SRS.md không mô tả thuật toán giải quyết xung đột.  
   - *Quyết định:* QA xác lập ASSUMPTION là "Timestamp-based Last-Write-Wins (newer updatedAt wins)" suy ra trực tiếp từ mã nguồn `taskStore.ts`.

3. **[ASSUMPTION-03] Xung đột hành vi phím `Enter`:**  
   - *Nguồn gốc:* `README.md` và `URD.md` ghi `Enter` = "Inline title edit mode / rename". Nhưng `user_story.md` US-03 ghi: `Enter` = "open Task Detail Inspector modal", và `keyboard.ts` dòng 128 gọi `taskStore.openDetail()` (mở modal), còn inline edit được map cho phím `i` (dòng 135).  
   - *Quyết định:* Test `Enter mở modal` (theo US-03 và code) sẽ PASS. Test `Enter sửa inline` (theo README/URD) sẽ đánh dấu `xfail` và ghi nhận vào `BUG_REPORT.md` loại "Spec conflict".

4. **[ASSUMPTION-04] Cơ chế kích hoạt Sync và Cấu hình Playwright WebServer cho E2E:**  
   - *Cơ chế kích hoạt Sync:* Frontend `taskStore.syncWithBackend()` được kích hoạt tự động qua sự kiện `window.addEventListener('online')` hoặc khi chuyển sang `BOARD` view, cũng như manual trigger khi hoàn tất chuỗi thao tác offline.  
   - *Cấu hình WebServer:* Playwright cấu hình khởi chạy backend uvicorn trên port `8001` với DB SQLite test cô lập (`test_e2e.db`), và Vite dev server với `VITE_API_URL=http://localhost:8001` trỏ thẳng tới backend test.

5. **[ASSUMPTION-05] Ngưỡng hiệu năng trong CI/CD & Đo JS Heap:**  
   - *Quyết định:* Đo JS Heap Memory qua CDP (`Performance.getMetrics` $\to$ `JSHeapUsedSize`) với $\ge 50$ mẫu sau khi GC idle. Áp dụng hệ số nới $1.5\times$ cho runner CI ($75\text{ms}$, $24\text{ms}$, $22.5\text{MB}$) và tách hoàn toàn khỏi suite chức năng thông thường.
