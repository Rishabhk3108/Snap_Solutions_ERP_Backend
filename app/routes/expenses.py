from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_token, require_admin_or_manager
from app.services import expenses as svc

router = APIRouter(tags=["Expenses"])


class ExpenseBody(BaseModel):
    empid: int
    title: str
    totalAmount: Optional[float] = None
    date: Optional[str] = None
    description: Optional[str] = None


class ExpenseDetailBody(BaseModel):
    expenseHeaderId: int
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    receiptUrl: Optional[str] = None


class StatusBody(BaseModel):
    status: str


@router.post("/expenseHeader/add")
def create(body: ExpenseBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.create(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/expenseHeader/list")
def get_list(db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_list(db)


@router.get("/expenseHeader/pending-expense-count")
def pending_count(db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.pending_count(db)


@router.put("/expenseHeader/{record_id}/status")
def update_status(record_id: int, body: StatusBody, db: Session = Depends(get_db), auth=Depends(require_admin_or_manager)):
    status, data = svc.update_status(db, record_id, body.status)
    return JSONResponse(status_code=status, content=data)


@router.delete("/expenseHeader/{record_id}")
def delete(record_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.delete(db, record_id)
    return JSONResponse(status_code=status, content=data)


@router.get("/expenseDetails/list/{header_id}")
def get_details(header_id: int, db: Session = Depends(get_db), auth=Depends(require_token)):
    return svc.get_details(db, header_id)


@router.post("/expenseDetails/add")
def add_detail(body: ExpenseDetailBody, db: Session = Depends(get_db), auth=Depends(require_token)):
    status, data = svc.add_detail(db, body.dict())
    return JSONResponse(status_code=status, content=data)


@router.get("/expenseCategory/list")
def get_categories(auth=Depends(require_token)):
    categories = [
        "Travel", "Food & Meals", "Accommodation", "Office Supplies",
        "Communication", "Training", "Medical", "Entertainment", "Other",
    ]
    return categories
