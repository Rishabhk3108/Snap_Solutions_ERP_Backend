import math
from datetime import date, datetime, timedelta
from typing import Optional

import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.models import Application, Attendance, Project, Restdays, User, UserFinancialInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_time(t) -> Optional[str]:
    """Convert a PyMySQL TIME result (timedelta) to HH:MM:SS string."""
    if t is None:
        return None
    if isinstance(t, timedelta):
        total = int(t.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    return str(t)


def _fmt_date(d) -> Optional[str]:
    if d is None:
        return None
    return str(d)


def _td_to_hours(t) -> float:
    """timedelta (from PyMySQL TIME col) -> float hours."""
    if isinstance(t, timedelta):
        return t.total_seconds() / 3600
    return 0.0


def _hours_between(start_t, end_t) -> float:
    """Calculate worked hours between two TIME values (timedelta or str)."""
    if isinstance(start_t, timedelta) and isinstance(end_t, timedelta):
        diff = end_t - start_t
        return diff.total_seconds() / 3600
    # Fallback: parse HH:MM:SS strings
    def parse(v):
        parts = str(v).split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return (parse(end_t) - parse(start_t)) / 3600


def _calculate_hours_with_ot(start_t, end_t, financial_info) -> tuple[float, int]:
    """
    Returns (number_of_hours, ot_hours) applying the OT rounding rule:
    - Extra <= 90 min  -> 1 OT hour
    - Extra > 90 min   -> ceil(extra_minutes / 60) OT hours
    """
    actual = _hours_between(start_t, end_t)
    if actual <= 0:
        raise ValueError("endTime must be after startTime.")

    working_hours = financial_info.ot_working_hours or 0
    is_ot_allowed = (financial_info.ot_status or "").lower() == "yes"

    if is_ot_allowed:
        if actual > working_hours:
            number_of_hours = working_hours
            extra_minutes = (actual - working_hours) * 60
            ot_hours = 1 if extra_minutes <= 90 else math.ceil(extra_minutes / 60)
        else:
            number_of_hours = actual
            ot_hours = 0
    else:
        number_of_hours = min(actual, working_hours)
        ot_hours = 0

    return round(number_of_hours, 2), ot_hours


# ---------------------------------------------------------------------------
# Service functions (one per endpoint)
# ---------------------------------------------------------------------------

def add_attendance(
    db: Session,
    empid: int,
    project_id: int,
    date_str: str,
    start_time: str,
    location: str,
    year: int,
    month: int,
) -> dict:
    if not db.query(User).filter(User.id == empid).first():
        return {"status": 404, "error": f"User with ID {empid} does not exist."}

    if not db.query(Project).filter(Project.id == project_id).first():
        return {"status": 404, "error": f"Project with ID {project_id} does not exist."}

    existing = db.query(Attendance).filter(
        Attendance.empid == empid,
        Attendance.project_id == project_id,
        Attendance.date == date_str,
    ).first()
    if existing:
        return {"status": 400, "error": "Attendance already exists for this day."}

    record = Attendance(
        empid=empid,
        project_id=project_id,
        date=date_str,
        start_time=start_time,
        location=location,
        year=year,
        month=month,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"status": 200, "message": "Attendance added successfully.", "attendance": _serialize(record)}


def update_attendance(db: Session, empid: int, date_str: str, end_time: str) -> dict:
    record = db.query(Attendance).filter(
        Attendance.empid == empid,
        Attendance.date == date_str,
    ).first()

    if not record:
        return {"status": 404, "error": "Attendance record not found."}

    hours = _hours_between(record.start_time, end_time)
    record.end_time = end_time
    record.number_of_hours = round(hours, 2)
    db.commit()
    db.refresh(record)

    return {"status": 200, "message": "Attendance updated successfully.", "attendance": _serialize(record)}


def get_attendance_for_project(db: Session, project_id: int, date_str: str) -> dict:
    records = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .filter(Attendance.project_id == project_id, Attendance.date == date_str)
        .all()
    )

    result = [
        {
            "id": r.id,
            "empid": r.empid,
            "name": r.user.full_name,
            "location": r.location,
            "startTime": _fmt_time(r.start_time),
            "endTime": _fmt_time(r.end_time),
            "numberOfHours": r.number_of_hours,
        }
        for r in records
    ]
    return {"status": 200, "data": result}


