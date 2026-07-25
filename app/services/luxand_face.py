import os
import requests

_TOKEN = os.getenv("LUXAND_API_TOKEN", "")
_BASE = "https://api.luxand.cloud"


def _h() -> dict:
    return {"token": _TOKEN}


def is_configured() -> bool:
    return bool(_TOKEN)


def create_person(empid: int, image_bytes: bytes) -> str:
    """
    Register a new person in Luxand cloud.
    Returns the person UUID to store in the DB.
    Raises requests.HTTPError on failure.
    """
    r = requests.post(
        f"{_BASE}/v2/person",
        headers=_h(),
        data={"name": f"Employee {empid}", "store": "1"},
        files={"photos": ("photo.jpg", image_bytes, "image/jpeg")},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["uuid"]


def delete_person(uuid: str) -> None:
    """Remove a person from Luxand cloud (called before re-registration)."""
    requests.delete(f"{_BASE}/v2/person/{uuid}", headers=_h(), timeout=10)


def verify(uuid: str, selfie_bytes: bytes, threshold: float = 0.8) -> dict:
    """
    Verify a selfie against the registered person.

    Luxand returns:
      {"status": "success"|"failure", "probability": float, ...}

    Returns {"match": bool, "score": float, "error": str|None}
    """
    r = requests.post(
        f"{_BASE}/photo/verify/{uuid}",
        headers=_h(),
        files={"photo": ("selfie.jpg", selfie_bytes, "image/jpeg")},
        timeout=20,
    )

    if r.status_code != 200:
        text = r.text.lower()
        if "face" in text or r.status_code == 400:
            return {"match": False, "score": 0.0, "error": "no_face_detected"}
        return {"match": False, "score": 0.0, "error": r.text}

    result = r.json()
    probability = float(result.get("probability", 0.0))
    matched = result.get("status") == "success" and probability >= threshold
    return {"match": matched, "score": round(probability, 4), "error": None}
