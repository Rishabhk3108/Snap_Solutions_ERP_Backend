from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token
from app.services import messages as svc

router = APIRouter(prefix="/messages", tags=["Messages"])


class MessageBody(BaseModel):
    senderId: int
    receiverId: int
    subject: Optional[str] = None
    content: str


@router.post("/")
def send(body: MessageBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/user/{user_id}")
def get_for_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_for_user(db, user_id)


@router.get("/{record_id}")
def get_one(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.get_one(db, record_id)
    return JSONResponse(status_code=status, content=data)
