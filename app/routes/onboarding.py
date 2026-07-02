from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import require_token
from app.core.database import get_db
from app.core.models import User

router = APIRouter()


@router.post("/complete")
def complete_onboarding(
    db: Session = Depends(get_db),
    auth: dict = Depends(require_token),
):
    """Mark onboarding as complete for the calling user. Called after face enrolment + test pass."""
    user_id = auth["user"]["id"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.onboarding_complete = True
    db.commit()
    return JSONResponse({"message": "Onboarding complete!", "onboarding_complete": True})


@router.get("/status")
def onboarding_status(
    db: Session = Depends(get_db),
    auth: dict = Depends(require_token),
):
    """Return the onboarding_complete flag for the calling user."""
    user_id = auth["user"]["id"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return JSONResponse({"onboarding_complete": bool(user.onboarding_complete)})