def get_attendance_for_project_by_report_id(
    db: Session, project_id: int, date_str: str, empid: int
) -> dict:
    # Reportees: employees whose reportid equals the manager's empid
    reportee_records = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .filter(
            Attendance.project_id == project_id,
            Attendance.date == date_str,
            User.reportid == str(empid),
        )
        .all()
    )

    # Manager's own attendance
    self_record = db.query(Attendance).filter(
        Attendance.project_id == project_id,
        Attendance.date == date_str,
        Attendance.empid == empid,
    ).first()

    result = []
    for r in reportee_records:
        result.append({
            "empid": r.empid,
            "name": r.user.full_name,
            "location": r.location,
            "startTime": _fmt_time(r.start_time),
            "endTime": _fmt_time(r.end_time),
            "numberOfHours": r.number_of_hours,
        })

    if self_record:
        result.append({
            "empid": self_record.empid,
            "name": self_record.user.full_name,
            "location": self_record.location,
            "startTime": _fmt_time(self_record.start_time),
            "endTime": _fmt_time(self_record.end_time),
            "numberOfHours": self_record.number_of_hours,
        })

    return {"status": 200, "data": result}


def get_days_worked_in_month(db: Session, empid: int, year: int, month: int) -> dict:
    records = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .filter(Attendance.empid == empid, Attendance.year == year, Attendance.month == month)
        .all()
    )

    if not records:
        return {
            "status": 200,
            "data": {"empid": empid, "fullName": None, "year": year, "month": month, "daysWorked": 0},
        }

    days_worked = len({_fmt_date(r.date) for r in records})
    full_name = records[0].user.full_name

    return {
        "status": 200,
        "data": {
            "empid": empid,
            "fullName": full_name,
            "year": year,
            "month": month,
            "daysWorked": days_worked,
        },
    }


def get_attendance_list_for_employee(db: Session, empid: int, year: int, month: int) -> dict:
    records = (
        db.query(Attendance)
        .join(Project, Attendance.project_id == Project.id)
        .filter(Attendance.empid == empid, Attendance.year == year, Attendance.month == month)
        .order_by(Attendance.date.asc())
        .all()
    )

    if not records:
        return {
            "status": 200,
            "data": {"empid": empid, "year": year, "month": month, "attendanceList": []},
        }

    attendance_list = [
        {
            "date": _fmt_date(r.date),
            "projectId": r.project_id,
            "projectName": r.project.name if r.project else "N/A",
            "startTime": _fmt_time(r.start_time),
            "endTime": _fmt_time(r.end_time) or "Not Updated",
            "numberOfHours": r.number_of_hours or 0,
            "location": r.location,
        }
        for r in records
    ]

    return {
        "status": 200,
        "data": {"empid": empid, "year": year, "month": month, "attendanceList": attendance_list},
    }


def update_attendance_by_id(
    db: Session, record_id: int, start_time: Optional[str], end_time: Optional[str]
) -> dict:
    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        return {"status": 404, "error": f"Attendance record with ID {record_id} not found."}

    existing_start = record.start_time
    existing_end = record.end_time

    if start_time and end_time:
        record.start_time = start_time
        record.end_time = end_time
        hours = _hours_between(start_time, end_time)
        if hours <= 0:
            return {"status": 400, "error": "endTime must be after startTime."}
        record.number_of_hours = round(hours, 2)

    elif start_time:
        record.start_time = start_time
        if existing_end:
            hours = _hours_between(start_time, existing_end)
            if hours <= 0:
                return {"status": 400, "error": "endTime must be after startTime."}
            record.number_of_hours = round(hours, 2)

    elif end_time:
        record.end_time = end_time
        if existing_start:
            hours = _hours_between(existing_start, end_time)
            if hours <= 0:
                return {"status": 400, "error": "endTime must be after startTime."}
            record.number_of_hours = round(hours, 2)

    db.commit()
    db.refresh(record)
    return {"status": 200, "message": "Attendance updated successfully.", "attendance": _serialize(record)}


def update_attendance_by_id_with_pass(
    db: Session,
    record_id: int,
    start_time: Optional[str],
    end_time: Optional[str],
    username: str,
    password: str,
) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        return {"status": 401, "error": "Invalid username or password."}

    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        return {"status": 404, "error": f"Attendance record with ID {record_id} not found."}

    financial_info = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == record.empid
    ).first()
    if not financial_info:
        return {"status": 400, "error": "User financial info not found."}

    if start_time:
        record.start_time = start_time
    if end_time:
        record.end_time = end_time

    if record.start_time and record.end_time:
        try:
            number_of_hours, ot_hours = _calculate_hours_with_ot(
                record.start_time, record.end_time, financial_info
            )
            record.number_of_hours = number_of_hours
            record.ot_hours = ot_hours
        except ValueError as e:
            return {"status": 400, "error": str(e)}

    db.commit()
    db.refresh(record)
    return {
        "status": 200,
        "message": "Attendance updated successfully with OT logic.",
        "attendance": _serialize(record),
    }


