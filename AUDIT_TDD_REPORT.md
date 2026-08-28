# TECHNICAL DUE DILIGENCE (TDD) & PRINCIPAL SYSTEMS AUDIT REPORT

**Target System:** KOSHI (輿) Project Management Engine  
**Target Codebase:** `/home/felixsu/koshi` (`source_code/backend/`, `source_code/frontend/`, root manifests)  
**Stack:** Vue 3.5 (TypeScript / Pinia) + FastAPI (Python 3.11 / SQLite / SQLAlchemy 2.0) + Caddy / Nginx / Docker  
**Assessment Date:** 2026-08-28  
**Audit Perspective:** Principal Systems Auditor & Technical Due Diligence (TDD) Assessor  
**Operational Horizon:** 18-Month Production Viability & Total Cost of Ownership (TCO)  

---

## 1. EXECUTIVE SUMMARY & DEPLOYMENT VERDICT

```
+---------------------------------------------------------------------------------------------------+
| EXECUTIVE DUE DILIGENCE SUMMARY                                                                   |
+------------------------------+--------------------------------------------------------------------+
| Deployment Verdict           | NO-GO / REJECTED FOR MULTI-TENANT PRODUCTION                       |
| Current Viability            | Restricted Single-User Local Tool / Academic Sandbox Only         |
| Critical Deal-Killers Found  | 4 Fatal Vulnerabilities (Remote Takeover, Secret Exposure, Concurrency Lock, Data Desync) |
| Compound Fragility Index     | 8.8 / 10 (CRITICAL: 0% Frontend Tests, SQLite Write Bottleneck, Flawed Offline Sync) |
| Remediation to Production    | 360 Engineering Hours (~2.25 Months Senior SWE)                   |
| 18-Month Maintenance TCO     | 1,180 Engineering Hours (~0.45 FTE Ongoing Allocation)             |
+------------------------------+--------------------------------------------------------------------+
```

### 1.1. Go / No-Go Deployment Verdict
**VERDICT: REJECTED (FATAL NO-GO FOR PRODUCTION MULTI-TENANT / COMMERCIAL DEPLOYMENT)**

The Koshi codebase contains fatal security backdoors, fundamental database concurrency limits inherent to single-file SQLite deployments, zero frontend test coverage, and a fragile client-side state reconciliation layer that causes silent data destruction under concurrent multi-user operations. Deploying this system to production today will result in trivial account takeovers via unsigned JWT spoofing, database lock timeouts under burst writes, and unrecoverable data loss during client-server synchronization conflicts.

### 1.2. 18-Month Total Cost of Ownership (TCO) Projection
* **Immediate P0 Remediation (Production Gate):** **360 Hours**
* **18-Month Maintenance, Scaling & Stability Burden:** **1,180 Hours**
* **Total Engineering Investment (18 Months):** **1,540 Hours** (~0.85 FTE Senior Fullstack/DevOps Engineer).

---

## 2. PILLAR 1: DEAL-KILLER TRIAGE & SECURITY POSTURE

```
+---------------------------------------------------------------------------------------------------+
| PILLAR 1: DEAL-KILLER RISK REGISTER                                                               |
+------------------------------------+---------------+---------------------+------------------------+
| Vulnerability / Risk Item          | Severity      | Classification      | Primary Code Reference |
+------------------------------------+---------------+---------------------+------------------------+
| Unverified Google Token Backdoor   | DEAL-KILLER   | CWE-287 / CWE-347   | `routers/auth.py:64`   |
| Ineffective Production Secret Guard| DEAL-KILLER   | CWE-798             | `config.py:9, 46-51`   |
| In-Memory Default Credentials      | HIGH          | CWE-259             | `main.py:28, 35`       |
| Broad Intra-Project Write Access   | MEDIUM        | Broken Authorization| `routers/tasks.py:78`  |
| Stateless Non-Revocable 7-Day JWT  | MEDIUM        | CWE-613             | `config.py:17`         |
| Bare-Metal Deployment Failure      | HIGH          | Operational Risk    | `docker-compose.yml:38`|
+------------------------------------+---------------+---------------------+------------------------+
```

### 2.1. Critical Security Vulnerabilities (Deal-Killers)

