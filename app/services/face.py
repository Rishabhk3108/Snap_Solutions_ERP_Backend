import io
import json

import numpy as np
from PIL import Image, ExifTags

try:
    import face_recognition
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _fix_rotation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation so the face detector sees the image right-side-up."""
    try:
        exif = img._getexif()
        if exif is None:
            return img
        orientation_key = next(
            (k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None
        )
        if orientation_key is None:
            return img
        orientation = exif.get(orientation_key)
        rotations = {3: 180, 6: 270, 8: 90}
        if orientation in rotations:
            img = img.rotate(rotations[orientation], expand=True)
    except Exception:
        pass
    return img


def extract_encoding(image_bytes: bytes):
    """
    Detect the largest face in image_bytes and return its 128-dim dlib encoding
    as a numpy array.  Returns None if no face is found or library is unavailable.
    """
    if not _AVAILABLE:
        return None

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = _fix_rotation(img)

    # Resize to max 1024px on the longer side — preserves enough detail for detection
    max_dim = 1024
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    arr = np.array(img)
    # upsample=2 finds faces that are smaller or slightly off-angle
    locations = face_recognition.face_locations(arr, number_of_times_to_upsample=2)
    if not locations:
        return None
    encodings = face_recognition.face_encodings(arr, locations)
    if not encodings:
        return None
    return encodings[0]


def compare(known_json: str, unknown: np.ndarray, tolerance: float = 0.6) -> dict:
    """
    Compare a stored JSON encoding (list of 128 floats) with a live numpy encoding.
    Returns {'match': bool, 'distance': float}.
    Lower distance = more similar faces.  Typical threshold: 0.6.
    """
    known = np.array(json.loads(known_json))
    distance = float(face_recognition.face_distance([known], unknown)[0])
    return {"match": distance <= tolerance, "distance": round(distance, 4)}


def is_available() -> bool:
    return _AVAILABLE
