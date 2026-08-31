from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import require_token
from app.core.database import get_db
from app.core.models import User
from app.services import personal_info as personal_info_svc

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
    """Return the onboarding_complete flag for the calling user.

    Derived from actual personal-info data (see sync_onboarding_flag) rather
    than only the stored flag, so data filled in by an admin on the user's
    behalf is picked up without requiring the mobile app's "finish
    onboarding" step to have run.
    """
    user_id = auth["user"]["id"]
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found.")
    return JSONResponse({"onboarding_complete": personal_info_svc.sync_onboarding_flag(db, user_id)})
