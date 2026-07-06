import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_token
from app.services import attendance as svc

# ---------------------------------------------------------------------------
# In-memory job store for async face-verification check-ins.
# Key: short UUID string  Value: {"status": "processing"|"success"|"error", "message": str, "created_at": float}
# Entries are cleaned up after 30 minutes to prevent unbounded growth.
# Single-instance only — works on Railway's free tier.
# ---------------------------------------------------------------------------
_checkin_jobs: dict = {}


def _cleanup_old_jobs():
    cutoff = datetime.now(timezone.utc).timestamp() - 1800  # 30 min
    stale = [k for k, v in _checkin_jobs.items() if v.get("created_at", 0) < cutoff]
    for k in stale:
        del _checkin_jobs[k]


async def _run_face_checkin(
    job_id: str,
    empid: int,
    project_id: int,
    date: str,
    start_time: str,
    location: str,
    year: int,
    month: int,
    image_bytes: bytes,
):
    """
    Background coroutine: run face recognition in a thread executor so the event loop
    stays free, then save attendance only if the face passes.
    """
    from app.services import face as face_svc
    from app.core.models import FaceEncoding
    from app.core.database import SessionLocal

    try:
        loop = asyncio.get_running_loop()

        try:
            encoding = await asyncio.wait_for(
                loop.run_in_executor(None, face_svc.extract_encoding, image_bytes),
                timeout=300.0,  # 5-minute hard cap
            )
        except asyncio.TimeoutError:
            _checkin_jobs[job_id] = {
                "status": "error",
                "message": "Face verification timed out. Please try again.",
            }
            return

        if encoding is None:
            _checkin_jobs[job_id] = {
                "status": "error",
                "message": "No face detected. Please move to better lighting and try again.",
            }
            return

        db = SessionLocal()
        try:
            stored = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
            if stored is not None:
                result = face_svc.compare(stored.encoding, encoding)
                if not result["match"]:
                    _checkin_jobs[job_id] = {
                        "status": "error",
                        "message": "Face not recognized. Please retake the selfie or contact admin.",
                    }
                    return

            # Face passed (or no stored face yet) — save attendance NOW
            svc.add_attendance(db, empid, project_id, date, start_time, location, year, month)
            _checkin_jobs[job_id] = {"status": "success"}

        finally:
            db.close()

    except Exception:
        _checkin_jobs[job_id] = {
            "status": "error",
            "message": "Check-in failed unexpectedly. Please try again.",
        }

router = APIRouter()


# ---------------------------------------------------------------------------
# Request body schemas
# ---------------------------------------------------------------------------

class AddAttendanceBody(BaseModel):
    empid: int
    projectId: int
    date: str
    startTime: str
    location: str
    year: int
    month: int


class UpdateAttendanceBody(BaseModel):
    empid: int
    date: str
    endTime: str


class UpdateByIdBody(BaseModel):
    id: int
    startTime: Optional[str] = None
    endTime: Optional[str] = None


class UpdateByIdWithPassBody(BaseModel):
    id: int
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    username: str
    password: str


class AttendanceByDateRangeBody(BaseModel):
    projectId: Optional[int] = None
    startDate: str
    endDate: str


class AttendanceByFilterEmpBody(BaseModel):
    empid: Optional[str] = None
    startDate: str
    endDate: str


class AddFullAttendanceBody(BaseModel):
    empid: int
    projectId: int
    date: str
    startTime: str
    endTime: str
    location: str


class AttendanceStatusBody(BaseModel):
    empid: int
    date: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _respond(result: dict):
    status = result.pop("status", 200)
    if "error" in result:
        return JSONResponse(status_code=status, content={"error": result["error"]})
    # Unwrap "data" key when present, or return message/attendance directly
    payload = result.get("data", result)
    return JSONResponse(status_code=status, content=payload)


# ---------------------------------------------------------------------------
# Routes  (mirrors Node.js attendance.routes.js exactly)
# ---------------------------------------------------------------------------

# POST /api/attendance/add
@router.post("/add")
def add_attendance(body: AddAttendanceBody, db: Session = Depends(get_db)):
    result = svc.add_attendance(
        db, body.empid, body.projectId, body.date,
        body.startTime, body.location, body.year, body.month,
    )
    return _respond(result)


# PUT /api/attendance/update
@router.put("/update")
def update_attendance(body: UpdateAttendanceBody, db: Session = Depends(get_db)):
    result = svc.update_attendance(db, body.empid, body.date, body.endTime)
    return _respond(result)


# GET /api/attendance/project/{projectId}/date/{date}
@router.get("/project/{project_id}/date/{date}")
def get_attendance_for_project(project_id: int, date: str, db: Session = Depends(get_db)):
    result = svc.get_attendance_for_project(db, project_id, date)
    return _respond(result)


# GET /api/attendance/reportee/{projectId}/{date}/{empid}
@router.get("/reportee/{project_id}/{date}/{empid}")
def get_attendance_for_project_by_report_id(
    project_id: int, date: str, empid: int, db: Session = Depends(get_db)
):
    result = svc.get_attendance_for_project_by_report_id(db, project_id, date, empid)
    return _respond(result)


# GET /api/attendance/days-worked/{empid}/{year}/{month}
@router.get("/days-worked/{empid}/{year}/{month}")
def get_days_worked_in_month(empid: int, year: int, month: int, db: Session = Depends(get_db)):
    result = svc.get_days_worked_in_month(db, empid, year, month)
    return _respond(result)


# GET /api/attendance/list/{empid}/{year}/{month}
@router.get("/list/{empid}/{year}/{month}")
def get_attendance_list_for_employee(
    empid: int, year: int, month: int, db: Session = Depends(get_db)
):
    result = svc.get_attendance_list_for_employee(db, empid, year, month)
    return _respond(result)


