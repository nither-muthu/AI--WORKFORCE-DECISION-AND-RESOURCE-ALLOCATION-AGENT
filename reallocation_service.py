"""
Dynamic Reallocation Service:
Orchestrates event triggers, ML prediction, OR-Tools optimization,
differential reassignment, audit logging, and notifications.
"""

from typing import Dict, Any, List, Optional
import datetime
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Employee, Task, Assignment, AllocationHistory, MonitoringEvent
)
from backend.app.services.workload_service import recalculate_all_workloads
from backend.app.services.notification_service import create_notification
from ml.predict import predict_batch, predict_pair
from optimizer.allocation_optimizer import WorkforceOptimizer


def serialize_employee(e: Employee) -> Dict[str, Any]:
    return {
        "id": e.id,
        "employee_code": e.employee_code,
        "name": e.name,
        "email": e.email,
        "department": e.department,
        "role_title": e.role_title,
        "skills": e.skills or [],
        "experience_years": e.experience_years,
        "certifications": e.certifications or [],
        "location": e.location,
        "availability_status": e.availability_status,
        "daily_capacity": e.daily_capacity,
        "current_workload_hours": e.current_workload_hours,
        "performance_score": e.performance_score,
        "is_active": e.is_active
    }


def serialize_task(t: Task) -> Dict[str, Any]:
    return {
        "id": t.id,
        "task_code": t.task_code,
        "title": t.title,
        "description": t.description,
        "required_skills": t.required_skills or [],
        "priority": t.priority,
        "deadline": t.deadline,
        "sla_hours": t.sla_hours,
        "estimated_hours": t.estimated_hours,
        "location": t.location,
        "department": t.department,
        "status": t.status,
        "assigned_employee_id": t.assigned_employee_id
    }


