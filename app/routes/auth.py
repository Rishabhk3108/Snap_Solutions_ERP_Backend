from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token
from app.services import auth as svc

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str = None
    fullname: str


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    status, data = svc.login(db, body.username, body.password)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status, content=data)


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    status, data = svc.register(db, body.username, body.password, body.fullname)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status, content=data)


@router.get("/checkToken", status_code=201)
def check_token(auth: dict = Depends(require_token)):
    _, data = svc.check_token(auth)
    return data
