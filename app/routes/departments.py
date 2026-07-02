from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import Department

router = APIRouter(prefix="/departments", tags=["Departments"])


def _s(d: Department):
    return {"id": d.id, "name": d.department_name}


class DeptBody(BaseModel):
    name: str


@router.get("")
def get_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_s(d) for d in db.query(Department).order_by(Department.id).all()]


@router.get("/{dept_id}")
def get_one(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    d = db.query(Department).filter(Department.id == dept_id).first()
    if not d:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _s(d)


@router.post("")
def create(body: DeptBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    d = Department(department_name=body.name)
    db.add(d); db.commit(); db.refresh(d)
    return JSONResponse(status_code=201, content=_s(d))


@router.put("/{dept_id}")
def update(dept_id: int, body: DeptBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    d = db.query(Department).filter(Department.id == dept_id).first()
    if not d:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    d.department_name = body.name
    db.commit()
    return _s(d)


@router.delete("/{dept_id}")
def delete(dept_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    d = db.query(Department).filter(Department.id == dept_id).first()
    if not d:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    db.delete(d); db.commit()
    return {"message": "Deleted"}
