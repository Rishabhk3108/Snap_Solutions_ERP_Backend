import bcrypt
from sqlalchemy.orm import Session
from app.core.models import User, Department


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()


def _next_user_id(db: Session) -> int:
    from sqlalchemy import func
    max_id = db.query(func.max(User.id)).scalar()
    return (max_id or 0) + 1


def _serialize(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "fullName": u.full_name,
        "role": u.role,
        "roleId": u.role_id,
        "active": u.active,
        "jobTitle": u.job_title,
        "reportid": u.reportid,
        "endDate": str(u.end_date) if u.end_date else None,
        "remark": u.remark,
        "departmentId": u.department_id,
        "department": {"id": u.department.id, "departmentName": u.department.department_name}
        if u.department else None,
        "projectId": u.project_id,
        "projectName": u.project.name if u.project else None,
    }


def create_user(db: Session, body: dict):
    hashed = _hash(str(body["password"])) if body.get("password") else None

    existing = db.query(User).filter(User.username == body.get("username", "")).first()
    if existing:
        return 403, {"message": "Username already exists"}

    new_id = _next_user_id(db)
    user = User(
        id=new_id,
        username=body.get("username", ""),
        password=hashed,
        full_name=body.get("fullname") or body.get("fullName", ""),
        role=body.get("role", "ROLE_EMPLOYEE"),
        active=bool(body.get("active")),
        job_title=body.get("jobTitle"),
        reportid=body.get("reportid"),
        role_id=body.get("roleId", 1),
        department_id=body.get("departmentId"),
    )
    db.add(user)
    db.flush()
    user.username = str(user.id)
    db.commit()
    db.refresh(user)
    return 200, _serialize(user)


def get_max_id(db: Session):
    from sqlalchemy import func
    max_id = db.query(func.max(User.id)).scalar()
    if max_id is None:
        return 404, {"message": "No users found in the database."}
    return 200, {"nextid": max_id + 1}


def get_all_users(db: Session, caller_role: str = None, caller_id: int = None):
    query = db.query(User).filter(User.end_date == None)
    if caller_role == "ROLE_MANAGER" and caller_id:
        from app.core.models import ProjectManager
        managed_ids = [pm.project_id for pm in db.query(ProjectManager).filter(ProjectManager.manager_id == caller_id).all()]
        if not managed_ids:
            return []
        query = query.filter(User.project_id.in_(managed_ids))
    return [_serialize(u) for u in query.all()]


def get_all_active(db: Session, caller_role: str = None, caller_id: int = None):
    query = db.query(User).filter(User.end_date == None)
    if caller_role == "ROLE_MANAGER" and caller_id:
        from app.core.models import ProjectManager
        managed_ids = [pm.project_id for pm in db.query(ProjectManager).filter(ProjectManager.manager_id == caller_id).all()]
        if not managed_ids:
            return []
        query = query.filter(User.project_id.in_(managed_ids))
    return [_serialize(u) for u in query.all()]


def get_all_exited(db: Session):
    users = db.query(User).filter(User.end_date != None).all()
    return [_serialize(u) for u in users]


def get_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"message": "User not found"}

    data = _serialize(user)

    # Include related records
    if user.personal_info:
        pi = user.personal_info
        data["user_personal_info"] = {
            "id": pi.id, "dateOfBirth": str(pi.date_of_birth) if pi.date_of_birth else None,
            "gender": pi.gender, "maritalStatus": pi.marital_status,
            "fatherName": pi.father_name, "idNumber": pi.id_number,
            "address": pi.address, "city": pi.city, "state": pi.state,
            "country": pi.country, "mobile": pi.mobile, "phone": pi.phone,
            "emailAddress": pi.email_address,
        }

    if user.financial_info:
        fi = user.financial_info
        data["user_financial_info"] = {
            "id": fi.id, "employmentType": fi.employment_type,
            "salaryBasic": fi.salary_basic, "salaryGross": fi.salary_gross,
            "salaryNet": fi.salary_net, "otStatus": fi.ot_status,
            "esicStatus": fi.esic_status, "OtWorkingHours": fi.ot_working_hours,
            "bankName": fi.bank_name, "accountName": fi.account_name,
            "accountNumber": fi.account_number, "iban": fi.iban,
        }

    if user.employee_record:
        er = user.employee_record
        data["employee"] = {
            "emailAddress": er.email_address,
            "Aadhaar_number": er.aadhaar_number,
            "pan_number": er.pan_number, "esic_number": er.esic_number,
            "pf_number": er.pf_number, "nominee_name": er.nominee_name,
            "nominee_relation": er.nominee_relation,
        }

    if user.reportid:
        reporter = db.query(User).filter(User.id == int(user.reportid)).first()
        if reporter:
            data["reportingUser"] = {"fullName": reporter.full_name, "reportid": reporter.id}

    return 200, data


def update_user(db: Session, user_id: int, body: dict):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"message": f"User with id={user_id} not found"}

    field_map = {
        "fullname": "full_name", "fullName": "full_name",
        "jobTitle": "job_title", "reportid": "reportid",
        "role": "role", "roleId": "role_id", "active": "active",
        "departmentId": "department_id", "endDate": "end_date",
        "remark": "remark",
    }
    for key, attr in field_map.items():
        if key in body:
            setattr(user, attr, body[key])

    db.commit()
    return 200, {"message": "User was updated successfully."}


def update_end_date(db: Session, user_id: int, end_date, remark: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"message": f"User with id={user_id} not found"}
    user.end_date = end_date
    user.remark = remark
    user.active = False
    db.commit()
    return 200, {"message": "User endDate and remark updated successfully."}


def update_password(db: Session, user_id: int, password: str):
    if not password or len(password) < 6:
        return 400, {"success": False, "message": "Password must be at least 6 characters long!"}
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"success": False, "message": "User not found with this empid!"}
    user.password = _hash(password)
    db.commit()
    return 200, {"success": True, "message": "Password updated successfully!"}


def change_password(db: Session, user_id: int, old_password: str, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 400, {"message": "No such user!"}
    if not user.password or not bcrypt.checkpw(old_password.encode(), user.password.encode()):
        return 400, {"message": "Wrong Password"}
    user.password = _hash(new_password)
    db.commit()
    return 200, {"message": "User was updated successfully."}


def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"message": f"User with id={user_id} not found"}
    db.delete(user)
    db.commit()
    return 200, {"message": "User was deleted successfully!"}


def get_by_department(db: Session, dept_id: int):
    users = db.query(User).filter(User.department_id == dept_id).all()
    return [_serialize(u) for u in users]


def get_reportees(db: Session, reportid: str):
    users = db.query(User).filter(User.reportid == str(reportid)).all()
    result = []
    for u in users:
        result.append({
            "id": u.id, "fullName": u.full_name, "jobTitle": u.job_title,
            "departmentName": u.department.department_name if u.department else "N/A",
        })
    return result


def verify_user(db: Session, user_id: int, date_of_birth, start_date):
    from datetime import date as date_type
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 404, {"success": False, "match": False, "message": "User not found"}
    pi = user.personal_info
    if not pi or not pi.date_of_birth:
        return 200, {"success": True, "match": False, "message": "DOB not found"}
    dob_match = pi.date_of_birth == date_of_birth
    return 200, {"success": True, "match": dob_match}


def get_total(db: Session):
    count = db.query(User).count()
    return str(count)


def get_total_by_dept(db: Session, dept_id: int):
    count = db.query(User).filter(User.department_id == dept_id).count()
    return str(count)
