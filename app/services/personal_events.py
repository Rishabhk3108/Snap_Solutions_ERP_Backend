from sqlalchemy.orm import Session
from app.core.models import PersonalEvent


def _serialize(e: PersonalEvent) -> dict:
    return {
        "id": e.id,
        "userId": e.user_id,
        "title": e.title,
        "date": str(e.date) if e.date else None,
        "type": e.type,
        "description": e.description,
    }


def create(db: Session, payload: dict):
    record = PersonalEvent(
        user_id=payload["userId"],
        title=payload["title"],
        date=payload["date"],
        type=payload.get("type", "Personal"),
        description=payload.get("description"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, _serialize(record)


def get_by_user(db: Session, user_id: int):
    return [_serialize(e) for e in db.query(PersonalEvent).filter(
        PersonalEvent.user_id == user_id
    ).order_by(PersonalEvent.date.desc()).all()]


def update(db: Session, record_id: int, payload: dict):
    record = db.query(PersonalEvent).filter(PersonalEvent.id == record_id).first()
    if not record:
        return 404, {"error": "Event not found."}
    for key, attr in {"title": "title", "date": "date", "type": "type", "description": "description"}.items():
        if key in payload:
            setattr(record, attr, payload[key])
    db.commit()
    return 200, _serialize(record)


def delete(db: Session, record_id: int):
    record = db.query(PersonalEvent).filter(PersonalEvent.id == record_id).first()
    if not record:
        return 404, {"error": "Event not found."}
    db.delete(record)
    db.commit()
    return 200, {"message": "Event deleted."}
