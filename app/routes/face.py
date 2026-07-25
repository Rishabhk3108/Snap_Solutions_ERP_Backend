import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import FaceEncoding
from app.services import face as face_svc
from app.services import luxand_face

router = APIRouter()


def _is_luxand_uuid(value: str) -> bool:
    """
    Luxand UUIDs are 36-char hex strings with dashes (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
    Old dlib encodings are JSON arrays starting with '['.
    This lets us support both without a schema change.
    """
    return bool(value) and not value.startswith("[")


@router.post("/register")
async def register_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Enrol an employee's face.

    Luxand path (when LUXAND_API_TOKEN is set):
      Creates a person in Luxand cloud and stores the returned UUID in the
      encoding column. No photo bytes stored locally — Luxand holds the face data.

    Fallback (no LUXAND_API_TOKEN):
      Runs dlib on the server and stores the face crop locally for PIL comparison.
    """
    image_bytes = await faceImage.read()
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()

    if luxand_face.is_configured():
        # Delete old Luxand person before re-registering
        if existing and _is_luxand_uuid(existing.encoding):
            luxand_face.delete_person(existing.encoding)

        try:
            uuid = luxand_face.create_person(empid, image_bytes)
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 400:
                raise HTTPException(
                    status_code=400,
                    detail="No face detected. Use a clear, well-lit, front-facing photo.",
                )
            raise HTTPException(status_code=503, detail=f"Face service error: {str(e)}")

        if existing:
            existing.encoding = uuid
            existing.photo = None
        else:
            db.add(FaceEncoding(empid=empid, encoding=uuid, photo=None))
        db.commit()
        return {"message": "Face registered successfully", "empid": empid, "provider": "luxand"}

    # Fallback: local dlib + PIL
    if not face_svc.is_available():
        raise HTTPException(status_code=503, detail="Face recognition service not available on this server.")

    _, face_crop_b64 = face_svc.extract_encoding_and_face_crop(image_bytes)
    if face_crop_b64 is None:
        raise HTTPException(status_code=400, detail="No face detected. Use a clear, well-lit, front-facing photo.")

    encoding_json = "[]"
    if existing:
        existing.encoding = encoding_json
        existing.photo = face_crop_b64
    else:
        db.add(FaceEncoding(empid=empid, encoding=encoding_json, photo=face_crop_b64))
    db.commit()
    return {"message": "Face registered successfully", "empid": empid, "provider": "local"}


@router.post("/compare")
def compare_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Compare a selfie against the employee's stored face.

    Luxand path: calls /photo/verify/{uuid} — cloud AI, ~500ms.
    PIL fallback: histogram comparison of stored face crop — ~50ms.
    FastAPI runs this sync def in a thread pool.
    """
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse(status_code=404, content={"match": False, "message": "No registered face found. Please contact admin."})

    image_bytes = faceImage.file.read()

    # Luxand path
    if luxand_face.is_configured() and _is_luxand_uuid(existing.encoding):
        try:
            result = luxand_face.verify(existing.encoding, image_bytes)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face verification service error: {str(e)}")

        if result.get("error") == "no_face_detected":
            return JSONResponse(status_code=400, content={"match": False, "message": "No face detected. Move to better lighting and try again."})

        return JSONResponse({
            "match": result["match"],
            "score": result["score"],
            "message": "Face verified." if result["match"] else "Face not recognized. Please try again or contact admin.",
        })

    # PIL fallback
    if not existing.photo:
        return JSONResponse(status_code=404, content={"match": False, "message": "Reference photo missing. Please ask admin to re-register your face."})

    try:
        result = face_svc.compare_fast(existing.photo, image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face comparison failed: {str(e)}")

    if result.get("error") == "no_face_detected":
        return JSONResponse(status_code=400, content={"match": False, "message": "No face detected in your photo. Move to better lighting and try again."})
    if result.get("error") == "invalid_image":
        return JSONResponse(status_code=400, content={"match": False, "message": "Could not read image. Please try again."})

    return JSONResponse({
        "match": result["match"],
        "score": result["score"],
        "message": "Face verified." if result["match"] else "Face not recognized. Please try again or contact admin.",
    })


@router.get("/status/{empid}")
def face_status(empid: int, db: Session = Depends(get_db)):
    """Return whether an employee has a registered face."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse({"empid": empid, "registered": False})
    provider = "luxand" if _is_luxand_uuid(existing.encoding) else "local"
    return JSONResponse({"empid": empid, "registered": True, "provider": provider})


@router.post("/verify-test")
async def verify_face_test(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Verify without marking attendance. Used during onboarding to confirm enrolment worked."""
    image_bytes = await faceImage.read()
    stored = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not stored:
        raise HTTPException(status_code=404, detail="No registered face found. Complete face enrolment first.")

    if luxand_face.is_configured() and _is_luxand_uuid(stored.encoding):
        try:
            result = luxand_face.verify(stored.encoding, image_bytes)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face verification service error: {str(e)}")

        if result.get("error") == "no_face_detected":
            raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")

        if not result["match"]:
            return JSONResponse(status_code=401, content={"match": False, "score": result["score"], "message": "Face not recognized. Please retake the selfie."})
        return JSONResponse({"match": True, "score": result["score"], "message": "Face verified successfully!"})

    # PIL fallback
    if not stored.photo:
        raise HTTPException(status_code=404, detail="No reference photo found. Complete face enrolment first.")

    result = face_svc.compare_fast(stored.photo, image_bytes)
    if result.get("error") == "no_face_detected":
        raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")
    if not result["match"]:
        return JSONResponse(status_code=401, content={"match": False, "score": result["score"], "message": "Face not recognized. Please retake the selfie."})
    return JSONResponse({"match": True, "score": result["score"], "message": "Face verified successfully!"})


@router.delete("/remove/{empid}")
def remove_face(empid: int, db: Session = Depends(get_db)):
    """Remove a stored face for an employee (admin use)."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        raise HTTPException(status_code=404, detail="No face encoding found for this employee.")

    if luxand_face.is_configured() and _is_luxand_uuid(existing.encoding):
        luxand_face.delete_person(existing.encoding)

    db.delete(existing)
    db.commit()
    return {"message": "Face encoding removed", "empid": empid}
