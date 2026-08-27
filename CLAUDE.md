# CLAUDE.md - Koshi Project Management Engine

## Overview & Authorship
- **Project**: Koshi (輿) Project Management Engine
- **Lead Architect & Developer**: Phạm Minh Tú (Felix Anderson / `felixsu`)
- **Fullstack Contributor & Testing**: Phạm Văn Huynh
- **Frontend Contributor & Documentation**: Đàm Đức Đôn
- **Live Production URL**: `https://koshi.felixsu.qzz.io`

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

## Common Development Commands

### Frontend (`/`)
- **Install Dependencies**: `pnpm install`
- **Development Server**: `pnpm run dev`
- **Production Build Check**: `pnpm run build` (runs `vue-tsc -b && vite build`)

### Backend (`/backend`)
- **Initialize Database**: `python init_db.py`
- **Run Backend Server**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Run Unit/Integration Tests**: `pytest`

### Production Deployment
```bash
# Push directly to umi remote container
tar --exclude='.git' --exclude='node_modules' --exclude='dist' -czf - -C /home/felixsu/.gemini/antigravity-ide/scratch/koshi . | ssh umi "tar -xzf - -C /home/felixsu/docker/koshi" && ssh umi "cd /home/felixsu/docker/koshi && docker compose build && docker compose up -d"
```
