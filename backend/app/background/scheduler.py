"""APScheduler background jobs for SLA monitoring and offer expiry."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_sla_check():
    """Run SLA compliance check."""
    try:
        from app.database import SessionLocal
        from app.services.sla_service import check_sla_compliance
        db = SessionLocal()
        try:
            result = check_sla_compliance(db)
            if result["at_risk"] > 0 or result["breached"] > 0:
                logger.warning(f"SLA check: {result}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"SLA check error: {e}")


def _run_offer_expiry():
    """Expire timed-out job offers and re-dispatch."""
    try:
        from app.database import SessionLocal
        from app.services.sla_service import expire_offers
        db = SessionLocal()
        try:
            expired = expire_offers(db)
            if expired > 0:
                logger.info(f"Expired {expired} offers, re-dispatching.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Offer expiry error: {e}")


def start_scheduler():
    """Start the background scheduler. Call once on app startup."""
    global _scheduler
    _scheduler = BackgroundScheduler()
    # SLA monitor: every 2 minutes
    _scheduler.add_job(_run_sla_check, IntervalTrigger(minutes=2), id="sla_check", replace_existing=True)
    # Offer expiry: every 30 seconds
    _scheduler.add_job(_run_offer_expiry, IntervalTrigger(seconds=30), id="offer_expiry", replace_existing=True)
    _scheduler.start()
    logger.info("Background scheduler started.")


def stop_scheduler():
    """Stop the background scheduler on app shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")

