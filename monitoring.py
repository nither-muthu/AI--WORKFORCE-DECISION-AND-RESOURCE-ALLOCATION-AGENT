"""
Monitoring & Simulation Routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import MonitoringEvent
from backend.app.schemas.schemas import SimulateEventRequest, MonitoringEventOut
from backend.app.services.reallocation_service import simulate_dynamic_event

router = APIRouter(prefix="/api/events", tags=["Monitoring & Simulation"])


@router.get("", response_model=List[MonitoringEventOut])
def get_events(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve event stream timeline."""
    return db.query(MonitoringEvent).order_by(MonitoringEvent.id.desc()).limit(limit).all()


@router.post("/simulate")
def simulate_event_endpoint(req: SimulateEventRequest, db: Session = Depends(get_db)):
    """
    Simulate real-time workforce disruption event for hackathon live demonstrations:
    - EMPLOYEE_UNAVAILABLE
    - NEW_CRITICAL_TASK
    - WORKLOAD_SPIKE
    - TASK_COMPLETED
    - DEADLINE_CHANGED
    """
    try:
        result = simulate_dynamic_event(
            db=db,
            event_type=req.event_type,
            target_id=req.target_id,
            payload=req.payload
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event simulation failed: {str(e)}")
