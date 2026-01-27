"""
Domain models for Field Service Intelligence Agent.
SQLAlchemy ORM models representing the core entities.
"""

from datetime import datetime
from datetime import date as date_type
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, 
    ForeignKey, JSON, Text, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ContractType(str, enum.Enum):
    """Employment contract types."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACTOR = "contractor"


class JobStatus(str, enum.Enum):
    """Job status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExpenseStatus(str, enum.Enum):
    """Expense approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RuleSeverity(str, enum.Enum):
    """Rule violation severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Technician(Base):
    """Technician/field worker model."""
    __tablename__ = "technicians"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    skills: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    contract_type: Mapped[ContractType] = mapped_column(
        SQLEnum(ContractType), nullable=False
    )
    max_daily_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    max_weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # Relationships
    work_logs: Mapped[List["WorkLog"]] = relationship(
        back_populates="technician", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Technician {self.name} ({self.contract_type.value})>"


class Job(Base):
    """Customer job/work order model."""
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    site_location: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    required_skills: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), default=JobStatus.PENDING
    )
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # Relationships
    work_logs: Mapped[List["WorkLog"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Job {self.id} - {self.customer_name} ({self.status.value})>"


class WorkLog(Base):
    """Work hours logged by technicians."""
    __tablename__ = "work_logs"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    technician_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("technicians.id"), nullable=False
    )
    job_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("jobs.id"), nullable=False
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    hours_logged: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Long text - will be embedded
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # Relationships
    technician: Mapped["Technician"] = relationship(back_populates="work_logs")
    job: Mapped["Job"] = relationship(back_populates="work_logs")
    
    def __repr__(self) -> str:
        return f"<WorkLog {self.technician_id} - {self.date} ({self.hours_logged}h)>"


class Expense(Base):
    """Job-related expenses."""
    __tablename__ = "expenses"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("jobs.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # materials, travel, equipment
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # OCR text - will be embedded
    status: Mapped[ExpenseStatus] = mapped_column(
        SQLEnum(ExpenseStatus), default=ExpenseStatus.PENDING
    )
    submitted_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # Relationships
    job: Mapped["Job"] = relationship(back_populates="expenses")
    
    def __repr__(self) -> str:
        return f"<Expense {self.id} - ${self.amount} ({self.status.value})>"


class ScheduleRule(Base):
    """Business rules for scheduling and operations."""
    __tablename__ = "schedule_rules"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_description: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Will be embedded
    severity: Mapped[RuleSeverity] = mapped_column(
        SQLEnum(RuleSeverity), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<ScheduleRule {self.rule_name} ({self.severity.value})>"
