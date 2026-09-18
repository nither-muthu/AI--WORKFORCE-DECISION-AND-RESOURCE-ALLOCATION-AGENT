"""
Notification Routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Notification
from backend.app.schemas.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut])
def list_notifications(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve all in-app notifications."""
    return db.query(Notification).order_by(Notification.id.desc()).limit(limit).all()


@router.put("/{id}/read", response_model=NotificationOut)
def mark_as_read(id: int, db: Session = Depends(get_db)):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all")
def mark_all_as_read(db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    db.query(Notification).update({Notification.is_read: True})
    db.commit()
    return {"message": "All notifications marked as read."}
