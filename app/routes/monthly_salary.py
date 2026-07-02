import csv
import io
from datetime import date as date_type

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import MonthlySalary, User, UserFinancialInfo, AdvancePayment, Fine

router = APIRouter(tags=["Monthly Salary"])


class PeriodBody(BaseModel):
    year: int
    month: int


def _serialize(r: MonthlySalary) -> dict:
    emp = r.employee
    return {
        "id": r.id,
        "empid": r.empid,
        "year": r.year,
        "month": r.month,
        "basicSalary": r.basic_salary or 0,
        "totalAllowances": r.allowance_total or 0,
        "totalDeductions": (r.deduction_total or 0) + (r.advance_deduction or 0) + (r.fine_deduction or 0),
        "advanceDeduction": r.advance_deduction or 0,
        "fineDeduction": r.fine_deduction or 0,
        "netSalary": r.net_salary or 0,
        "status": r.status,
        "employee": {"fullname": emp.full_name} if emp else None,
    }


@router.get("/monthlySalary/monthly-details/{year}/{month}")
def get_monthly_details(year: int, month: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    records = (
        db.query(MonthlySalary)
        .filter(MonthlySalary.year == year, MonthlySalary.month == month)
        .all()
    )
    return [_serialize(r) for r in records]


@router.get("/monthlySalary/list")
def list_monthly(db: Session = Depends(get_db), auth=Depends(require_token)):
    records = db.query(MonthlySalary).order_by(MonthlySalary.year.desc(), MonthlySalary.month.desc()).all()
    return [_serialize(r) for r in records]


@router.post("/monthlySalary/generate")
def generate_monthly(body: PeriodBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    year, month = body.year, body.month

    # Get all active employees with financial info
    employees = db.query(User).filter(User.active == True).all()
    created = 0
    updated = 0

    for emp in employees:
        fi = db.query(UserFinancialInfo).filter(UserFinancialInfo.user_id == emp.id).first()
        if not fi:
            continue

        # Sum advance deductions for this month
        adv_sum = sum(
            a.amount for a in db.query(AdvancePayment)
            .filter(
                AdvancePayment.empid == emp.id,
                AdvancePayment.adjusted == False,
            ).all()
            if a.date and a.date.year == year and a.date.month == month
        )

        # Sum fine deductions for this month
        fine_sum = sum(
            f.amount for f in db.query(Fine)
            .filter(Fine.empid == emp.id).all()
            if f.date and f.date.year == year and f.date.month == month
        )

        basic = fi.salary_basic or 0
        allowances = fi.allowance_total or 0
        deductions = fi.deduction_total or 0
        net = basic + allowances - deductions - adv_sum - fine_sum

        existing = db.query(MonthlySalary).filter(
            MonthlySalary.empid == emp.id,
            MonthlySalary.year == year,
            MonthlySalary.month == month,
        ).first()

        if existing:
            existing.basic_salary = basic
            existing.allowance_total = allowances
            existing.deduction_total = deductions
            existing.advance_deduction = adv_sum
            existing.fine_deduction = fine_sum
            existing.net_salary = net
            updated += 1
        else:
            record = MonthlySalary(
                empid=emp.id, year=year, month=month,
                basic_salary=basic, allowance_total=allowances,
                deduction_total=deductions, advance_deduction=adv_sum,
                fine_deduction=fine_sum, net_salary=net, status="Generated",
            )
            db.add(record)
            created += 1

    db.commit()
    return JSONResponse(status_code=200, content={
        "message": f"Salary generated for {created + updated} employees ({created} new, {updated} updated).",
        "created": created, "updated": updated,
    })


@router.post("/monthlySalary/change-status")
def change_status(body: PeriodBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    records = db.query(MonthlySalary).filter(
        MonthlySalary.year == body.year, MonthlySalary.month == body.month
    ).all()
    for r in records:
        r.status = "Paid"
    db.commit()
    return JSONResponse(status_code=200, content={"message": f"{len(records)} salary records marked as Paid."})


@router.get("/monthlySalary/csv/{year}/{month}")
def export_csv(year: int, month: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    records = db.query(MonthlySalary).filter(
        MonthlySalary.year == year, MonthlySalary.month == month
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Name", "Basic", "Allowances", "Deductions", "Advance Ded.", "Fine Ded.", "Net Salary", "Status"])
    for r in records:
        name = r.employee.full_name if r.employee else f"Employee #{r.empid}"
        total_ded = (r.deduction_total or 0) + (r.advance_deduction or 0) + (r.fine_deduction or 0)
        writer.writerow([
            r.empid, name, r.basic_salary or 0, r.allowance_total or 0,
            total_ded, r.advance_deduction or 0, r.fine_deduction or 0,
            r.net_salary or 0, r.status,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=salary_{year}_{str(month).zfill(2)}.csv"},
    )
