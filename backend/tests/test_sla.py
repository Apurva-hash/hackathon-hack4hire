"""Unit tests for the SLA service — compute_deadlines and get_sla_stats."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_sla_tier(
    response_minutes=60,
    resolution_minutes=240,
    is_default=True,
    priority_level=3,
):
    tier = MagicMock()
    tier.id = "tier-001"
    tier.name = "Normal"
    tier.priority_level = priority_level
    tier.response_time_minutes = response_minutes
    tier.resolution_time_minutes = resolution_minutes
    tier.is_default = is_default
    return tier


def make_request(
    created_at=None,
    sla_tier_id=None,
    status="requested",
):
    req = MagicMock()
    req.id = "req-001"
    req.sla_tier_id = sla_tier_id
    req.created_at = created_at or datetime(2026, 1, 1, 10, 0, 0)
    req.sla_response_deadline = None
    req.sla_resolution_deadline = None
    req.status = status
    req.sla_response_met = None
    req.sla_resolution_met = None
    req.completed_at = None
    return req


def make_db_with_tier(tier):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.return_value = tier
    q.count.return_value = 0
    db.query.return_value = q
    return db


# ── compute_deadlines tests ───────────────────────────────────────────────────

class TestComputeDeadlines:
    def test_sets_response_deadline(self):
        """compute_deadlines should set sla_response_deadline based on tier."""
        from app.services.sla_service import compute_deadlines

        tier = make_sla_tier(response_minutes=60, resolution_minutes=240)
        req = make_request(created_at=datetime(2026, 1, 1, 10, 0, 0))
        db = make_db_with_tier(tier)

        compute_deadlines(db, req)

        expected_response = datetime(2026, 1, 1, 11, 0, 0)  # +60min
        assert req.sla_response_deadline == expected_response

    def test_sets_resolution_deadline(self):
        """compute_deadlines should set sla_resolution_deadline based on tier."""
        from app.services.sla_service import compute_deadlines

        tier = make_sla_tier(response_minutes=60, resolution_minutes=240)
        req = make_request(created_at=datetime(2026, 1, 1, 10, 0, 0))
        db = make_db_with_tier(tier)

        compute_deadlines(db, req)

        expected_resolution = datetime(2026, 1, 1, 14, 0, 0)  # +240min
        assert req.sla_resolution_deadline == expected_resolution

    def test_deadlines_consistent_for_same_inputs(self):
        """Same tier + same created_at must always produce the same deadlines."""
        from app.services.sla_service import compute_deadlines

        tier = make_sla_tier(response_minutes=30, resolution_minutes=120)
        req1 = make_request(created_at=datetime(2026, 6, 15, 9, 0, 0))
        req2 = make_request(created_at=datetime(2026, 6, 15, 9, 0, 0))
        db = make_db_with_tier(tier)

        compute_deadlines(db, req1)
        compute_deadlines(db, req2)

        assert req1.sla_response_deadline == req2.sla_response_deadline
        assert req1.sla_resolution_deadline == req2.sla_resolution_deadline

    def test_no_deadline_when_no_tier(self):
        """If no SLA tier exists, deadlines should remain None."""
        from app.services.sla_service import compute_deadlines

        req = make_request()
        db = make_db_with_tier(None)  # No tier in DB

        result = compute_deadlines(db, req)

        assert req.sla_response_deadline is None
        assert req.sla_resolution_deadline is None

    def test_uses_tier_linked_to_request(self):
        """Request with explicit sla_tier_id should use that tier's deadlines."""
        from app.services.sla_service import compute_deadlines

        specific_tier = make_sla_tier(response_minutes=15, resolution_minutes=60)
        req = make_request(created_at=datetime(2026, 1, 1, 8, 0, 0), sla_tier_id="tier-001")
        db = make_db_with_tier(specific_tier)

        compute_deadlines(db, req)

        assert req.sla_response_deadline == datetime(2026, 1, 1, 8, 15, 0)
        assert req.sla_resolution_deadline == datetime(2026, 1, 1, 9, 0, 0)

    def test_critical_tier_shorter_deadlines(self):
        """A critical tier (15min response) must produce a tighter deadline than normal (60min)."""
        from app.services.sla_service import compute_deadlines

        critical_tier = make_sla_tier(response_minutes=15, resolution_minutes=60)
        normal_tier = make_sla_tier(response_minutes=60, resolution_minutes=240)

        base_time = datetime(2026, 1, 1, 10, 0, 0)
        req_critical = make_request(created_at=base_time)
        req_normal = make_request(created_at=base_time)

        db_critical = make_db_with_tier(critical_tier)
        db_normal = make_db_with_tier(normal_tier)

        compute_deadlines(db_critical, req_critical)
        compute_deadlines(db_normal, req_normal)

        assert req_critical.sla_response_deadline < req_normal.sla_response_deadline
        assert req_critical.sla_resolution_deadline < req_normal.sla_resolution_deadline


# ── get_sla_stats tests ───────────────────────────────────────────────────────

class TestGetSlaStats:
    def test_empty_db_returns_zero_stats(self):
        """When no evaluated requests exist, all stats should be zero/None."""
        from app.services.sla_service import get_sla_stats
        from app.models import ServiceRequest, SLAEvent, JobOffer

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.count.return_value = 0
        q.all.return_value = []
        db.query.return_value = q

        stats = get_sla_stats(db)

        assert stats["total_evaluated"] == 0
        assert stats["compliance_pct"] == 0.0
        assert stats["at_risk_count"] == 0
        assert stats["breached_count"] == 0

    def test_returns_required_keys(self):
        """get_sla_stats should always return the expected set of keys."""
        from app.services.sla_service import get_sla_stats

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.count.return_value = 0
        q.all.return_value = []
        db.query.return_value = q

        stats = get_sla_stats(db)
        required_keys = {
            "compliance_pct", "at_risk_count", "breached_count",
            "avg_response_minutes", "avg_resolution_minutes", "total_evaluated",
        }
        assert required_keys.issubset(stats.keys())

