from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import Vendor

router = APIRouter(tags=["Vendors"])


class VendorBody(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


def _serialize(v: Vendor) -> dict:
    return {"id": v.id, "name": v.name, "email": v.email, "phone": v.phone, "address": v.address}


@router.get("/vendor")
def list_vendors(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(v) for v in db.query(Vendor).order_by(Vendor.name).all()]


@router.get("/vendor/{vendor_id}")
def get_vendor(vendor_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    return _serialize(v)


@router.post("/vendor")
def create_vendor(body: VendorBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    record = Vendor(name=body.name, email=body.email, phone=body.phone, address=body.address)
    db.add(record)
    db.commit()
    db.refresh(record)
    return JSONResponse(status_code=201, content=_serialize(record))
