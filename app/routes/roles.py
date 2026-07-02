from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token, require_admin
from app.core.models import Role, Permission, RolePermission

router = APIRouter(tags=["Roles"])


class RoleBody(BaseModel):
    name: str
    description: Optional[str] = None


class PermBody(BaseModel):
    name: str
    description: Optional[str] = None


class AssignBody(BaseModel):
    roleId: int
    permissionId: int


def _role(r: Role):
    return {"id": r.id, "name": r.name, "description": r.description, "deleted": r.deleted}


def _perm(p: Permission):
    return {"id": p.id, "name": p.name, "description": p.description}


def _rp(rp: RolePermission):
    return {"id": rp.id, "roleId": rp.role_id, "permissionId": rp.permission_id,
            "roleName": rp.role.name if rp.role else None,
            "permissionName": rp.permission.name if rp.permission else None}


# ---- Roles ----
@router.get("/role")
def list_roles(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_role(r) for r in db.query(Role).filter(Role.deleted == False).all()]


@router.post("/role")
def create_role(body: RoleBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    r = Role(name=body.name, description=body.description)
    db.add(r); db.commit(); db.refresh(r)
    return JSONResponse(status_code=201, content=_role(r))


@router.put("/role/{role_id}")
def update_role(role_id: int, body: RoleBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    r = db.query(Role).filter(Role.id == role_id).first()
    if not r:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    r.name = body.name; r.description = body.description
    db.commit()
    return _role(r)


@router.delete("/role/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    r = db.query(Role).filter(Role.id == role_id).first()
    if not r:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    r.deleted = True; db.commit()
    return {"message": "Role soft-deleted"}


@router.patch("/role/restore/{role_id}")
def restore_role(role_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    r = db.query(Role).filter(Role.id == role_id).first()
    if not r:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    r.deleted = False; db.commit()
    return _role(r)


# ---- Permissions ----
@router.get("/permission")
def list_permissions(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_perm(p) for p in db.query(Permission).all()]


@router.post("/permission")
def create_permission(body: PermBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = Permission(name=body.name, description=body.description)
    db.add(p); db.commit(); db.refresh(p)
    return JSONResponse(status_code=201, content=_perm(p))


@router.put("/permission/{perm_id}")
def update_permission(perm_id: int, body: PermBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    p = db.query(Permission).filter(Permission.id == perm_id).first()
    if not p:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    p.name = body.name; p.description = body.description
    db.commit()
    return _perm(p)


# ---- Role-Permission mappings ----
@router.get("/rolePermission")
def list_role_permissions(db: Session = Depends(get_db), auth=Depends(require_token)):
    return [_rp(rp) for rp in db.query(RolePermission).all()]


@router.get("/rolePermission/rolePermission/{role_id}")
def get_permissions_for_role(role_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    rps = db.query(RolePermission).filter(RolePermission.role_id == role_id).all()
    return [_perm(rp.permission) for rp in rps if rp.permission]


@router.post("/rolePermission")
def assign_permission(body: AssignBody, db: Session = Depends(get_db), auth=Depends(require_admin)):
    existing = db.query(RolePermission).filter(
        RolePermission.role_id == body.roleId,
        RolePermission.permission_id == body.permissionId
    ).first()
    if existing:
        return JSONResponse(status_code=409, content={"message": "Already assigned"})
    rp = RolePermission(role_id=body.roleId, permission_id=body.permissionId)
    db.add(rp); db.commit(); db.refresh(rp)
    return JSONResponse(status_code=201, content=_rp(rp))


@router.delete("/rolePermission/delete")
def remove_permission(id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    rp = db.query(RolePermission).filter(RolePermission.id == id).first()
    if not rp:
        return JSONResponse(status_code=404, content={"message": "Not found"})
    db.delete(rp); db.commit()
    return {"message": "Removed"}
