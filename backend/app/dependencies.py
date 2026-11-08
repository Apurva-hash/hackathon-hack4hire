"""FastAPI dependencies — auth, role guards, DB session."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.jwt import verify_token
from app.models.user import User, UserRole

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT bearer token and return the active User."""
    payload = verify_token(credentials.credentials, "access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: UserRole):
    """Return a dependency that enforces one of the given roles."""
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return _checker


def require_admin():
    """Enforce that only the single authorized Admin account can access admin routes."""
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != UserRole.ADMIN or current_user.email.lower() != "admin11@gmail.com":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to authorized administrator")
        return current_user
    return _checker


get_current_customer = require_role(UserRole.CUSTOMER)
get_current_technician = require_role(UserRole.TECHNICIAN)
get_current_admin = require_admin()
