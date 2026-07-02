from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import attendance
from app.routes import auth
from app.routes import users
from app.routes import personal_info
from app.routes import financial_info
from app.routes import employee_info
from app.routes import applications
from app.routes import expenses
from app.routes import announcements
from app.routes import messages
from app.routes import personal_events
from app.routes import salary
from app.routes import departments
from app.routes import projects
from app.routes import customers
from app.routes import advance_payments
from app.routes import fines
from app.routes import holidays
from app.routes import jobs
from app.routes import vendors
from app.routes import monthly_salary
from app.routes import roles
from app.routes import payment_records
from app.routes import company_expenses

from app.core.database import engine
from app.core.models import (
    ExpenseHeader, ExpenseDetail, DepartmentAnnouncement, Message, PersonalEvent,
    AdvancePayment, Fine, Holiday, JobPosition, Vendor, MonthlySalary,
    Role, Permission, RolePermission, PaymentRecord, CompanyExpense, Base
)

# Create only the new tables that don't exist yet
Base.metadata.create_all(
    bind=engine,
    tables=[
        ExpenseHeader.__table__,
        ExpenseDetail.__table__,
        DepartmentAnnouncement.__table__,
        Message.__table__,
        PersonalEvent.__table__,
        AdvancePayment.__table__,
        Fine.__table__,
        Holiday.__table__,
        JobPosition.__table__,
        Vendor.__table__,
        MonthlySalary.__table__,
        Role.__table__,
        Permission.__table__,
        RolePermission.__table__,
        PaymentRecord.__table__,
        CompanyExpense.__table__,
    ],
    checkfirst=True,
)

app = FastAPI(title="Snap Solutions ERP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(auth.router, prefix="/api", tags=["Auth"])

# User management
app.include_router(users.router, prefix="/api", tags=["Users"])

# Employee sub-resources
app.include_router(personal_info.router, prefix="/api", tags=["Personal Info"])
app.include_router(financial_info.router, prefix="/api", tags=["Financial Info"])
app.include_router(employee_info.router, prefix="/api", tags=["Employee"])

# Attendance
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])

# Leave applications
app.include_router(applications.router, prefix="/api", tags=["Applications"])

# Expenses
app.include_router(expenses.router, prefix="/api", tags=["Expenses"])

# Announcements
app.include_router(announcements.router, prefix="/api", tags=["Announcements"])

# Messages
app.include_router(messages.router, prefix="/api", tags=["Messages"])

# Personal Events
app.include_router(personal_events.router, prefix="/api", tags=["Personal Events"])

# Salary
app.include_router(salary.router, prefix="/api", tags=["Salary"])

# Departments / Projects / Customers
app.include_router(departments.router, prefix="/api", tags=["Departments"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(customers.router, prefix="/api", tags=["Customers"])

# Advance Payments / Fines / Holidays
app.include_router(advance_payments.router, prefix="/api", tags=["Advance Payments"])
app.include_router(fines.router, prefix="/api", tags=["Fines"])
app.include_router(holidays.router, prefix="/api", tags=["Holidays"])

# Jobs / Vendors
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(vendors.router, prefix="/api", tags=["Vendors"])

# Monthly Salary / Payroll
app.include_router(monthly_salary.router, prefix="/api", tags=["Monthly Salary"])

# Roles / Permissions
app.include_router(roles.router, prefix="/api", tags=["Roles"])

# Payment Records / Company Expenses
app.include_router(payment_records.router, prefix="/api", tags=["Payment Records"])
app.include_router(company_expenses.router, prefix="/api", tags=["Company Expenses"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
