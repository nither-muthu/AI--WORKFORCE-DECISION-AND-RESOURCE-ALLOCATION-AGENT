"""
Employee Management Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Employee, Task, User
from backend.app.schemas.schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut
from backend.app.services.workload_service import recalculate_employee_workload, recalculate_all_workloads
from backend.app.services.notification_service import create_notification
from backend.app.utils.auth_utils import hash_password

router = APIRouter(prefix="/api/employees", tags=["Employees"])


def enrich_employee(emp: Employee) -> dict:
    """Helper to convert Employee ORM object to EmployeeOut schema dictionary with workload %."""
    cap = float(emp.daily_capacity or 8.0)
    work = float(emp.current_workload_hours or 0.0)
    workload_pct = min(200.0, round((work / cap) * 100.0, 1)) if cap > 0 else 100.0

    return {
        "id": emp.id,
        "employee_code": emp.employee_code,
        "name": emp.name,
        "email": emp.email,
        "department": emp.department,
        "role_title": emp.role_title,
        "skills": emp.skills or [],
        "experience_years": float(emp.experience_years or 3.0),
        "certifications": emp.certifications or [],
        "location": emp.location,
        "availability_status": emp.availability_status,
        "daily_capacity": cap,
        "current_workload_hours": work,
        "workload_percentage": workload_pct,
        "performance_score": float(emp.performance_score or 80.0),
        "is_active": emp.is_active,
        "created_at": emp.created_at,
        "updated_at": emp.updated_at
    }


@router.get("", response_model=List[EmployeeOut])
def list_employees(
    department: Optional[str] = None,
    availability: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve all employees with dynamic workload calculation and filters."""
    recalculate_all_workloads(db)
    query = db.query(Employee)

    if department:
        query = query.filter(Employee.department.ilike(f"%{department}%"))
    if availability:
        query = query.filter(Employee.availability_status == availability)
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.name.ilike(search_term)) |
            (Employee.email.ilike(search_term)) |
            (Employee.employee_code.ilike(search_term)) |
            (Employee.role_title.ilike(search_term))
        )

    employees = query.order_by(Employee.id.asc()).all()
    return [enrich_employee(e) for e in employees]


@router.get("/{id}", response_model=EmployeeOut)
def get_employee(id: int, db: Session = Depends(get_db)):
    """Retrieve a single employee by ID."""
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    recalculate_employee_workload(db, emp.id)
    return enrich_employee(emp)


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(emp_data: EmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee and optional default user account."""
    existing = db.query(Employee).filter(Employee.email == emp_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee with this email already exists.")

    count = db.query(Employee).count() + 1
    emp_code = emp_data.employee_code or f"EMP-{count:03d}"

    emp = Employee(
        employee_code=emp_code,
        name=emp_data.name,
        email=emp_data.email,
        department=emp_data.department,
        role_title=emp_data.role_title,
        skills=emp_data.skills,
        experience_years=emp_data.experience_years,
        certifications=emp_data.certifications,
        location=emp_data.location,
        availability_status=emp_data.availability_status,
        daily_capacity=emp_data.daily_capacity,
        performance_score=emp_data.performance_score,
        is_active=emp_data.is_active
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    # Automatically create user login for employee if not exists
    user_existing = db.query(User).filter(User.email == emp.email).first()
    if not user_existing:
        new_user = User(
            email=emp.email,
            name=emp.name,
            hashed_password=hash_password("employee123"),
            role="employee",
            employee_id=emp.id
        )
        db.add(new_user)
        db.commit()

    create_notification(
        db=db,
        title="New Employee Onboarded",
        message=f"{emp.name} ({emp.role_title}) added to {emp.department} team.",
        type="info"
    )

    return enrich_employee(emp)


@router.put("/{id}", response_model=EmployeeOut)
def update_employee(id: int, emp_data: EmployeeUpdate, db: Session = Depends(get_db)):
    """Update employee details (skills, availability, experience, location, capacity, etc.)."""
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    old_status = emp.availability_status
    update_dict = emp_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(emp, key, value)

    db.commit()
    recalculate_employee_workload(db, emp.id)
    db.refresh(emp)

    # If availability changed to Unavailable, alert manager
    if "availability_status" in update_dict and update_dict["availability_status"] != old_status:
        create_notification(
            db=db,
            title="Availability Status Updated",
            message=f"{emp.name} availability status changed to '{emp.availability_status}'.",
            type="warning" if emp.availability_status != "Available" else "info"
        )

    return enrich_employee(emp)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(id: int, db: Session = Depends(get_db)):
    """Delete an employee and unassign their tasks."""
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Unassign any active tasks
    tasks = db.query(Task).filter(Task.assigned_employee_id == id).all()
    for t in tasks:
        t.assigned_employee_id = None
        t.status = "Unassigned"

    db.delete(emp)
    db.commit()
    return None
