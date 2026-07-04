from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import Project, User, ProjectManager

router = APIRouter(tags=["Projects"])


def _s(p: Project, db: Session = None):
    managers, employees = [], []
    if db is not None:
        pms = db.query(ProjectManager).filter(ProjectManager.project_id == p.id).all()
        managers = [
            {"id": pm.manager_user.id, "fullName": pm.manager_user.full_name, "jobTitle": pm.manager_user.job_title}
            for pm in pms if pm.manager_user
        ]
        emps = db.query(User).filter(User.project_id == p.id, User.end_date == None).all()
        employees = [
            {"id": u.id, "fullName": u.full_name, "jobTitle": u.job_title, "role": u.role}
            for u in emps
        ]
    return {
        "id": p.id,
        "name": p.name,
        "status": p.status or "Active",
        "description": p.description,
        "customerId": p.customer_id,
        "startDate": str(p.start_date) if p.start_date else None,
        "endDate": str(p.end_date) if p.end_date else None,
        "managerCount": len(managers),
        "employeeCount": len(employees),
        "managers": managers,
        "employees": employees,
    }


class ProjectBody(BaseModel):
    name: str
    customerId: Optional[int] = None
    status: Optional[str] = "Active"
    description: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class AssignManagerBody(BaseModel):
    managerId: int


class AssignEmployeeBody(BaseModel):
    userId: int
    projectId: int


@router.get("/project")
def get_all(db: Session = Depends(get_db), auth=Depends(require_token)):
    projects = db.query(Project).order_by(Project.id).all()
    result = []
    for p in projects:
        mc = db.query(ProjectManager).filter(ProjectManager.project_id == p.id).count()
        ec = db.query(User).filter(User.project_id == p.id, User.end_date == None).count()
        result.append({
            "id": p.id, "name": p.name,
            "status": p.status or "Active",
            "description": p.description,
            "customerId": p.customer_id,
            "startDate": str(p.start_date) if p.start_date else None,
            "endDate": str(p.end_date) if p.end_date else None,
            "managerCount": mc,
            "employeeCount": ec,
        })
    return result


@router.get("/project/{proj_id}")
def get_one(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _s(p, db)


@router.post("/project")
def create(body: ProjectBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    from datetime import date
    p = Project(
        name=body.name,
        status=body.status or "Active",
        description=body.description,
        customer_id=body.customerId,
    )
    if body.startDate:
        try:
            p.start_date = date.fromisoformat(body.startDate)
        except Exception:
            pass
    if body.endDate:
        try:
            p.end_date = date.fromisoformat(body.endDate)
        except Exception:
            pass
    db.add(p)
    db.commit()
    db.refresh(p)
    return JSONResponse(status_code=201, content=_s(p))


@router.put("/project/{proj_id}")
def update(proj_id: int, body: ProjectBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    from datetime import date
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    p.name = body.name
    if body.status:
        p.status = body.status
    if body.description is not None:
        p.description = body.description
    if body.customerId is not None:
        p.customer_id = body.customerId
    if body.startDate:
        try:
            p.start_date = date.fromisoformat(body.startDate)
        except Exception:
            pass
    if body.endDate:
        try:
            p.end_date = date.fromisoformat(body.endDate)
        except Exception:
            pass
    db.commit()
    return _s(p, db)


@router.delete("/project/{proj_id}")
def delete(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    emp_count = db.query(User).filter(User.project_id == proj_id).count()
    if emp_count > 0:
        return JSONResponse(
            status_code=400,
            content={"error": f"Cannot delete: {emp_count} employee(s) still assigned. Reassign them first."},
        )
    db.delete(p)
    db.commit()
    return {"message": "Deleted"}


# ── Manager assignment ────────────────────────────────────────────────────────

@router.get("/project/{proj_id}/managers")
def get_managers(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    pms = db.query(ProjectManager).filter(ProjectManager.project_id == proj_id).all()
    return [
        {"id": pm.manager_user.id, "fullName": pm.manager_user.full_name, "jobTitle": pm.manager_user.job_title}
        for pm in pms if pm.manager_user
    ]


@router.post("/project/{proj_id}/managers")
def assign_manager(proj_id: int, body: AssignManagerBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Project not found"})
    mgr = db.query(User).filter(User.id == body.managerId).first()
    if not mgr:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    existing = db.query(ProjectManager).filter(
        ProjectManager.project_id == proj_id,
        ProjectManager.manager_id == body.managerId,
    ).first()
    if existing:
        return JSONResponse(status_code=400, content={"error": "Manager already assigned to this project"})
    db.add(ProjectManager(project_id=proj_id, manager_id=body.managerId))
    db.commit()
    return {"message": "Manager assigned"}


@router.delete("/project/{proj_id}/managers/{manager_id}")
def remove_manager(proj_id: int, manager_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    pm = db.query(ProjectManager).filter(
        ProjectManager.project_id == proj_id,
        ProjectManager.manager_id == manager_id,
    ).first()
    if not pm:
        return JSONResponse(status_code=404, content={"error": "Assignment not found"})
    db.delete(pm)
    db.commit()
    return {"message": "Manager removed"}


# ── Employee assignment ───────────────────────────────────────────────────────

@router.get("/project/{proj_id}/employees")
def get_project_employees(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    users = db.query(User).filter(User.project_id == proj_id, User.end_date == None).all()
    return [{"id": u.id, "fullName": u.full_name, "jobTitle": u.job_title, "role": u.role} for u in users]


@router.put("/project/{proj_id}/employees/{user_id}")
def assign_employee_to_project(proj_id: int, user_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"error": "Project not found"})
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    u.project_id = proj_id
    db.commit()
    return {"message": "Employee assigned to project"}


@router.delete("/project/{proj_id}/employees/{user_id}")
def remove_employee_from_project(proj_id: int, user_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id, User.project_id == proj_id).first()
    if not u:
        return JSONResponse(status_code=404, content={"error": "User not found in this project"})
    u.project_id = None
    db.commit()
    return {"message": "Employee removed from project"}


# ── Legacy endpoints (kept for compatibility) ─────────────────────────────────

@router.post("/employeeProject/assign")
def assign_legacy(body: AssignEmployeeBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    u = db.query(User).filter(User.id == body.userId).first()
    if not u:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    u.project_id = body.projectId
    db.commit()
    return {"message": "Assigned"}


@router.put("/employeeProject/remove")
def remove_legacy(body: dict, db: Session = Depends(get_db), auth=Depends(require_admin)):
    u = db.query(User).filter(User.id == body.get("userId")).first()
    if u:
        u.project_id = None
        db.commit()
    return {"message": "Removed"}


@router.get("/employeeProject/employee/{proj_id}")
def get_employees_legacy(proj_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    users = db.query(User).filter(User.project_id == proj_id, User.end_date == None).all()
    return [{"id": u.id, "fullName": u.full_name} for u in users]
