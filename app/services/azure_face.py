import base64
import io
import os

import requests
from PIL import Image

_KEY = os.getenv("AZURE_FACE_KEY", "")
_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT", "").rstrip("/")
_DETECT_MODEL = "detection_03"


def _base() -> str:
    return f"{_ENDPOINT}/face/v1.0"


def _h(content_type: str = "application/json") -> dict:
    return {
        "Ocp-Apim-Subscription-Key": _KEY,
        "Content-Type": content_type,
    }


def is_configured() -> bool:
    return bool(_KEY and _ENDPOINT)


def _compress(image_bytes: bytes, max_dim: int = 640) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def crop_face(image_bytes: bytes) -> str:
    """
    Use Azure Face Detect with returnFaceId=false (bounding box only) to precisely
    locate and crop the face from the registration photo.

    returnFaceId=false does NOT trigger the Limited Access requirement — Microsoft
    explicitly keeps plain face detection (no recognition) available to all customers.

    Returns a 256×256 base64 JPEG face crop for storage in the DB photo column.
    Raises ValueError('no_face') if no face detected.
    Raises requests.HTTPError if the API call fails.
    """
    compressed = _compress(image_bytes)
    r = requests.post(
        f"{_base()}/detect",
        headers=_h("application/octet-stream"),
        params={"detectionModel": _DETECT_MODEL, "returnFaceId": "false"},
        data=compressed,
        timeout=15,
    )
    r.raise_for_status()
    faces = r.json()
    if not faces:
        raise ValueError("no_face")

    # Take the largest face in the frame
    face = max(faces, key=lambda f: f["faceRectangle"]["width"] * f["faceRectangle"]["height"])
    rect = face["faceRectangle"]

    img = Image.open(io.BytesIO(compressed))
    img_w, img_h = img.size
    pad = int(max(rect["width"], rect["height"]) * 0.35)
    left = max(0, rect["left"] - pad)
    top = max(0, rect["top"] - pad)
    right = min(img_w, rect["left"] + rect["width"] + pad)
    bottom = min(img_h, rect["top"] + rect["height"] + pad)

    face_crop = img.crop((left, top, right, bottom)).resize((256, 256), Image.LANCZOS)
    buf = io.BytesIO()
    face_crop.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()
