from datetime import date as date_type

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.core.models import AdvancePayment, User

router = APIRouter(tags=["Advance Payments"])


class AdvancePaymentBody(BaseModel):
    empid: int
    amount: float
    date: str
    note: Optional[str] = None


def _serialize(a: AdvancePayment) -> dict:
    emp = a.employee
    return {
        "id": a.id,
        "empid": a.empid,
        "amount": a.amount,
        "date": str(a.date) if a.date else None,
        "note": a.note,
        "adjusted": a.adjusted,
        "employee": {"fullname": emp.full_name} if emp else None,
    }


@router.post("/advancePayment/add")
def add_advance(body: AdvancePaymentBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    emp = db.query(User).filter(User.id == body.empid).first()
    if not emp:
        return JSONResponse(status_code=404, content={"message": "Employee not found"})
    record = AdvancePayment(
        empid=body.empid,
        amount=body.amount,
        date=date_type.fromisoformat(body.date),
        note=body.note,
        adjusted=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return JSONResponse(status_code=200, content={"message": "Advance payment recorded", "data": _serialize(record)})


@router.get("/advancePayment/list")
def list_advances(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    records = db.query(AdvancePayment).order_by(AdvancePayment.date.desc()).all()
    return [_serialize(r) for r in records]
