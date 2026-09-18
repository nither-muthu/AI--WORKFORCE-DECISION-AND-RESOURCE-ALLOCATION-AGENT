"""
Optimization API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.schemas import OptimizeRequest, OptimizeResponse
from backend.app.services.reallocation_service import run_dynamic_allocation

router = APIRouter(prefix="/api/optimize", tags=["Optimization Engine"])


@router.post("/assign", response_model=OptimizeResponse)
def run_optimization(req: OptimizeRequest, db: Session = Depends(get_db)):
    """
    Execute Google OR-Tools optimization engine to find the globally optimal task allocation
    under hard and soft constraints, using ML suitability and completion time predictions.
    """
    try:
        result = run_dynamic_allocation(
            db=db,
            task_ids=req.task_ids,
            apply_to_db=req.apply_assignments,
            trigger_reason="Optimization Execution",
            weights=req.weights
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")
