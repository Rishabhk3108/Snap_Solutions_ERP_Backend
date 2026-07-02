from sqlalchemy.orm import Session
from app.core.models import UserFinancialInfo


def get_salary_slip(db: Session, empid: int, year: int, month: int):
    fi = db.query(UserFinancialInfo).filter(UserFinancialInfo.user_id == empid).first()
    if not fi:
        return 404, {"error": "No financial info found for this employee."}
    return 200, {
        "empid": empid,
        "year": year,
        "month": month,
        "basicSalary": fi.salary_basic,
        "grossSalary": fi.salary_gross,
        "netSalary": fi.salary_net,
        "allowanceTotal": fi.allowance_total,
        "deductionTotal": fi.deduction_total,
        "status": "Generated",
    }


def get_salary_details(db: Session, empid: int, year: int, month: int):
    return get_salary_slip(db, empid, year, month)