def get_filtered_attendance(
    db: Session, start_date: str, end_date: str, project_id: Optional[int]
) -> dict:
    query = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .join(Project, Attendance.project_id == Project.id)
        .filter(Attendance.date.between(start_date, end_date))
        .order_by(Attendance.date.asc())
    )

    if project_id:
        query = query.filter(Attendance.project_id == project_id)

    records = query.all()
    if not records:
        return {"status": 400, "error": "No attendance records found for the given criteria."}

    result = [
        {
            "id": r.id,
            "empid": r.empid,
            "employeeName": r.user.full_name if r.user else "N/A",
            "jobTitle": r.user.job_title if r.user else "N/A",
            "projectId": r.project_id,
            "projectName": r.project.name if r.project else "N/A",
            "date": _fmt_date(r.date),
            "startTime": _fmt_time(r.start_time) or "N/A",
            "endTime": _fmt_time(r.end_time) or "N/A",
            "numberOfHours": r.number_of_hours or 0,
            "location": r.location or "N/A",
            "ot_hours": r.ot_hours,
        }
        for r in records
    ]
    return {"status": 200, "data": result}


def get_current_month_attendance_for_desktop(db: Session) -> dict:
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    first_day = today.replace(day=1).strftime("%Y-%m-%d")

    records = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .join(Project, Attendance.project_id == Project.id)
        .filter(
            Attendance.date.between(first_day, yesterday_str),
            Attendance.number_of_hours.is_(None),
            Attendance.end_time.is_(None),
        )
        .order_by(Attendance.date.asc())
        .all()
    )

    if not records:
        return {"status": 200, "data": []}

    result = [
        {
            "id": r.id,
            "empid": r.empid,
            "employeeName": r.user.full_name if r.user else "N/A",
            "username": r.user.username if r.user else "N/A",
            "jobTitle": r.user.job_title if r.user else "N/A",
            "projectId": r.project_id,
            "projectName": r.project.name if r.project else "N/A",
            "date": _fmt_date(r.date),
            "startTime": _fmt_time(r.start_time) or "N/A",
            "endTime": _fmt_time(r.end_time) or "N/A",
            "numberOfHours": r.number_of_hours or 0,
            "location": r.location or "N/A",
            "ot_hours": r.ot_hours or 0,
        }
        for r in records
    ]

    return {
        "status": 200,
        "data": {"fromDate": first_day, "toDate": yesterday_str, "records": result},
    }


def clean_invalid_attendances(db: Session) -> dict:
    today_str = datetime.today().strftime("%Y-%m-%d")

    rest_entries = db.query(Restdays).filter(Restdays.date == today_str).all()
    if not rest_entries:
        return {"status": 200, "message": "No rest days found for today. No action taken."}

    total_deleted = 0
    for entry in rest_entries:
        deleted = (
            db.query(Attendance)
            .filter(
                Attendance.project_id == entry.project_id,
                Attendance.empid == entry.empid,
                Attendance.date == today_str,
            )
            .delete(synchronize_session=False)
        )
        total_deleted += deleted

    db.commit()
    return {
        "status": 200,
        "message": f"{total_deleted} invalid attendance record(s) deleted for employees on rest day.",
    }


def get_attendance_by_filter_employee(
    db: Session, start_date: str, end_date: str, empid: Optional[str]
) -> dict:
    query = (
        db.query(Attendance)
        .join(User, Attendance.empid == User.id)
        .join(Project, Attendance.project_id == Project.id)
        .filter(Attendance.date.between(start_date, end_date))
        .order_by(Attendance.date.asc())
    )

    if empid and empid.lower() != "all":
        query = query.filter(Attendance.empid == int(empid))

    records = query.all()
    if not records:
        return {"status": 200, "data": []}

    result = [
        {
            "id": r.id,
            "empid": r.empid,
            "employeeName": r.user.full_name if r.user else "N/A",
            "projectId": r.project_id,
            "projectName": r.project.name if r.project else "N/A",
            "date": _fmt_date(r.date),
            "startTime": _fmt_time(r.start_time) or "N/A",
            "endTime": _fmt_time(r.end_time) or "N/A",
            "numberOfHours": r.number_of_hours or 0,
            "location": r.location or "N/A",
            "OtHours": r.ot_hours,
        }
        for r in records
    ]
    return {"status": 200, "data": result}


