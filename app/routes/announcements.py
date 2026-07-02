from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.services import announcements as svc

router = APIRouter(prefix="/departmentAnnouncements", tags=["Announcements"])


class AnnouncementBody(BaseModel):
    departmentId: Optional[int] = None
    title: str
    content: Optional[str] = None
    createdBy: Optional[str] = None


@router.get("/")
def get_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_all(db)


@router.get("/department/{dept_id}")
def get_by_dept(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_by_dept(db, dept_id)


@router.get("/recent/department/{dept_id}")
def get_recent(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_recent_by_dept(db, dept_id)


@router.post("")
def create(body: AnnouncementBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.delete("/{record_id}")
def delete(record_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.delete(db, record_id)
    return JSONResponse(status_code=status, content=data)
