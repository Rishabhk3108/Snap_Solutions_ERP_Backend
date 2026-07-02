from sqlalchemy.orm import Session
from app.core.models import Message, User


def _serialize(m: Message) -> dict:
    sender = m.sender
    return {
        "id": m.id,
        "senderId": m.sender_id,
        "receiverId": m.receiver_id,
        "subject": m.subject,
        "content": m.content,
        "createdAt": str(m.created_at) if m.created_at else None,
        "sender": {"fullname": sender.full_name} if sender else None,
    }


def create(db: Session, payload: dict):
    record = Message(
        sender_id=payload["senderId"],
        receiver_id=payload["receiverId"],
        subject=payload.get("subject"),
        content=payload["content"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, _serialize(record)


def get_for_user(db: Session, user_id: int):
    records = db.query(Message).filter(
        Message.receiver_id == user_id
    ).order_by(Message.id.desc()).all()
    return [_serialize(m) for m in records]


def get_one(db: Session, record_id: int):
    record = db.query(Message).filter(Message.id == record_id).first()
    if not record:
        return 404, {"error": "Message not found."}
    return 200, _serialize(record)
