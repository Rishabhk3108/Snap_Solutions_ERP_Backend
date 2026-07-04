from datetime import date
from sqlalchemy.orm import Session
from app.core.models import UserFinancialInfo


def _serialize(f: UserFinancialInfo) -> dict:
    return {
        "id": f.id,
        "userId": f.user_id,
        "employmentType": f.employment_type,
        "salaryBasic": f.salary_basic,
        "salaryGross": f.salary_gross,
        "salaryNet": f.salary_net,
        "salaryBalance": f.salary_balance,
        "tripBalance": f.trip_balance,
        "allowanceHouseRent": f.allowance_house_rent,
        "allowanceMedical": f.allowance_medical,
        "allowanceSpecial": f.allowance_special,
        "allowanceTravelling": f.allowance_travelling,
        "allowanceOther": f.allowance_other,
        "allowanceTotal": f.allowance_total,
        "deductionProvidentFund": f.deduction_provident_fund,
        "deductionProfessionalTax": f.deduction_professional_tax,
        "deductionTax": f.deduction_tax,
        "deductionOther": f.deduction_other,
        "deductionTotal": f.deduction_total,
        "bankName": f.bank_name,
        "accountName": f.account_name,
        "accountNumber": f.account_number,
        "iban": f.iban,
        "startDate": str(f.start_date) if f.start_date else None,
        "endDate": str(f.end_date) if f.end_date else None,
        "otStatus": f.ot_status,
        "esicStatus": f.esic_status,
        "OtWorkingHours": f.ot_working_hours,
        "panNumber": f.pan_number,
        "esicNumber": f.esic_number,
        "pfNumber": f.pf_number,
    }


def create(db: Session, body: dict):
    user_id = body.get("userId")
    existing = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == user_id,
        UserFinancialInfo.end_date == None,
    ).first()
    if existing and (existing.salary_basic is not None or existing.employment_type is not None):
        return 403, {"message": "Financial Information Already Exists for this User"}

    if existing:
        # Stub from register — fill it in
        return update_by_user_id(db, user_id, body)

    fi = _build(body)
    db.add(fi)
    db.commit()
    db.refresh(fi)
    return 200, _serialize(fi)


def find_all(db: Session):
    records = db.query(UserFinancialInfo).all()
    return [_serialize(r) for r in records]


def find_by_user_id(db: Session, user_id: int):
    records = db.query(UserFinancialInfo).filter(UserFinancialInfo.user_id == user_id).all()
    return [_serialize(r) for r in records]


def find_one(db: Session, record_id: int):
    fi = db.query(UserFinancialInfo).filter(UserFinancialInfo.id == record_id).first()
    if not fi:
        return 404, {"message": f"Financial info with id={record_id} not found"}
    return 200, _serialize(fi)


def update_by_user_id(db: Session, user_id: int, body: dict):
    fi = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == user_id,
        UserFinancialInfo.end_date == None,
    ).first()
    if not fi:
        return 404, {"message": f"No financial info for user_id={user_id}"}

    _apply(fi, body)
    db.commit()
    return 200, {"message": "UserFinancialInformation was updated successfully."}


