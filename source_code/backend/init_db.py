import os
import sqlite3
import hashlib
from datetime import datetime, timedelta

def hash_pw(password: str) -> str:
    try:
        import bcrypt
        pwd_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
    except Exception:
        return "$2b$12$" + hashlib.sha256(password.encode()).hexdigest()[:53]

DB_PATH = os.path.join(os.path.dirname(__file__), "app", "data", "koshi.db")

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enforce SQLite WAL concurrency and foreign keys
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA busy_timeout = 30000;")
    
    schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
        
    # Migrate any missing columns in tasks if table already existed
    cursor.execute("PRAGMA table_info(tasks);")
    task_cols = [row[1] for row in cursor.fetchall()]
    if "dependencies_json" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN dependencies_json TEXT DEFAULT '[]';")
    if "acceptance_criteria_json" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN acceptance_criteria_json TEXT DEFAULT '[]';")
    if "documents_json" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN documents_json TEXT DEFAULT '[]';")
    if "requested_priority" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN requested_priority VARCHAR(20) DEFAULT NULL;")
    if "priority_request_reason" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN priority_request_reason VARCHAR(255) DEFAULT NULL;")
    if "priority_requested_by_id" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN priority_requested_by_id INTEGER DEFAULT NULL;")

    cursor.execute("PRAGMA table_info(task_dependencies);")
    td_cols = [row[1] for row in cursor.fetchall()]
    if td_cols and "depends_on_id" not in td_cols:
        if "depends_on_task_id" in td_cols:
            cursor.execute("ALTER TABLE task_dependencies ADD COLUMN depends_on_id INTEGER DEFAULT NULL;")
            cursor.execute("UPDATE task_dependencies SET depends_on_id = depends_on_task_id WHERE depends_on_id IS NULL;")
        else:
            cursor.execute("ALTER TABLE task_dependencies ADD COLUMN depends_on_id INTEGER DEFAULT NULL;")

    now = datetime.utcnow()
    pw_hash = hash_pw("koshi123")

    # Seed Accounts: pm@tupm.qzz.io, dev@tupm.qzz.io, tupm.pm@ictu.edu.vn
    users_data = [
        ("pm@tupm.qzz.io", pw_hash, "Phạm Minh Tú (PM)", "architecture,fastapi,vue,devops"),
        ("dev@tupm.qzz.io", pw_hash, "Dev Member", "frontend,vue,tailwind,typescript"),
        ("tupm.pm@ictu.edu.vn", pw_hash, "Tú PM (ICTU)", "management,scrum,agile"),
        ("huynh@tupm.qzz.io", pw_hash, "Phạm Văn Huynh", "backend,python,testing,sql"),
        ("don@tupm.qzz.io", pw_hash, "Đàm Đức Đôn", "frontend,vue,ui,css"),
    ]

    for email, pwd, name, skills in users_data:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO users (email, hashed_password, full_name, skills)
                VALUES (?, ?, ?, ?)
            """, (email, pwd, name, skills))
        else:
            cursor.execute("""
                UPDATE users SET hashed_password = ?, full_name = ?, skills = ? WHERE email = ?
            """, (pwd, name, skills, email))

    # Fetch user IDs
    user_map = {}
    for email, _, _, _ in users_data:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_map[email] = cursor.fetchone()[0]

    pm_id = user_map["pm@tupm.qzz.io"]
    dev_id = user_map["dev@tupm.qzz.io"]
    tupm_id = user_map["tupm.pm@ictu.edu.vn"]

    # Seed Project #1
    cursor.execute("SELECT id FROM projects WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO projects (id, name, description, owner_id)
            VALUES (1, 'Koshi Core Engine', 'High-velocity project management tracker', ?)
        """, (pm_id,))
    else:
        cursor.execute("""
            UPDATE projects SET name = 'Koshi Core Engine', description = 'High-velocity project management tracker', owner_id = ? WHERE id = 1
        """, (pm_id,))

    # Map seed accounts to Project #1 with appropriate roles
    membership_data = [
        (1, pm_id, "OWNER"),
        (1, dev_id, "MEMBER"),
        (1, tupm_id, "PM"),
    ]
    for email in ["huynh@tupm.qzz.io", "don@tupm.qzz.io"]:
        if email in user_map:
            membership_data.append((1, user_map[email], "MEMBER"))

    for proj_id, uid, role in membership_data:
        cursor.execute("""
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (?, ?, ?)
            ON CONFLICT(project_id, user_id) DO UPDATE SET role = excluded.role
        """, (proj_id, uid, role))

    # Seed two sprints for Project #1:
    # Sprint 1: Core Engine (is_active=True, dates covering current week)
    # Sprint 2: Extensibility (is_active=False, dates for next month)
    sprint1_start = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    sprint1_end = (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    sprint2_start = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    sprint2_end = (now + timedelta(days=44)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT id FROM sprints WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO sprints (id, project_id, name, goal, start_date, end_date, is_active)
            VALUES (1, 1, 'Sprint 1: Core Engine', 'Complete Table, Kanban, DAG and AI PM workflows', ?, ?, 1)
        """, (sprint1_start, sprint1_end))
    else:
        cursor.execute("""
            UPDATE sprints
            SET name = 'Sprint 1: Core Engine', goal = 'Complete Table, Kanban, DAG and AI PM workflows',
                start_date = ?, end_date = ?, is_active = 1
            WHERE id = 1
        """, (sprint1_start, sprint1_end))

    cursor.execute("SELECT id FROM sprints WHERE id = 2")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO sprints (id, project_id, name, goal, start_date, end_date, is_active)
            VALUES (2, 1, 'Sprint 2: Extensibility', 'Scale integrations, webhooks, and analytics', ?, ?, 0)
        """, (sprint2_start, sprint2_end))
    else:
        cursor.execute("""
            UPDATE sprints
            SET name = 'Sprint 2: Extensibility', goal = 'Scale integrations, webhooks, and analytics',
                start_date = ?, end_date = ?, is_active = 0
            WHERE id = 2
        """, (sprint2_start, sprint2_end))

    # Distribute seeded tasks across sprint_id = 1 and sprint_id = None (Backlog)
    tasks_seed = [
        (1, 1, 1, pm_id, 'Implement FastAPI backend with SQLite', 'Setup entities and routers', 'DONE', 'HIGH', 3, (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), None, '[]', '[]', '[]'),
        (2, 1, 1, dev_id, 'Build 2D Spatial Kanban Navigation', 'Vim hotkeys and focus tracking', 'IN_PROGRESS', 'CRITICAL', 3, (now + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"), None, '[1]', '[]', '[]'),
        (3, 1, None, tupm_id, 'Integrate AI PM Workflow Endpoints', 'Weekly summary and minutes extraction', 'BLOCKED', 'HIGH', 2, (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"), 'Waiting on API token configuration', '[1]', '[]', '[]'),
        (4, 1, None, dev_id, 'Offline-First Sync Engine and Service Worker', 'Ensure local resilience and caching', 'TODO', 'MEDIUM', 2, (now + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), None, '[]', '[]', '[]')
    ]

    for t_id, p_id, s_id, a_id, title, desc, status, priority, pts, due, blk, deps, ac, docs in tasks_seed:
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (t_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO tasks (id, project_id, sprint_id, assignee_id, title, description, status, priority, complexity_points, due_date, blocking_reason, dependencies_json, acceptance_criteria_json, documents_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (t_id, p_id, s_id, a_id, title, desc, status, priority, pts, due, blk, deps, ac, docs))
        else:
            cursor.execute("""
                UPDATE tasks
                SET project_id = ?, sprint_id = ?, assignee_id = ?, title = ?, description = ?, status = ?, priority = ?, complexity_points = ?, due_date = ?, blocking_reason = ?, dependencies_json = ?, acceptance_criteria_json = ?, documents_json = ?
                WHERE id = ?
            """, (p_id, s_id, a_id, title, desc, status, priority, pts, due, blk, deps, ac, docs, t_id))

    cursor.execute("DELETE FROM task_dependencies WHERE task_id = 2 AND depends_on_id = 1")
    cursor.execute("INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_id) VALUES (2, 1)")

    conn.commit()
    conn.close()
    print(f"Database initialized with WAL mode and seeded at: {DB_PATH}")

if __name__ == "__main__":
    init_database()
