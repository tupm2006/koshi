# System Architecture - Koshi Project Management Engine

## 1. High-Level Topology

```
+-----------------------------------------------------------------------------+
|                            CLIENT TIER (Vue 3 SPA)                          |
|  - Vue 3.5 Composition API + TypeScript 5.7                                |
|  - Pinia 2.3 Store (Local-first IndexedDB via idb-keyval + Remote Sync)     |
|  - 0ms Latency UI Engine (Instant keyboard state machines)                  |
|  - In-browser Kahn's Algorithm & Critical Path Method (CPM) Solver          |
+-----------------------------------------------------------------------------+
                                       |
                            HTTPS / JSON REST API
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                     EDGE & REVERSE PROXY TIER (Nginx / Caddy)              |
|  - TLS Termination & HTTP/2 Multiplexing                                    |
|  - Static Asset Delivery (/dist) & Upstream API Routing (/api/v1)           |
+-----------------------------------------------------------------------------+
                                       |
                               Unix Socket / TCP
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                      APPLICATION TIER (FastAPI 0.110+)                      |
|  - Python 3.11 Async Runtime + Uvicorn ASGI Server                          |
|  - JWT Bearer Authentication & Google OAuth2 Token Verification             |
|  - Role-Based Access Control (RBAC: PM vs MEMBER)                           |
|  - Multi-Tier AI PM Cascade (Rule Heuristics -> Local Model -> Gemini Flash)|
+-----------------------------------------------------------------------------+
                                       |
                             SQLAlchemy 2.0 ORM
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                        PERSISTENCE TIER (SQLite 3)                          |
|  - Embedded ACID relational engine (Mounted volume /app/data/koshi.db)      |
|  - Foreign key cascading constraints & unique indexes                       |
+-----------------------------------------------------------------------------+
```

---

## 2. State Invariant & Graph Mathematical Models

### 2.1 Cyclic Task Status Progression
The status of any task $t \in T$ follows a deterministic finite state machine (FSM) over the alphabet $\Sigma = \{\text{cycle}\}$:

$$\delta(s) = \begin{cases} 
\text{IN\_PROGRESS}, & s = \text{TODO} \\
\text{DONE}, & s = \text{IN\_PROGRESS} \\
\text{BLOCKED}, & s = \text{DONE} \\
\text{TODO}, & s = \text{BLOCKED}
\end{cases}$$

### 2.2 2D Spatial Circular Kanban Navigation
For column index $c \in \{0, 1, 2, 3\}$ corresponding to `[TODO, IN_PROGRESS, BLOCKED, DONE]`:

$$\text{NextCol}(c, \Delta) = (c + \Delta + 4) \pmod 4, \quad \Delta \in \{-1, +1\}$$

### 2.3 Critical Path Method (CPM) & DAG Cycle Detection
1. Construct directed graph $G = (V, E)$ where $V = \text{Tasks}$ and $(u, v) \in E \iff v \text{ depends on } u$.
2. Compute in-degree $d^-(v)$ for all $v \in V$.
3. Enqueue all vertices $v$ with $d^-(v) = 0$.
4. **Topological Order Extraction**: Process vertices in queue, decrementing child in-degrees. If processed count $|L| < |V|$, a circular dependency (cycle) is detected and rejected with `HTTP 400`.
5. **Early / Late Timing Pass**:
   - Earliest Finish: $\text{EF}(v) = \text{ES}(v) + \text{duration}(v)$, where $\text{ES}(v) = \max_{u \in \text{Pred}(v)} \text{EF}(u)$.
   - Total Float: $\text{TF}(v) = \text{LS}(v) - \text{ES}(v)$.
   - **Critical Path Invariant**: $\text{Critical}(v) \iff \text{TF}(v) = 0 \land \text{Status}(v) \neq \text{DONE}$.

---

## 3. Multi-Tier AI Cascade Architecture

```
[User Request / PM Action]
             |
             v
+-----------------------------+
|  Tier 1: Client Heuristic   | ---> Match? ---> Return instantaneous plan (< 5ms)
+-----------------------------+
             | No
             v
+-----------------------------+
|  Tier 2: Backend Rule Match | ---> Match? ---> Return structured DTO (< 50ms)
+-----------------------------+
             | No
             v
+-----------------------------+
|  Tier 3: Gemini 1.5 Flash   | ---> Invoke API with JSON Schema (< 1500ms)
+-----------------------------+
```
