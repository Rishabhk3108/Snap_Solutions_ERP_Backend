import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.models import User, UserPersonalInfo, UserFinancialInfo

SECRET_KEY = os.getenv("SECRET_KEY", "snap_erp_secret_key_change_me")
ALGORITHM = "HS256"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()


def _verify(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _make_token(user_data: dict) -> str:
    payload = {
        "user": user_data,
        "exp": datetime.now(timezone.utc) + timedelta(days=365),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def login(db: Session, username: str, password: str):
    if not username or not password:
        return 400, {"message": "Username and password are required!"}

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return 401, {"message": "Incorrect Credentials!"}
    if not user.active:
        return 403, {"message": "Account is not active!"}
    if not user.password or not _verify(password, user.password):
        return 401, {"message": "Incorrect Credentials!"}

    dept_id = user.department_id
    user_data = {
        "id": user.id,
        "username": user.username,
        "fullname": user.full_name,
        "role": user.role,
        "departmentId": dept_id,
        "roleId": user.role_id,
    }
    token = _make_token(user_data)
    return 200, {"message": "Login successful!", "token": token, "user": user_data}


def _next_user_id(db: Session) -> int:
    from sqlalchemy import func
    max_id = db.query(func.max(User.id)).scalar()
    return (max_id or 0) + 1


def register(db: Session, username: str, password: str, fullname: str):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return 403, {"message": "Username already exists"}

    hashed = _hash(password) if password else None
    new_id = _next_user_id(db)
    user = User(
        id=new_id,
        username=username,
        password=hashed,
        full_name=fullname,
        role="ROLE_EMPLOYEE",
        active=False,
    )
    db.add(user)
    db.flush()
    # Mirror Node.js afterCreate hook: username becomes the user's numeric ID
    user.username = str(user.id)
    db.flush()

    # Auto-create empty stubs (mirrors register.controller.js)
    personal_stub = UserPersonalInfo(user_id=user.id)
    financial_stub = UserFinancialInfo(user_id=user.id)
    db.add(personal_stub)
    db.add(financial_stub)
    db.commit()
    db.refresh(user)

    return 200, {
        "id": user.id,
        "username": user.username,
        "fullName": user.full_name,
        "role": user.role,
        "active": user.active,
    }


def check_token(auth: dict):
    return 201, {"message": "Access granted!", "authData": auth}
