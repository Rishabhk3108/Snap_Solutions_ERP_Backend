from datetime import date as date_type

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.core.models import PaymentRecord

router = APIRouter(tags=["Payment Records"])


class PaymentBody(BaseModel):
    userId: Optional[int] = None
    jobId: Optional[int] = None
    amount: float
    year: Optional[int] = None
    status: Optional[str] = "Pending"
    description: Optional[str] = None
    date: Optional[str] = None


def _serialize(p: PaymentRecord) -> dict:
    emp = p.employee
    job = p.job
    return {
        "id": p.id,
        "userId": p.user_id,
        "jobId": p.job_id,
        "amount": p.amount,
        "year": p.year,
        "status": p.status,
        "description": p.description,
        "date": str(p.date) if p.date else None,
        "employee": {"fullname": emp.full_name} if emp else None,
        "job": {"title": job.title} if job else None,
    }


@router.get("/payments")
def list_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(p) for p in db.query(PaymentRecord).order_by(PaymentRecord.date.desc()).all()]


@router.get("/payments/year/{year}")
def list_by_year(year: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(p) for p in db.query(PaymentRecord).filter(PaymentRecord.year == year).all()]


@router.get("/payments/job/{job_id}")
def list_by_job(job_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(p) for p in db.query(PaymentRecord).filter(PaymentRecord.job_id == job_id).all()]


@router.get("/payments/{payment_id}")
def get_one(payment_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    p = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    return _serialize(p)


@router.post("/payments")
def create(body: PaymentBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = PaymentRecord(
        user_id=body.userId, job_id=body.jobId, amount=body.amount,
        year=body.year, status=body.status or "Pending",
        description=body.description,
        date=date_type.fromisoformat(body.date) if body.date else None,
    )
    db.add(record); db.commit(); db.refresh(record)
    return JSONResponse(status_code=201, content=_serialize(record))


@router.put("/payments/{payment_id}")
def update(payment_id: int, body: PaymentBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    if body.status is not None:
        record.status = body.status
    if body.description is not None:
        record.description = body.description
    if body.amount is not None:
        record.amount = body.amount
    db.commit()
    return _serialize(record)
