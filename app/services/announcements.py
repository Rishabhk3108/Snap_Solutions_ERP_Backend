from sqlalchemy.orm import Session
from app.core.models import DepartmentAnnouncement


def _serialize(a: DepartmentAnnouncement) -> dict:
    return {
        "id": a.id,
        "departmentId": a.department_id,
        "title": a.title,
        "content": a.content,
        "createdBy": a.created_by,
        "createdAt": str(a.created_at) if a.created_at else None,
    }


def get_all(db: Session):
    return [_serialize(a) for a in db.query(DepartmentAnnouncement).order_by(DepartmentAnnouncement.id.desc()).all()]


def get_by_dept(db: Session, dept_id: int):
    return [_serialize(a) for a in db.query(DepartmentAnnouncement).filter(
        DepartmentAnnouncement.department_id == dept_id
    ).order_by(DepartmentAnnouncement.id.desc()).all()]


def get_recent_by_dept(db: Session, dept_id: int, limit: int = 5):
    return [_serialize(a) for a in db.query(DepartmentAnnouncement).filter(
        DepartmentAnnouncement.department_id == dept_id
    ).order_by(DepartmentAnnouncement.id.desc()).limit(limit).all()]


def create(db: Session, payload: dict):
    record = DepartmentAnnouncement(
        department_id=payload.get("departmentId"),
        title=payload["title"],
        content=payload.get("content"),
        created_by=payload.get("createdBy"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, _serialize(record)


def delete(db: Session, record_id: int):
    record = db.query(DepartmentAnnouncement).filter(DepartmentAnnouncement.id == record_id).first()
    if not record:
        return 404, {"error": "Announcement not found."}
    db.delete(record)
    db.commit()
    return 200, {"message": "Announcement deleted."}
