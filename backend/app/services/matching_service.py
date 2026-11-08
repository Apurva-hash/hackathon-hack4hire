"""Matching and dispatch engine for DispatchGrid v2.

This module implements the full lifecycle of technician dispatch:
candidate scoring, offer creation, acceptance/rejection handling,
and automatic escalation when no suitable technician can be found.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ServiceRequest,
    JobOffer,
    TechnicianProfile,
    MatchingConfig,
    Notification,
    SLATier,
    RequestStatus,
    RequestUrgency,
    OfferStatus,
    NotificationType,
    User,
    UserRole,
)
from app.utils.geo import haversine_km

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_config(db: Session) -> MatchingConfig:
    """Return the singleton MatchingConfig row, creating a default if absent."""
    config = db.query(MatchingConfig).first()
    if config is None:
        logger.warning("No MatchingConfig found – using ORM defaults.")
        config = MatchingConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _count_active_jobs(db: Session, tech_id: str) -> int:
    """Count active (non-terminal) service requests assigned to a technician."""
    terminal = {
        RequestStatus.COMPLETED,
        RequestStatus.CANCELLED,
        RequestStatus.ESCALATED,
    }
    return (
        db.query(func.count(ServiceRequest.id))
        .filter(
            ServiceRequest.assigned_technician_id == tech_id,
            ServiceRequest.status.notin_([s.value for s in terminal]),
        )
        .scalar()
        or 0
    )


def _notify_admins(
    db: Session,
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_type: str = "service_request",
    entity_id: Optional[str] = None,
) -> None:
    """Create in-app notifications for every active admin user."""
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
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(notif)


# ---------------------------------------------------------------------------
# 1. score_technician
# ---------------------------------------------------------------------------

def score_technician(
    tech: TechnicianProfile,
    request: ServiceRequest,
    config: MatchingConfig,
    distance_km: float,
    current_active_jobs: int,
) -> float:
    """Compute a composite matching score for a technician against a request.

    All sub-scores are in [0, 1] and weighted by the corresponding
    ``MatchingConfig`` weight.  A higher total score is better.

    Args:
        tech: The technician profile being evaluated.
        request: The service request to be matched.
        config: Singleton matching configuration containing weights.
        distance_km: Pre-computed haversine distance in kilometres.
        current_active_jobs: Number of non-terminal jobs already assigned.

    Returns:
        Weighted composite score (float, unbounded above 0 when weights > 1).
    """
    distance_score = max(0.0, 1.0 - distance_km / 50.0)
    rating_score = tech.avg_rating / 5.0
    workload_score = max(
        0.0,
        1.0 - current_active_jobs / max(tech.max_concurrent_jobs, 1),
    )
    skill_score = tech.certification_level / 5.0
    acceptance_score = tech.acceptance_rate

    total = (
        config.weight_distance * distance_score
        + config.weight_rating * rating_score
        + config.weight_workload * workload_score
        + config.weight_skill_level * skill_score
        + config.weight_acceptance_rate * acceptance_score
    )
    return total


# ---------------------------------------------------------------------------
# 2. find_candidates
# ---------------------------------------------------------------------------

def find_candidates(
    db: Session,
    request: ServiceRequest,
    config: MatchingConfig,
) -> list[tuple[TechnicianProfile, float, float]]:
    """Find and rank eligible technicians for a service request.

    Applies hard eligibility filters first, then computes scores for
    all passing technicians and returns them sorted descending by score.

    Args:
        db: Active SQLAlchemy database session.
        request: The service request requiring a technician.
        config: Singleton matching configuration.

    Returns:
        List of ``(TechnicianProfile, score, distance_km)`` tuples,
        ordered from highest to lowest score.
    """
    is_high_risk = request.urgency in (RequestUrgency.CRITICAL, RequestUrgency.HIGH)

    # Determine effective search radius
    search_radius_km: Optional[float] = (
        config.high_risk_wider_radius_km if is_high_risk else None
    )

    # Load all online, unsuspended technicians
    base_q = (
        db.query(TechnicianProfile)
        .options(
            joinedload(TechnicianProfile.technician),
        )
        .filter(
            TechnicianProfile.is_online == True,       # noqa: E712
            TechnicianProfile.is_suspended == False,   # noqa: E712
        )
    )

    candidates: list[tuple[TechnicianProfile, float, float]] = []

    for tech in base_q.all():
        tech_lat = tech.lat if tech.lat is not None else 12.9716
        tech_lng = tech.lng if tech.lng is not None else 77.5946

        # Compute distance to customer
        dist = haversine_km(tech_lat, tech_lng, request.lat, request.lng)

        # Workload filter: skip fully booked technicians
        active_count = _count_active_jobs(db, tech.id)
        if active_count >= max(tech.max_concurrent_jobs, 1):
            continue

        score = score_technician(tech, request, config, dist, active_count)
        candidates.append((tech, score, dist))

    # Sort descending by score
    candidates.sort(key=lambda t: t[1], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# 3. send_offer
# ---------------------------------------------------------------------------

def send_offer(
    db: Session,
    request: ServiceRequest,
    tech: TechnicianProfile,
    attempt_no: int,
    config: MatchingConfig,
) -> JobOffer:
    """Create a pending ``JobOffer`` and update the service request state.

    Also creates an in-app notification for the technician so they see the
    new offer immediately.

    Args:
        db: Active SQLAlchemy database session.
        request: The service request being dispatched.
        tech: The technician profile to send the offer to.
        attempt_no: Which dispatch attempt this offer belongs to (1-based).
        config: Singleton matching configuration (supplies timeout).

    Returns:
        The newly committed ``JobOffer`` record.
    """
    now = datetime.utcnow()

    # Pick timeout: ensure at least 600 seconds (10 mins) so technicians have time to review and accept
    is_high_risk = request.urgency in (RequestUrgency.CRITICAL, RequestUrgency.HIGH)
    timeout_secs = max(
        config.high_risk_offer_timeout_seconds if is_high_risk else config.offer_timeout_seconds,
        600
    )
    expires_at = now + timedelta(seconds=timeout_secs)

    offer = JobOffer(
        service_request_id=request.id,
        technician_profile_id=tech.id,
        offered_at=now,
        expires_at=expires_at,
        status=OfferStatus.PENDING,
        attempt_number=attempt_no,
    )
    db.add(offer)

    # Update the service request to MATCHING so all candidate techs can see it
    request.status = RequestStatus.MATCHING
    request.offer_attempt = attempt_no

    # Notify the technician
    category_name = request.category.name if request.category else "service"
    notif = Notification(
        user_id=tech.user_id,
        type=NotificationType.OFFER_RECEIVED,
        title="New Job Offer",
        body=f"You have a new {category_name} job near you.",
        entity_type="service_request",
        entity_id=request.id,
    )
    db.add(notif)

    db.commit()
    db.refresh(offer)
    logger.info(
        "Offer sent: request=%s tech=%s attempt=%d expires=%s",
        request.id,
        tech.id,
        attempt_no,
        expires_at.isoformat(),
    )
    return offer


# ---------------------------------------------------------------------------
# 4. dispatch
# ---------------------------------------------------------------------------

def dispatch(db: Session, request_id: str) -> dict:
    """Main dispatch entry-point: find best available tech and send an offer.

    This function is idempotent with respect to already-offered technicians —
    it will skip any technician that has already received an offer for this
    request (in any state: pending, accepted, rejected, or expired).

    Args:
        db: Active SQLAlchemy database session.
        request_id: Primary key of the ``ServiceRequest`` to dispatch.

    Returns:
        A dict with key ``"status"`` set to either ``"offer_sent"``
        (along with ``"technician_id"`` and ``"attempt"``) or ``"escalated"``.

    Raises:
        ValueError: If the ``ServiceRequest`` does not exist.
    """
    request: Optional[ServiceRequest] = (
        db.query(ServiceRequest)
        .options(
            joinedload(ServiceRequest.category),
            joinedload(ServiceRequest.offers),
        )
        .filter(ServiceRequest.id == request_id)
        .first()
    )
    if request is None:
        raise ValueError(f"ServiceRequest {request_id!r} not found.")

    config = _get_config(db)

    # Move to MATCHING state
    request.status = RequestStatus.MATCHING
    db.flush()

    # Collect IDs of technicians that have already been tried
    already_offered_ids: set[str] = {
        offer.technician_profile_id for offer in request.offers
    }

    candidates = find_candidates(db, request, config)

    # Filter out previously-offered technicians
    remaining = [
        (tech, score, dist)
        for tech, score, dist in candidates
        if tech.id not in already_offered_ids
    ]

    if not remaining:
        # No eligible candidates — escalate
        request.status = RequestStatus.ESCALATED
        request.escalated_to_admin = True
        _notify_admins(
            db,
            notification_type=NotificationType.ADMIN_ACTION,
            title="Dispatch Escalated",
            body=(
                f"No technician available for service request {request.id} "
                f"after {request.offer_attempt} attempt(s). Manual assignment required."
            ),
            entity_type="service_request",
            entity_id=request.id,
        )
        db.commit()
        logger.warning("Request %s escalated: no remaining candidates.", request.id)
        return {"status": "escalated"}

    attempt_no = request.offer_attempt + 1
    # Broadcast to all available matching candidate technicians in queue
    dispatched_tech_ids = []
    for cand_tech, cand_score, cand_dist in remaining:
        send_offer(db, request, cand_tech, attempt_no, config)
        dispatched_tech_ids.append(cand_tech.id)

    logger.info(
        "Broadcast dispatched request=%s to %d technicians: %s (attempt=%d)",
        request.id,
        len(dispatched_tech_ids),
        dispatched_tech_ids,
        attempt_no,
    )
    return {
        "status": "offer_sent",
        "technicians_dispatched": len(dispatched_tech_ids),
        "technician_ids": dispatched_tech_ids,
        "attempt": attempt_no,
    }


# ---------------------------------------------------------------------------
# 5. handle_rejection
# ---------------------------------------------------------------------------

def handle_rejection(db: Session, offer_id: str, reason: str) -> dict:
    """Process a technician's rejection of a job offer.

    Updates the offer status, recalculates the technician's acceptance rate,
    and either re-dispatches to the next candidate or escalates.

    Args:
        db: Active SQLAlchemy database session.
        offer_id: Primary key of the ``JobOffer`` being rejected.
        reason: Free-text reason provided by the technician.

    Returns:
        A dict with ``"status"`` set to ``"redispatching"`` or ``"escalated"``.

    Raises:
        ValueError: If the ``JobOffer`` does not exist.
    """
    offer: Optional[JobOffer] = (
        db.query(JobOffer)
        .options(
            joinedload(JobOffer.service_request),
            joinedload(JobOffer.technician_profile),
        )
        .filter(JobOffer.id == offer_id)
        .first()
    )
    if offer is None:
        raise ValueError(f"JobOffer {offer_id!r} not found.")

    # Mark offer as rejected
    offer.status = OfferStatus.REJECTED
    offer.rejection_reason = reason

    # Update acceptance rate for the technician
    tech: TechnicianProfile = offer.technician_profile
    tech.total_jobs_rejected = (tech.total_jobs_rejected or 0) + 1
    total_offers = tech.total_jobs_completed + tech.total_jobs_rejected
    tech.acceptance_rate = (
        tech.total_jobs_completed / total_offers if total_offers > 0 else 0.0
    )

    db.flush()

    request: ServiceRequest = offer.service_request
    config = _get_config(db)

    # Check escalation threshold
    if request.offer_attempt >= config.max_offer_attempts:
        request.status = RequestStatus.ESCALATED
        request.escalated_to_admin = True
        _notify_admins(
            db,
            notification_type=NotificationType.ADMIN_ACTION,
            title="Dispatch Escalated – Max Attempts Reached",
            body=(
                f"Service request {request.id} reached the maximum of "
                f"{config.max_offer_attempts} offer attempt(s) without acceptance."
            ),
            entity_type="service_request",
            entity_id=request.id,
        )
        db.commit()
        logger.warning(
            "Request %s escalated after max offer attempts (%d).",
            request.id,
            config.max_offer_attempts,
        )
        return {"status": "escalated"}

    db.commit()

    # Re-dispatch to the next best candidate
    logger.info(
        "Offer %s rejected by tech %s (reason: %s). Re-dispatching request %s.",
        offer_id,
        tech.id,
        reason,
        request.id,
    )
    result = dispatch(db, request.id)
    if result["status"] == "offer_sent":
        return {"status": "redispatching"}
    return result


# ---------------------------------------------------------------------------
# 6. handle_acceptance
# ---------------------------------------------------------------------------

def handle_acceptance(db: Session, offer_id: str) -> dict:
    """Process a technician's acceptance of a job offer.

    Updates offer and request states, evaluates the SLA response deadline,
    and notifies the customer.

    Args:
        db: Active SQLAlchemy database session.
        offer_id: Primary key of the ``JobOffer`` being accepted.

    Returns:
        A dict with ``"status": "accepted"``.

    Raises:
        ValueError: If the ``JobOffer`` does not exist.
    """
    offer: Optional[JobOffer] = (
        db.query(JobOffer)
        .options(
            joinedload(JobOffer.service_request).joinedload(ServiceRequest.customer),
            joinedload(JobOffer.technician_profile),
        )
        .filter(JobOffer.id == offer_id)
        .first()
    )
    if offer is None:
        raise ValueError(f"JobOffer {offer_id!r} not found.")

    now = datetime.utcnow()

    # Atomic check: has another technician already accepted this request?
    request: ServiceRequest = offer.service_request
    if (
        request.assigned_technician_id is not None
        or request.status in (RequestStatus.ACCEPTED, RequestStatus.EN_ROUTE, RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED)
    ):
        offer.status = OfferStatus.EXPIRED
        db.commit()
        raise ValueError("This booking has already been accepted by another technician.")

    # First technician to accept claims the booking atomically
    tech: TechnicianProfile = offer.technician_profile
    offer.status = OfferStatus.ACCEPTED
    request.status = RequestStatus.ACCEPTED
    request.assigned_technician_id = tech.id

    # Immediately expire and remove this request from all other technicians' queues
    other_offers = db.query(JobOffer).filter(
        JobOffer.service_request_id == request.id,
        JobOffer.id != offer.id,
        JobOffer.status == OfferStatus.PENDING,
    ).all()
    for o_off in other_offers:
        o_off.status = OfferStatus.EXPIRED

    # SLA response compliance
    if request.sla_response_deadline is not None:
        request.sla_response_met = now <= request.sla_response_deadline
    else:
        request.sla_response_met = True  # No deadline set → treat as met

    # Notify the customer
    customer = request.customer
    if customer is not None:
        notif = Notification(
            user_id=customer.user_id,
            type=NotificationType.OFFER_ACCEPTED,
            title="Technician On The Way!",
            body=f"Your technician {tech.name} has accepted your request.",
            entity_type="service_request",
            entity_id=request.id,
        )
        db.add(notif)

    db.commit()
    logger.info(
        "Offer %s accepted by tech %s for request %s (SLA met=%s).",
        offer_id,
        tech.id,
        request.id,
        request.sla_response_met,
    )
    return {"status": "accepted"}
