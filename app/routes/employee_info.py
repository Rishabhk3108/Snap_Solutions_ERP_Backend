from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import employee_info as svc

router = APIRouter(prefix="/employee", tags=["Employee"])


class EmployeeBody(BaseModel):
    id: int
    emailAddress: Optional[str] = None
    Aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    esic_number: Optional[str] = None
    pf_number: Optional[str] = None
    nominee_name: Optional[str] = None
    nominee_relation: Optional[str] = None


class EmployeeUpdateBody(BaseModel):
    emailAddress: Optional[str] = None
    Aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    esic_number: Optional[str] = None
    pf_number: Optional[str] = None
    nominee_name: Optional[str] = None
    nominee_relation: Optional[str] = None


@router.post("")
def create(body: EmployeeBody, db: Session = Depends(get_db)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/{emp_id}")
def get_by_id(emp_id: int, db: Session = Depends(get_db)):
    status, data = svc.get_by_id(db, emp_id)
    return JSONResponse(status_code=status, content=data)


@router.put("/update/{user_id}")
def update(user_id: int, body: EmployeeUpdateBody, db: Session = Depends(get_db)):
    status, data = svc.update(db, user_id, body.dict(exclude_none=True))
    return JSONResponse(status_code=status, content=data)
