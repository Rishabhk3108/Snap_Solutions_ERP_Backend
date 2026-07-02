from datetime import date as date_type

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.core.models import Fine, User

router = APIRouter(tags=["Fines"])


class FineBody(BaseModel):
    empid: int
    amount: float
    reason: Optional[str] = None
    date: str


def _serialize(f: Fine) -> dict:
    emp = f.employee
    return {
        "id": f.id,
        "empid": f.empid,
        "amount": f.amount,
        "date": str(f.date) if f.date else None,
        "reason": f.reason,
        "employee": {"fullname": emp.full_name} if emp else None,
    }


@router.post("/fine/create")
def create_fine(body: FineBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    emp = db.query(User).filter(User.id == body.empid).first()
    if not emp:
        return JSONResponse(status_code=404, content={"message": "Employee not found"})
    record = Fine(
        empid=body.empid,
        amount=body.amount,
        date=date_type.fromisoformat(body.date),
        reason=body.reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return JSONResponse(status_code=200, content={"message": "Fine recorded", "data": _serialize(record)})


@router.get("/fine/list")
def list_fines(db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    records = db.query(Fine).order_by(Fine.date.desc()).all()
    return [_serialize(r) for r in records]
