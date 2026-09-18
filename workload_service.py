"""
Workload Service: Calculates dynamic workloads automatically from assigned tasks.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.entities import Employee, Task


def recalculate_employee_workload(db: Session, employee_id: int) -> float:
    """
    Recalculate dynamic workload hours for a single employee based on active assigned tasks.
    Formula: Workload = Sum of estimated hours of all active (Assigned / In Progress) tasks.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return 0.0

    active_tasks = db.query(Task).filter(
        Task.assigned_employee_id == employee_id,
        Task.status.in_(["Assigned", "In Progress", "Blocked"])
    ).all()

    total_hours = sum(float(t.estimated_hours or 0.0) for t in active_tasks)
    employee.current_workload_hours = round(total_hours, 1)
    db.commit()
    db.refresh(employee)
    return total_hours


def recalculate_all_workloads(db: Session) -> None:
    """
    Recalculate dynamic workloads for all employees in the system.
    """
    employees = db.query(Employee).all()
    for emp in employees:
        active_tasks = db.query(Task).filter(
            Task.assigned_employee_id == emp.id,
            Task.status.in_(["Assigned", "In Progress", "Blocked"])
        ).all()
        total_hours = sum(float(t.estimated_hours or 0.0) for t in active_tasks)
        emp.current_workload_hours = round(total_hours, 1)

    db.commit()


def get_workload_percentage(employee: Employee) -> float:
    """Return workload percentage for an employee."""
    capacity = float(employee.daily_capacity or 8.0)
    if capacity <= 0:
        return 100.0
    return min(200.0, round((float(employee.current_workload_hours or 0.0) / capacity) * 100.0, 1))
