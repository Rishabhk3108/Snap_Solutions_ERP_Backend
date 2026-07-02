from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.services import applications as svc

router = APIRouter(prefix="/applications", tags=["Applications"])


class CreateLeaveBody(BaseModel):
    user_id: int
    start_date: str
    end_date: str
    year: Optional[int] = None
    month: Optional[int] = None
    type: Optional[str] = "Casual Leave"
    reason: Optional[str] = None


class UpdateStatusBody(BaseModel):
    status: str  # "Approved" | "Rejected" | "Pending"


@router.post("/")
def apply_leave(body: CreateLeaveBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("")
def get_all_leaves(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_all(db)


@router.get("/user/{user_id}")
def get_my_leaves(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_by_user(db, user_id)


@router.get("/recent/user/{user_id}")
def get_recent_leaves(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_recent_by_user(db, user_id)


@router.get("/department/{dept_id}")
def get_leaves_by_dept(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.get_by_department(db, dept_id)


@router.get("/{record_id}")
def get_leave(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.get_one(db, record_id)
    return JSONResponse(status_code=status, content=data)


@router.put("/{record_id}")
def update_leave_status(record_id: int, body: UpdateStatusBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    status, data = svc.update_status(db, record_id, body.status)
    return JSONResponse(status_code=status, content=data)


@router.delete("/{record_id}")
def delete_leave(record_id: int, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    status, data = svc.delete(db, record_id)
    return JSONResponse(status_code=status, content=data)
