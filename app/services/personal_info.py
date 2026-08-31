from datetime import date
from sqlalchemy.orm import Session
from app.core.models import User, UserPersonalInfo

# Fields the mobile onboarding wizard itself treats as mandatory (see
# PersonalDetailsScreen.js). Used to derive onboarding completion from data,
# not from who filled it in.
REQUIRED_ONBOARDING_FIELDS = ("mobile", "nominee_name", "nominee_relationship")


def _serialize(p: UserPersonalInfo) -> dict:
    return {
        "id": p.id,
        "userId": p.user_id,
        "dateOfBirth": str(p.date_of_birth) if p.date_of_birth else None,
        "gender": p.gender,
        "maritalStatus": p.marital_status,
        "fatherName": p.father_name,
        "idNumber": p.id_number,
        "address": p.address,
        "city": p.city,
        "state": p.state,
        "country": p.country,
        "mobile": p.mobile,
        "phone": p.phone,
        "emailAddress": p.email_address,
        "nomineeName": p.nominee_name,
        "nomineeRelationship": p.nominee_relationship,
    }


def create(db: Session, body: dict):
    user_id = body.get("userId")
    existing = db.query(UserPersonalInfo).filter(UserPersonalInfo.user_id == user_id).first()
    if existing:
        # If stub already exists (created by register), update it instead
        return update_by_user_id(db, user_id, body)

    pi = UserPersonalInfo(
        user_id=user_id,
        date_of_birth=body.get("dateOfBirth"),
        gender=body.get("gender"),
        marital_status=body.get("maritalStatus"),
        father_name=body.get("fatherName"),
        id_number=body.get("idNumber"),
        address=body.get("address"),
        city=body.get("city"),
        state=body.get("state"),
        country=body.get("country"),
        mobile=body.get("mobile"),
        phone=body.get("phone"),
        email_address=body.get("emailAddress"),
        nominee_name=body.get("nomineeName"),
        nominee_relationship=body.get("nomineeRelationship"),
    )
    db.add(pi)
    db.commit()
    db.refresh(pi)
    return 200, _serialize(pi)


def find_by_user_id(db: Session, user_id: int):
    record = db.query(UserPersonalInfo).filter(UserPersonalInfo.user_id == user_id).first()
    return _serialize(record) if record else None


def find_one(db: Session, record_id: int):
    pi = db.query(UserPersonalInfo).filter(UserPersonalInfo.id == record_id).first()
    if not pi:
        return 404, {"message": f"Personal info with id={record_id} not found"}
    return 200, _serialize(pi)


def update_by_user_id(db: Session, user_id: int, body: dict):
    pi = db.query(UserPersonalInfo).filter(UserPersonalInfo.user_id == user_id).first()
    if not pi:
        pi = UserPersonalInfo(user_id=user_id)
        db.add(pi)

    field_map = {
        "dateOfBirth": "date_of_birth",
        "gender": "gender",
        "maritalStatus": "marital_status",
        "fatherName": "father_name",
        "idNumber": "id_number",
        "address": "address",
        "city": "city",
        "state": "state",
        "country": "country",
        "mobile": "mobile",
        "phone": "phone",
        "emailAddress": "email_address",
        "nomineeName": "nominee_name",
        "nomineeRelationship": "nominee_relationship",
    }
    for key, attr in field_map.items():
        if key in body:
            setattr(pi, attr, body[key])

    db.commit()
    return 200, {"message": "UserPersonalInformation was updated successfully."}


def delete_record(db: Session, record_id: int):
    pi = db.query(UserPersonalInfo).filter(UserPersonalInfo.id == record_id).first()
    if not pi:
        return 404, {"message": f"Personal info with id={record_id} not found"}
    db.delete(pi)
    db.commit()
    return 200, {"message": "UserPersonalInformation was deleted successfully!"}


def sync_onboarding_flag(db: Session, user_id: int) -> bool:
    """
    Derive User.onboarding_complete from the presence of required personal-info
    data instead of relying solely on the mobile app's explicit "finish
    onboarding" call, so data entered by an admin (on their own or on the
    employee's behalf) unblocks login the same way self-service entry does.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return False
    if user.onboarding_complete:
        return True

    pi = db.query(UserPersonalInfo).filter(UserPersonalInfo.user_id == user_id).first()
    if pi and all(getattr(pi, field) for field in REQUIRED_ONBOARDING_FIELDS):
        user.onboarding_complete = True
        db.commit()
        return True

    return False
