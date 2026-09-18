"""
Notification Service: Dispatches in-app alerts and notifications.
"""

from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Notification


def create_notification(
    db: Session,
    title: str,
    message: str,
    type: str = "info",  # info, warning, critical, success
    user_id: Optional[int] = None,
    recipient_role: Optional[str] = "all"
) -> Notification:
    """Create and persist an in-app notification."""
    notif = Notification(
        user_id=user_id,
        recipient_role=recipient_role,
        title=title,
        message=message,
        type=type,
        is_read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
