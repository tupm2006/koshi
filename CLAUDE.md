# CLAUDE.md - Koshi Project Management Engine

## Overview & Authorship
- **Project**: Koshi (輿) Project Management Engine
- **Team**: Nhóm 04 (ICTU)
- **Lead Architect & Developer**: Phạm Minh Tú
- **Fullstack Contributor & Testing**: Phạm Văn Huynh
- **Frontend Contributor & Documentation**: Đàm Đức Đôn
- **Live Production URL**: `https://koshi.tupm.qzz.io`

---

## Architectural Rules & Non-Negotiables
1. **0ms Latency UI Standard**:
   - Zero animations (`transition-duration: 0s !important`, `animation-duration: 0s !important`).
   - Solid contrast with WCAG AA standard against pure slate backgrounds.
   - All state mutations render instantaneously without frame interpolation.
2. **Deterministic State Invariants**:
   - Cyclic status progression: `TODO` $\to$ `IN_PROGRESS` $\to$ `DONE` $\to$ `BLOCKED` $\to$ `TODO`.
   - Circular Kanban navigation: `(col ± 1 + 4) % 4` on boundary traversal.
   - DAG Critical Path Analysis: Kahn's topological sort for cycle detection and CPM critical path derivation.
3. **Local-First & Multi-Tier AI Cascade**:
   - Tier 1: Client heuristic / regex rules (< 5ms).
   - Tier 2: FastAPI Backend rule-based assignment (< 50ms).
   - Tier 3: Gemini 1.5 Flash structured output LLM (< 1500ms).

---

## Directory Organization
- **Root**: Specifications (`URD.md`, `SRS.md`, `user_story.md`, `nhom4.docx`, `README.md`, `CLAUDE.md`, `docker-compose.yml`).
- **`source_code/frontend/`**: Vue 3.5 SPA, Tailwind CSS v4, Pinia, TypeScript.
- **`source_code/backend/`**: FastAPI REST API, SQLAlchemy 2.0, SQLite, AI cascade services.
- **`source_code/scripts/`**: Report generator (`generate_docx.py`) and packaging script (`package_submission.sh`).
- **`docs/`**: ISO-29148 requirements specifications and architecture design.

---

## Common Development Commands

### Frontend (`source_code/frontend`)
- **Install Dependencies**: `cd source_code/frontend && npm install`
- **Development Server**: `npm run dev`
- **Production Build Check**: `npm run build` (runs `vue-tsc -b && vite build`)

### Backend (`source_code/backend`)
- **Initialize Database**: `python3 source_code/backend/init_db.py`
- **Run Backend Server**: `cd source_code/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Run Unit/Integration Tests**: `pytest source_code/backend/tests`

### Package & Submission
- **Generate Docx**: `python3 source_code/scripts/generate_docx.py`
- **Package Archive**: `bash source_code/scripts/package_submission.sh`
