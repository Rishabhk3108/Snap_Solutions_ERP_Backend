from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import Project, User

router = APIRouter(tags=["Projects"])


def _s(p: Project):
    return {
        "id": p.id, "name": p.name,
        "customerId": None, "status": None,
        "description": None, "startDate": None, "endDate": None,
    }


class ProjectBody(BaseModel):
    name: str
    customerId: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None


@router.get("/project")
def get_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_s(p) for p in db.query(Project).order_by(Project.id).all()]


@router.get("/project/{proj_id}")
def get_one(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _s(p)


@router.post("/project")
def create(body: ProjectBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = Project(name=body.name)
    db.add(p); db.commit(); db.refresh(p)
    return JSONResponse(status_code=201, content=_s(p))


@router.put("/project/{proj_id}")
def update(proj_id: int, body: ProjectBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    p.name = body.name
    db.commit()
    return _s(p)


@router.delete("/project/{proj_id}")
def delete(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    db.delete(p); db.commit()
    return {"message": "Deleted"}


@router.post("/employeeProject/assign")
def assign(body: dict, db: Session = Depends(get_db), auth=Depends(require_admin)):
    return {"message": "Assigned"}


@router.put("/employeeProject/remove")
def remove(body: dict, db: Session = Depends(get_db), auth=Depends(require_admin)):
    return {"message": "Removed"}


@router.get("/employeeProject/employee/{proj_id}")
def get_employees(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return []
