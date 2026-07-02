from datetime import date
from sqlalchemy.orm import Session
from app.core.models import Application, User


def _serialize(a: Application) -> dict:
    user = a.user
    return {
        "id": a.id,
        "user_id": a.user_id,
        "user": {"fullname": user.full_name, "id": user.id, "departmentId": user.department_id} if user else None,
        "status": a.status,
        "type": a.type,
        "reason": a.reason,
        "start_date": str(a.start_date)[:10] if a.start_date else None,
        "end_date": str(a.end_date)[:10] if a.end_date else None,
        "year": a.year,
        "month": a.month,
        "departmentId": user.department_id if user else None,
    }


def create(db: Session, payload: dict):
    try:
        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])
    except Exception:
        return 400, {"error": "Invalid date format. Use YYYY-MM-DD."}

    # Reject past start dates
    if start < date.today():
        return 400, {"error": "Leave start date cannot be in the past."}

    # Reject if an overlapping leave already exists for this employee
    overlap = db.query(Application).filter(
        Application.user_id == payload["user_id"],
        Application.start_date <= end,
        Application.end_date >= start,
    ).first()
    if overlap:
        return 409, {"error": f"A leave application already exists for overlapping dates ({overlap.start_date} – {overlap.end_date})."}

    record = Application(
        user_id=payload["user_id"],
        status="Pending",
        type=payload.get("type", "Casual Leave"),
        reason=payload.get("reason"),
        start_date=start,
        end_date=end,
        year=payload.get("year", start.year),
        month=payload.get("month", start.month),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, _serialize(record)


def get_all(db: Session):
    records = (
        db.query(Application)
        .join(User, Application.user_id == User.id)
        .order_by(Application.id.desc())
        .all()
    )
    return [_serialize(r) for r in records]


def get_by_user(db: Session, user_id: int):
    records = (
        db.query(Application)
        .filter(Application.user_id == user_id)
        .order_by(Application.id.desc())
        .all()
    )
    return [_serialize(r) for r in records]


def get_recent_by_user(db: Session, user_id: int, limit: int = 5):
    records = (
        db.query(Application)
        .filter(Application.user_id == user_id)
        .order_by(Application.id.desc())
        .limit(limit)
        .all()
    )
    return [_serialize(r) for r in records]


def get_by_department(db: Session, dept_id: int):
    records = (
        db.query(Application)
        .join(User, Application.user_id == User.id)
        .filter(User.department_id == dept_id)
        .order_by(Application.id.desc())
        .all()
    )
    return [_serialize(r) for r in records]


def get_one(db: Session, record_id: int):
    record = db.query(Application).filter(Application.id == record_id).first()
    if not record:
        return 404, {"error": "Leave application not found."}
    return 200, _serialize(record)


def update_status(db: Session, record_id: int, status: str):
    record = db.query(Application).filter(Application.id == record_id).first()
    if not record:
        return 404, {"error": "Leave application not found."}
    record.status = status
    db.commit()
    db.refresh(record)
    return 200, _serialize(record)


def delete(db: Session, record_id: int):
    record = db.query(Application).filter(Application.id == record_id).first()
    if not record:
        return 404, {"error": "Leave application not found."}
    db.delete(record)
    db.commit()
    return 200, {"message": "Leave application deleted."}