def add_full_attendance_with_ot(
    db: Session,
    empid: int,
    project_id: int,
    date_str: str,
    start_time: str,
    end_time: str,
    location: str,
) -> dict:
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"status": 400, "error": "Invalid date format."}

    year = parsed_date.year
    month = parsed_date.month

    if not db.query(User).filter(User.id == empid).first():
        return {"status": 400, "error": f"User with ID {empid} does not exist."}

    if not db.query(Project).filter(Project.id == project_id).first():
        return {"status": 400, "error": f"Project with ID {project_id} does not exist."}

    if db.query(Attendance).filter(
        Attendance.empid == empid,
        Attendance.project_id == project_id,
        Attendance.date == date_str,
    ).first():
        return {"status": 400, "error": "Attendance already exists for this day."}

    financial_info = db.query(UserFinancialInfo).filter(
        UserFinancialInfo.user_id == empid
    ).first()
    if not financial_info:
        return {"status": 400, "error": "User financial info not found."}

    try:
        number_of_hours, ot_hours = _calculate_hours_with_ot(start_time, end_time, financial_info)
    except ValueError as e:
        return {"status": 400, "error": str(e)}

    record = Attendance(
        empid=empid,
        project_id=project_id,
        date=date_str,
        start_time=start_time,
        end_time=end_time,
        location=location,
        year=year,
        month=month,
        number_of_hours=number_of_hours,
        ot_hours=ot_hours,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": 200,
        "message": "Attendance added successfully with OT logic.",
        "attendance": _serialize(record),
    }


def get_attendance_status(db: Session, empid: int, date_str: str) -> dict:
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # 1. Check approved leave application covering the date
    approved_leave = db.query(Application).filter(
        Application.status == "Approved",
        Application.user_id == empid,
        Application.start_date <= target_date,
        Application.end_date >= target_date,
    ).first()
    if approved_leave:
        return {"status": 200, "data": {"status": "L"}}

    # 2. Check rest day
    rest_day = db.query(Restdays).filter(
        Restdays.empid == empid,
        Restdays.date == target_date,
    ).first()
    if rest_day:
        return {"status": 200, "data": {"status": "R"}}

    # 3. PostgreSQL-compatible version of the Node.js TIMESTAMPDIFF logic
    row = db.execute(
        text("""
            SELECT date,
                   SUM(EXTRACT(EPOCH FROM (COALESCE(end_time, start_time) - start_time)) / 3600) AS total_hours
            FROM attendance
            WHERE empid = :empid AND date = :date
            GROUP BY date
        """),
        {"empid": empid, "date": str(target_date)},
    ).fetchone()

    if row and row.total_hours is not None:
        total_hours = float(row.total_hours)
        if total_hours == 0:
            return {"status": 200, "data": {"status": "NC"}}
        elif total_hours < 5:
            return {"status": 200, "data": {"status": "H"}}
        else:
            return {"status": 200, "data": {"status": "P"}}

    # 4. Absent
    return {"status": 200, "data": {"status": "A"}}


def get_todays_attendance_summary(db: Session) -> dict:
    today_str = datetime.today().strftime("%Y-%m-%d")
    total = db.query(User).filter(User.active == True).count()
    present = (
        db.query(Attendance.empid)
        .filter(
            Attendance.date == today_str,
            Attendance.start_time.isnot(None),
        )
        .distinct()
        .count()
    )
    absent = max(0, total - present)
    return {"status": 200, "data": {"present": present, "absent": absent, "total": total}}


# ---------------------------------------------------------------------------
# Internal serializer
# ---------------------------------------------------------------------------

def _serialize(r: Attendance) -> dict:
    return {
        "id": r.id,
        "empid": r.empid,
        "projectId": r.project_id,
        "date": _fmt_date(r.date),
        "startTime": _fmt_time(r.start_time),
        "endTime": _fmt_time(r.end_time),
        "numberOfHours": r.number_of_hours,
        "OtHours": r.ot_hours,
        "location": r.location,
        "year": r.year,
        "month": r.month,
    }
