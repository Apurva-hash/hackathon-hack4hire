"""Auth router — register, login, refresh, me, logout."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole, Customer, TechnicianProfile
from app.services.auth_service import hash_password, authenticate_user, create_tokens
from app.utils.jwt import verify_token
from app.dependencies import get_current_user
from app.models.base import generate_uuid

router = APIRouter(tags=["Auth"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterCustomerRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None


class RegisterTechnicianRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    service_radius_km: float = 15.0
    certification_level: int = 1


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register/customer", status_code=201)
def register_customer(body: RegisterCustomerRequest, db: Session = Depends(get_db)):
    """Register a new customer account."""
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=generate_uuid(),
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(user)
    db.flush()

    customer = Customer(
        id=generate_uuid(),
        user_id=user.id,
        name=body.name,
        phone=body.phone,
        saved_addresses=[],
    )
    db.add(customer)
    db.commit()

    tokens = create_tokens(user.id, user.role.value)
    return {**tokens, "user_id": user.id, "role": user.role.value, "name": body.name}


@router.post("/register/technician", status_code=201)
def register_technician(body: RegisterTechnicianRequest, db: Session = Depends(get_db)):
    """Register a new technician (requires admin approval before going online)."""
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=generate_uuid(),
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role=UserRole.TECHNICIAN,
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = TechnicianProfile(
        id=generate_uuid(),
        user_id=user.id,
        name=body.name,
        phone=body.phone,
        bio=body.bio,
        service_radius_km=body.service_radius_km,
        certification_level=max(1, min(5, body.certification_level)),
        is_online=False,
        is_approved=False,
        is_suspended=False,
    )
    db.add(profile)
    db.commit()

    tokens = create_tokens(user.id, user.role.value)
    return {
        **tokens,
        "user_id": user.id,
        "role": user.role.value,
        "name": body.name,
        "message": "Registration successful. Awaiting admin approval before you can go online.",
    }


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return JWT tokens."""
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    tokens = create_tokens(user.id, user.role.value)

    name = None
    if user.customer_profile:
        name = user.customer_profile.name
    elif user.technician_profile:
        name = user.technician_profile.name

    return {**tokens, "user_id": user.id, "role": user.role.value, "name": name}


@router.post("/refresh")
def refresh_token(body: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    from app.utils.jwt import create_access_token
    payload = verify_token(body.refresh_token, "refresh")
    new_access = create_access_token({"sub": payload["sub"], "role": payload.get("role", "")})
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return current user info and profile."""
    profile = None
    if current_user.customer_profile:
        c = current_user.customer_profile
        profile = {"name": c.name, "phone": c.phone, "avg_rating": c.avg_rating, "total_bookings": c.total_bookings}
    elif current_user.technician_profile:
        t = current_user.technician_profile
        profile = {
            "name": t.name, "phone": t.phone, "is_online": t.is_online,
            "is_approved": t.is_approved, "avg_rating": t.avg_rating,
            "certification_level": t.certification_level,
            "total_jobs_completed": t.total_jobs_completed,
        }
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role.value, "profile": profile}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint — stateless JWT; client should discard tokens."""
    return {"message": "Logged out successfully"}
