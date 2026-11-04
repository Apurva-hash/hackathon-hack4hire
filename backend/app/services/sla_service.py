"""SLA deadline computation, monitoring, and escalation service.

This module provides:
- Deadline computation at booking time (``compute_deadlines``).
- A periodic background check that flags at-risk and breached requests
  (``check_sla_compliance``), intended to be called by APScheduler every 2 min.
- Offer expiry processing (``expire_offers``), intended to be called every 30 s.
- Aggregate SLA statistics (``get_sla_stats``).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ServiceRequest,
    JobOffer,
    SLATier,
    SLAEvent,
    SLAEventType,
    Notification,
    NotificationType,
    User,
    UserRole,
    RequestStatus,
    OfferStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal constants and helpers
# ---------------------------------------------------------------------------

#: Statuses considered terminal — excluded from active monitoring.
_TERMINAL_STATUSES: list[str] = [
    RequestStatus.COMPLETED.value,
    RequestStatus.CANCELLED.value,
    RequestStatus.ESCALATED.value,
]

#: Percentage of response deadline that triggers an AT_RISK event.
_AT_RISK_THRESHOLD = 0.80


def _notify_admins(
    db: Session,
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_id: Optional[str] = None,
) -> None:
    """Create Notification records for every active admin user.

    Args:
        db: Active SQLAlchemy session.
        notification_type: Enum value for the notification type column.
        title: Short notification title.
        body: Longer notification body text.
        entity_id: Optional FK to attach to the notification (service_request id).
    """
    admin_users = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.is_active == True)  # noqa: E712
        .all()
    )
    for admin in admin_users:
        notif = Notification(
            user_id=admin.id,
            type=notification_type,
            title=title,
            body=body,
            entity_type="service_request",
            entity_id=entity_id,
        )
        db.add(notif)


def _create_sla_event(
    db: Session,
    request: ServiceRequest,
    event_type: SLAEventType,
    message: str,
) -> SLAEvent:
    """Append a new SLAEvent to the audit trail without committing.

    Args:
        db: Active SQLAlchemy session.
        request: The service request that the event belongs to.
        event_type: Enum value (AT_RISK, BREACHED, RESOLVED, ESCALATED).
        message: Human-readable description of the event.

    Returns:
        The un-committed ``SLAEvent`` instance (already added to the session).
    """
    event = SLAEvent(
        service_request_id=request.id,
        event_type=event_type,
        message=message,
        occurred_at=datetime.utcnow(),
    )
    db.add(event)
    return event


def _get_default_sla_tier(db: Session) -> Optional[SLATier]:
    """Return the default SLA tier (is_default=True), or the lowest-priority one.

    Args:
        db: Active SQLAlchemy session.

    Returns:
        A ``SLATier`` instance, or ``None`` if the table is empty.
    """
    tier = db.query(SLATier).filter(SLATier.is_default == True).first()  # noqa: E712
    if tier is None:
        tier = db.query(SLATier).order_by(SLATier.priority_level.desc()).first()
    return tier


# ---------------------------------------------------------------------------
# 1. compute_deadlines
# ---------------------------------------------------------------------------

def compute_deadlines(db: Session, request: ServiceRequest) -> ServiceRequest:
    """Compute and persist SLA response / resolution deadlines for a request.

    Uses the SLA tier linked to the request (``request.sla_tier_id``), or the
    default / lowest-priority tier when none is set.

    Args:
        db: Active SQLAlchemy session.
        request: The ``ServiceRequest`` to annotate with deadlines.

    Returns:
        The updated and committed ``ServiceRequest`` instance.
    """
    # Resolve tier
    tier: Optional[SLATier] = None
    if request.sla_tier_id:
        tier = db.query(SLATier).filter(SLATier.id == request.sla_tier_id).first()

    if tier is None:
        tier = _get_default_sla_tier(db)

    if tier is None:
        logger.warning(
            "No SLATier found for request %s; deadlines will not be set.", request.id
        )
        return request

    base_time: datetime = request.created_at or datetime.utcnow()

    request.sla_response_deadline = base_time + timedelta(
        minutes=tier.response_time_minutes
    )
    request.sla_resolution_deadline = base_time + timedelta(
        minutes=tier.resolution_time_minutes
    )

    db.commit()
    db.refresh(request)
    logger.debug(
        "SLA deadlines set for request %s: response=%s resolution=%s",
        request.id,
        request.sla_response_deadline.isoformat(),
        request.sla_resolution_deadline.isoformat(),
    )
    return request


# ---------------------------------------------------------------------------
# 2. check_sla_compliance
# ---------------------------------------------------------------------------

def check_sla_compliance(db: Session) -> dict:
    """Periodic SLA audit — flags at-risk and breached requests.

    Intended to be called by APScheduler every **2 minutes**.

    Logic per active request:

    1. **Breached response**: past ``sla_response_deadline`` and still not
       ACCEPTED → mark ``sla_response_met=False``, create BREACHED event,
       notify admins.
    2. **Breached resolution**: past ``sla_resolution_deadline`` and still not
       COMPLETED → mark ``sla_resolution_met=False``, create BREACHED event,
       notify admins, re-dispatch via ``dispatch()``.
    3. **At-risk response**: ≥80 % of response window elapsed but not yet
       ACCEPTED → create AT_RISK event, re-dispatch.

    Args:
        db: Active SQLAlchemy session.

    Returns:
        ``{"checked": int, "at_risk": int, "breached": int}``
    """
    # Import here to avoid circular imports (matching_service → sla_service loop)
    from app.services.matching_service import dispatch  # noqa: PLC0415

    now = datetime.utcnow()
    active_requests: list[ServiceRequest] = (
        db.query(ServiceRequest)
        .filter(ServiceRequest.status.notin_(_TERMINAL_STATUSES))
        .all()
    )

    checked = 0
    at_risk_count = 0
    breached_count = 0

    for request in active_requests:
        checked += 1
        is_accepted = request.status in (
            RequestStatus.ACCEPTED,
            RequestStatus.EN_ROUTE,
            RequestStatus.IN_PROGRESS,
        )
        is_completed = request.status == RequestStatus.COMPLETED

        # ── Response deadline breach ─────────────────────────────────────────
        if (
            not is_accepted
            and request.sla_response_deadline is not None
            and now > request.sla_response_deadline
            and request.sla_response_met is not False  # avoid duplicate events
        ):
            request.sla_response_met = False
            _create_sla_event(
                db,
                request,
                SLAEventType.BREACHED,
                f"SLA response deadline breached at {now.isoformat()}.",
            )
            _notify_admins(
                db,
                NotificationType.SLA_BREACHED,
                "SLA Response Breached",
                f"Request {request.id} has exceeded its response SLA deadline.",
                entity_id=request.id,
            )
            breached_count += 1
            logger.warning("SLA response breached: request=%s", request.id)

        # ── Resolution deadline breach ───────────────────────────────────────
        if (
            not is_completed
            and request.sla_resolution_deadline is not None
            and now > request.sla_resolution_deadline
            and request.sla_resolution_met is not False  # avoid duplicate events
        ):
            request.sla_resolution_met = False
            _create_sla_event(
                db,
                request,
                SLAEventType.BREACHED,
                f"SLA resolution deadline breached at {now.isoformat()}.",
            )
            _notify_admins(
                db,
                NotificationType.SLA_BREACHED,
                "SLA Resolution Breached",
                f"Request {request.id} has exceeded its resolution SLA deadline.",
                entity_id=request.id,
            )
            breached_count += 1
            logger.warning("SLA resolution breached: request=%s", request.id)

            # Attempt re-dispatch if the request is stuck without a tech
            if not is_accepted:
                try:
                    db.commit()  # flush current changes before dispatch modifies state
                    dispatch(db, request.id)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Re-dispatch failed for breached request %s: %s",
                        request.id,
                        exc,
                    )

        # ── At-risk: 80 % of response window elapsed ─────────────────────────
        if (
            not is_accepted
            and request.sla_response_deadline is not None
            and request.created_at is not None
        ):
            response_window = (
                request.sla_response_deadline - request.created_at
            ).total_seconds()
            elapsed = (now - request.created_at).total_seconds()

            if (
                response_window > 0
                and elapsed >= _AT_RISK_THRESHOLD * response_window
                and now <= request.sla_response_deadline  # not yet breached
            ):
                # Only create AT_RISK event if none already exists for this request
                existing_at_risk = (
                    db.query(SLAEvent)
                    .filter(
                        SLAEvent.service_request_id == request.id,
                        SLAEvent.event_type == SLAEventType.AT_RISK,
                    )
                    .first()
                )
                if existing_at_risk is None:
                    _create_sla_event(
                        db,
                        request,
                        SLAEventType.AT_RISK,
                        (
                            f"Request {request.id} is at risk: "
                            f"{elapsed:.0f}s of {response_window:.0f}s elapsed."
                        ),
                    )
                    _notify_admins(
                        db,
                        NotificationType.SLA_AT_RISK,
                        "SLA At Risk",
                        f"Request {request.id} is approaching its response deadline.",
                        entity_id=request.id,
                    )
                    at_risk_count += 1
                    logger.info("SLA at-risk flagged: request=%s", request.id)

                    # Proactively re-dispatch to try to get someone faster
                    try:
                        db.commit()
                        dispatch(db, request.id)
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Proactive re-dispatch failed for at-risk request %s: %s",
                            request.id,
                            exc,
                        )

    db.commit()
    logger.info(
        "SLA compliance check complete: checked=%d at_risk=%d breached=%d",
        checked,
        at_risk_count,
        breached_count,
    )
    return {"checked": checked, "at_risk": at_risk_count, "breached": breached_count}


# ---------------------------------------------------------------------------
# 3. expire_offers
# ---------------------------------------------------------------------------

def expire_offers(db: Session) -> int:
    """Expire pending job offers whose timeout has passed and re-dispatch.

    Intended to be called by APScheduler every **30 seconds**.

    For each expired offer the function:
    1. Sets ``offer.status = expired``.
    2. Calls ``dispatch()`` to offer the job to the next best technician.

    Args:
        db: Active SQLAlchemy session.

    Returns:
        Count of offers that were expired in this run.
    """
    from app.services.matching_service import dispatch  # noqa: PLC0415

    now = datetime.utcnow()
    expired_offers: list[JobOffer] = (
        db.query(JobOffer)
        .filter(
            JobOffer.status == OfferStatus.PENDING,
            JobOffer.expires_at <= now,
        )
        .all()
    )

    count = 0
    for offer in expired_offers:
        offer.status = OfferStatus.EXPIRED
        count += 1
        logger.info(
            "Offer %s expired (tech=%s, request=%s).",
            offer.id,
            offer.technician_profile_id,
            offer.service_request_id,
        )

    if count:
        db.commit()

        # Re-dispatch each affected request after flushing expiry changes
        seen_request_ids: set[str] = set()
        for offer in expired_offers:
            if offer.service_request_id in seen_request_ids:
                continue
            seen_request_ids.add(offer.service_request_id)
            try:
                dispatch(db, offer.service_request_id)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Re-dispatch after expiry failed for request %s: %s",
                    offer.service_request_id,
                    exc,
                )

    logger.info("expire_offers: %d offer(s) expired.", count)
    return count


# ---------------------------------------------------------------------------
# 4. get_sla_stats
# ---------------------------------------------------------------------------

def get_sla_stats(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Compute aggregate SLA compliance statistics, optionally within a date range.

    Evaluates only service requests where ``sla_response_met`` or
    ``sla_resolution_met`` has been recorded (i.e., evaluated requests).

    Args:
        db: Active SQLAlchemy session.
        date_from: Optional inclusive lower bound on ``created_at``.
        date_to: Optional inclusive upper bound on ``created_at``.

    Returns:
        A dict with keys:
        - ``compliance_pct`` (float): Percentage of requests that met both deadlines.
        - ``at_risk_count`` (int): Requests with at least one AT_RISK SLA event.
        - ``breached_count`` (int): Requests with at least one BREACHED SLA event.
        - ``avg_response_minutes`` (float | None): Mean actual response time.
        - ``avg_resolution_minutes`` (float | None): Mean actual resolution time.
        - ``total_evaluated`` (int): Requests where SLA has been evaluated.
    """
    # Base query filtered by date range
    base_q = db.query(ServiceRequest)
    if date_from is not None:
        base_q = base_q.filter(ServiceRequest.created_at >= date_from)
    if date_to is not None:
        base_q = base_q.filter(ServiceRequest.created_at <= date_to)

    # Requests where at least one SLA dimension has been evaluated
    evaluated_q = base_q.filter(
        (ServiceRequest.sla_response_met.isnot(None))
        | (ServiceRequest.sla_resolution_met.isnot(None))
    )
    total_evaluated: int = evaluated_q.count()

    # Compliance = both response AND resolution met (or only one set and it's True)
    if total_evaluated == 0:
        return {
            "compliance_pct": 0.0,
            "at_risk_count": 0,
            "breached_count": 0,
            "avg_response_minutes": None,
            "avg_resolution_minutes": None,
            "total_evaluated": 0,
        }

    compliant_count: int = evaluated_q.filter(
        and_(
            ServiceRequest.sla_response_met != False,    # noqa: E712
            ServiceRequest.sla_resolution_met != False,  # noqa: E712
        )
    ).count()
    compliance_pct = round((compliant_count / total_evaluated) * 100.0, 2)

    # AT_RISK count: distinct requests with at least one AT_RISK event
    at_risk_subq = (
        db.query(SLAEvent.service_request_id)
        .filter(SLAEvent.event_type == SLAEventType.AT_RISK)
        .distinct()
        .subquery()
    )
    at_risk_count: int = (
        base_q.filter(ServiceRequest.id.in_(at_risk_subq)).count()
    )

    # BREACHED count: distinct requests with at least one BREACHED event
    breached_subq = (
        db.query(SLAEvent.service_request_id)
        .filter(SLAEvent.event_type == SLAEventType.BREACHED)
        .distinct()
        .subquery()
    )
    breached_count: int = (
        base_q.filter(ServiceRequest.id.in_(breached_subq)).count()
    )

    # Average actual response time: time from created_at to first ACCEPTED offer
    # We approximate using sla_response_deadline and sla_response_met flag.
    # For a more precise metric we'd need an explicit accepted_at column; absent
    # that, compute the mean gap between created_at and sla_response_deadline
    # (which equals the tier's response_time_minutes).
    # Instead we query JobOffers to find the accepted one and compare timestamps.
    avg_response_minutes: Optional[float] = None
    avg_resolution_minutes: Optional[float] = None

    # Gather requests that have been accepted (have a completed_at or accepted offer)
    accepted_offers = (
        db.query(JobOffer)
        .join(ServiceRequest, JobOffer.service_request_id == ServiceRequest.id)
        .filter(JobOffer.status == OfferStatus.ACCEPTED)
        .all()
    )

    response_deltas: list[float] = []
    for offer in accepted_offers:
        req = offer.service_request
        if req and req.created_at and offer.offered_at:
            delta_minutes = (offer.offered_at - req.created_at).total_seconds() / 60.0
            response_deltas.append(delta_minutes)

    if response_deltas:
        avg_response_minutes = round(sum(response_deltas) / len(response_deltas), 2)

    completed_requests = (
        base_q.filter(
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.completed_at.isnot(None),
        ).all()
    )

    resolution_deltas: list[float] = []
    for req in completed_requests:
        if req.created_at and req.completed_at:
            delta_minutes = (req.completed_at - req.created_at).total_seconds() / 60.0
            resolution_deltas.append(delta_minutes)

    if resolution_deltas:
        avg_resolution_minutes = round(
            sum(resolution_deltas) / len(resolution_deltas), 2
        )

    return {
        "compliance_pct": compliance_pct,
        "at_risk_count": at_risk_count,
        "breached_count": breached_count,
        "avg_response_minutes": avg_response_minutes,
        "avg_resolution_minutes": avg_resolution_minutes,
        "total_evaluated": total_evaluated,
    }