# POST /api/attendance/updateById
@router.post("/updateById")
def update_attendance_by_id(body: UpdateByIdBody, db: Session = Depends(get_db)):
    if not body.id:
        return JSONResponse(status_code=400, content={"error": "ID is required."})
    result = svc.update_attendance_by_id(db, body.id, body.startTime, body.endTime)
    return _respond(result)


# POST /api/attendance/updatepass
@router.post("/updatepass")
def update_attendance_by_id_with_pass(body: UpdateByIdWithPassBody, db: Session = Depends(get_db)):
    result = svc.update_attendance_by_id_with_pass(
        db, body.id, body.startTime, body.endTime, body.username, body.password
    )
    return _respond(result)


# POST /api/attendance/attendanceByDateRange
@router.post("/attendanceByDateRange")
def get_filtered_attendance(body: AttendanceByDateRangeBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    caller = auth.get("user", {})
    result = svc.get_filtered_attendance(db, body.startDate, body.endDate, body.projectId,
                                         caller_role=caller.get("role"), caller_id=caller.get("id"))
    return _respond(result)


# GET /api/attendance/attendanceForDesktop
@router.get("/attendanceForDesktop")
def get_current_month_attendance_for_desktop(db: Session = Depends(get_db)):
    result = svc.get_current_month_attendance_for_desktop(db)
    return _respond(result)


# POST /api/attendance/cleanattendance
@router.post("/cleanattendance")
def clean_invalid_attendances(db: Session = Depends(get_db)):
    result = svc.clean_invalid_attendances(db)
    return _respond(result)


# POST /api/attendance/attendanceByFilterEmp
@router.post("/attendanceByFilterEmp")
def get_attendance_by_filter_employee(
    body: AttendanceByFilterEmpBody, db: Session = Depends(get_db), auth=Depends(require_token)
):
    caller = auth.get("user", {})
    result = svc.get_attendance_by_filter_employee(
        db, body.startDate, body.endDate, body.empid,
        caller_role=caller.get("role"), caller_id=caller.get("id"),
    )
    return _respond(result)


# POST /api/attendance/full
@router.post("/full")
def add_full_attendance_with_ot(body: AddFullAttendanceBody, db: Session = Depends(get_db)):
    result = svc.add_full_attendance_with_ot(
        db, body.empid, body.projectId, body.date,
        body.startTime, body.endTime, body.location,
    )
    return _respond(result)


# POST /api/attendance/getAttendanceStatus
@router.post("/getAttendanceStatus")
def get_attendance_status(body: AttendanceStatusBody, db: Session = Depends(get_db)):
    result = svc.get_attendance_status(db, body.empid, body.date)
    return _respond(result)


# GET /api/attendance/today-summary
@router.get("/today-summary")
def get_todays_attendance_summary(db: Session = Depends(get_db), auth=Depends(require_token)):
    caller = auth.get("user", {})
    result = svc.get_todays_attendance_summary(db, caller_role=caller.get("role"), caller_id=caller.get("id"))
    return _respond(result)


@router.get("/incomplete-today")
def get_incomplete_checkouts_today(db: Session = Depends(get_db)):
    from datetime import date
    from app.core.models import Attendance, User
    today_str = date.today().isoformat()
    rows = (
        db.query(Attendance, User)
        .join(User, Attendance.empid == User.id)
        .filter(
            Attendance.date == today_str,
            Attendance.start_time.isnot(None),
            Attendance.end_time.is_(None),
        )
        .all()
    )
    return [
        {
            "empid": att.empid,
            "fullname": emp.full_name,
            "start_time": str(att.start_time) if att.start_time else None,
        }
        for att, emp in rows
    ]


# ---------------------------------------------------------------------------
# POST /api/attendance/checkin  — multipart, used by the mobile app
# Accepts the same fields as /add plus an optional faceImage file.
# If the employee has a registered face, the selfie must match it (distance < 0.6).
# If no face is registered yet, check-in is allowed (graceful rollout).
# ---------------------------------------------------------------------------

@router.post("/checkin")
async def checkin_with_face(
    background_tasks: BackgroundTasks,
    empid: int = Form(...),
    projectId: int = Form(...),
    date: str = Form(...),
    startTime: str = Form(...),
    location: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    faceImage: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Submit a check-in with an optional face selfie.

    When a face image is provided, attendance is NOT saved immediately.
    Instead, a background job runs face recognition and saves attendance only if
    the face matches.  The caller should poll GET /checkin/status/{jobId} until
    status is "success" or "error".

    When no face image is provided (fallback), attendance is saved directly.
    """
    if faceImage is None:
        # No face image — save attendance directly (legacy / fallback path)
        result = svc.add_attendance(db, empid, projectId, date, startTime, location, year, month)
        return _respond(result)

    _cleanup_old_jobs()
    job_id = uuid.uuid4().hex[:12]
    _checkin_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now(timezone.utc).timestamp(),
    }

    image_bytes = await faceImage.read()
    background_tasks.add_task(
        _run_face_checkin,
        job_id, empid, projectId, date, startTime, location, year, month, image_bytes,
    )

    return JSONResponse({"jobId": job_id, "status": "processing"})


@router.get("/checkin/status/{job_id}")
def get_checkin_status(job_id: str):
    """Poll this endpoint after POST /checkin to check face-verification progress."""
    job = _checkin_jobs.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"error": "Job not found or expired. Please try checking in again."},
        )
    return JSONResponse({"status": job["status"], "message": job.get("message", "")})
