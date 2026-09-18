"""
SQLAlchemy Data Models for Workforce Management Platform
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="employee")  # admin, manager, employee
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    department = Column(String(100), nullable=False)
    role_title = Column(String(100), nullable=False)
    skills = Column(JSON, default=list)  # ["Python", "FastAPI", "React", ...]
    experience_years = Column(Float, default=3.0)
    certifications = Column(JSON, default=list)  # ["AWS Certified", "PMP", ...]
    location = Column(String(100), default="Remote")
    availability_status = Column(String(50), default="Available")  # Available, Unavailable, On Leave, Busy
    daily_capacity = Column(Float, default=8.0)  # hours per day
    current_workload_hours = Column(Float, default=0.0)  # calculated dynamically
    performance_score = Column(Float, default=85.0)  # 0 to 100
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="employee", uselist=False)
    assigned_tasks = relationship("Task", back_populates="assigned_employee")
    assignments = relationship("Assignment", back_populates="employee")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    required_skills = Column(JSON, default=list)  # ["Python", "Machine Learning"]
    priority = Column(String(50), default="Medium")  # Critical, High, Medium, Low
    deadline = Column(String(100), nullable=False)  # ISO string or date
    sla_hours = Column(Float, default=24.0)  # SLA window in hours
    estimated_hours = Column(Float, default=4.0)  # Estimated duration in hours
    location = Column(String(100), default="Remote")
    department = Column(String(100), default="Engineering")
    status = Column(String(50), default="Unassigned")  # Unassigned, Assigned, In Progress, Completed, Blocked
    assigned_employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    assigned_employee = relationship("Employee", back_populates="assigned_tasks")
    assignments = relationship("Assignment", back_populates="task")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="Active")  # Active, Completed, Reassigned
    ai_suitability_score = Column(Float, default=85.0)
    predicted_completion_hours = Column(Float, default=4.0)
    reason_summary = Column(Text, default="")
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments")


class AllocationHistory(Base):
    __tablename__ = "allocation_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    task_code = Column(String(50), nullable=False)
    task_title = Column(String(255), nullable=False)
    previous_employee_id = Column(Integer, nullable=True)
    previous_employee_name = Column(String(255), nullable=True)
    new_employee_id = Column(Integer, nullable=False)
    new_employee_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    trigger_event = Column(String(100), default="Manual Assignment")  # e.g., "Employee Unavailable", "AI Optimization"
    ai_score = Column(Float, default=85.0)
    predicted_completion_hours = Column(Float, default=4.0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="INFO")  # INFO, WARNING, CRITICAL, SUCCESS
    reallocated_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    recipient_role = Column(String(50), nullable=True)  # all, admin, manager, employee
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")  # info, warning, critical, success
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")
