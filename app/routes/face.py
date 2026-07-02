import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import FaceEncoding
from app.services import face as face_svc

router = APIRouter()


@router.post("/register")
async def register_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Enrol an employee's face. Admin calls this once per employee with a clear photo."""
    if not face_svc.is_available():
        raise HTTPException(
            status_code=503,
            detail="Face recognition service not available on this server.",
        )

    image_bytes = await faceImage.read()
    encoding = face_svc.extract_encoding(image_bytes)
    if encoding is None:
        raise HTTPException(
            status_code=400,
            detail="No face detected. Use a clear, well-lit, front-facing photo.",
        )

    encoding_json = json.dumps(encoding.tolist())
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if existing:
        existing.encoding = encoding_json
    else:
        db.add(FaceEncoding(empid=empid, encoding=encoding_json))
    db.commit()

    return {"message": "Face registered successfully", "empid": empid}


@router.get("/status/{empid}")
def face_status(empid: int, db: Session = Depends(get_db)):
    """Return whether an employee has a registered face encoding."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    return JSONResponse({"empid": empid, "registered": existing is not None})


@router.post("/verify-test")
async def verify_face_test(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Verify a selfie against the registered face without marking attendance.
    Used during onboarding to confirm face enrolment worked.
    """
    if not face_svc.is_available():
        raise HTTPException(status_code=503, detail="Face recognition service not available on this server.")

    image_bytes = await faceImage.read()
    encoding = face_svc.extract_encoding(image_bytes)
    if encoding is None:
        raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")

    stored = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not stored:
        raise HTTPException(status_code=404, detail="No registered face found. Complete face enrolment first.")

    result = face_svc.compare(stored.encoding, encoding)
    if not result["match"]:
        return JSONResponse(
            status_code=401,
            content={
                "match": False,
                "distance": result["distance"],
                "message": "Face not recognized. Please retake the selfie.",
            },
        )

    return JSONResponse({"match": True, "distance": result["distance"], "message": "Face verified successfully!"})


@router.delete("/remove/{empid}")
def remove_face(empid: int, db: Session = Depends(get_db)):
    """Remove a stored face encoding for an employee (admin use)."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        raise HTTPException(status_code=404, detail="No face encoding found for this employee.")
    db.delete(existing)
    db.commit()
    return {"message": "Face encoding removed", "empid": empid}
