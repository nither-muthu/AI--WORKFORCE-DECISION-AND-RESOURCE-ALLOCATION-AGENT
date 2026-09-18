"""
Task Management Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Task, Employee, AllocationHistory, Assignment
from backend.app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut
from backend.app.services.workload_service import recalculate_employee_workload, recalculate_all_workloads
from backend.app.services.notification_service import create_notification

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def enrich_task(task: Task) -> dict:
    emp_name = task.assigned_employee.name if task.assigned_employee else None
    return {
        "id": task.id,
        "task_code": task.task_code,
        "title": task.title,
        "description": task.description or "",
        "required_skills": task.required_skills or [],
        "priority": task.priority,
        "deadline": task.deadline,
        "sla_hours": float(task.sla_hours or 24.0),
        "estimated_hours": float(task.estimated_hours or 4.0),
        "location": task.location,
        "department": task.department,
        "status": task.status,
        "assigned_employee_id": task.assigned_employee_id,
        "assigned_employee_name": emp_name,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }


@router.get("", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List tasks with multi-field filtering and search."""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if department:
        query = query.filter(Task.department.ilike(f"%{department}%"))
    if employee_id:
        query = query.filter(Task.assigned_employee_id == employee_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Task.title.ilike(search_term)) |
            (Task.task_code.ilike(search_term)) |
            (Task.description.ilike(search_term))
        )

    tasks = query.order_by(Task.id.desc()).all()
    return [enrich_task(t) for t in tasks]


@router.get("/{id}", response_model=TaskOut)
def get_task(id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return enrich_task(task)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    count = db.query(Task).count() + 1
    task_code = task_data.task_code or f"TASK-{count:03d}"

    # Default status
    initial_status = "Assigned" if task_data.assigned_employee_id else (task_data.status or "Unassigned")

    task = Task(
        task_code=task_code,
        title=task_data.title,
        description=task_data.description,
        required_skills=task_data.required_skills,
        priority=task_data.priority,
        deadline=task_data.deadline,
        sla_hours=task_data.sla_hours,
        estimated_hours=task_data.estimated_hours,
        location=task_data.location,
        department=task_data.department,
        status=initial_status,
        assigned_employee_id=task_data.assigned_employee_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    if task.assigned_employee_id:
        recalculate_employee_workload(db, task.assigned_employee_id)

    # Check for critical priority notification
    if task.priority == "Critical":
        create_notification(
            db=db,
            title="Critical Task Created",
            message=f"Critical task '{task.title}' requires immediate attention ({task.sla_hours}h SLA).",
            type="critical"
        )
    else:
        create_notification(
            db=db,
            title="New Task Created",
            message=f"Task '{task.title}' added to backlog.",
            type="info"
        )

    return enrich_task(task)


@router.put("/{id}", response_model=TaskOut)
def update_task(id: int, task_data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_employee_id = task.assigned_employee_id
    old_status = task.status
    update_dict = task_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(task, key, value)

    db.commit()

    if old_employee_id:
        recalculate_employee_workload(db, old_employee_id)
    if task.assigned_employee_id and task.assigned_employee_id != old_employee_id:
        recalculate_employee_workload(db, task.assigned_employee_id)

    db.refresh(task)
    return enrich_task(task)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    emp_id = task.assigned_employee_id
    db.delete(task)
    db.commit()

    if emp_id:
        recalculate_employee_workload(db, emp_id)

    return None
