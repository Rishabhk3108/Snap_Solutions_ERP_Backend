from sqlalchemy.orm import Session
from app.core.models import ExpenseHeader, ExpenseDetail


def _serialize(e: ExpenseHeader) -> dict:
    return {
        "id": e.id,
        "empid": e.empid,
        "title": e.title,
        "totalAmount": e.total_amount,
        "status": e.status,
        "date": str(e.date) if e.date else None,
        "description": e.description,
        "createdAt": str(e.created_at) if e.created_at else None,
    }


def _serialize_detail(d: ExpenseDetail) -> dict:
    return {
        "id": d.id,
        "expenseHeaderId": d.expense_header_id,
        "category": d.category,
        "amount": d.amount,
        "description": d.description,
        "receiptUrl": d.receipt_url,
    }


def create(db: Session, payload: dict):
    record = ExpenseHeader(
        empid=payload["empid"],
        title=payload["title"],
        total_amount=payload.get("totalAmount"),
        status="Pending",
        date=payload.get("date"),
        description=payload.get("description"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, _serialize(record)


def get_all(db: Session):
    return [_serialize(e) for e in db.query(ExpenseHeader).order_by(ExpenseHeader.id.desc()).all()]


def get_by_emp(db: Session, empid: int):
    return [_serialize(e) for e in db.query(ExpenseHeader).filter(ExpenseHeader.empid == empid).order_by(ExpenseHeader.id.desc()).all()]


def get_list(db: Session):
    return [_serialize(e) for e in db.query(ExpenseHeader).order_by(ExpenseHeader.id.desc()).all()]


def delete(db: Session, record_id: int):
    record = db.query(ExpenseHeader).filter(ExpenseHeader.id == record_id).first()
    if not record:
        return 404, {"error": "Expense not found."}
    db.delete(record)
    db.commit()
    return 200, {"message": "Expense deleted."}


def update_status(db: Session, record_id: int, status: str):
    record = db.query(ExpenseHeader).filter(ExpenseHeader.id == record_id).first()
    if not record:
        return 404, {"error": "Expense not found."}
    record.status = status
    db.commit()
    return 200, _serialize(record)


def pending_count(db: Session):
    count = db.query(ExpenseHeader).filter(ExpenseHeader.status == "Pending").count()
    return {"count": count}


def get_details(db: Session, header_id: int):
    return [_serialize_detail(d) for d in db.query(ExpenseDetail).filter(ExpenseDetail.expense_header_id == header_id).all()]


def add_detail(db: Session, payload: dict):
    d = ExpenseDetail(
        expense_header_id=payload["expenseHeaderId"],
        category=payload.get("category"),
        amount=payload.get("amount"),
        description=payload.get("description"),
        receipt_url=payload.get("receiptUrl"),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return 201, _serialize_detail(d)
