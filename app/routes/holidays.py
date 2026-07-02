from datetime import date as date_type

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.core.models import Holiday

router = APIRouter(tags=["Holidays"])


class HolidayBody(BaseModel):
    name: str
    date: str
    type: Optional[str] = "Public"


def _serialize(h: Holiday) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "date": str(h.date) if h.date else None,
        "type": h.type,
    }


@router.get("/daysHolidays")
def list_holidays(db: Session = Depends(get_db), auth=Depends(require_token)):
    records = db.query(Holiday).order_by(Holiday.date.asc()).all()
    return [_serialize(r) for r in records]


@router.post("/daysHolidays")
def create_holiday(body: HolidayBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = Holiday(
        name=body.name,
        date=date_type.fromisoformat(body.date),
        type=body.type,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return JSONResponse(status_code=200, content={"message": "Holiday added", "data": _serialize(record)})


@router.delete("/daysHolidays/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    record = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "Holiday not found"})
    db.delete(record)
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Holiday deleted"})
