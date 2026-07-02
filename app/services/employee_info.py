from sqlalchemy.orm import Session
from app.core.models import EmployeeRecord


def _serialize(e: EmployeeRecord) -> dict:
    return {
        "id": e.id,
        "emailAddress": e.email_address,
        "Aadhaar_number": e.aadhaar_number,
        "pan_number": e.pan_number,
        "esic_number": e.esic_number,
        "pf_number": e.pf_number,
        "nominee_name": e.nominee_name,
        "nominee_relation": e.nominee_relation,
    }


def create(db: Session, body: dict):
    emp_id = body.get("id")
    record = EmployeeRecord(
        id=emp_id,
        email_address=body.get("emailAddress"),
        aadhaar_number=body.get("Aadhaar_number"),
        pan_number=body.get("pan_number"),
        esic_number=body.get("esic_number"),
        pf_number=body.get("pf_number"),
        nominee_name=body.get("nominee_name"),
        nominee_relation=body.get("nominee_relation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return 201, {"message": "Employee created successfully", "employee": _serialize(record)}


def get_by_id(db: Session, emp_id: int):
    record = db.query(EmployeeRecord).filter(EmployeeRecord.id == emp_id).first()
    if not record:
        return 404, {"message": "Employee not found"}
    return 200, {"message": "Employee details retrieved successfully", "employee": _serialize(record)}


def update(db: Session, user_id: int, body: dict):
    record = db.query(EmployeeRecord).filter(EmployeeRecord.id == user_id).first()
    if not record:
        return 404, {"message": f"Employee with userId {user_id} not found."}

    field_map = {
        "emailAddress": "email_address",
        "Aadhaar_number": "aadhaar_number",
        "pan_number": "pan_number",
        "esic_number": "esic_number",
        "pf_number": "pf_number",
        "nominee_name": "nominee_name",
        "nominee_relation": "nominee_relation",
    }
    for key, attr in field_map.items():
        if key in body:
            setattr(record, attr, body[key])

    db.commit()
    db.refresh(record)
    return 200, {"message": "Employee updated successfully", "employee": _serialize(record)}
