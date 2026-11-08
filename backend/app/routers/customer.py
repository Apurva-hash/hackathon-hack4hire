"""Customer-facing API router.

All endpoints require a valid JWT with role=customer.
Prefix: /api/customer
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field, confloat
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_customer
from app.models import (
    User, Customer, TechnicianProfile, ServiceCategory, ServiceRequest,
    JobOffer, TechnicianLocation, Rating, Notification,
    RequestStatus, RequestUrgency, OfferStatus, NotificationType,
)
from app.models.base import generate_uuid
from app.services.matching_service import dispatch
from app.services.sla_service import compute_deadlines
from app.services.notification_service import notify, mark_read
from app.utils.geo import haversine_km, eta_minutes

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Customer"])


# ── Schema helpers ────────────────────────────────────────────────────────────

class AddressBody(BaseModel):
    label: str
    address: str
    lat: float
    lng: float


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class BookingCreate(BaseModel):
    category_id: str
    description: Optional[str] = None
    address: str
    lat: float
    lng: float
    urgency: RequestUrgency = RequestUrgency.NORMAL
    preferred_time_start: Optional[datetime] = None
    preferred_time_end: Optional[datetime] = None
    sla_tier_id: Optional[str] = None


class RatingCreate(BaseModel):
    score: float = Field(..., ge=1.0, le=5.0)
    feedback_text: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_customer(db: Session, user: User) -> Customer:
    c = user.customer_profile
    if not c:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return c


def _sr_dict(sr: ServiceRequest, include_tech: bool = False) -> dict:
    """Serialise a ServiceRequest to a safe dict."""
    d = {
        "id": sr.id,
        "status": sr.status.value if sr.status else None,
        "urgency": sr.urgency.value if sr.urgency else None,
        "category_id": sr.category_id,
        "category_name": sr.category.name if sr.category else None,
        "description": sr.description,
        "address": sr.address,
        "lat": sr.lat,
        "lng": sr.lng,
        "estimated_price": sr.estimated_price,
        "sla_response_deadline": sr.sla_response_deadline.isoformat() if sr.sla_response_deadline else None,
        "sla_resolution_deadline": sr.sla_resolution_deadline.isoformat() if sr.sla_resolution_deadline else None,
        "sla_response_met": sr.sla_response_met,
        "sla_resolution_met": sr.sla_resolution_met,
        "preferred_time_start": sr.preferred_time_start.isoformat() if sr.preferred_time_start else None,
        "preferred_time_end": sr.preferred_time_end.isoformat() if sr.preferred_time_end else None,
        "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
        "completion_notes": sr.completion_notes,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
    }
    if include_tech and sr.assigned_technician:
        t = sr.assigned_technician
        d["assigned_technician"] = {
            "id": t.id,
            "name": t.name,
            "phone": t.phone,
            "avg_rating": t.avg_rating,
            "certification_level": t.certification_level,
        }
    return d


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    c = _get_customer(db, current_user)
    return {
        "id": c.id,
        "user_id": c.user_id,
        "email": current_user.email,
        "name": c.name,
        "phone": c.phone,
        "avg_rating": c.avg_rating,
        "total_bookings": c.total_bookings,
        "saved_addresses": c.saved_addresses or [],
    }


@router.patch("/profile")
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    if body.name is not None:
        c.name = body.name
    if body.phone is not None:
        c.phone = body.phone
    db.commit()
    db.refresh(c)
    return {"message": "Profile updated", "name": c.name, "phone": c.phone}


# ── Addresses ─────────────────────────────────────────────────────────────────

@router.get("/addresses")
def list_addresses(current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    c = _get_customer(db, current_user)
    return {"addresses": c.saved_addresses or []}


@router.post("/addresses", status_code=201)
def add_address(
    body: AddressBody,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    addresses = list(c.saved_addresses or [])
    addresses.append(body.dict())
    c.saved_addresses = addresses
    db.commit()
    return {"message": "Address saved", "addresses": c.saved_addresses}


@router.delete("/addresses/{index}", status_code=200)
def delete_address(
    index: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    addresses = list(c.saved_addresses or [])
    if index < 0 or index >= len(addresses):
        raise HTTPException(status_code=404, detail="Address index out of range")
    addresses.pop(index)
    c.saved_addresses = addresses
    db.commit()
    return {"message": "Address deleted", "addresses": c.saved_addresses}


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_customer)):
    cats = db.query(ServiceCategory).filter(ServiceCategory.is_active == True).all()  # noqa: E712
    if not cats:
        try:
            from app.seed.v2_seed import seed
            seed()
            cats = db.query(ServiceCategory).filter(ServiceCategory.is_active == True).all()  # noqa: E712
        except Exception as e:
            logger.warning("Auto-seed categories failed: %s", e)
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "icon": c.icon,
            "price_per_minute": c.price_per_minute,
            "required_certification_level": c.required_certification_level,
        }
        for c in cats
    ]


# ── Nearby technicians ────────────────────────────────────────────────────────

@router.get("/nearby-technicians")
def nearby_technicians(
    lat: float = Query(..., description="Customer latitude"),
    lng: float = Query(..., description="Customer longitude"),
    category_id: Optional[str] = Query(None),
    radius_km: float = Query(20.0, le=100.0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_customer),
):
    """Find available technicians nearby, sorted nearest-first (Uber-style)."""
    q = db.query(TechnicianProfile).filter(
        TechnicianProfile.is_online == True,       # noqa: E712
        TechnicianProfile.is_approved == True,     # noqa: E712
        TechnicianProfile.is_suspended == False,   # noqa: E712
        TechnicianProfile.lat.isnot(None),
        TechnicianProfile.lng.isnot(None),
    )

    # Optional skill filter via category
    if category_id:
        cat = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if cat and cat.skill_id:
            # Only include techs linked to legacy Technician with this skill
            q = q.filter(TechnicianProfile.technician_id.isnot(None))

    techs = q.all()
    results = []
    for t in techs:
        dist = haversine_km(lat, lng, t.lat, t.lng)
        if dist > radius_km:
            continue
        # Skill check
        if category_id and cat and cat.skill_id:
            if t.technician is None:
                continue
            if cat.skill_id not in {s.id for s in t.technician.skills}:
                continue
        eta = eta_minutes(dist)
        results.append({
            "id": t.id,
            "name": t.name,
            "avg_rating": t.avg_rating,
            "certification_level": t.certification_level,
            "distance_km": round(dist, 2),
            "eta_minutes": eta,
        })

    results.sort(key=lambda x: x["distance_km"])
    return {"count": len(results), "technicians": results}


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.post("/bookings", status_code=201)
def create_booking(
    body: BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)

    # Validate category
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == body.category_id, ServiceCategory.is_active == True).first()  # noqa: E712
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found or inactive")

    sr = ServiceRequest(
        id=generate_uuid(),
        customer_id=c.id,
        category_id=body.category_id,
        sla_tier_id=body.sla_tier_id,
        description=body.description,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        urgency=body.urgency,
        preferred_time_start=body.preferred_time_start,
        preferred_time_end=body.preferred_time_end,
        status=RequestStatus.REQUESTED,
        offer_attempt=0,
        created_at=datetime.utcnow(),
    )
    db.add(sr)
    c.total_bookings = (c.total_bookings or 0) + 1
    db.commit()
    db.refresh(sr)

    # Compute SLA deadlines synchronously
    compute_deadlines(db, sr)

    # Notify customer
    notify(
        db, current_user.id, NotificationType.STATUS_CHANGED,
        "Booking Received",
        f"Your {cat.name} request has been received. Finding a technician...",
        entity_type="service_request", entity_id=sr.id,
    )
    db.commit()

    # Trigger dispatch in background
    background_tasks.add_task(_dispatch_safely, sr.id)

    return {
        "message": "Booking created. Matching technicians...",
        "booking_id": sr.id,
        "status": sr.status.value,
        "sla_response_deadline": sr.sla_response_deadline.isoformat() if sr.sla_response_deadline else None,
        "sla_resolution_deadline": sr.sla_resolution_deadline.isoformat() if sr.sla_resolution_deadline else None,
    }


def _dispatch_safely(request_id: str):
    """Run dispatch in a background task with its own DB session."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        dispatch(db, request_id)
    except Exception as exc:
        logger.error("Background dispatch failed for %s: %s", request_id, exc)
    finally:
        db.close()


