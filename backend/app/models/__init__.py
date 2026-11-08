"""Database models for DispatchGrid."""

# ── Phase 1-7: Original models ────────────────────────────────────────────────
from app.models.base import TimestampMixin, generate_uuid
from app.models.skill import Skill
from app.models.service_zone import ServiceZone
from app.models.technician import Technician, TechnicianStatus
from app.models.job import Job, JobPriority, JobStatus
from app.models.assignment import Assignment, AssignmentStatus
from app.models.availability_block import AvailabilityBlock
from app.models.scheduling_run import SchedulingRun, RunStatus, TriggerType
from app.models.scheduling_decision import SchedulingDecision, Feasibility, RejectionReason
from app.models.disruption_event import DisruptionEvent, DisruptionEventType
from app.models.associations import technician_skills, technician_zones, job_skills

# ── Phase 8+: New platform models ────────────────────────────────────────────
from app.models.user import User, Customer, TechnicianProfile, UserRole
from app.models.category import ServiceCategory, MatchingConfig
from app.models.sla import SLATier, SLAEvent, SLAEventType
from app.models.service_request import (
    ServiceRequest, JobOffer, TechnicianLocation,
    RequestStatus, RequestUrgency, OfferStatus,
)
from app.models.rating import Rating, AuditLog
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment, PaymentMethod, PaymentStatus

__all__ = [
    # Base
    "TimestampMixin", "generate_uuid",

    # Phase 1-7 models
    "Skill", "ServiceZone", "Technician", "Job", "Assignment",
    "AvailabilityBlock", "SchedulingRun", "SchedulingDecision",
    "DisruptionEvent",

    # Phase 1-7 enums
    "TechnicianStatus", "JobPriority", "JobStatus", "AssignmentStatus",
    "RunStatus", "TriggerType", "Feasibility", "RejectionReason", "DisruptionEventType",

    # Association tables
    "technician_skills", "technician_zones", "job_skills",

    # Phase 8+ auth & profiles
    "User", "Customer", "TechnicianProfile", "UserRole",

    # Categories & config
    "ServiceCategory", "MatchingConfig",

    # SLA
    "SLATier", "SLAEvent", "SLAEventType",

    # Service requests
    "ServiceRequest", "JobOffer", "TechnicianLocation",
    "RequestStatus", "RequestUrgency", "OfferStatus",

    # Ratings & audit
    "Rating", "AuditLog",

    # Notifications
    "Notification", "NotificationType",

    # Payments & Revenue
    "Payment", "PaymentMethod", "PaymentStatus",
]
