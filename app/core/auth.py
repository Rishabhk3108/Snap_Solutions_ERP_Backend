import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "snap_erp_secret_key_change_me")
ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


def require_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Access denied: No token provided")
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Access denied: Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Access denied: Wrong access token")


def require_admin(
    auth: dict = Depends(require_token),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == auth["user"]["id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Forbidden")
    if user.role != "ROLE_ADMIN":
        raise HTTPException(status_code=401, detail="Access denied: Role can't access this api")
    return auth


def require_admin_or_manager(
    auth: dict = Depends(require_token),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == auth["user"]["id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Forbidden")
    if user.role not in ("ROLE_ADMIN", "ROLE_MANAGER"):
        raise HTTPException(status_code=401, detail="Access denied: Role can't access this api")
    return auth
