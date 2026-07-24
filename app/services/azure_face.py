import os
import requests

_KEY = os.getenv("AZURE_FACE_KEY", "")
_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT", "").rstrip("/")
_LIST_ID = "snap-employees"
_DETECT_MODEL = "detection_03"
_RECOG_MODEL = "recognition_04"


def _base() -> str:
    return f"{_ENDPOINT}/face/v1.0"


def _h(content_type: str = "application/json") -> dict:
    return {
        "Ocp-Apim-Subscription-Key": _KEY,
        "Content-Type": content_type,
    }


def is_configured() -> bool:
    return bool(_KEY and _ENDPOINT)


def ensure_face_list() -> None:
    """Create the FaceList if it doesn't exist yet. Safe to call on every startup."""
    if not is_configured():
        return
    url = f"{_base()}/facelists/{_LIST_ID}"
    r = requests.get(url, headers=_h(), timeout=10)
    if r.status_code == 404:
        requests.put(
            url,
            headers=_h(),
            json={"name": "Snap Employees", "recognitionModel": _RECOG_MODEL},
            timeout=10,
        ).raise_for_status()


def add_face(image_bytes: bytes) -> str:
    """
    Upload a registration photo to the Azure FaceList.
    Returns the persistedFaceId (store this in the DB).
    Raises ValueError('no_face') if Azure cannot detect a face.
    Raises requests.HTTPError on other failures.
    """
    r = requests.post(
        f"{_base()}/facelists/{_LIST_ID}/persistedfaces",
        headers=_h("application/octet-stream"),
        params={"detectionModel": _DETECT_MODEL},
        data=image_bytes,
        timeout=20,
    )
    if r.status_code == 400:
        try:
            code = r.json().get("error", {}).get("code", "")
        except Exception:
            code = ""
        if code in ("NoFaceDetected", "InvalidImage", "BadArgument"):
            raise ValueError("no_face")
    r.raise_for_status()
    return r.json()["persistedFaceId"]


def remove_face(persisted_face_id: str) -> None:
    """Remove a persisted face from the FaceList (call before re-registering an employee)."""
    requests.delete(
        f"{_base()}/facelists/{_LIST_ID}/persistedfaces/{persisted_face_id}",
        headers=_h(),
        timeout=10,
    )


def verify(selfie_bytes: bytes, persisted_face_id: str, threshold: float = 0.5) -> dict:
    """
    Verify a live selfie against the employee's registered face.

    Flow:
      1. Detect face in selfie → get temporary faceId (expires in 24h — we never store it)
      2. FindSimilar against our FaceList → returns ranked candidates with confidence
      3. Check if the top candidate is the expected employee AND confidence >= threshold

    Returns {"match": bool, "score": float, "error": str|None}
    """
    # Step 1 — detect
    r = requests.post(
        f"{_base()}/detect",
        headers=_h("application/octet-stream"),
        params={
            "detectionModel": _DETECT_MODEL,
            "recognitionModel": _RECOG_MODEL,
            "returnFaceId": "true",
        },
        data=selfie_bytes,
        timeout=15,
    )
    r.raise_for_status()
    faces = r.json()
    if not faces:
        return {"match": False, "score": 0.0, "error": "no_face_detected"}

    # Pick the largest face (most likely the employee in a selfie)
    face_id = max(
        faces,
        key=lambda f: f["faceRectangle"]["width"] * f["faceRectangle"]["height"],
    )["faceId"]

    # Step 2 — find similar in our company FaceList
    r = requests.post(
        f"{_base()}/findsimilars",
        headers=_h(),
        json={
            "faceId": face_id,
            "faceListId": _LIST_ID,
            "maxNumOfCandidatesReturned": 1,
            "mode": "matchPerson",
        },
        timeout=15,
    )
    r.raise_for_status()
    candidates = r.json()

    if not candidates:
        return {"match": False, "score": 0.0, "error": None}

    top = candidates[0]
    confidence = float(top.get("confidence", 0.0))
    # Verify the top match is THIS employee specifically (prevents proxy check-in)
    matched = (top.get("persistedFaceId") == persisted_face_id) and (confidence >= threshold)

    return {"match": matched, "score": round(confidence, 4), "error": None}
