"""
Pydantic Validation Schemas for REST API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ================= AUTH SCHEMAS =================
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    employee_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ================= EMPLOYEE SCHEMAS =================
class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str = "Engineering"
    role_title: str = "Software Engineer"
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 3.0
    certifications: List[str] = Field(default_factory=list)
    location: str = "Remote"
    availability_status: str = "Available"
    daily_capacity: float = 8.0
    performance_score: float = 85.0
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    employee_code: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    role_title: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    certifications: Optional[List[str]] = None
    location: Optional[str] = None
    availability_status: Optional[str] = None
    daily_capacity: Optional[float] = None
    performance_score: Optional[float] = None
    is_active: Optional[bool] = None


class EmployeeOut(EmployeeBase):
    id: int
    employee_code: str
    current_workload_hours: float = 0.0
    workload_percentage: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ================= TASK SCHEMAS =================
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    required_skills: List[str] = Field(default_factory=list)
    priority: str = "Medium"  # Critical, High, Medium, Low
    deadline: str
    sla_hours: float = 24.0
    estimated_hours: float = 4.0
    location: str = "Remote"
    department: str = "Engineering"
    status: str = "Unassigned"  # Unassigned, Assigned, In Progress, Completed, Blocked
    assigned_employee_id: Optional[int] = None


class TaskCreate(TaskBase):
    task_code: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None
    sla_hours: Optional[float] = None
    estimated_hours: Optional[float] = None
    location: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    assigned_employee_id: Optional[int] = None


class TaskOut(TaskBase):
    id: int
    task_code: str
    assigned_employee_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ================= ASSIGNMENT & REASSIGNMENT SCHEMAS =================
class AssignTaskRequest(BaseModel):
    task_id: int
    employee_id: int
    reason: Optional[str] = "Manual assignment"
    ai_suitability_score: Optional[float] = None
    predicted_completion_hours: Optional[float] = None


class ReassignTaskRequest(BaseModel):
    task_id: int
    new_employee_id: int
    reason: str
    trigger_event: Optional[str] = "Dynamic Reallocation"
    ai_score: Optional[float] = None
    predicted_completion_hours: Optional[float] = None


class AssignmentOut(BaseModel):
    id: int
    task_id: int
    employee_id: int
    status: str
    ai_suitability_score: float
    predicted_completion_hours: float
    reason_summary: Optional[str] = None
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ================= ML SCHEMAS =================
class MLPredictRequest(BaseModel):
    employee: Dict[str, Any]
    task: Dict[str, Any]


class MLPredictResponse(BaseModel):
    predicted_completion_hours: float
    suitability_score: float
    features: Dict[str, float]


class MLTrainRequest(BaseModel):
    num_samples: Optional[int] = 3500
    noise_level: Optional[float] = 1.0
    skill_weight: Optional[float] = 40.0
    workload_weight: Optional[float] = 20.0
    experience_weight: Optional[float] = 10.0
    custom_records: Optional[List[Dict[str, Any]]] = None


class MLBatchTestRequest(BaseModel):
    employees: List[Dict[str, Any]]
    task: Dict[str, Any]


# ================= OPTIMIZE SCHEMAS =================
class OptimizeRequest(BaseModel):
    task_ids: Optional[List[int]] = None  # None for all unassigned/eligible tasks
    apply_assignments: bool = False       # If true, directly commit assignments to database
    weights: Optional[Dict[str, int]] = None


class AssignmentRecommendation(BaseModel):
    task_id: int
    task_title: str
    task_priority: str
    task_deadline: str
    employee_id: int
    employee_name: str
    employee_department: str
    ai_suitability_score: float
    predicted_completion_hours: float
    workload_before_pct: float
    workload_after_pct: float
    is_reassignment: bool = False
    reasons: List[str]
    summary_explanation: str


class OptimizeResponse(BaseModel):
    status: str
    solver_objective_value: Optional[float] = None
    total_assigned: int
    total_tasks_considered: int
    assignments: List[AssignmentRecommendation]
    unassigned_tasks: List[int]
    message: str


# ================= MONITORING & SIMULATION SCHEMAS =================
class SimulateEventRequest(BaseModel):
    event_type: str  # EMPLOYEE_UNAVAILABLE, NEW_CRITICAL_TASK, WORKLOAD_SPIKE, TASK_COMPLETED, DEADLINE_CHANGED
    target_id: Optional[int] = None  # employee_id or task_id
    payload: Optional[Dict[str, Any]] = None


class MonitoringEventOut(BaseModel):
    id: int
    event_type: str
    title: str
    description: str
    severity: str
    reallocated_count: int
    timestamp: datetime

    class Config:
        from_attributes = True


class AllocationHistoryOut(BaseModel):
    id: int
    task_id: int
    task_code: str
    task_title: str
    previous_employee_id: Optional[int] = None
    previous_employee_name: Optional[str] = None
    new_employee_id: int
    new_employee_name: str
    reason: str
    trigger_event: str
    ai_score: float
    predicted_completion_hours: float
    timestamp: datetime

    class Config:
        from_attributes = True


# ================= NOTIFICATION SCHEMAS =================
class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ================= DASHBOARD SUMMARY SCHEMA =================
class DashboardSummaryOut(BaseModel):
    total_employees: int
    active_employees: int
    total_tasks: int
    unassigned_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    average_workload_pct: float
    sla_at_risk_count: int
    reallocation_count: int
    tasks_by_priority: Dict[str, int]
    tasks_by_status: Dict[str, int]
    workload_distribution: List[Dict[str, Any]]
    skill_distribution: List[Dict[str, Any]]
    recent_events: List[MonitoringEventOut]
    recent_allocations: List[AllocationHistoryOut]
