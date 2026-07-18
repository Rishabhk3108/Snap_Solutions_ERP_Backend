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


def compare_fast(ref_photo_b64: str, live_image_bytes: bytes, threshold: float = 0.55) -> dict:
    """
    Fast face comparison using OpenCV Haar cascade detection + histogram correlation.
    Runs in ~200ms on CPU — used at check-in/check-out instead of slow dlib encoding.
    Returns {'match': bool, 'score': float, 'error': str|None}
    """
    import base64
    import cv2

    ref_bytes = base64.b64decode(ref_photo_b64)

    ref_arr = np.frombuffer(ref_bytes, np.uint8)
    live_arr = np.frombuffer(live_image_bytes, np.uint8)

    ref_img = cv2.imdecode(ref_arr, cv2.IMREAD_GRAYSCALE)
    live_img = cv2.imdecode(live_arr, cv2.IMREAD_GRAYSCALE)

    if ref_img is None or live_img is None:
        return {"match": False, "score": 0.0, "error": "invalid_image"}

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    def _crop_face(gray_img):
        faces = face_cascade.detectMultiScale(gray_img, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # largest face
        return gray_img[y : y + h, x : x + w]

    ref_face = _crop_face(ref_img)
    live_face = _crop_face(live_img)

    if live_face is None:
        return {"match": False, "score": 0.0, "error": "no_face_detected"}

    # If no face found in stored reference photo, fall back to full image
    if ref_face is None:
        ref_face = ref_img

    size = (128, 128)
    ref_resized = cv2.resize(ref_face, size)
    live_resized = cv2.resize(live_face, size)

    ref_hist = cv2.calcHist([ref_resized], [0], None, [256], [0, 256])
    live_hist = cv2.calcHist([live_resized], [0], None, [256], [0, 256])
    cv2.normalize(ref_hist, ref_hist)
    cv2.normalize(live_hist, live_hist)

    score = float(cv2.compareHist(ref_hist, live_hist, cv2.HISTCMP_CORREL))
    return {"match": score >= threshold, "score": round(score, 4), "error": None}
