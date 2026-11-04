"""WebSocket and SSE endpoints for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Connection managers ────────────────────────────────────────────────────────

class BookingConnectionManager:
    """Manages WebSocket connections for booking status updates."""
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}  # booking_id -> set of websockets

    async def connect(self, websocket: WebSocket, booking_id: str):
        await websocket.accept()
        self.active.setdefault(booking_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, booking_id: str):
        if booking_id in self.active:
            self.active[booking_id].discard(websocket)

    async def broadcast(self, booking_id: str, data: dict):
        """Send message to all watchers of a booking."""
        if booking_id not in self.active:
            return
        dead = set()
        for ws in self.active[booking_id]:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active[booking_id].discard(ws)


class TechnicianOfferManager:
    """Manages WebSocket connections for technician offer push."""
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}  # tech_profile_id -> websocket

    async def connect(self, websocket: WebSocket, tech_id: str):
        await websocket.accept()
        self.active[tech_id] = websocket

    def disconnect(self, tech_id: str):
        self.active.pop(tech_id, None)

    async def send_offer(self, tech_id: str, offer_data: dict):
        ws = self.active.get(tech_id)
        if ws:
            try:
                await ws.send_text(json.dumps(offer_data))
            except Exception:
                self.active.pop(tech_id, None)


booking_manager = BookingConnectionManager()
technician_manager = TechnicianOfferManager()


# ── WebSocket endpoints ────────────────────────────────────────────────────────

@router.websocket("/ws/bookings/{booking_id}")
async def booking_status_ws(websocket: WebSocket, booking_id: str):
    """
    Customer WebSocket: streams live booking status + technician location.
    Sends a status ping every 10 seconds.
    """
    await booking_manager.connect(websocket, booking_id)
    try:
        while True:
            # Keep alive — in production, push events from service layer
            await asyncio.sleep(10)
            await websocket.send_text(json.dumps({
                "type": "ping",
                "booking_id": booking_id,
                "ts": datetime.utcnow().isoformat(),
            }))
    except WebSocketDisconnect:
        booking_manager.disconnect(websocket, booking_id)


@router.websocket("/ws/technician/offers")
async def technician_offers_ws(
    websocket: WebSocket,
    tech_id: str = Query(..., description="TechnicianProfile ID"),
):
    """
    Technician WebSocket: receives real-time job offer pushes.
    Client authenticates by passing their tech_id as query param.
    (Production: validate JWT token here)
    """
    await technician_manager.connect(websocket, tech_id)
    try:
        while True:
            # Keep alive
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping", "ts": datetime.utcnow().isoformat()}))
    except WebSocketDisconnect:
        technician_manager.disconnect(tech_id)


# ── SSE polling fallback ───────────────────────────────────────────────────────

@router.get("/api/stream/booking/{booking_id}/status")
async def booking_status_sse(booking_id: str):
    """
    SSE fallback: polls the booking status every 5 seconds.
    Frontend can use EventSource if WebSocket is blocked.
    """
    from app.database import SessionLocal
    from app.models import ServiceRequest

    async def event_generator():
        while True:
            db = SessionLocal()
            try:
                req = db.query(ServiceRequest).filter(ServiceRequest.id == booking_id).first()
                if req:
                    data = json.dumps({
                        "status": req.status.value if req.status else None,
                        "assigned_technician_id": req.assigned_technician_id,
                        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
                    })
                    yield f"data: {data}\n\n"
                else:
                    yield "data: {\"error\": \"not_found\"}\n\n"
            finally:
                db.close()
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Push helpers (called by service layer) ────────────────────────────────────

async def push_booking_update(booking_id: str, status: str, extra: dict = None):
    """Push a booking status update to all connected watchers."""
    data = {"type": "status_update", "booking_id": booking_id, "status": status}
    if extra:
        data.update(extra)
    await booking_manager.broadcast(booking_id, data)


async def push_offer_to_technician(tech_id: str, offer: dict):
    """Push a new job offer to a connected technician."""
    await technician_manager.send_offer(tech_id, {"type": "new_offer", **offer})

