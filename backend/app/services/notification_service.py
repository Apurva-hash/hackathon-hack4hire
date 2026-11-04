"""Notification service — create and manage in-app notifications.

All writes use the provided session; the caller is responsible for committing.
Push / SMS / email adapters can be plugged in by extending `notify()`.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification, NotificationType, User, UserRole
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)


def notify(
    db: Session,
    user_id: str,
    notif_type: NotificationType,
    title: str,
    body: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> Notification:
    """Create an in-app notification for a single user.

    Does NOT commit — the caller must commit when ready.

    Args:
        db: Active SQLAlchemy session.
        user_id: Primary key of the target ``User``.
        notif_type: Notification type enum value.
        title: Short notification title (shown in badges).
        body: Longer message body.
        entity_type: Optional string identifying the related model (e.g. ``"service_request"``).
        entity_id: Optional PK of the related entity.

    Returns:
        The un-committed ``Notification`` instance.
    """
    notif = Notification(
        id=generate_uuid(),
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(notif)
    logger.debug("Notification queued: user=%s type=%s title=%r", user_id, notif_type, title)
    return notif


def notify_admins(
    db: Session,
    notif_type: NotificationType,
    title: str,
    body: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> list[Notification]:
    """Create the same notification for every active admin user.

    Does NOT commit — the caller must commit when ready.

    Returns:
        List of un-committed ``Notification`` instances.
    """
    admins = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.is_active == True)  # noqa: E712
        .all()
    )
    notifications: list[Notification] = []
    for admin in admins:
        n = notify(db, admin.id, notif_type, title, body, entity_type, entity_id)
        notifications.append(n)
    return notifications


def mark_read(db: Session, notification_id: str, user_id: str) -> Notification:
    """Mark a single notification as read.

    Raises:
        ValueError: If the notification does not exist or belongs to another user.
    """
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if notif is None:
        raise ValueError(f"Notification {notification_id!r} not found for user {user_id!r}.")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

