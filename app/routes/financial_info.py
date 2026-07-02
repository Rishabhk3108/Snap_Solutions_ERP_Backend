from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin, require_admin_or_manager
from app.services import financial_info as svc

router = APIRouter(prefix="/financialInformations", tags=["Financial Info"])


class FinancialInfoBody(BaseModel):
    userId: int
    employmentType: Optional[str] = None
    salaryBasic: Optional[int] = None
    salaryGross: Optional[int] = None
    salaryNet: Optional[int] = None
    allowanceHouseRent: Optional[int] = None
    allowanceMedical: Optional[int] = None
    allowanceSpecial: Optional[int] = None
    allowanceFuel: Optional[int] = None
    allowancePhoneBill: Optional[int] = None
    allowanceOther: Optional[int] = None
    allowanceTotal: Optional[int] = None
    deductionProvidentFund: Optional[int] = None
    deductionTax: Optional[int] = None
    deductionOther: Optional[int] = None
    deductionTotal: Optional[int] = None
    bankName: Optional[str] = None
    accountName: Optional[str] = None
    accountNumber: Optional[str] = None
    iban: Optional[str] = None
    otStatus: Optional[str] = "No"
    esicStatus: Optional[str] = "No"
    OtWorkingHours: Optional[int] = 8


class SalaryUpdateBody(BaseModel):
    userId: int
    salaryBasic: int
    salaryGross: int
    salaryNet: int


@router.post("")
def create(body: FinancialInfoBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("")
def find_all(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    return svc.find_all(db)


@router.get("/user/{user_id}")
def find_by_user(user_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.find_by_user_id(db, user_id)


@router.get("/advances/{user_id}")
def get_advances(user_id: int, db: Session = Depends(get_db)):
    status, data = svc.get_advances(db, user_id)
    return JSONResponse(status_code=status, content=data)


@router.post("/salaryUpdate")
def salary_update(body: SalaryUpdateBody, db: Session = Depends(get_db)):
    status, data = svc.salary_update(db, body.userId, body.salaryBasic, body.salaryGross, body.salaryNet)
    return JSONResponse(status_code=status, content=data)


@router.get("/{record_id}")
def find_one(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.find_one(db, record_id)
    return JSONResponse(status_code=status, content=data)


@router.put("/{user_id}")
def update(user_id: int, body: FinancialInfoBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.update_by_user_id(db, user_id, body.dict(exclude_none=True))
    return JSONResponse(status_code=status, content=data)


@router.delete("/{record_id}")
def delete(record_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    status, data = svc.delete_record(db, record_id)
    return JSONResponse(status_code=status, content=data)