def run_dynamic_allocation(
    db: Session,
    task_ids: Optional[List[int]] = None,
    apply_to_db: bool = True,
    trigger_reason: str = "AI Optimization Engine",
    weights: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Run full AI prediction + OR-Tools optimization pipeline.
    """
    # 1. Update all dynamic workloads first
    recalculate_all_workloads(db)

    # 2. Fetch active and available employees
    active_employees = db.query(Employee).filter(Employee.is_active == True).all()
    emp_dicts = [serialize_employee(e) for e in active_employees]

    # 3. Fetch tasks to allocate
    task_query = db.query(Task)
    if task_ids:
        task_query = task_query.filter(Task.id.in_(task_ids))
    else:
        # Include all unassigned tasks + tasks whose assignee is inactive/unavailable/overloaded
        task_query = task_query.filter(Task.status.in_(["Unassigned", "Blocked", "Assigned", "In Progress"]))

    candidate_tasks = task_query.all()
    if not candidate_tasks:
        return {
            "status": "NO_TASKS",
            "message": "No pending tasks found for allocation.",
            "assignments": [],
            "total_assigned": 0,
            "total_tasks_considered": 0
        }

    task_dicts = [serialize_task(t) for t in candidate_tasks]

    # 4. Run Machine Learning predictions for all employee-task pairs
    predictions = predict_batch(emp_dicts, task_dicts)

    # 5. Run OR-Tools Optimization Engine
    optimizer = WorkforceOptimizer(weights=weights)
    optimization_result = optimizer.solve_allocation(emp_dicts, task_dicts, predictions)

    # 6. Apply to Database if requested
    reallocated_count = 0
    if apply_to_db and optimization_result["assignments"]:
        for rec in optimization_result["assignments"]:
            t_id = rec["task_id"]
            new_e_id = rec["employee_id"]

            task_record = db.query(Task).filter(Task.id == t_id).first()
            new_emp = db.query(Employee).filter(Employee.id == new_e_id).first()

            if not task_record or not new_emp:
                continue

            old_e_id = task_record.assigned_employee_id
            old_emp_name = None

            # Check if this is a new assignment or reallocation
            is_changed = (old_e_id != new_e_id)

            if old_e_id:
                old_emp = db.query(Employee).filter(Employee.id == old_e_id).first()
                old_emp_name = old_emp.name if old_emp else f"EMP-{old_e_id}"

            if is_changed:
                reallocated_count += 1
                task_record.assigned_employee_id = new_e_id
                task_record.status = "Assigned"

                # Record in Allocation History
                history = AllocationHistory(
                    task_id=t_id,
                    task_code=task_record.task_code,
                    task_title=task_record.title,
                    previous_employee_id=old_e_id,
                    previous_employee_name=old_emp_name,
                    new_employee_id=new_e_id,
                    new_employee_name=new_emp.name,
                    reason=rec["summary_explanation"],
                    trigger_event=trigger_reason,
                    ai_score=rec["ai_suitability_score"],
                    predicted_completion_hours=rec["predicted_completion_hours"]
                )
                db.add(history)

                # Create assignment link
                assignment_rec = Assignment(
                    task_id=t_id,
                    employee_id=new_e_id,
                    status="Active",
                    ai_suitability_score=rec["ai_suitability_score"],
                    predicted_completion_hours=rec["predicted_completion_hours"],
                    reason_summary=rec["summary_explanation"]
                )
                db.add(assignment_rec)

                # Send Notification
                if old_emp_name:
                    notif_msg = f"Task '{task_record.title}' was reallocated from {old_emp_name} to {new_emp.name} ({trigger_reason})."
                else:
                    notif_msg = f"Task '{task_record.title}' was assigned to {new_emp.name} with {rec['ai_suitability_score']}% AI match score."

                create_notification(
                    db=db,
                    title="Task Allocation Update",
                    message=notif_msg,
                    type="success" if not old_emp_name else "warning"
                )

        db.commit()
        # Recalculate dynamic workloads post-assignment
        recalculate_all_workloads(db)

    optimization_result["reallocated_count"] = reallocated_count
    return optimization_result


def simulate_dynamic_event(
    db: Session,
    event_type: str,
    target_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Simulate realistic workforce disruptions for hackathon live demonstrations:
    - EMPLOYEE_UNAVAILABLE: Sets an employee to Unavailable / On Leave and triggers auto-reallocation of their tasks.
    - NEW_CRITICAL_TASK: Creates an urgent high-priority task and instantly optimizes placement.
    - WORKLOAD_SPIKE: Injects extra hours onto an employee to simulate bottleneck and rebalance.
    - TASK_COMPLETED: Marks an active task as Completed and frees up employee capacity.
    - DEADLINE_CHANGED: Shortens deadline and triggers SLA risk detection and re-optimization.
    """
    payload = payload or {}
    event_title = ""
    event_desc = ""
    severity = "INFO"

    if event_type == "EMPLOYEE_UNAVAILABLE":
        # Target specific or first available employee with tasks
        if target_id:
            emp = db.query(Employee).filter(Employee.id == target_id).first()
        else:
            # Find an employee with assigned tasks
            task_with_emp = db.query(Task).filter(Task.assigned_employee_id.isnot(None), Task.status == "Assigned").first()
            emp = task_with_emp.assigned_employee if task_with_emp else db.query(Employee).first()

        if emp:
            emp.availability_status = "Unavailable"
            db.commit()
            event_title = f"Employee {emp.name} became Unavailable"
            event_desc = f"{emp.name} ({emp.department}) marked unavailable due to unexpected leave. Affected tasks queued for dynamic reallocation."
            severity = "CRITICAL"
            create_notification(
                db=db,
                title="Employee Unavailable",
                message=f"{emp.name} is now unavailable. Triggering dynamic task reallocation.",
                type="critical"
            )

    elif event_type == "NEW_CRITICAL_TASK":
        # Create a new critical urgency task
        count = db.query(Task).count() + 1
        new_task = Task(
            task_code=f"TASK-CRIT-{count:03d}",
            title=payload.get("title", f"Urgent Production Incident Patch #{count}"),
            description=payload.get("description", "High severity incident requiring immediate resolution within 4h SLA window."),
            required_skills=payload.get("required_skills", ["Python", "FastAPI", "Docker"]),
            priority="Critical",
            deadline=payload.get("deadline", "Today 8:00 PM"),
            sla_hours=payload.get("sla_hours", 4.0),
            estimated_hours=payload.get("estimated_hours", 3.5),
            location="Remote",
            department="Engineering",
            status="Unassigned"
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        event_title = f"Critical Task Created: {new_task.task_code}"
        event_desc = f"High priority task '{new_task.title}' arrived with 4-hour SLA. Immediate AI matching triggered."
        severity = "WARNING"
        create_notification(
            db=db,
            title="Critical Task Arrived",
            message=f"Critical task '{new_task.title}' requires immediate AI assignment.",
            type="warning"
        )

    elif event_type == "WORKLOAD_SPIKE":
        emp = db.query(Employee).filter(Employee.id == target_id).first() if target_id else db.query(Employee).first()
        if emp:
            # Create a heavy in-progress task assigned to this employee to spike workload
            count = db.query(Task).count() + 1
            heavy_task = Task(
                task_code=f"TASK-SPIKE-{count:03d}",
                title=f"Emergency Infrastructure Audit ({emp.name})",
                description="Urgent comprehensive security audit consuming full daily capacity.",
                required_skills=emp.skills[:2] if emp.skills else ["Python"],
                priority="High",
                deadline="Today",
                sla_hours=8.0,
                estimated_hours=6.0,
                status="In Progress",
                assigned_employee_id=emp.id
            )
            db.add(heavy_task)
            db.commit()
            recalculate_all_workloads(db)
            event_title = f"Workload Spike for {emp.name}"
            event_desc = f"{emp.name} workload increased to {emp.current_workload_hours}h ({round((emp.current_workload_hours/emp.daily_capacity)*100)}%). Checking for overload bottlenecks."
            severity = "WARNING"
            create_notification(
                db=db,
                title="Workload Capacity Alert",
                message=f"Employee {emp.name} workload exceeded 85% threshold.",
                type="warning"
            )

    elif event_type == "TASK_COMPLETED":
        task = db.query(Task).filter(Task.id == target_id).first() if target_id else db.query(Task).filter(Task.status.in_(["Assigned", "In Progress"])).first()
        if task:
            task.status = "Completed"
            emp_name = task.assigned_employee.name if task.assigned_employee else "Assigned Employee"
            db.commit()
            recalculate_all_workloads(db)
            event_title = f"Task Completed: {task.task_code}"
            event_desc = f"'{task.title}' was completed by {emp_name}. Capacity restored."
            severity = "SUCCESS"
            create_notification(
                db=db,
                title="Task Completed",
                message=f"Task '{task.title}' completed by {emp_name}. Workload recalculated.",
                type="success"
            )

    elif event_type == "DEADLINE_CHANGED":
        task = db.query(Task).filter(Task.id == target_id).first() if target_id else db.query(Task).filter(Task.status.in_(["Assigned", "In Progress"])).first()
        if task:
            task.deadline = "URGENT (2 Hours Left)"
            task.priority = "Critical"
            task.sla_hours = 2.0
            db.commit()
            event_title = f"Deadline Shortened: {task.task_code}"
            event_desc = f"Deadline for '{task.title}' moved to 2 hours. SLA risk escalated to Critical."
            severity = "CRITICAL"
            create_notification(
                db=db,
                title="SLA Risk Escalation",
                message=f"SLA risk detected for Task {task.task_code}: deadline shortened to 2 hours.",
                type="critical"
            )

    else:
        event_title = "Manual Monitoring Trigger"
        event_desc = "Triggered routine AI workforce optimization pass."
        severity = "INFO"

    # Automatically run dynamic reallocation following the event!
    alloc_result = run_dynamic_allocation(
        db=db,
        apply_to_db=True,
        trigger_reason=event_title
    )

    # Save monitoring event
    mon_event = MonitoringEvent(
        event_type=event_type,
        title=event_title,
        description=f"{event_desc} Result: {alloc_result.get('reallocated_count', 0)} tasks reallocated.",
        severity=severity,
        reallocated_count=alloc_result.get("reallocated_count", 0),
        timestamp=datetime.datetime.utcnow()
    )
    db.add(mon_event)
    db.commit()
    db.refresh(mon_event)

    return {
        "event": {
            "id": mon_event.id,
            "event_type": mon_event.event_type,
            "title": mon_event.title,
            "description": mon_event.description,
            "severity": mon_event.severity,
            "reallocated_count": mon_event.reallocated_count,
            "timestamp": mon_event.timestamp.isoformat()
        },
        "allocation_result": alloc_result
    }
