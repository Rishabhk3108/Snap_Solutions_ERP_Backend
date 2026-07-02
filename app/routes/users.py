from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin, require_admin_or_manager
from app.services import users as svc

router = APIRouter()


class CreateUserBody(BaseModel):
    username: str = ""
    password: Optional[str] = None
    fullname: str
    role: str = "ROLE_EMPLOYEE"
    active: bool = False
    jobTitle: Optional[str] = None
    reportid: Optional[str] = None
    roleId: int = 1
    departmentId: Optional[int] = None


class UpdateUserBody(BaseModel):
    fullname: Optional[str] = None
    fullName: Optional[str] = None
    role: Optional[str] = None
    active: Optional[int] = None
    jobTitle: Optional[str] = None
    reportid: Optional[str] = None
    roleId: Optional[int] = None
    departmentId: Optional[int] = None
    endDate: Optional[str] = None
    remark: Optional[str] = None


class PasswordUpdateBody(BaseModel):
    id: int
    password: str


class ChangePasswordBody(BaseModel):
    oldPassword: str
    newPassword: str


class VerifyUserBody(BaseModel):
    id: int
    date_of_birth: str
    startDate: str = None


class EndDateBody(BaseModel):
    endDate: str
    remark: str = None


# ── Public endpoints (no auth) ────────────────────────────────
@router.post("/users")
def create_user(body: CreateUserBody, db: Session = Depends(get_db)):
    status, data = svc.create_user(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.post("/users/emp-password-update")
def update_password(body: PasswordUpdateBody, db: Session = Depends(get_db)):
    status, data = svc.update_password(db, body.id, body.password)
    return JSONResponse(status_code=status, content=data)


@router.post("/users/verify-user")
def verify_user(body: VerifyUserBody, db: Session = Depends(get_db)):
    from datetime import date
    try:
        dob = date.fromisoformat(body.date_of_birth)
    except Exception:
        dob = None
    status, data = svc.verify_user(db, body.id, dob, body.startDate)
    return JSONResponse(status_code=status, content=data)


@router.get("/users/maxid")
def max_id(db: Session = Depends(get_db)):
    status, data = svc.get_max_id(db)
    return JSONResponse(status_code=status, content=data)


@router.get("/users/reportees/{reportid}")
def get_reportees(reportid: str, db: Session = Depends(get_db)):
    data = svc.get_reportees(db, reportid)
    return data


# ── Protected endpoints ───────────────────────────────────────
@router.get("/users")
def get_all_users(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_all_users(db)


@router.get("/users/nullend")
def get_active_users(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_all_active(db)


@router.get("/users/notnull")
def get_exited_users(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_all_exited(db)


@router.get("/users/total")
def get_total(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_total(db)


@router.get("/users/total/department/{dept_id}")
def get_total_by_dept(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_total_by_dept(db, dept_id)


@router.get("/users/department/{dept_id}")
def get_by_department(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_by_department(db, dept_id)


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.get_user(db, user_id)
    return JSONResponse(status_code=status, content=data)


@router.put("/users/updateEndDate/{user_id}")
def update_end_date(user_id: int, body: EndDateBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    from datetime import date
    try:
        end_date = date.fromisoformat(body.endDate)
    except Exception:
        end_date = None
    status, data = svc.update_end_date(db, user_id, end_date, body.remark)
    return JSONResponse(status_code=status, content=data)


@router.put("/users/changePassword/{user_id}")
def change_password(user_id: int, body: ChangePasswordBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.change_password(db, user_id, body.oldPassword, body.newPassword)
    return JSONResponse(status_code=status, content=data)


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UpdateUserBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.update_user(db, user_id, body.dict(exclude_none=True))
    return JSONResponse(status_code=status, content=data)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.delete_user(db, user_id)
    return JSONResponse(status_code=status, content=data)
