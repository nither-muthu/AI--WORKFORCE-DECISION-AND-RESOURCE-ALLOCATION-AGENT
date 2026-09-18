"""
Dashboard Summary Routes
"""

from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    Employee, Task, AllocationHistory, MonitoringEvent
)
from backend.app.schemas.schemas import DashboardSummaryOut
from backend.app.services.workload_service import recalculate_all_workloads

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Retrieve real-time KPI metrics, chart distributions, and recent events for dashboard.
    """
    recalculate_all_workloads(db)

    employees = db.query(Employee).all()
    tasks = db.query(Task).all()
    history = db.query(AllocationHistory).order_by(AllocationHistory.id.desc()).limit(10).all()
    events = db.query(MonitoringEvent).order_by(MonitoringEvent.id.desc()).limit(10).all()

    total_employees = len(employees)
    active_employees = sum(1 for e in employees if e.is_active and e.availability_status == "Available")

    total_tasks = len(tasks)
    unassigned_tasks = sum(1 for t in tasks if t.status == "Unassigned" or not t.assigned_employee_id)
    in_progress_tasks = sum(1 for t in tasks if t.status in ["In Progress", "Assigned"])
    completed_tasks = sum(1 for t in tasks if t.status == "Completed")

    # Average Workload
    workloads = []
    for e in employees:
        cap = float(e.daily_capacity or 8.0)
        work = float(e.current_workload_hours or 0.0)
        pct = min(100.0, round((work / cap) * 100.0, 1)) if cap > 0 else 0.0
        workloads.append(pct)

    avg_workload = round(sum(workloads) / len(workloads), 1) if workloads else 0.0

    # SLA at Risk Count: Critical/High tasks or approaching deadline
    sla_at_risk = sum(1 for t in tasks if (t.priority == "Critical" or "urgent" in str(t.deadline).lower() or t.status == "Blocked") and t.status != "Completed")

    # Priority breakdown
    prio_counts = Counter(t.priority for t in tasks)
    tasks_by_priority = {
        "Critical": prio_counts.get("Critical", 0),
        "High": prio_counts.get("High", 0),
        "Medium": prio_counts.get("Medium", 0),
        "Low": prio_counts.get("Low", 0)
    }

    # Status breakdown
    status_counts = Counter(t.status for t in tasks)
    tasks_by_status = {
        "Unassigned": status_counts.get("Unassigned", 0),
        "Assigned": status_counts.get("Assigned", 0),
        "In Progress": status_counts.get("In Progress", 0),
        "Completed": status_counts.get("Completed", 0),
        "Blocked": status_counts.get("Blocked", 0)
    }

    # Workload Distribution for charts
    workload_distribution = [
        {
            "id": e.id,
            "name": e.name,
            "department": e.department,
            "capacity": float(e.daily_capacity or 8.0),
            "assigned_hours": float(e.current_workload_hours or 0.0),
            "workload_pct": min(100.0, round(((e.current_workload_hours or 0.0) / (e.daily_capacity or 8.0)) * 100, 1)),
            "status": e.availability_status
        }
        for e in employees
    ]

    # Skill distribution across team
    all_skills = []
    for e in employees:
        if e.skills:
            all_skills.extend(e.skills)
    skill_counter = Counter(all_skills)
    skill_distribution = [
        {"skill": skill, "count": count}
        for skill, count in skill_counter.most_common(12)
    ]

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "total_tasks": total_tasks,
        "unassigned_tasks": unassigned_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
        "average_workload_pct": avg_workload,
        "sla_at_risk_count": sla_at_risk,
        "reallocation_count": db.query(AllocationHistory).count(),
        "tasks_by_priority": tasks_by_priority,
        "tasks_by_status": tasks_by_status,
        "workload_distribution": workload_distribution,
        "skill_distribution": skill_distribution,
        "recent_events": events,
        "recent_allocations": history
    }
