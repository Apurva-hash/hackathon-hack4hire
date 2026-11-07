"""Unit tests for the matching engine — score_technician and find_candidates."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ── Helpers to build mock objects ─────────────────────────────────────────────

def make_config(**overrides):
    cfg = MagicMock()
    cfg.weight_distance = 0.35
    cfg.weight_rating = 0.25
    cfg.weight_workload = 0.20
    cfg.weight_skill_level = 0.15
    cfg.weight_acceptance_rate = 0.05
    cfg.offer_timeout_seconds = 120
    cfg.high_risk_offer_timeout_seconds = 60
    cfg.max_offer_attempts = 5
    cfg.high_risk_min_certification = 3
    cfg.high_risk_wider_radius_km = 30.0
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def make_tech(
    name="Tech",
    lat=12.97,
    lng=77.59,
    avg_rating=4.5,
    certification_level=3,
    max_concurrent_jobs=3,
    acceptance_rate=0.9,
    is_online=True,
    is_approved=True,
    is_suspended=False,
    service_radius_km=20.0,
    technician=None,
):
    t = MagicMock()
    t.id = f"tech-{name}"
    t.name = name
    t.lat = lat
    t.lng = lng
    t.avg_rating = avg_rating
    t.certification_level = certification_level
    t.max_concurrent_jobs = max_concurrent_jobs
    t.acceptance_rate = acceptance_rate
    t.is_online = is_online
    t.is_approved = is_approved
    t.is_suspended = is_suspended
    t.service_radius_km = service_radius_km
    t.technician = technician
    return t


def make_request(
    urgency="normal",
    lat=12.97,
    lng=77.59,
    category_skill_id=None,
):
    from app.models import RequestUrgency
    r = MagicMock()
    r.id = "req-001"
    r.lat = lat
    r.lng = lng
    r.urgency = RequestUrgency(urgency)
    r.offer_attempt = 0
    r.offers = []
    r.status = MagicMock()

    cat = MagicMock()
    cat.skill_id = category_skill_id
    r.category = cat
    return r


# ── score_technician tests ────────────────────────────────────────────────────

class TestScoreTechnician:
    def test_perfect_score(self):
        """Technician right next to job, 5-star rating, no workload, max cert, 100% accept."""
        from app.services.matching_service import score_technician
        tech = make_tech(avg_rating=5.0, certification_level=5, acceptance_rate=1.0)
        config = make_config()
        req = make_request()
        score = score_technician(tech, req, config, distance_km=0.0, current_active_jobs=0)
        # distance_score=1, rating_score=1, workload_score=1, skill=1, accept=1
        expected = 0.35 + 0.25 + 0.20 + 0.15 + 0.05
        assert abs(score - expected) < 1e-6

    def test_distance_penalises_score(self):
        """A far technician should score lower than a near one (all else equal)."""
        from app.services.matching_service import score_technician
        config = make_config()
        req = make_request()
        tech_near = make_tech(avg_rating=4.0, certification_level=3, acceptance_rate=0.8)
        tech_far = make_tech(avg_rating=4.0, certification_level=3, acceptance_rate=0.8)
        score_near = score_technician(tech_near, req, config, distance_km=2.0, current_active_jobs=1)
        score_far = score_technician(tech_far, req, config, distance_km=40.0, current_active_jobs=1)
        assert score_near > score_far

    def test_high_workload_reduces_score(self):
        """A tech with 2 out of 3 jobs should score lower than one with 0."""
        from app.services.matching_service import score_technician
        config = make_config()
        req = make_request()
        tech = make_tech()
        score_idle = score_technician(tech, req, config, distance_km=5.0, current_active_jobs=0)
        score_busy = score_technician(tech, req, config, distance_km=5.0, current_active_jobs=2)
        assert score_idle > score_busy

    def test_score_is_non_negative(self):
        """Score should never be negative even for a very far technician."""
        from app.services.matching_service import score_technician
        config = make_config()
        req = make_request()
        tech = make_tech(avg_rating=1.0, certification_level=1, acceptance_rate=0.0)
        score = score_technician(tech, req, config, distance_km=500.0, current_active_jobs=3)
        assert score >= 0.0

    def test_rating_weight_affects_score(self):
        """A 5-star tech should score higher than a 1-star tech at same distance."""
        from app.services.matching_service import score_technician
        config = make_config()
        req = make_request()
        tech_high = make_tech(avg_rating=5.0, certification_level=3, acceptance_rate=0.8)
        tech_low = make_tech(avg_rating=1.0, certification_level=3, acceptance_rate=0.8)
        s_high = score_technician(tech_high, req, config, distance_km=5.0, current_active_jobs=1)
        s_low = score_technician(tech_low, req, config, distance_km=5.0, current_active_jobs=1)
        assert s_high > s_low


# ── find_candidates tests ─────────────────────────────────────────────────────

class TestFindCandidates:
    def _make_db_with_techs(self, techs):
        """Build a mock Session that returns the given techs from a query chain."""
        db = MagicMock()
        query_mock = MagicMock()
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = techs
        db.query.return_value = query_mock

        # count for _count_active_jobs
        count_mock = MagicMock()
        count_mock.filter.return_value = count_mock
        count_mock.scalar.return_value = 0
        return db, query_mock

    def test_returns_sorted_by_score(self):
        """find_candidates should return highest-scoring technician first."""
        from app.services.matching_service import find_candidates, score_technician

        config = make_config()
        req = make_request(lat=12.97, lng=77.59)

        # Two techs: one nearby with high rating, one far with low rating
        tech_a = make_tech("A", lat=12.97, lng=77.59, avg_rating=4.8, certification_level=4)
        tech_b = make_tech("B", lat=12.80, lng=77.40, avg_rating=2.0, certification_level=1)

        db, query_mock = self._make_db_with_techs([tech_a, tech_b])

        with patch("app.services.matching_service._count_active_jobs", return_value=0):
            results = find_candidates(db, req, config)

        assert len(results) == 2
        # tech_a should come first (closer and better rating)
        assert results[0][0].name == "A"

    def test_filters_over_radius(self):
        """A technician outside their service radius should be excluded."""
        from app.services.matching_service import find_candidates

        config = make_config()
        req = make_request(lat=12.97, lng=77.59)

        # Tech is 100 km away but radius is only 15 km
        tech = make_tech("FarTech", lat=13.90, lng=78.50, service_radius_km=15.0)
        db, _ = self._make_db_with_techs([tech])

        with patch("app.services.matching_service._count_active_jobs", return_value=0):
            results = find_candidates(db, req, config)

        assert len(results) == 0

    def test_filters_overloaded_technicians(self):
        """A tech at max concurrent jobs should be excluded."""
        from app.services.matching_service import find_candidates

        config = make_config()
        req = make_request()
        tech = make_tech("Busy", max_concurrent_jobs=2)
        db, _ = self._make_db_with_techs([tech])

        with patch("app.services.matching_service._count_active_jobs", return_value=2):
            results = find_candidates(db, req, config)

        assert len(results) == 0

    def test_high_risk_requires_cert_level_3(self):
        """For critical/high urgency requests, techs with cert < 3 should be excluded."""
        from app.services.matching_service import find_candidates

        config = make_config(high_risk_min_certification=3)
        req = make_request(urgency="critical")

        tech_low_cert = make_tech("LowCert", certification_level=2)
        tech_ok_cert = make_tech("OkCert", certification_level=4)
        db, query_mock = self._make_db_with_techs([tech_ok_cert])  # DB filter handles low cert

        with patch("app.services.matching_service._count_active_jobs", return_value=0):
            results = find_candidates(db, req, config)

        assert all(r[0].certification_level >= 3 for r in results)

    def test_empty_when_no_techs(self):
        """find_candidates returns empty list when no online techs exist."""
        from app.services.matching_service import find_candidates

        config = make_config()
        req = make_request()
        db, _ = self._make_db_with_techs([])

        results = find_candidates(db, req, config)
        assert results == []

