"""
Assignment and Reassignment Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Task, Employee, Assignment, AllocationHistory
from backend.app.schemas.schemas import AssignTaskRequest, ReassignTaskRequest, AssignmentOut, AllocationHistoryOut
from backend.app.services.workload_service import recalculate_employee_workload
from backend.app.services.notification_service import create_notification
from ml.predict import predict_pair

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])


@router.get("", response_model=List[AssignmentOut])
def list_assignments(db: Session = Depends(get_db)):
    """List all recorded assignments."""
    return db.query(Assignment).order_by(Assignment.id.desc()).all()


@router.post("", response_model=AssignmentOut)
def assign_task(req: AssignTaskRequest, db: Session = Depends(get_db)):
    """Manually assign a task to an employee."""
    task = db.query(Task).filter(Task.id == req.task_id).first()
    emp = db.query(Employee).filter(Employee.id == req.employee_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    old_emp_id = task.assigned_employee_id
    old_emp_name = task.assigned_employee.name if task.assigned_employee else None

    # Calculate ML score if not provided
    ai_score = req.ai_suitability_score
    pred_hours = req.predicted_completion_hours
    if ai_score is None or pred_hours is None:
        from backend.app.services.reallocation_service import serialize_employee, serialize_task
        pred = predict_pair(serialize_employee(emp), serialize_task(task))
        ai_score = pred["suitability_score"]
        pred_hours = pred["predicted_completion_hours"]

    task.assigned_employee_id = emp.id
    task.status = "Assigned"

    assignment = Assignment(
        task_id=task.id,
        employee_id=emp.id,
        status="Active",
        ai_suitability_score=ai_score,
        predicted_completion_hours=pred_hours,
        reason_summary=req.reason
    )
    db.add(assignment)

    # History log
    history = AllocationHistory(
        task_id=task.id,
        task_code=task.task_code,
        task_title=task.title,
        previous_employee_id=old_emp_id,
        previous_employee_name=old_emp_name,
        new_employee_id=emp.id,
        new_employee_name=emp.name,
        reason=req.reason or f"Assigned to {emp.name} based on skill profile.",
        trigger_event="Manual Assignment",
        ai_score=ai_score,
        predicted_completion_hours=pred_hours
    )
    db.add(history)
    db.commit()

    recalculate_employee_workload(db, emp.id)
    if old_emp_id and old_emp_id != emp.id:
        recalculate_employee_workload(db, old_emp_id)

    create_notification(
        db=db,
        title="Task Assigned",
        message=f"Task '{task.title}' assigned to {emp.name} (AI score: {ai_score}%).",
        type="info"
    )

    db.refresh(assignment)
    return assignment


@router.post("/reassign", response_model=AssignmentOut)
def reassign_task(req: ReassignTaskRequest, db: Session = Depends(get_db)):
    """Reassign a task to a different employee with explicit audit logging."""
    task = db.query(Task).filter(Task.id == req.task_id).first()
    new_emp = db.query(Employee).filter(Employee.id == req.new_employee_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not new_emp:
        raise HTTPException(status_code=404, detail="New employee not found")

    old_emp_id = task.assigned_employee_id
    old_emp_name = task.assigned_employee.name if task.assigned_employee else "Unassigned"

    # ML Score
    ai_score = req.ai_score
    pred_hours = req.predicted_completion_hours
    if ai_score is None or pred_hours is None:
        from backend.app.services.reallocation_service import serialize_employee, serialize_task
        pred = predict_pair(serialize_employee(new_emp), serialize_task(task))
        ai_score = pred["suitability_score"]
        pred_hours = pred["predicted_completion_hours"]

    task.assigned_employee_id = new_emp.id
    task.status = "Assigned"

    assignment = Assignment(
        task_id=task.id,
        employee_id=new_emp.id,
        status="Active",
        ai_suitability_score=ai_score,
        predicted_completion_hours=pred_hours,
        reason_summary=req.reason
    )
    db.add(assignment)

    history = AllocationHistory(
        task_id=task.id,
        task_code=task.task_code,
        task_title=task.title,
        previous_employee_id=old_emp_id,
        previous_employee_name=old_emp_name,
        new_employee_id=new_emp.id,
        new_employee_name=new_emp.name,
        reason=req.reason,
        trigger_event=req.trigger_event or "Dynamic Reassignment",
        ai_score=ai_score,
        predicted_completion_hours=pred_hours
    )
    db.add(history)
    db.commit()

    recalculate_employee_workload(db, new_emp.id)
    if old_emp_id and old_emp_id != new_emp.id:
        recalculate_employee_workload(db, old_emp_id)

    create_notification(
        db=db,
        title="Task Reallocated",
        message=f"Task '{task.title}' reallocated from {old_emp_name} to {new_emp.name}. Reason: {req.reason}",
        type="warning"
    )

    db.refresh(assignment)
    return assignment


@router.get("/history", response_model=List[AllocationHistoryOut])
def get_allocation_history(
    task_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve full audit history log of all allocations and dynamic reassignments."""
    query = db.query(AllocationHistory)
    if task_id:
        query = query.filter(AllocationHistory.task_id == task_id)
    return query.order_by(AllocationHistory.id.desc()).limit(limit).all()
