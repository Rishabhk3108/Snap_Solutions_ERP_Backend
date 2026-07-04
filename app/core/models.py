from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Float, Date, Time, DateTime, ForeignKey, Enum, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Department(Base):
    __tablename__ = "department"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_name = Column("department_name", String(255), nullable=False)

    users = relationship("User", back_populates="department")


class User(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=True)
    full_name = Column("full_name", String(255), nullable=False)
    role = Column(String(20))
    role_id = Column("role_id", Integer, default=1)
    active = Column(Boolean, nullable=False, default=False)
    job_title = Column("job_title", String(255), nullable=True)
    reportid = Column("reportid", String(255), nullable=True)
    end_date = Column("end_date", Date, nullable=True)
    remark = Column(String(255), nullable=True)
    department_id = Column("department_id", Integer, ForeignKey("department.id"), nullable=True)
    onboarding_complete = Column("onboarding_complete", Boolean, nullable=False, server_default='false')
    project_id = Column("project_id", Integer, ForeignKey("projects.id"), nullable=True)

    department = relationship("Department", back_populates="users")
    attendances = relationship("Attendance", back_populates="user", foreign_keys="Attendance.empid")
    financial_info = relationship("UserFinancialInfo", back_populates="user", uselist=False)
    personal_info = relationship("UserPersonalInfo", back_populates="user", uselist=False)
    employee_record = relationship("EmployeeRecord", back_populates="user", uselist=False)
    applications = relationship("Application", back_populates="user")
    project = relationship("Project", back_populates="members", foreign_keys=[project_id])


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    status = Column(String(50), server_default="Active")
    description = Column(Text, nullable=True)
    customer_id = Column("customer_id", Integer, nullable=True)
    start_date = Column("start_date", Date, nullable=True)
    end_date = Column("end_date", Date, nullable=True)

    attendances = relationship("Attendance", back_populates="project")
    members = relationship("User", back_populates="project", foreign_keys="[User.project_id]")
    project_managers = relationship("ProjectManager", back_populates="project", cascade="all, delete-orphan")


