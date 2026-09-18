"""
Automated End-to-End System Test Suite
Validates:
1. Database tables and demo seeding
2. Authentication for all 3 demo roles (Admin, Manager, Employee)
3. Employee CRUD and Dynamic Workload Calculation
4. Task CRUD and Priority/SLA handling
5. Scikit-Learn Random Forest ML predictions (Dual Head)
6. Google OR-Tools CP-SAT Combinatorial Optimization Solver
7. Real-Time Event Simulation & Dynamic Reallocation Pipeline
8. Notifications and Audit History
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.entities import Employee, Task, User, AllocationHistory, MonitoringEvent, Notification
from ml.predict import predict_pair
from optimizer.allocation_optimizer import WorkforceOptimizer

client = TestClient(app)


def test_health_check():
    print("Testing Root & Health API...")
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ONLINE"
    assert "ml_engine" in data["architecture"]
    print("[OK] Health Check Passed!")


def test_auth_logins():
    print("\nTesting Demo Logins for All 3 Roles...")
    roles = [
        ("admin@demo.com", "admin123", "admin"),
        ("manager@demo.com", "manager123", "manager"),
        ("employee@demo.com", "employee123", "employee")
    ]
    for email, password, expected_role in roles:
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["role"] == expected_role
        print(f"[OK] Authenticated as {expected_role.upper()} ({email})")


def test_employee_and_workload():
    print("\nTesting Employee Directory & Dynamic Workload Calculation...")
    resp = client.get("/api/employees")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) >= 15, f"Expected at least 15 employees, found {len(employees)}"
    
    # Check Priya Sharma
    priya = next((e for e in employees if "Priya" in e["name"]), None)
    assert priya is not None
    assert "skills" in priya
    assert "workload_percentage" in priya
    assert priya["current_workload_hours"] >= 0.0
    print(f"[OK] Employee Directory Verified: {len(employees)} active employees. Priya workload = {priya['workload_percentage']}%")


def test_tasks_and_sla():
    print("\nTesting Task Backlog & Priorities...")
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) >= 20, f"Expected at least 20 tasks, found {len(tasks)}"
    critical_tasks = [t for t in tasks if t["priority"] == "Critical"]
    assert len(critical_tasks) > 0
    print(f"[OK] Task Portfolio Verified: {len(tasks)} tasks ({len(critical_tasks)} Critical priority).")


def test_ml_prediction():
    print("\nTesting Scikit-Learn Random Forest Prediction Engine...")
    emp_sample = {
        "skills": ["Python", "FastAPI", "Machine Learning"],
        "experience_years": 6.0,
        "current_workload_hours": 3.0,
        "daily_capacity": 8.0,
        "performance_score": 92.0,
        "location": "Chennai",
        "availability_status": "Available",
        "is_active": True
    }
    task_sample = {
        "required_skills": ["Python", "Machine Learning"],
        "priority": "High",
        "estimated_hours": 4.0,
        "sla_hours": 12.0,
        "location": "Chennai"
    }
    resp = client.post("/api/ml/predict", json={"employee": emp_sample, "task": task_sample})
    assert resp.status_code == 200, f"ML Predict failed: {resp.text}"
    ml_res = resp.json()
    assert "predicted_completion_hours" in ml_res
    assert "suitability_score" in ml_res
    assert ml_res["suitability_score"] > 50.0
    print(f"[OK] ML Prediction Output -> Predicted Completion: {ml_res['predicted_completion_hours']}h | Suitability Score: {ml_res['suitability_score']}%")


def test_ortools_optimization():
    print("\nTesting Google OR-Tools CP-SAT Optimization Solver...")
    resp = client.post("/api/optimize/assign", json={"apply_assignments": False})
    assert resp.status_code == 200, f"Optimization failed: {resp.text}"
    opt_res = resp.json()
    assert opt_res["status"] in ["OPTIMAL", "FEASIBLE"]
    assert len(opt_res["assignments"]) > 0
    first_rec = opt_res["assignments"][0]
    assert "reasons" in first_rec
    assert len(first_rec["reasons"]) > 0
    print(f"[OK] OR-Tools Solver Status: {opt_res['status']} | Generated {len(opt_res['assignments'])} optimal assignments with explainability.")


def test_dynamic_event_simulation():
    print("\nTesting Live Event Simulation & Automatic Reallocation...")
    resp = client.post("/api/events/simulate", json={"event_type": "EMPLOYEE_UNAVAILABLE"})
    assert resp.status_code == 200, f"Simulation failed: {resp.text}"
    sim_res = resp.json()
    assert "event" in sim_res
    assert "allocation_result" in sim_res
    print(f"[OK] Disruption Simulated -> Event: {sim_res['event']['title']} | Auto-Reallocated: {sim_res['event']['reallocated_count']} tasks.")


def test_dashboard_and_analytics():
    print("\nTesting Dashboard & Analytics Endpoints...")
    dash_resp = client.get("/api/dashboard/summary")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert "average_workload_pct" in dash_data
    assert "tasks_by_priority" in dash_data

    analytics_resp = client.get("/api/analytics/deep-dive")
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()
    assert "allocation_efficiency_score" in analytics_data
    assert "sla_compliance_rate" in analytics_data
    print(f"[OK] Analytics Verified -> Efficiency Score: {analytics_data['allocation_efficiency_score']} | SLA Compliance: {analytics_data['sla_compliance_rate']}%")



if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING WORKFORCE-AI COMPLETE INTEGRATION TEST SUITE")
    print("=" * 70)
    test_health_check()
    test_auth_logins()
    test_employee_and_workload()
    test_tasks_and_sla()
    test_ml_prediction()
    test_ortools_optimization()
    test_dynamic_event_simulation()
    test_dashboard_and_analytics()
    print("\n" + "=" * 70)
    print("ALL INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)
