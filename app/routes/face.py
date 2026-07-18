import base64
import io
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import FaceEncoding
from app.services import face as face_svc

router = APIRouter()


def _resize_and_encode(image_bytes: bytes, max_dim: int = 512) -> str:
    """Resize photo to max_dim on the longest side and return as base64 JPEG string."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


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
    photo_b64 = _resize_and_encode(image_bytes)  # store resized reference photo

    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if existing:
        existing.encoding = encoding_json
        existing.photo = photo_b64
    else:
        db.add(FaceEncoding(empid=empid, encoding=encoding_json, photo=photo_b64))
    db.commit()

    return {"message": "Face registered successfully", "empid": empid}


@router.post("/compare")
async def compare_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Compare a selfie against the employee's stored registration photo.
    Used at check-in and check-out. Returns {match, score} in ~200ms.
    """
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse(status_code=404, content={"match": False, "message": "No registered face found. Please contact admin."})
    if not existing.photo:
        # Face encoding exists but photo not stored yet — re-register to fix
        return JSONResponse(status_code=404, content={"match": False, "message": "Reference photo missing. Please re-register face with admin."})

    image_bytes = await faceImage.read()
    result = face_svc.compare_fast(existing.photo, image_bytes)

    if result.get("error") == "no_face_detected":
        return JSONResponse(status_code=400, content={"match": False, "message": "No face detected in your photo. Please move to better lighting and try again."})

    if result.get("error") == "invalid_image":
        return JSONResponse(status_code=400, content={"match": False, "message": "Could not read image. Please try again."})

    return JSONResponse({
        "match": result["match"],
        "score": result["score"],
        "message": "Face verified." if result["match"] else "Face not recognized. Please try again or contact admin.",
    })


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
