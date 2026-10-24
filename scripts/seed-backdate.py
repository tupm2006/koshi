"""
Spread the seeded Scrum project's completion timestamps across its sprints, so
burndown and velocity show history rather than "everything finished today".

The API can only record completion as *now* — that is correct for real use and
deliberately not overridable — so this one step writes to the database. Run it
inside the backend container, and only against seed data:

    docker exec -i koshi-backend-prod-local python - < scripts/seed-backdate.py
"""
from datetime import timedelta
from app.database import SessionLocal
from app.models.entities import Project, Sprint, Task, TaskStatusEnum

db = SessionLocal()
projects = db.query(Project).filter(Project.name.in_(["Koshi Mobile App", "Website Bán Hàng Q4"])).all()
if not projects:
    raise SystemExit("seed projects not found — run scripts/seed-demo.py first")
for s in db.query(Sprint).filter(Sprint.project_id.in_([p.id for p in projects])).all():
    done = db.query(Task).filter(Task.sprint_id == s.id, Task.status == TaskStatusEnum.DONE).order_by(Task.id).all()
    span = max((s.end_date - s.start_date).days, 1)
    for i, t in enumerate(done):
        day = min(int((i + 1) * span / (len(done) + 1)) + 1, span)
        if s.completed_at is None:  # active sprint: keep within elapsed days
            day = min(day, 2)
        t.completed_at = s.start_date + timedelta(days=day, hours=15)
        t.updated_at = t.completed_at
    if s.completed_at is not None:
        s.completed_at = s.end_date
db.commit()
print("backdated", ", ".join(p.name for p in projects))
