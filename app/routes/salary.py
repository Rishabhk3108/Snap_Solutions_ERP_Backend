from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.services import salary as svc
from app.core.models import MonthlySalary

router = APIRouter(prefix="/salary", tags=["Salary"])


class SalaryAdjustBody(BaseModel):
    empid: int
    year: int
    month: int
    adjustment: float
    reason: Optional[str] = None


@router.get("/salary-slip/{empid}/{year}/{month}")
def get_slip(empid: int, year: int, month: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.get_salary_slip(db, empid, year, month)
    return JSONResponse(status_code=status, content=data)


@router.get("/details/{empid}/{year}/{month}")
def get_details(empid: int, year: int, month: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.get_salary_details(db, empid, year, month)
    return JSONResponse(status_code=status, content=data)


@router.get("/salarylist/{year}/{month}")
def salary_list(year: int, month: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    records = db.query(MonthlySalary).filter(
        MonthlySalary.year == year, MonthlySalary.month == month
    ).all()
    return [
        {
            "id": r.id, "empid": r.empid, "year": r.year, "month": r.month,
            "basicSalary": r.basic_salary or 0, "totalAllowances": r.allowance_total or 0,
            "totalDeductions": (r.deduction_total or 0) + (r.advance_deduction or 0) + (r.fine_deduction or 0),
            "netSalary": r.net_salary or 0, "status": r.status,
            "employee": {"fullname": r.employee.full_name} if r.employee else None,
        }
        for r in records
    ]


@router.post("/adjust")
def adjust_salary(body: SalaryAdjustBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    record = db.query(MonthlySalary).filter(
        MonthlySalary.empid == body.empid,
        MonthlySalary.year == body.year,
        MonthlySalary.month == body.month,
    ).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "No salary record found for this employee/period. Generate first."})
    record.net_salary = (record.net_salary or 0) + body.adjustment
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Salary adjusted.", "netSalary": record.net_salary})