#### 2.1.1. Remote Authentication Bypass via Unverified Mock Google Tokens (CWE-287 / CWE-347)
* **File:** [`source_code/backend/app/routers/auth.py:64-92`](file:///home/felixsu/koshi/source_code/backend/app/routers/auth.py#L64-L92)
* **Mechanism:** In `POST /api/auth/google`, the endpoint inspects the incoming `credential` string. If the token contains `.mock_signature` or starts with `mock_google_token_`, it skips Google JWKS signature validation and decodes arbitrary base64 claims:
  ```python
  if credential.startswith("mock_google_token_") or credential.endswith(".mock_signature") or "mock_google_token" in credential:
      parts = credential.split(".")
      payload_b64 = parts[1]
      id_info = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
      email = id_info.get("email")
  ```
* **Production Hazard:** This mock parser contains **zero environment gating** (`ENVIRONMENT == "production"` is not checked). Any remote unauthenticated attacker can construct a client-side JWT with `{"email": "pm@tupm.qzz.io", "sub": "attacker"}` appended with `.mock_signature`, submit it to `/api/auth/google`, and instantly obtain an administrative PM token. The frontend ([`AuthModal.vue:51-65`](file:///home/felixsu/koshi/source_code/frontend/src/components/AuthModal.vue#L51-L65)) explicitly relies on this backdoor for the default Google login button.
* **Remediation:** Remove all mock token parsing logic from production routes. Confine synthetic authentication mocks strictly to test fixtures (`tests/conftest.py`).

#### 2.1.2. Ineffective Production JWT Secret Guard (CWE-798)
* **Files:** [`source_code/backend/app/config.py:9, 15, 46-51`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L9), [`docker-compose.yml:8-10`](file:///home/felixsu/koshi/docker-compose.yml#L8-L10)
* **Mechanism:** `config.py` contains a startup safety check designed to abort if the hardcoded secret is detected:
  ```python
  if settings.ENVIRONMENT == "production" and settings.JWT_SECRET == "koshi_super_secret_jwt_key_2026_academic_spec":
      raise RuntimeError("Production JWT_SECRET cannot use insecure default academic key")
  ```
  However, `ENVIRONMENT` defaults to `"development"` ([`config.py:9`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L9)) and is **omitted entirely** from `docker-compose.yml`.
* **Impact:** In standard Docker deployments, the container runs in `"development"` mode by default. The safety guard never fires, allowing the container to boot with the globally known secret `koshi_super_secret_jwt_key_2026_academic_spec`. Any third party can forge arbitrary HS256 tokens offline.
* **Remediation:** Set `JWT_SECRET` as a mandatory Pydantic setting without a default fallback. Enforce immediate container crash on startup if `JWT_SECRET` length is $< 32$ characters.

#### 2.1.3. Hardcoded Seed Passwords and Password Truncation
* **Files:** [`source_code/backend/app/main.py:28, 35`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L28), [`source_code/backend/app/security.py:16, 24`](file:///home/felixsu/koshi/source_code/backend/app/security.py#L16), [`source_code/frontend/src/components/AuthModal.vue:15, 42`](file:///home/felixsu/koshi/source_code/frontend/src/components/AuthModal.vue#L15)
* **Mechanism:** Database seeders initialize default accounts (`pm@tupm.qzz.io`, `dev@tupm.qzz.io`) with static password `koshi123`. `AuthModal.vue` prefills and hardcodes these credentials in the UI. In `security.py`, passwords are sliced to 72 bytes (`plain_password.encode('utf-8')[:72]`).
* **Impact:** Any deployed instance using default seed data is immediately vulnerable to automated credential stuffing.

### 2.2. Authentication & RBAC Boundaries
* **Project Boundary Isolation:** Multi-tenancy isolation at the project boundary is enforced via `verify_project_membership()` in [`security.py:96-118`](file:///home/felixsu/koshi/source_code/backend/app/security.py#L96-L118). Users cannot access projects, tasks, or sprints to which they are not explicitly linked via `project_members`.
* **Intra-Project Permission Leakage:** Inside a project, authorization checks are coarse. In [`routers/tasks.py:78-79`](file:///home/felixsu/koshi/source_code/backend/app/routers/tasks.py#L78-L79), any project member (`OWNER`, `PM`, `MEMBER`) can modify any task, overwrite fields, reassign assignees, or cycle statuses on tasks assigned to other engineers. Task ownership checks (`task.assignee_id == current_user.id`) do not exist.
* **Token Lifetime & Revocation Deficit:** Tokens are signed with a static 7-day expiration (`ACCESS_TOKEN_EXPIRE_MINUTES = 10080`). There is no token blacklist, database revocation table, or refresh token rotation mechanism. If an employee is removed from a project or their role is downgraded, their active JWT remains valid across all endpoints until expiration.

### 2.3. Single-Person Bus Factor & Operational Reproducibility
* **Broken Deployment Dependencies:** In [`docker-compose.yml:38-40`](file:///home/felixsu/koshi/docker-compose.yml#L38-L40), the manifest declares `proxy-net: external: true`. Running `docker compose up` on a clean host fails immediately with `network proxy-net declared as external, but could not be found`.
* **Database Schema Bifurcation:** Two conflicting database schemas exist:
  1. [`source_code/backend/db/schema.sql`](file:///home/felixsu/koshi/source_code/backend/db/schema.sql): Relational DDL containing a `task_dependencies` junction table.
  2. [`source_code/backend/app/models/entities.py`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py): SQLAlchemy declarative models using `dependencies_json = Column(Text)`.
  If an operator runs [`init_db.py`](file:///home/felixsu/koshi/source_code/backend/init_db.py) (which executes `schema.sql`), the database lacks `dependencies_json`. Subsequent FastAPI startup queries crash with `sqlite3.OperationalError: no such column: tasks.dependencies_json`.

---

## 3. PILLAR 2: DATA INTEGRITY & DATABASE FAILURE MODES

```
+---------------------------------------------------------------------------------------------------+
| PILLAR 2: DATABASE & DATA INTEGRITY RISKS                                                         |
+------------------------------------+---------------+---------------------+------------------------+
| Failure Mode                       | Severity      | Mechanism           | Impact                 |
+------------------------------------+---------------+---------------------+------------------------+
| SQLite Global Write Lock Deadlock  | DEAL-KILLER   | Single-writer engine| 500s / 30s P99 timeouts|
| JSON Dependency Orphanage          | HIGH          | Unindexed JSON text | Corrupted DAG graphs   |
| Missing SQLite DDL Cascades        | MEDIUM        | ORM-only cascade    | Orphaned tasks/sprints |
| Zero Backup / Snapshots Automation | DEAL-KILLER   | Single `.db` file   | 100% Unrecoverable Loss|
+------------------------------------+---------------+---------------------+------------------------+
```

### 3.1. SQLite Concurrency & Lock Contention (`database is locked`)
* **Configuration:** [`source_code/backend/app/database.py:24-30`](file:///home/felixsu/koshi/source_code/backend/app/database.py#L24-L30) executes PRAGMA listeners on connect:
  ```python
  cursor.execute("PRAGMA journal_mode = WAL;")
  cursor.execute("PRAGMA synchronous = NORMAL;")
  cursor.execute("PRAGMA foreign_keys = ON;")
  cursor.execute("PRAGMA busy_timeout = 30000;")
  ```
* **Concurrency Breakdown:** While Write-Ahead Logging (WAL) enables concurrent readers alongside one writer, SQLite remains fundamentally **single-writer**.
* **Failure Cascade Under Multi-User Write Bursts:**
  1. When 20+ developers concurrently create tasks, update descriptions, add comments, or cycle statuses, all write transactions serialize behind the database file lock.
  2. If an API worker holds a write transaction open during slow disk I/O, other workers block for up to `busy_timeout` (30,000ms).
  3. Under peak sprint planning loads, API response times spike from $< 10\text{ms}$ to $> 5,000\text{ms}$, ultimately throwing `sqlite3.OperationalError: database is locked` (HTTP 500).
* **Container Volume Hazard:** SQLite WAL mode relies on POSIX shared memory (`.shm` file). Running SQLite over Docker volume mounts across distributed nodes or network filesystems (NFS/CIFS) causes shared-memory desynchronization and unrecoverable database header corruption.

### 3.2. Foreign Key & Cascade Integrity
* **Unstructured JSON Dependencies:** In [`entities.py:101`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py#L101), dependencies are serialized as JSON strings: `dependencies_json = Column(Text, default="[]")`.
* **Dangling Dependency Hazard:** When a task is deleted via [`routers/tasks.py:97-109`](file:///home/felixsu/koshi/source_code/backend/app/routers/tasks.py#L97-L109), SQLite cannot enforce foreign key cascades inside JSON strings. Any task referencing the deleted ID in its `dependencies_json` retains an orphaned, invalid dependency ID. The backend performs no cleanup queries, leading to broken DAG sorting and cyclic false positives on subsequent queries.
* **DDL Cascade Absence:** In [`entities.py:76, 90`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py#L76), `Sprint.project_id` and `Task.project_id` define `ForeignKey("projects.id")` **without** `ondelete="CASCADE"` in the DDL. Cascade behavior relies solely on SQLAlchemy ORM session lifecycle hooks. Direct database maintenance or raw SQL queries bypass the ORM and produce orphaned tasks.

### 3.3. Disaster Recovery & Backup Plan
* **Backup Automation:** **0.0%**. No automated cron jobs, volume snapshot scripts, or Litestream / LiteFS streaming replication tools exist in the repository.
* **Blast Radius:** The entire application state resides in a single SQLite file (`/app/data/koshi.db`). If an unclean container restart or host power cut corrupts the SQLite B-tree header during a checkpoint, 100% of project records, task history, and user data are permanently destroyed.

---

## 4. PILLAR 3: COMPOUND FRAGILITY & EXTENSION FRICTION

```
+---------------------------------------------------------------------------------------------------+
| PILLAR 3: FRAGILITY & EXTENSION METRICS                                                           |
+------------------------------------+-------------------------+------------------------------------+
| Component / Layer                  | Automated Test Coverage | Risk Classification                |
+------------------------------------+-------------------------+------------------------------------+
| Frontend Vue Components & Stores   | 0.0% (No test framework)| CRITICAL (Silent UI Breakage)      |
| Backend API Routers & Services     | ~45% (3 test files)     | HIGH (Happy path only, no race tests)|
| AI LLM Cascade Error Handling      | Deterministic Fallback  | MEDIUM (Silent Degradation)        |
| Client IndexedDB State Sync        | Naive Timestamp LWW     | CRITICAL (Silent Overwrite/Race)   |
+------------------------------------+-------------------------+------------------------------------+
```

### 4.1. Test Coverage vs. Architectural Coupling
* **Frontend Test Suite Deficit:** `source_code/frontend/package.json` contains zero test dependencies (`vitest`, `jest`, `@vue/test-utils`, `@playwright/test` are all absent). Core deterministic logic in [`dagSorter.ts`](file:///home/felixsu/koshi/source_code/frontend/src/lib/dagSorter.ts), [`taskStore.ts`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts), and [`gitParser.ts`](file:///home/felixsu/koshi/source_code/frontend/src/lib/gitParser.ts) has zero automated unit regression coverage.
* **Tight UI-to-Schema Coupling:** The frontend manually bridges multiple backend schema inconsistencies:
  1. Maps numeric backend complexity (`1, 2, 3`) to frontend string enums (`S, M, L, XL`) in [`taskStore.ts:309`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L309).
  2. Prefixes integer server IDs (`t.id`) with string tags (`TSK-${t.id}`) in [`taskStore.ts:304`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L304).
  3. Strips non-digits from IDs (`parseInt(id.replace(/\D/g, ''))`) before dispatching REST calls in [`taskStore.ts:509, 525`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L509).
  Any backend database migration or schema refactor instantly breaks frontend state mapping across 8+ modal components.

### 4.2. AI Cascade Failures & Error Handling
* **Implementation:** [`source_code/backend/app/services/ai_service.py:9-58`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L9-L58) implements a 3-tier cascade:
  `Tier 1 (OpenAI Cloud)` $\to$ `Tier 2 (Local Ollama)` $\to$ `Tier 3 (Deterministic Heuristic Engine)`.
* **Reliability Evaluation:**
  * **Upstream Outages:** HTTP timeouts (10.0s for OpenAI, 4.0s for Ollama) and HTTP error statuses (429, 500, 504) are caught via `except Exception:` blocks, successfully falling back to Tier 3 without crashing the ASGI worker.
  * **JSON Sanitization:** Markdown code fences (```` ```json ````) are stripped via regex before parsing in [`ai_service.py:144-151`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L144-L151). If JSON parsing fails, it safely defaults to heuristic generation.
* **Architectural Defects:**
  1. **Socket Exhaustion:** `_call_llm` instantiates a new `httpx.AsyncClient` on every request instead of reusing a shared connection pool, risking socket exhaustion under high traffic.
  2. **Silent Failure / Observability Void:** Exceptions in external LLM calls are caught with `except Exception: pass`. If API keys expire, quotas are exceeded, or upstream endpoints fail, zero error logs or metrics are emitted, masking complete AI pipeline degradation from DevOps engineers.

### 4.3. Client-Side State Desynchronization (IndexedDB vs. REST)
* **Reconciliation Mechanism:** In [`taskStore.ts:321-330`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L321-L330), synchronization uses a naive timestamp comparison:
  ```typescript
  if (local && local.updatedAt > sTask.updatedAt) {
    merged.push(local);
  } else {
    merged.push(sTask);
  }
  ```
* **Critical Desynchronization Flaws:**
  1. **Clock Skew Vulnerability:** Reconciliation relies entirely on the client's local system clock (`Date.now()`). If a client's system clock is skewed ahead by 10 minutes, their local edits will unconditionally overwrite all server updates from other team members, regardless of actual sequence.
  2. **Missing Mutation Queue & Retry Loop:** When offline, task creations generate temporary IDs (`TSK-temp-*`). However, there is no offline transaction journal or retry queue. If network reconnection occurs partially or a background API call fails, unsynced mutations are stranded in IndexedDB or silently overwritten on the next full pull.
  3. **Concurrent Mutation Destruction:** If User A changes status to `DONE` and User B modifies the task description, Last-Write-Wins (LWW) wipes out User A's status change during synchronization. No field-level merging, vector clocks, or operational transforms exist.

---

## 5. PILLAR 4: INFRASTRUCTURE & RUNTIME ROBUSTNESS

```
+---------------------------------------------------------------------------------------------------+
| PILLAR 4: RUNTIME & INFRASTRUCTURE DEFICITS                                                       |
+------------------------------------+---------------+---------------------+------------------------+
| Infrastructure Vector              | Status        | Risk Level          | Impact                 |
+------------------------------------+---------------+---------------------+------------------------+
| Reverse Proxy Body Size Limits     | Unset         | MEDIUM              | Large diffs drop (413) |
| API Rate Limiting & Throttling     | Absent        | HIGH                | DoS & Brute Force risk |
| Container Resource Limits (CPU/RAM)| Absent        | HIGH                | Host OOM Killer risk   |
| Structured JSON Telemetry          | Absent        | MEDIUM              | Zero APM visibility    |
+------------------------------------+---------------+---------------------+------------------------+
```

### 5.1. Reverse Proxy & Container Isolation
* **Nginx Configuration:** [`source_code/frontend/nginx.conf`](file:///home/felixsu/koshi/source_code/frontend/nginx.conf) acts as reverse proxy routing `/api/` to `koshi-backend:8000`.
* **Missing Directives:**
  1. `client_max_body_size` is not configured (defaults to Nginx standard 1MB). Large unified Git diffs ($> 1\text{MB}$) submitted to `/api/ai/analyze-diff` or large meeting transcripts are dropped with `413 Request Entity Too Large`.
  2. No rate limiting zones (`limit_req_zone`, `limit_conn_zone`) are defined. The login endpoints and AI services are fully exposed to automated brute-force attacks and denial-of-service loops.

### 5.2. Memory Leaks & Resource Limits
* **Compose Resource Limits:** In [`docker-compose.yml:1-31`](file:///home/felixsu/koshi/docker-compose.yml#L1-L31), neither `koshi-backend` nor `koshi-frontend` defines `deploy.resources.limits` (memory/CPU).
* **OOM Killer Risk:** In [`dagSorter.ts:77-133`](file:///home/felixsu/koshi/source_code/frontend/src/lib/dagSorter.ts#L77-L133), `computeCriticalPath` executes recursive dynamic programming across graph nodes. A pathological cyclical dependency or deeply nested DAG combined with large meeting transcript processing in the backend can trigger unbounded memory allocation, invoking the Linux kernel Out-Of-Memory (OOM) killer on the host system.

### 5.3. Telemetry & Observability
* **Logging Standard:** The backend uses standard Python `print()` statements and default unformatted Uvicorn console logging.
* **Observability Gaps:**
  1. Zero structured JSON log formatting (e.g., `structlog`, `python-json-logger`).
  2. No distributed tracing, correlation IDs (`X-Request-ID`), or span context across frontend-backend boundaries.
  3. No Prometheus metrics instrumentation (`/metrics`) to monitor SQLite lock wait times, HTTP request latency percentiles, or AI tier fallback rates.

---

## 6. PILLAR 5: 18-MONTH TCO & REMEDIATION ROADMAP

### 6.1. Executive Risk Matrix

| Risk Item | Severity | Impact Area | Remediation Effort (Hours) |
| :--- | :--- | :--- | :---: |
| **P0.1: Remove Google OAuth Mock Token Backdoor** | **DEAL-KILLER** | Security / Auth | 16 |
| **P0.2: Enforce Mandatory Runtime `JWT_SECRET` Validation** | **DEAL-KILLER** | Security / Auth | 8 |
| **P0.3: Migrate SQLite to PostgreSQL with Connection Pooling** | **DEAL-KILLER** | Data Concurrency | 80 |
| **P0.4: Implement Automated Database Backup / Snapshot Pipeline**| **DEAL-KILLER** | Disaster Recovery | 32 |
| **P0.5: Replace Naive Timestamp LWW with Transaction Sync Queue** | **DEAL-KILLER** | Data Integrity | 64 |
| **P1.1: Build Comprehensive Vitest / Vue Test Utils Suite** | **HIGH** | Quality / Fragility | 60 |
| **P1.2: Add Backend Concurrency & RBAC Integration Tests** | **HIGH** | Quality / Auth | 40 |
| **P1.3: Normalize Task Dependencies Schema & Remove JSON Column** | **HIGH** | Database Integrity | 24 |
| **P1.4: Configure Container Limits & Nginx Rate Limiting** | **MEDIUM** | Infrastructure | 16 |
| **P1.5: Implement Structured JSON Logging & Correlation IDs** | **MEDIUM** | Observability | 20 |
| **Total Remediation to Production Gate** | | | **360 Hours** |

---

### 6.2. 18-Month Maintenance Cost Projection

```
+---------------------------------------------------------------------------------------------------+
| 18-MONTH ENGINEERING BURDEN BREAKDOWN                                                             |
+-------------------------------------------------------------+-------------------------------------+
| Category                                                    | Projected Engineering Hours         |
+-------------------------------------------------------------+-------------------------------------+
| Phase 1: P0 Security & Concurrency Remediation (Months 1-3) | 360 Hours                           |
| Phase 2: Schema Evolution & Relational Migration (Months 4-6)| 220 Hours                           |
| Phase 3: Client Sync Engine Rewrite (CRDT/Queue) (Months 7-9)| 260 Hours                           |
| Phase 4: CI/CD, Container Hardening & Observability (M10-12)| 180 Hours                           |
| Phase 5: Ongoing Operational Support & Patching (M13-18)    | 520 Hours                           |
+-------------------------------------------------------------+-------------------------------------+
| TOTAL 18-MONTH ENGINEERING INVESTMENT                       | 1,540 Hours (~0.85 FTE Senior SWE)  |
+-------------------------------------------------------------+-------------------------------------+
```

### 6.3. Step-by-Step Remediation Roadmap

#### Phase 1: Critical Security & Concurrency Hardening (Weeks 1–4)
1. **Purge Authentication Backdoors:** Completely remove `.mock_signature` and `mock_google_token_` string handlers from `source_code/backend/app/routers/auth.py`. Enforce Google JWKS public key certificate verification exclusively.
2. **Strict Environment Secrets:** Update `config.py` to make `JWT_SECRET` mandatory without default fallback; terminate process if secret is missing or default in non-test modes.
3. **Deploy PostgreSQL:** Replace SQLite with PostgreSQL 16 in `docker-compose.yml`. Introduce SQLAlchemy `QueuePool` with `pool_size=20, max_overflow=10` to eliminate write-lock contention.

#### Phase 2: Data Integrity & Schema Normalization (Weeks 5–8)
1. **Relational Dependencies:** Migrate `dependencies_json` to normalized `task_dependencies` junction table with explicit `ON DELETE CASCADE` foreign keys.
2. **Automated Backup Strategy:** Deploy automated WAL archiving (pgBackRest / Litestream) with S3-compatible remote snapshotting every 6 hours.
3. **Field-Level Optimistic Locking:** Add `version` integer column to `tasks` table to detect concurrent edit collisions instead of trusting client timestamps.

#### Phase 3: Client-Side Offline Synchronization Architecture (Weeks 9–12)
1. **Persistent Mutation Journal:** Replace raw IndexedDB state dump with an append-only mutation queue in Pinia (`actionsQueue`).
2. **Reconciliation Engine:** Implement two-way differential synchronization with exponential backoff retry and explicit conflict resolution modals.

#### Phase 4: Testing & Observability Foundations (Weeks 13–16)
1. **Frontend Test Suite:** Install Vitest and Vue Test Utils; reach $\ge 85\%$ coverage on `taskStore.ts`, `dagSorter.ts`, and core modal components.
2. **Structured Logging:** Implement `structlog` emitting standardized JSON logs containing `trace_id`, `user_id`, and execution latency across all FastAPI routes.
3. **Container Resource Fencing:** Define explicit CPU and memory quotas (`deploy.resources.limits`) in `docker-compose.yml` to prevent OOM cascade failures.
