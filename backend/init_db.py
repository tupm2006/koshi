import os
import sqlite3
import hashlib

def hash_pw(password: str) -> str:
    # Use standard sha256 or bcrypt representation for portability without external deps
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except ImportError:
        # Fallback hash format for zero-dependency local seeding
        return "$2b$12$" + hashlib.sha256(password.encode()).hexdigest()[:53]

DB_PATH = os.path.join(os.path.dirname(__file__), "app", "data", "koshi.db")

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
        
    # Seed default PM and team members
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (email, hashed_password, full_name, role, skills)
            VALUES (?, ?, ?, ?, ?)
        """, ("pm@felixsu.qzz.io", hash_pw("admin123"), "Phạm Minh Tú (PM)", "PM", "architecture,fastapi,vue,devops"))
        
        cursor.execute("""
            INSERT INTO users (email, hashed_password, full_name, role, skills)
            VALUES (?, ?, ?, ?, ?)
        """, ("huynh@felixsu.qzz.io", hash_pw("user123"), "Phạm Văn Huynh", "MEMBER", "backend,python,testing,sql"))
        
        cursor.execute("""
            INSERT INTO users (email, hashed_password, full_name, role, skills)
            VALUES (?, ?, ?, ?, ?)
        """, ("don@felixsu.qzz.io", hash_pw("user123"), "Đàm Đức Đôn", "MEMBER", "frontend,vue,ui,css"))
        
        cursor.execute("""
            INSERT INTO projects (name, description, owner_id)
            VALUES ('Koshi Core Engine', 'High-velocity project management tracker', 1)
        """)
        
        cursor.execute("""
            INSERT INTO sprints (project_id, name, goal, is_active)
            VALUES (1, 'Sprint 1 - Core Workspace', 'Complete Table, Kanban, DAG and AI PM workflows', 1)
        """)
        
        cursor.execute("""
            INSERT INTO tasks (id, project_id, sprint_id, assignee_id, title, description, status, priority, complexity_points)
            VALUES ('TSK-1', 1, 1, 1, 'Implement FastAPI backend with SQLite', 'Setup entities and routers', 'DONE', 'HIGH', 3)
        """)
        cursor.execute("""
            INSERT INTO tasks (id, project_id, sprint_id, assignee_id, title, description, status, priority, complexity_points)
            VALUES ('TSK-2', 1, 1, 2, 'Build 2D Spatial Kanban Navigation', 'Vim hotkeys and focus tracking', 'IN_PROGRESS', 'CRITICAL', 3)
        """)
        cursor.execute("""
            INSERT INTO tasks (id, project_id, sprint_id, assignee_id, title, description, status, priority, complexity_points, blocking_reason)
            VALUES ('TSK-3', 1, 1, 3, 'Integrate AI PM Workflow Endpoints', 'Weekly summary and minutes extraction', 'BLOCKED', 'HIGH', 2, 'Waiting on API token configuration')
        """)
        
        cursor.execute("INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES ('TSK-2', 'TSK-1')")
        cursor.execute("INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES ('TSK-3', 'TSK-1')")
        
        conn.commit()
    conn.close()
    print(f"Database initialized and seeded at: {DB_PATH}")

if __name__ == "__main__":
    init_database()
