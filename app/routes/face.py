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
    - If Azure Face API is configured: uploads to Azure FaceList and stores persistedFaceId.
    - Fallback: dlib encoding + PIL face crop stored locally (Railway CPU, slower).
    """
    image_bytes = await faceImage.read()
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()

    if azure_face.is_configured():
        try:
            azure_face.ensure_face_list()
        except Exception as e:
            raise HTTPException(status_code=503, detail="Face service temporarily unavailable. Please try again in a moment.")

        # Remove the old Azure face before re-registering (avoids orphaned entries)
        if existing and existing.azure_person_id:
            azure_face.remove_face(existing.azure_person_id)

        try:
            persisted_face_id = azure_face.add_face(image_bytes)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="No face detected. Please retake the photo in good lighting with your face clearly visible and centred.",
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face service error: {str(e)}")

        if existing:
            existing.azure_person_id = persisted_face_id
            existing.photo = None  # Azure is now authoritative; clear stale PIL crop
        else:
            db.add(FaceEncoding(empid=empid, encoding="[]", photo=None, azure_person_id=persisted_face_id))
        db.commit()
        return {"message": "Face registered successfully", "empid": empid, "provider": "azure"}

    # Fallback: local dlib / PIL path
    if not face_svc.is_available():
        raise HTTPException(status_code=503, detail="Face recognition service not available on this server.")

    encoding, face_crop_b64 = face_svc.extract_encoding_and_face_crop(image_bytes)
    if encoding is None:
        raise HTTPException(status_code=400, detail="No face detected. Use a clear, well-lit, front-facing photo.")

    encoding_json = json.dumps(encoding.tolist())
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
    Compare a selfie against the employee's stored registration.
    Called at every check-in and check-out. Runs sync so FastAPI uses a thread pool.
    Azure path: ~500ms. PIL fallback: ~50ms (less accurate).
    """
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse(status_code=404, content={"match": False, "message": "No registered face found. Please contact admin."})

    image_bytes = faceImage.file.read()

    # Azure path — preferred when employee is registered via Azure
    if azure_face.is_configured() and existing.azure_person_id:
        try:
            result = azure_face.verify(image_bytes, existing.azure_person_id)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face verification service error: {str(e)}")

        if result.get("error") == "no_face_detected":
            return JSONResponse(status_code=400, content={"match": False, "message": "No face detected. Move to better lighting and try again."})

        return JSONResponse({
            "match": result["match"],
            "score": result["score"],
            "message": "Face verified." if result["match"] else "Face not recognized. Please try again or contact admin.",
        })

    # PIL fallback — for employees not yet re-registered after Azure was added
    if not existing.photo:
        return JSONResponse(status_code=404, content={"match": False, "message": "Reference photo missing. Please ask admin to re-register your face."})

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
    """Return whether an employee has a registered face encoding."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        return JSONResponse({"empid": empid, "registered": False})
    return JSONResponse({
        "empid": empid,
        "registered": True,
        "provider": "azure" if existing.azure_person_id else "local",
    })


@router.post("/verify-test")
async def verify_face_test(
    empid: int = Form(...),
    faceImage: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Verify a selfie without marking attendance. Used during onboarding to confirm enrolment.
    Delegates to the same Azure path as /compare when available.
    """
    image_bytes = await faceImage.read()
    stored = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not stored:
        raise HTTPException(status_code=404, detail="No registered face found. Complete face enrolment first.")

    if azure_face.is_configured() and stored.azure_person_id:
        try:
            result = azure_face.verify(image_bytes, stored.azure_person_id)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face verification service error: {str(e)}")

        if result.get("error") == "no_face_detected":
            raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")

        if not result["match"]:
            return JSONResponse(status_code=401, content={"match": False, "score": result["score"], "message": "Face not recognized. Please retake the selfie."})
        return JSONResponse({"match": True, "score": result["score"], "message": "Face verified successfully!"})

    # Fallback: dlib comparison
    if not face_svc.is_available():
        raise HTTPException(status_code=503, detail="Face recognition service not available on this server.")

    encoding = face_svc.extract_encoding(image_bytes)
    if encoding is None:
        raise HTTPException(status_code=400, detail="No face detected. Take a clearer selfie in better lighting.")

    result = face_svc.compare(stored.encoding, encoding)
    if not result["match"]:
        return JSONResponse(status_code=401, content={"match": False, "distance": result["distance"], "message": "Face not recognized. Please retake the selfie."})
    return JSONResponse({"match": True, "distance": result["distance"], "message": "Face verified successfully!"})


@router.delete("/remove/{empid}")
def remove_face(empid: int, db: Session = Depends(get_db)):
    """Remove a stored face encoding for an employee (admin use)."""
    existing = db.query(FaceEncoding).filter(FaceEncoding.empid == empid).first()
    if not existing:
        raise HTTPException(status_code=404, detail="No face encoding found for this employee.")

    # Clean up Azure FaceList entry too
    if existing.azure_person_id and azure_face.is_configured():
        azure_face.remove_face(existing.azure_person_id)

    db.delete(existing)
    db.commit()
    return {"message": "Face encoding removed", "empid": empid}