class ProjectManager(Base):
    __tablename__ = "project_managers"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    manager_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)

    project = relationship("Project", back_populates="project_managers")
    manager_user = relationship("User", foreign_keys=[manager_id])


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    project_id = Column("project_id", Integer, ForeignKey("projects.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column("start_time", Time, nullable=True)
    end_time = Column("end_time", Time, nullable=True)
    number_of_hours = Column("number_of_hours", Float, nullable=True)
    ot_hours = Column("ot_hours", Integer, nullable=True, default=0)
    location = Column(String(255), nullable=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    user = relationship("User", back_populates="attendances", foreign_keys=[empid])
    project = relationship("Project", back_populates="attendances")


class Restdays(Base):
    __tablename__ = "restdays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    project_id = Column("project_id", Integer, ForeignKey("projects.id"), nullable=False)
    date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    remarks = Column(String(500), nullable=True)


class UserFinancialInfo(Base):
    __tablename__ = "user_financial_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey("employees.id"), nullable=False)
    employment_type = Column("employment_type", String(50), nullable=True)
    salary_basic = Column("salary_basic", BigInteger, nullable=True)
    salary_gross = Column("salary_gross", BigInteger, nullable=True)
    salary_net = Column("salary_net", BigInteger, nullable=True)
    salary_balance = Column("salary_balance", BigInteger, nullable=False, default=0)
    trip_balance = Column("trip_balance", BigInteger, nullable=False, default=0)
    allowance_house_rent = Column("allowance_house_rent", BigInteger, nullable=True)
    allowance_medical = Column("allowance_medical", BigInteger, nullable=True)
    allowance_special = Column("allowance_special", BigInteger, nullable=True)
    allowance_travelling = Column("allowance_travelling", BigInteger, nullable=True)
    allowance_other = Column("allowance_other", BigInteger, nullable=True)
    allowance_total = Column("allowance_total", BigInteger, nullable=True)
    deduction_provident_fund = Column("deduction_provident_fund", BigInteger, nullable=True)
    deduction_professional_tax = Column("deduction_professional_tax", BigInteger, nullable=True)
    deduction_tax = Column("deduction_tax", BigInteger, nullable=True)
    deduction_other = Column("deduction_other", BigInteger, nullable=True)
    deduction_total = Column("deduction_total", BigInteger, nullable=True)
    bank_name = Column("bank_name", String(255), nullable=True)
    account_name = Column("account_name", String(255), nullable=True)
    account_number = Column("account_number", String(255), nullable=True)
    iban = Column("iban", String(255), nullable=True)
    start_date = Column("start_date", Date, nullable=True)
    end_date = Column("end_date", Date, nullable=True)
    ot_status = Column("ot_status", String(3), nullable=False, server_default="No")
    esic_status = Column("esic_status", String(3), nullable=False, server_default="No")
    ot_working_hours = Column("ot_working_hours", Integer, nullable=True, default=8)
    pan_number = Column("pan_number", String(50), nullable=True)
    esic_number = Column("esic_number", String(50), nullable=True)
    pf_number = Column("pf_number", String(50), nullable=True)

    user = relationship("User", back_populates="financial_info")


class UserPersonalInfo(Base):
    __tablename__ = "user_personal_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey("employees.id"), nullable=True)
    date_of_birth = Column("date_of_birth", Date, nullable=True)
    gender = Column(String(10), nullable=True)
    marital_status = Column("marital_status", String(20), nullable=True)
    father_name = Column("father_name", String(255), nullable=True)
    id_number = Column("id_number", String(255), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    mobile = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    email_address = Column("email_address", String(255), nullable=True)
    nominee_name = Column("nominee_name", String(255), nullable=True)
    nominee_relationship = Column("nominee_relationship", String(100), nullable=True)

    user = relationship("User", back_populates="personal_info")


class EmployeeRecord(Base):
    """Govt IDs table — 'employee' (distinct from the 'employees' user table)."""
    __tablename__ = "employee"

    id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    email_address = Column("email_address", String(255), nullable=True)
    aadhaar_number = Column("aadhaar_number", String(25), nullable=True)
    pan_number = Column("pan_number", String(25), nullable=True)
    esic_number = Column("esic_number", String(25), nullable=True)
    pf_number = Column("pf_number", String(25), nullable=True)
    nominee_name = Column("nominee_name", String(255), nullable=True)
    nominee_relation = Column("nominee_relation", String(255), nullable=True)

    user = relationship("User", back_populates="employee_record")


class Application(Base):
    __tablename__ = "application"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey("employees.id"), nullable=False)
    reason = Column(String(500), nullable=True)
    start_date = Column("start_date", Date, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    end_date = Column("end_date", Date, nullable=False)
    status = Column(Enum("Approved", "Rejected", "Pending", name="application_status"), nullable=False)
    type = Column(Enum("Casual Leave", "Sick Leave", "LWP", name="application_leave_type"), nullable=False)

    user = relationship("User", back_populates="applications")


class ExpenseHeader(Base):
    __tablename__ = "expense_header"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    title = Column(String(255), nullable=False)
    total_amount = Column("total_amount", Float, nullable=True)
    status = Column(String(20), nullable=False, server_default="Pending")
    date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column("created_at", DateTime, server_default=func.now())

    employee = relationship("User", foreign_keys=[empid])
    details = relationship("ExpenseDetail", back_populates="header")


class ExpenseDetail(Base):
    __tablename__ = "expense_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_header_id = Column("expense_header_id", Integer, ForeignKey("expense_header.id"), nullable=False)
    category = Column(String(255), nullable=True)
    amount = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    receipt_url = Column("receipt_url", String(500), nullable=True)

    header = relationship("ExpenseHeader", back_populates="details")


class DepartmentAnnouncement(Base):
    __tablename__ = "department_announcement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column("department_id", Integer, ForeignKey("department.id"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    created_by = Column("created_by", String(255), nullable=True)
    created_at = Column("created_at", DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column("sender_id", Integer, ForeignKey("employees.id"), nullable=False)
    receiver_id = Column("receiver_id", Integer, ForeignKey("employees.id"), nullable=False)
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column("created_at", DateTime, server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class PersonalEvent(Base):
    __tablename__ = "personal_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey("employees.id"), nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=True, server_default="Personal")
    description = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class AdvancePayment(Base):
    __tablename__ = "advance_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    note = Column(String(500), nullable=True)
    adjusted = Column(Boolean, nullable=False, default=False)

    employee = relationship("User", foreign_keys=[empid])


class Fine(Base):
    __tablename__ = "fines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    reason = Column(String(500), nullable=True)

    employee = relationship("User", foreign_keys=[empid])


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=True, server_default="Public")


class JobPosition(Base):
    __tablename__ = "job_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    department_id = Column("department_id", Integer, ForeignKey("department.id"), nullable=True)

    department = relationship("Department", foreign_keys=[department_id])


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)


class MonthlySalary(Base):
    __tablename__ = "monthly_salary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column("empid", Integer, ForeignKey("employees.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    basic_salary = Column("basic_salary", Float, nullable=True, default=0)
    allowance_total = Column("allowance_total", Float, nullable=True, default=0)
    deduction_total = Column("deduction_total", Float, nullable=True, default=0)
    advance_deduction = Column("advance_deduction", Float, nullable=True, default=0)
    fine_deduction = Column("fine_deduction", Float, nullable=True, default=0)
    net_salary = Column("net_salary", Float, nullable=True, default=0)
    status = Column(String(20), nullable=False, server_default="Generated")

    employee = relationship("User", foreign_keys=[empid])


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    permissions = relationship("RolePermission", back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)

    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column("role_id", Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column("permission_id", Integer, ForeignKey("permissions.id"), nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey("employees.id"), nullable=True)
    job_id = Column("job_id", Integer, ForeignKey("job_positions.id"), nullable=True)
    amount = Column(Float, nullable=False)
    year = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, server_default="Pending")
    description = Column(String(500), nullable=True)
    date = Column(Date, nullable=True)

    employee = relationship("User", foreign_keys=[user_id])
    job = relationship("JobPosition", foreign_keys=[job_id])


class CompanyExpense(Base):
    __tablename__ = "company_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    department_id = Column("department_id", Integer, ForeignKey("department.id"), nullable=True)
    year = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="Pending")

    department = relationship("Department", foreign_keys=[department_id])


class FaceEncoding(Base):
    __tablename__ = "face_encodings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empid = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    encoding = Column(Text, nullable=False)  # JSON array of 128 floats from dlib ResNet
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    employee = relationship("User", foreign_keys=[empid])
