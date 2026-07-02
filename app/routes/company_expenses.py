from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.core.models import CompanyExpense

router = APIRouter(tags=["Company Expenses"])


class ExpenseBody(BaseModel):
    title: str
    amount: float
    departmentId: Optional[int] = None
    year: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = "Pending"


def _serialize(e: CompanyExpense) -> dict:
    dept = e.department
    return {
        "id": e.id,
        "title": e.title,
        "amount": e.amount,
        "departmentId": e.department_id,
        "year": e.year,
        "description": e.description,
        "status": e.status,
        "departmentName": dept.department_name if dept else None,
    }


@router.get("/expenses")
def list_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(e) for e in db.query(CompanyExpense).order_by(CompanyExpense.id.desc()).all()]


@router.get("/expenses/department/{dept_id}")
def list_by_dept(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(e) for e in db.query(CompanyExpense).filter(CompanyExpense.department_id == dept_id).all()]


@router.get("/expenses/year/{year}/department/{dept_id}")
def list_by_year_dept(year: int, dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(e) for e in db.query(CompanyExpense)
            .filter(CompanyExpense.year == year, CompanyExpense.department_id == dept_id).all()]


@router.get("/expenses/{expense_id}")
def get_one(expense_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    e = db.query(CompanyExpense).filter(CompanyExpense.id == expense_id).first()
    if not e:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    return _serialize(e)


@router.post("/expenses")
def create(body: ExpenseBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = CompanyExpense(
        title=body.title, amount=body.amount, department_id=body.departmentId,
        year=body.year, description=body.description, status=body.status or "Pending",
    )
    db.add(record); db.commit(); db.refresh(record)
    return JSONResponse(status_code=201, content=_serialize(record))


@router.put("/expenses/{expense_id}")
def update(expense_id: int, body: ExpenseBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = db.query(CompanyExpense).filter(CompanyExpense.id == expense_id).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    record.title = body.title
    record.amount = body.amount
    record.description = body.description
    if body.status:
        record.status = body.status
    db.commit()
    return _serialize(record)
