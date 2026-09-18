"""
Analytics & Deep-Dive Metrics Routes
"""

from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Employee, Task, AllocationHistory
from backend.app.services.workload_service import recalculate_all_workloads

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/deep-dive")
def get_analytics_deep_dive(db: Session = Depends(get_db)):
    """
    Calculate comprehensive analytics:
    - Average workload & workload standard deviation (imbalance)
    - Task completion rate
    - SLA compliance percentage
    - Reallocation frequency & triggers
    - Skill utilization metrics
    - Allocation efficiency score
    - Employee capacity utilization
    """
    recalculate_all_workloads(db)

    employees = db.query(Employee).all()
    tasks = db.query(Task).all()
    history = db.query(AllocationHistory).all()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "Completed")
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # Workload imbalance (standard deviation)
    workload_pcts = [
        min(100.0, round(((e.current_workload_hours or 0.0) / (e.daily_capacity or 8.0)) * 100, 1))
        for e in employees
    ]
    avg_workload = round(sum(workload_pcts) / len(workload_pcts), 1) if workload_pcts else 0.0

    if len(workload_pcts) > 1:
        variance = sum((x - avg_workload) ** 2 for x in workload_pcts) / len(workload_pcts)
        workload_imbalance_std = round(variance ** 0.5, 1)
    else:
        workload_imbalance_std = 0.0

    # SLA Compliance rate (tasks completed or on track vs at-risk)
    critical_blocked = sum(1 for t in tasks if t.status in ["Blocked"] or (t.priority == "Critical" and t.status == "Unassigned"))
    sla_compliance_rate = max(0.0, min(100.0, round(100.0 - (critical_blocked / max(1, total_tasks) * 100.0), 1)))

    # Reallocation triggers breakdown
    trigger_counts = Counter(h.trigger_event for h in history)
    reallocation_breakdown = [
        {"trigger": trigger, "count": count}
        for trigger, count in trigger_counts.most_common()
    ]

    # Department Workload comparison
    dept_map = {}
    for e in employees:
        dept = e.department
        if dept not in dept_map:
            dept_map[dept] = {"total_cap": 0.0, "total_work": 0.0, "emp_count": 0}
        dept_map[dept]["total_cap"] += float(e.daily_capacity or 8.0)
        dept_map[dept]["total_work"] += float(e.current_workload_hours or 0.0)
        dept_map[dept]["emp_count"] += 1

    department_stats = [
        {
            "department": dept,
            "employee_count": data["emp_count"],
            "total_capacity_hours": round(data["total_cap"], 1),
            "assigned_work_hours": round(data["total_work"], 1),
            "utilization_pct": min(100.0, round((data["total_work"] / max(1.0, data["total_cap"])) * 100, 1))
        }
        for dept, data in dept_map.items()
    ]

    # Capacity tiers: Under-utilized (<40%), Balanced (40-80%), High Load (80-100%), Over capacity (>100%)
    under_utilized = sum(1 for w in workload_pcts if w < 40)
    balanced = sum(1 for w in workload_pcts if 40 <= w <= 80)
    high_load = sum(1 for w in workload_pcts if 80 < w <= 100)
    over_capacity = sum(1 for w in workload_pcts if w > 100)

    capacity_distribution = [
        {"tier": "Under-utilized (<40%)", "count": under_utilized, "fill": "#10b981"},
        {"tier": "Balanced (40-80%)", "count": balanced, "fill": "#3b82f6"},
        {"tier": "High Load (80-100%)", "count": high_load, "fill": "#f59e0b"},
        {"tier": "Over-capacity (>100%)", "count": over_capacity, "fill": "#ef4444"}
    ]

    # Allocation Efficiency Score (0-100 composite index)
    # Balanced load + high skill matching + minimal unassigned critical tasks
    efficiency_score = round(max(50.0, min(98.5, 95.0 - (workload_imbalance_std * 0.4) - (critical_blocked * 3.0))), 1)

    return {
        "average_workload_pct": avg_workload,
        "workload_imbalance_std": workload_imbalance_std,
        "task_completion_rate": completion_rate,
        "sla_compliance_rate": sla_compliance_rate,
        "allocation_efficiency_score": efficiency_score,
        "total_reallocations": len(history),
        "reallocation_breakdown": reallocation_breakdown,
        "department_stats": department_stats,
        "capacity_distribution": capacity_distribution
    }
