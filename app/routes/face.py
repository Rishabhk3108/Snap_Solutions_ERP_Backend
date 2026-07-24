import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import FaceEncoding
from app.services import face as face_svc
from app.services import azure_face

router = APIRouter()


@router.post("/register")
async def register_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Enrol an employee's face.

    Azure path (when AZURE_FACE_KEY + AZURE_FACE_ENDPOINT are set):
      Calls Face Detect with returnFaceId=false (bounding box only — no Limited Access
      required) to precisely crop the face, then stores a 256×256 JPEG in the photo column.
      No recognition, identification, or FaceList is used.

    Fallback (no Azure env vars):
      Runs dlib face detection + encoding on the server CPU and stores the face crop.
      Slower at registration but the same fast PIL comparison runs at check-in.

    Check-in always uses PIL histogram comparison (~50ms) regardless of path.
    """
    image_bytes = await faceImage.read()
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()

    face_crop_b64 = None
    provider = "local"

    if azure_face.is_configured():
        try:
            face_crop_b64 = azure_face.crop_face(image_bytes)
            provider = "azure-detect"
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="No face detected. Use a clear, well-lit, front-facing photo.",
            )
        except Exception:
            # Azure unavailable — fall through to dlib below
            face_crop_b64 = None

    if face_crop_b64 is None:
        # Dlib fallback
        if not face_svc.is_available():
            raise HTTPException(status_code=503, detail="Face recognition service not available on this server.")
        _, face_crop_b64 = face_svc.extract_encoding_and_face_crop(image_bytes)
        if face_crop_b64 is None:
            raise HTTPException(status_code=400, detail="No face detected. Use a clear, well-lit, front-facing photo.")

    if existing:
        existing.photo = face_crop_b64
        existing.encoding = "[]"
    else:
        db.add(FaceEncoding(empid=empid, encoding="[]", photo=face_crop_b64))
    db.commit()
    return {"message": "Face registered successfully", "empid": empid, "provider": provider}


@router.post("/compare")
def compare_face(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Compare a selfie against the employee's stored face crop.
    Uses PIL histogram comparison (~50ms). No Azure call at check-in time.
    FastAPI runs this sync def in a thread pool automatically.
    """
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse(status_code=404, content={"match": False, "message": "No registered face found. Please contact admin."})
    if not existing.photo:
        return JSONResponse(status_code=404, content={"match": False, "message": "Reference photo missing. Please ask admin to re-register your face."})

    image_bytes = faceImage.file.read()
    try:
        result = face_svc.compare_fast(existing.photo, image_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face comparison failed: {str(e)}")

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
    """Return whether an employee has a registered face."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse({"empid": empid, "registered": False})
    return JSONResponse({"empid": empid, "registered": existing.photo is not None})


@router.post("/verify-test")
async def verify_face_test(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Verify without marking attendance. Used during onboarding to confirm enrolment worked."""
    image_bytes = await faceImage.read()
    stored = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not stored or not stored.photo:
        raise HTTPException(status_code=404, detail="No registered face found. Complete face enrolment first.")

    result = face_svc.compare_fast(stored.photo, image_bytes)

    if result.get("error") == "no_face_detected":
        raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")

    if not result["match"]:
        return JSONResponse(status_code=401, content={"match": False, "score": result["score"], "message": "Face not recognized. Please retake the selfie."})
    return JSONResponse({"match": True, "score": result["score"], "message": "Face verified successfully!"})


@router.delete("/remove/{empid}")
def remove_face(empid: int, db: Session = Depends(get_db)):
    """Remove a stored face encoding for an employee (admin use)."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        raise HTTPException(status_code=404, detail="No face encoding found for this employee.")
    db.delete(existing)
    db.commit()
    return {"message": "Face encoding removed", "empid": empid}
