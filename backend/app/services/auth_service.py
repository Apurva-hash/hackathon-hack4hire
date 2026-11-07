"""Auth service — password hashing and token generation."""
import hashlib
import secrets
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.category import MatchingConfig
from app.utils.jwt import create_access_token, create_refresh_token

# Resilient password hashing (supports bcrypt, passlib, or built-in hashlib fallback)
try:
    import bcrypt
    _has_bcrypt = True
except ImportError:
    _has_bcrypt = False

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    _pwd_context = None


def hash_password(password: str) -> str:
    if _has_bcrypt:
        try:
            return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except Exception:
            pass
    if _pwd_context:
        try:
            return _pwd_context.hash(password)
        except Exception:
            pass
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${h}"


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("sha256$"):
        parts = hashed.split("$")
        if len(parts) == 3:
            salt, h = parts[1], parts[2]
            return hashlib.sha256((salt + plain).encode("utf-8")).hexdigest() == h
    if hashed.startswith("$2b$") or hashed.startswith("$2a$") or hashed.startswith("$2y$"):
        if _has_bcrypt:
            try:
                return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
            except Exception:
                pass
        if _pwd_context:
            try:
                return _pwd_context.verify(plain, hashed)
            except Exception:
                pass
    return plain == hashed


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_tokens(user_id: str, role: str) -> dict:
    payload = {"sub": user_id, "role": role}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
    }


def get_or_create_matching_config(db: Session) -> MatchingConfig:
    cfg = db.query(MatchingConfig).filter(MatchingConfig.id == 1).first()
    if not cfg:
        cfg = MatchingConfig()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
