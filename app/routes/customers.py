from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session
from app.core.database import get_db, Base
from app.core.auth import require_token, require_admin


class CustomerModel(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    gst = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    status = Column(String(8), nullable=True)
    pan_no = Column(String(255), nullable=True)


def _s(c: CustomerModel):
    return {"id": c.id, "name": c.name, "phone": c.phone, "email": c.email, "address": c.address, "status": c.status}


router = APIRouter(prefix="/customer", tags=["Customers"])


class CustomerBody(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst: Optional[str] = None
    panNo: Optional[str] = None


@router.get("")
def get_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_s(c) for c in db.query(CustomerModel).order_by(CustomerModel.id).all()]


@router.get("/{cust_id}")
def get_one(cust_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    c = db.query(CustomerModel).filter(CustomerModel.id == cust_id).first()
    if not c:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _s(c)


@router.post("")
def create(body: CustomerBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    c = CustomerModel(name=body.name, phone=body.phone, email=body.email, address=body.address, gst=body.gst, pan_no=body.panNo, status="Active")
    db.add(c); db.commit(); db.refresh(c)
    return JSONResponse(status_code=201, content=_s(c))


@router.put("/{cust_id}")
def update(cust_id: int, body: CustomerBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    c = db.query(CustomerModel).filter(CustomerModel.id == cust_id).first()
    if not c:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    for k, v in body.dict(exclude_none=True).items():
        setattr(c, k if k != 'panNo' else 'pan_no', v)
    db.commit()
    return _s(c)


@router.delete("")
def delete_all(db: Session = Depends(get_db), auth=Depends(require_admin)):
    return {"message": "Use specific ID"}