@router.get("/bookings")
def list_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    q = db.query(ServiceRequest).filter(ServiceRequest.customer_id == c.id)
    if status_filter:
        q = q.filter(ServiceRequest.status == status_filter)
    total = q.count()
    items = q.order_by(ServiceRequest.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "bookings": [_sr_dict(sr) for sr in items],
    }


@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == booking_id,
        ServiceRequest.customer_id == c.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _sr_dict(sr, include_tech=True)


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == booking_id,
        ServiceRequest.customer_id == c.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Booking not found")

    non_cancellable = {RequestStatus.COMPLETED, RequestStatus.CANCELLED, RequestStatus.IN_PROGRESS}
    if sr.status in non_cancellable:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a booking with status '{sr.status.value}'")

    sr.status = RequestStatus.CANCELLED
    # Expire any pending offers
    for offer in sr.offers:
        if offer.status == OfferStatus.PENDING:
            offer.status = OfferStatus.EXPIRED

    notify(
        db, current_user.id, NotificationType.STATUS_CHANGED,
        "Booking Cancelled", f"Your booking #{booking_id[:8]} has been cancelled.",
        entity_type="service_request", entity_id=sr.id,
    )
    db.commit()
    return {"message": "Booking cancelled", "booking_id": booking_id}


@router.post("/bookings/{booking_id}/rate", status_code=201)
def rate_booking(
    booking_id: str,
    body: RatingCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == booking_id,
        ServiceRequest.customer_id == c.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Booking not found")
    if sr.status != RequestStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Can only rate completed bookings")
    if sr.rating:
        raise HTTPException(status_code=409, detail="Booking already rated")
    if not sr.assigned_technician_id:
        raise HTTPException(status_code=409, detail="No technician assigned to this booking")

    rating = Rating(
        id=generate_uuid(),
        service_request_id=sr.id,
        customer_id=c.id,
        technician_profile_id=sr.assigned_technician_id,
        score=body.score,
        feedback_text=body.feedback_text,
        created_at=datetime.utcnow(),
    )
    db.add(rating)

    # Recalculate technician's avg rating
    tech = sr.assigned_technician
    if tech:
        all_ratings = db.query(Rating).filter(Rating.technician_profile_id == tech.id).all()
        scores = [r.score for r in all_ratings] + [body.score]
        tech.avg_rating = round(sum(scores) / len(scores), 2)

    db.commit()
    return {"message": "Rating submitted", "rating_id": rating.id, "score": body.score}


# ── Technician location (for tracking) ───────────────────────────────────────

@router.get("/bookings/{booking_id}/technician-location")
def technician_location(
    booking_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    c = _get_customer(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == booking_id,
        ServiceRequest.customer_id == c.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not sr.assigned_technician_id:
        raise HTTPException(status_code=404, detail="No technician assigned yet")

    loc = db.query(TechnicianLocation).filter(
        TechnicianLocation.technician_profile_id == sr.assigned_technician_id
    ).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Technician location not available")

    dist = haversine_km(sr.lat, sr.lng, loc.lat, loc.lng)
    return {
        "technician_id": sr.assigned_technician_id,
        "lat": loc.lat,
        "lng": loc.lng,
        "updated_at": loc.updated_at.isoformat() if loc.updated_at else None,
        "distance_to_job_km": round(dist, 2),
        "eta_minutes": eta_minutes(dist),
    }


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "notifications": [
            {
                "id": n.id,
                "type": n.type.value,
                "title": n.title,
                "body": n.body,
                "is_read": n.is_read,
                "entity_type": n.entity_type,
                "entity_id": n.entity_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        mark_read(db, notification_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Marked as read"}

