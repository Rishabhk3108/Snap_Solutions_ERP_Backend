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

    # Resize to max 640px — selfies have large faces so this is plenty, and it's ~2.5x faster than 1024
    max_dim = 640
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    arr = np.array(img)
    # upsample=1 (default) is fast enough for selfies where the face fills the frame
    locations = face_recognition.face_locations(arr, number_of_times_to_upsample=1)
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


def compare_fast(ref_photo_b64: str, live_image_bytes: bytes, threshold: float = 0.75) -> dict:
    """
    Fast face comparison using dlib HOG detection (already installed via face_recognition)
    + Pillow/numpy grayscale histogram similarity.
    No OpenCV required. Runs in ~1-3s on CPU — much faster than full dlib encoding.
    Returns {'match': bool, 'score': float, 'error': str|None}
    """
    import base64

    ref_bytes = base64.b64decode(ref_photo_b64)

    def _load_and_detect(img_bytes: bytes):
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size
        if max(w, h) > 640:
            scale = 640 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        arr = np.array(img)
        locations = face_recognition.face_locations(arr, number_of_times_to_upsample=1, model="hog")
        return img, arr, locations

    try:
        ref_img, ref_arr, ref_locs = _load_and_detect(ref_bytes)
        live_img, live_arr, live_locs = _load_and_detect(live_image_bytes)
    except Exception:
        return {"match": False, "score": 0.0, "error": "invalid_image"}

    if not live_locs:
        return {"match": False, "score": 0.0, "error": "no_face_detected"}

    def _crop_face(arr, locs, pad: float = 0.2):
        top, right, bottom, left = locs[0]
        h, w = arr.shape[:2]
        ph = int((bottom - top) * pad)
        pw = int((right - left) * pad)
        t = max(0, top - ph)
        l = max(0, left - pw)
        b = min(h, bottom + ph)
        r = min(w, right + pw)
        crop = Image.fromarray(arr[t:b, l:r])
        return crop.convert("L").resize((128, 128), Image.LANCZOS)

    live_face = _crop_face(live_arr, live_locs)
    # Fall back to full image if reference has no detectable face
    ref_face = _crop_face(ref_arr, ref_locs) if ref_locs else Image.fromarray(ref_arr).convert("L").resize((128, 128))

    ref_hist, _ = np.histogram(np.array(ref_face, dtype=float), bins=64, range=(0, 256))
    live_hist, _ = np.histogram(np.array(live_face, dtype=float), bins=64, range=(0, 256))

    ref_hist = ref_hist / (ref_hist.sum() + 1e-8)
    live_hist = live_hist / (live_hist.sum() + 1e-8)

    # Bhattacharyya similarity coefficient: 1.0 = identical, ~0.5 = unrelated
    score = float(np.sum(np.sqrt(ref_hist * live_hist)))

    return {"match": score >= threshold, "score": round(score, 4), "error": None}