def salary_update(db: Session, user_id: int, salary_basic: int, salary_gross: int, salary_net: int):
    existing = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == user_id,
        UserFinancialInfo.end_date == None,
    ).first()
    if not existing:
        return 404, {"message": "User financial information not found."}

    existing.end_date = date.today()
    db.flush()

    new_record = UserFinancialInfo(
        user_id=user_id,
        employment_type=existing.employment_type,
        salary_basic=salary_basic,
        salary_gross=salary_gross,
        salary_net=salary_net,
        allowance_house_rent=existing.allowance_house_rent,
        allowance_medical=existing.allowance_medical,
        allowance_special=existing.allowance_special,
        allowance_travelling=existing.allowance_travelling,
        allowance_other=existing.allowance_other,
        allowance_total=existing.allowance_total,
        bank_name=existing.bank_name,
        account_name=existing.account_name,
        account_number=existing.account_number,
        iban=existing.iban,
        start_date=date.today(),
        end_date=None,
        ot_status=existing.ot_status,
        esic_status=existing.esic_status,
        pan_number=existing.pan_number,
        esic_number=existing.esic_number,
        pf_number=existing.pf_number,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return 200, {"message": "Salary updated successfully.", "newSalaryRecord": _serialize(new_record)}


def get_advances(db: Session, user_id: int):
    fi = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == user_id,
        UserFinancialInfo.end_date == None,
    ).first()
    if not fi:
        return 404, {"message": "User financial info not found"}
    return 200, {
        "userId": user_id,
        "salaryAdvance": fi.salary_balance,
        "tripAdvance": fi.trip_balance,
    }


def delete_record(db: Session, record_id: int):
    fi = db.query(UserFinancialInfo).filter(UserFinancialInfo.id == record_id).first()
    if not fi:
        return 404, {"message": f"Financial info with id={record_id} not found"}
    db.delete(fi)
    db.commit()
    return 200, {"message": "UserFinancialInformation was deleted successfully!"}


def _build(body: dict) -> UserFinancialInfo:
    return UserFinancialInfo(
        user_id=body.get("userId"),
        employment_type=body.get("employmentType"),
        salary_basic=body.get("salaryBasic"),
        salary_gross=body.get("salaryGross"),
        salary_net=body.get("salaryNet"),
        allowance_house_rent=body.get("allowanceHouseRent"),
        allowance_medical=body.get("allowanceMedical"),
        allowance_special=body.get("allowanceSpecial"),
        allowance_travelling=body.get("allowanceTravelling"),
        allowance_other=body.get("allowanceOther"),
        allowance_total=body.get("allowanceTotal"),
        deduction_provident_fund=body.get("deductionProvidentFund"),
        deduction_professional_tax=body.get("deductionProfessionalTax"),
        deduction_tax=body.get("deductionTax"),
        deduction_other=body.get("deductionOther"),
        deduction_total=body.get("deductionTotal"),
        bank_name=body.get("bankName"),
        account_name=body.get("accountName"),
        account_number=body.get("accountNumber"),
        iban=body.get("iban"),
        ot_status=body.get("otStatus", "No"),
        esic_status=body.get("esicStatus", "No"),
        ot_working_hours=body.get("OtWorkingHours", 8),
        pan_number=body.get("panNumber"),
        esic_number=body.get("esicNumber"),
        pf_number=body.get("pfNumber"),
    )


def _apply(fi: UserFinancialInfo, body: dict):
    field_map = {
        "employmentType": "employment_type",
        "salaryBasic": "salary_basic", "salaryGross": "salary_gross",
        "salaryNet": "salary_net", "salaryBalance": "salary_balance",
        "tripBalance": "trip_balance",
        "allowanceHouseRent": "allowance_house_rent",
        "allowanceMedical": "allowance_medical", "allowanceSpecial": "allowance_special",
        "allowanceTravelling": "allowance_travelling",
        "allowanceOther": "allowance_other", "allowanceTotal": "allowance_total",
        "deductionProvidentFund": "deduction_provident_fund",
        "deductionProfessionalTax": "deduction_professional_tax",
        "deductionTax": "deduction_tax", "deductionOther": "deduction_other",
        "deductionTotal": "deduction_total",
        "bankName": "bank_name", "accountName": "account_name",
        "accountNumber": "account_number", "iban": "iban",
        "startDate": "start_date", "endDate": "end_date",
        "otStatus": "ot_status", "esicStatus": "esic_status",
        "OtWorkingHours": "ot_working_hours",
        "panNumber": "pan_number", "esicNumber": "esic_number",
        "pfNumber": "pf_number",
    }
    for key, attr in field_map.items():
        if key in body:
            setattr(fi, attr, body[key])
