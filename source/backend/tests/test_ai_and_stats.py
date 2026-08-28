import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_mandated_ai_features(client: TestClient, pm_auth_headers: dict, project_with_member):
    project_id, _ = project_with_member

    # 1. Feature A: Weekly Progress Summary
    summary_res = client.post(f"/api/ai/weekly-summary?project_id={project_id}", headers=pm_auth_headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["status"] == "success"
    assert "summary" in summary_data
    assert len(summary_data["summary"]) > 20

    # 2. Feature B: Meeting Minutes Extractor
    notes_payload = {
        "notes": (
            "Họp ngày 22/08: Phạm Minh Tú phụ trách hoàn thiện backend FastAPI và SQLite trước 18h.\n"
            "Dev Member kiểm tra Svelte 5 runes và giao diện Kanban.\n"
            "Đã chốt: Chạy toàn bộ test suite trước khi merge code vào production."
        )
    }
    minutes_res = client.post("/api/ai/meeting-minutes", json=notes_payload, headers=pm_auth_headers)
    assert minutes_res.status_code == 200
    min_data = minutes_res.json()
    assert min_data["status"] == "success"
    assert len(min_data["main_topics"]) > 0
    assert len(min_data["action_items"]) > 0
    assert len(min_data["key_decisions"]) > 0

    # 3. Feature C: Skill & Workload-based Task Assignment
    rec_payload = {
        "title": "Tối ưu hóa Database Indexing & Query Latency",
        "description": "Cấu hình composite indexes và đo lường latency dưới 10ms."
    }
    rec_res = client.post(f"/api/ai/recommend-assignment?project_id={project_id}", json=rec_payload, headers=pm_auth_headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["status"] == "success"
    assert "recommended_name" in rec_data["recommendation"]
    assert "rationale" in rec_data["recommendation"]

    # 4. Feature D: Deterministic Goal Decomposition
    decomp_res = client.post("/api/ai/decompose", json={"goal": "Xây dựng hệ thống thông báo realtime"}, headers=pm_auth_headers)
    assert decomp_res.status_code == 200
    decomp_data = decomp_res.json()
    assert len(decomp_data["subtasks"]) == 3

def test_workload_and_delayed_tasks_stats(client: TestClient, pm_auth_headers: dict, project_with_member):
    project_id, _ = project_with_member

    # Test Workload stats endpoint (now scoped to one project's members)
    workload_res = client.get(f"/api/stats/workload?project_id={project_id}", headers=pm_auth_headers)
    assert workload_res.status_code == 200
    workloads = workload_res.json()
    assert isinstance(workloads, list)
    assert len(workloads) > 0
    assert "total_complexity_points" in workloads[0]

    # Test Delayed tasks endpoint
    delayed_res = client.get(f"/api/stats/delayed-tasks?project_id={project_id}", headers=pm_auth_headers)
    assert delayed_res.status_code == 200
    assert isinstance(delayed_res.json(), list)
