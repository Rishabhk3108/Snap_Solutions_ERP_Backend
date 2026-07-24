import base64
import concurrent.futures
import io
import os

import requests
from PIL import Image

_KEY = os.getenv("AZURE_FACE_KEY", "")
_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT", "").rstrip("/")
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


def _compress(image_bytes: bytes, max_dim: int = 512) -> bytes:
    """Resize to max_dim on longest side and re-encode as JPEG. Keeps Azure payloads small."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _detect(image_bytes: bytes) -> list:
    """Call Azure Face Detect. Returns list of face objects with faceId."""
    r = requests.post(
        f"{_base()}/detect",
        headers=_h("application/octet-stream"),
        params={
            "detectionModel": _DETECT_MODEL,
            "recognitionModel": _RECOG_MODEL,
            "returnFaceId": "true",
        },
        data=image_bytes,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def validate_face(image_bytes: bytes) -> str:
    """
    Validate that the registration photo has a detectable face.
    Returns a compressed base64 JPEG suitable for storage in the DB photo column.
    Raises ValueError('no_face') if Azure cannot find a face.
    """
    compressed = _compress(image_bytes)
    faces = _detect(compressed)
    if not faces:
        raise ValueError("no_face")
    return base64.b64encode(compressed).decode()


def verify(selfie_bytes: bytes, ref_photo_b64: str, threshold: float = 0.6) -> dict:
    """
    Verify a selfie against a stored reference photo.

    Uses Detect×2 (parallel) + Verify — fully supported on the F0 free tier.
    No FaceList or PersonGroup is involved, so no Limited Access approval is needed.

    Flow:
      1. Compress selfie and decode reference photo
      2. Call Azure Detect on both simultaneously (ThreadPoolExecutor)
      3. Call Azure Verify(refFaceId, liveFaceId) → isIdentical + confidence

    Returns {"match": bool, "score": float, "error": str|None}
    """
    ref_bytes = base64.b64decode(ref_photo_b64)
    compressed_selfie = _compress(selfie_bytes)

    # Detect both faces in parallel to cut wall-clock time roughly in half
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        ref_fut = ex.submit(_detect, ref_bytes)
        live_fut = ex.submit(_detect, compressed_selfie)
        ref_faces = ref_fut.result()
        live_faces = live_fut.result()

    if not ref_faces:
        return {"match": False, "score": 0.0, "error": "no_ref_face"}
    if not live_faces:
        return {"match": False, "score": 0.0, "error": "no_face_detected"}

    ref_face_id = ref_faces[0]["faceId"]
    live_face_id = max(
        live_faces,
        key=lambda f: f["faceRectangle"]["width"] * f["faceRectangle"]["height"],
    )["faceId"]

    r = requests.post(
        f"{_base()}/verify",
        headers=_h(),
        json={"faceId1": ref_face_id, "faceId2": live_face_id},
        timeout=15,
    )
    r.raise_for_status()
    result = r.json()
    confidence = float(result.get("confidence", 0.0))
    return {
        "match": result.get("isIdentical", False) and confidence >= threshold,
        "score": round(confidence, 4),
        "error": None,
    }
