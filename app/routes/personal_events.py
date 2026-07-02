from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token
from app.services import personal_events as svc

router = APIRouter(prefix="/personalEvents", tags=["Personal Events"])


class EventBody(BaseModel):
    userId: int
    title: str
    date: str
    type: Optional[str] = "Personal"
    description: Optional[str] = None


class EventUpdateBody(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


@router.post("/")
def create(body: EventBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/user/{user_id}")
def get_by_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_by_user(db, user_id)


@router.put("/{record_id}")
def update(record_id: int, body: EventUpdateBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.update(db, record_id, body.dict(exclude_none=True))
    return JSONResponse(status_code=status, content=data)


@router.delete("/{record_id}")
def delete(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.delete(db, record_id)
    return JSONResponse(status_code=status, content=data)
