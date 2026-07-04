from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.services import personal_info as svc

router = APIRouter(prefix="/personalInformations", tags=["Personal Info"])


class PersonalInfoBody(BaseModel):
    userId: int
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None
    maritalStatus: Optional[str] = None
    fatherName: Optional[str] = None
    idNumber: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    emailAddress: Optional[str] = None
    nomineeName: Optional[str] = None
    nomineeRelationship: Optional[str] = None


class PersonalInfoUpdateBody(BaseModel):
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None
    maritalStatus: Optional[str] = None
    fatherName: Optional[str] = None
    idNumber: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    emailAddress: Optional[str] = None
    nomineeName: Optional[str] = None
    nomineeRelationship: Optional[str] = None


@router.post("")
def create(body: PersonalInfoBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/user/{user_id}")
def find_by_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    data = svc.find_by_user_id(db, user_id)
    return data if data is not None else {}


@router.get("/{record_id}")
def find_one(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.find_one(db, record_id)
    return JSONResponse(status_code=status, content=data)


@router.put("/{user_id}")
def update(user_id: int, body: PersonalInfoUpdateBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.update_by_user_id(db, user_id, body.dict(exclude_none=True))
    return JSONResponse(status_code=status, content=data)


@router.delete("/{record_id}")
def delete(record_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.delete_record(db, record_id)
    return JSONResponse(status_code=status, content=data)
