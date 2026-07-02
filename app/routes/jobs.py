from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import JobPosition, Department

router = APIRouter(tags=["Jobs"])


class JobBody(BaseModel):
    title: str
    description: Optional[str] = None
    departmentId: Optional[int] = None


def _serialize(j: JobPosition) -> dict:
    return {
        "id": j.id,
        "title": j.title,
        "description": j.description,
        "departmentId": j.department_id,
        "departmentName": j.department.department_name if j.department else None,
    }


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_serialize(j) for j in db.query(JobPosition).order_by(JobPosition.title).all()]


@router.post("/jobs")
def create_job(body: JobBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    record = JobPosition(title=body.title, description=body.description, department_id=body.departmentId)
    db.add(record)
    db.commit()
    db.refresh(record)
    return JSONResponse(status_code=201, content=_serialize(record))


@router.put("/jobs/{job_id}")
def update_job(job_id: int, body: JobBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    record = db.query(JobPosition).filter(JobPosition.id == job_id).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    record.title = body.title
    record.description = body.description
    record.department_id = body.departmentId
    db.commit()
    db.refresh(record)
    return _serialize(record)


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    record = db.query(JobPosition).filter(JobPosition.id == job_id).first()
    if not record:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    db.delete(record)
    db.commit()
    return {"message": "Deleted"}
