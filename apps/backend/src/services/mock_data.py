"""
Mock data generator for Field Service Intelligence Agent.
Creates realistic test data for technicians, jobs, work logs, and expenses.
"""

from datetime import datetime, timedelta, date
from typing import List
import random
from faker import Faker

from ..models.domain import (
    Technician, Job, WorkLog, Expense, ScheduleRule,
    ContractType, JobStatus, ExpenseStatus, RuleSeverity
)
from ..models.database import get_db, init_db, drop_db, DB_PATH
from ..utils.logger import logger


fake = Faker()

# Realistic field service skills
TECHNICAL_SKILLS = [
    "HVAC", "Plumbing", "Electrical", "Carpentry", "Welding",
    "Appliance Repair", "Locksmith", "Painting", "Roofing",
    "Network Installation", "Security Systems", "Solar Installation"
]

# Common expense types
EXPENSE_TYPES = [
    "materials", "travel", "equipment", "tools", "permits", "parking"
]

# Customer companies
CUSTOMER_COMPANIES = [
    "Acme Corp", "Global Industries", "TechStart Inc", "BuildRight LLC",
    "Metro Services", "Premier Solutions", "Urban Facilities", "ProTech Systems"
]


def generate_technicians(count: int = 10) -> List[Technician]:
    """Generate realistic technician data."""
    technicians = []
    
    for i in range(count):
        # Assign 2-4 random skills
        skills = random.sample(TECHNICAL_SKILLS, random.randint(2, 4))
        
        # Determine contract type and hours
        contract_type = random.choice(list(ContractType))
        if contract_type == ContractType.FULL_TIME:
            max_daily = 8
            max_weekly = 40
            hourly_rate = random.randint(25, 45)
        elif contract_type == ContractType.PART_TIME:
            max_daily = 6
            max_weekly = 20
            hourly_rate = random.randint(20, 35)
        else:  # CONTRACTOR
            max_daily = 10
            max_weekly = 50
            hourly_rate = random.randint(40, 75)
        
        tech = Technician(
            id=f"tech_{i+1:03d}",
            name=fake.name(),
            email=fake.email(),
            skills=skills,
            contract_type=contract_type,
            max_daily_hours=max_daily,
            max_weekly_hours=max_weekly,
            hourly_rate=float(hourly_rate),
            active=True
        )
        technicians.append(tech)
    
    return technicians


def generate_jobs(count: int = 50) -> List[Job]:
    """Generate realistic job/work order data."""
    jobs = []
    
    # Generate jobs spread over last 3 months and next 2 weeks
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now() + timedelta(days=14)
    
    for i in range(count):
        # Random job start within the range
        days_offset = random.randint(0, (end_date - start_date).days)
        scheduled_start = start_date + timedelta(days=days_offset)
        
        # Job duration: 2-8 hours
        duration_hours = random.randint(2, 8)
        scheduled_end = scheduled_start + timedelta(hours=duration_hours)
        
        # Required skills: 1-2 random skills
        required_skills = random.sample(TECHNICAL_SKILLS, random.randint(1, 2))
        
        # Budget based on duration
        budget = duration_hours * random.randint(50, 150)
        
        # Status based on date
        if scheduled_start < datetime.now() - timedelta(days=7):
            status = JobStatus.COMPLETED
        elif scheduled_start < datetime.now():
            status = random.choice([JobStatus.IN_PROGRESS, JobStatus.COMPLETED])
        else:
            status = JobStatus.PENDING
        
        job = Job(
            id=f"job_{i+1:04d}",
            customer_id=f"cust_{random.randint(1, 20):03d}",
            customer_name=random.choice(CUSTOMER_COMPANIES),
            site_location=fake.address().replace('\n', ', '),
            description=fake.paragraph(nb_sentences=3),
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            required_skills=required_skills,
            status=status,
            budget=float(budget)
        )
        jobs.append(job)
    
    return jobs


def generate_work_logs(
    technicians: List[Technician], 
    jobs: List[Job], 
    count: int = 200
) -> List[WorkLog]:
    """Generate realistic work log entries."""
    work_logs = []
    
    # Get completed and in-progress jobs
    active_jobs = [j for j in jobs if j.status in [JobStatus.COMPLETED, JobStatus.IN_PROGRESS]]
    
    for i in range(count):
        job = random.choice(active_jobs)
        
        # Find technician with matching skills
        eligible_techs = [
            t for t in technicians 
            if any(skill in t.skills for skill in job.required_skills)
        ]
        
        if not eligible_techs:
            eligible_techs = technicians  # Fallback to any technician
        
        technician = random.choice(eligible_techs)
        
        # Work date between job start and end
        job_duration = (job.scheduled_end - job.scheduled_start).days + 1
        work_date = job.scheduled_start.date() + timedelta(
            days=random.randint(0, max(0, job_duration - 1))
        )
        
        # Hours logged (respecting daily limits, with occasional violations for testing)
        max_hours = technician.max_daily_hours
        # 10% chance of overtime (for violation testing)
        if random.random() < 0.1:
            hours = random.uniform(max_hours + 0.5, max_hours + 3)
        else:
            hours = random.uniform(2, min(8, max_hours))
        
        work_log = WorkLog(
            id=f"wlog_{i+1:05d}",
            technician_id=technician.id,
            job_id=job.id,
            date=work_date,
            hours_logged=round(hours, 2),
            description=fake.paragraph(nb_sentences=2),
            approved=random.choice([True, True, True, False])  # 75% approved
        )
        work_logs.append(work_log)
    
    return work_logs


def generate_expenses(jobs: List[Job], count: int = 100) -> List[Expense]:
    """Generate realistic expense entries."""
    expenses = []
    
    # Only add expenses to completed/in-progress jobs
    active_jobs = [j for j in jobs if j.status in [JobStatus.COMPLETED, JobStatus.IN_PROGRESS]]
    
    for i in range(count):
        job = random.choice(active_jobs)
        expense_type = random.choice(EXPENSE_TYPES)
        
        # Amount varies by type
        if expense_type == "materials":
            amount = random.uniform(50, 500)
        elif expense_type == "travel":
            amount = random.uniform(10, 100)
        elif expense_type == "equipment":
            amount = random.uniform(100, 1000)
        else:
            amount = random.uniform(20, 200)
        
        # Some expenses over budget (for testing)
        status = ExpenseStatus.APPROVED
        if random.random() < 0.15:
            status = ExpenseStatus.PENDING
        elif random.random() < 0.05:
            status = ExpenseStatus.REJECTED
        
        # Receipt text for some expenses
        receipt_text = None
        if random.random() < 0.7:
            receipt_text = f"""
            Receipt #{fake.random_number(digits=6)}
            Date: {fake.date_this_month()}
            Vendor: {fake.company()}
            Item: {expense_type.title()} - {fake.catch_phrase()}
            Amount: ${amount:.2f}
            Payment Method: {random.choice(['Credit Card', 'Cash', 'Check'])}
            """
        
        expense = Expense(
            id=f"exp_{i+1:05d}",
            job_id=job.id,
            type=expense_type,
            amount=round(amount, 2),
            description=fake.sentence(),
            receipt_text=receipt_text,
            status=status,
            submitted_date=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        expenses.append(expense)
    
    return expenses


def generate_schedule_rules() -> List[ScheduleRule]:
    """Generate business rules for scheduling and operations."""
    rules = [
        ScheduleRule(
            id="rule_001",
            rule_name="Maximum Daily Hours",
            rule_description="Technicians cannot exceed their contract's daily hour limit without overtime approval.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_002",
            rule_name="Maximum Weekly Hours",
            rule_description="Technicians cannot exceed their contract's weekly hour limit.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_003",
            rule_name="Required Skills Match",
            rule_description="Assigned technician must have at least one of the required job skills.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_004",
            rule_name="Budget Threshold Warning",
            rule_description="Warn when job expenses exceed 80% of allocated budget.",
            severity=RuleSeverity.WARNING
        ),
        ScheduleRule(
            id="rule_005",
            rule_name="Budget Exceeded Error",
            rule_description="Job expenses cannot exceed 120% of allocated budget.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_006",
            rule_name="Expense Receipt Required",
            rule_description="Expenses over $100 require a receipt for approval.",
            severity=RuleSeverity.WARNING
        ),
        ScheduleRule(
            id="rule_007",
            rule_name="No Job Overlap",
            rule_description="Technician cannot be assigned to overlapping jobs.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_008",
            rule_name="Inactive Technician",
            rule_description="Cannot assign jobs to inactive technicians.",
            severity=RuleSeverity.ERROR
        ),
        ScheduleRule(
            id="rule_009",
            rule_name="Unapproved Hours",
            rule_description="Work logs should be approved within 7 days.",
            severity=RuleSeverity.WARNING
        ),
        ScheduleRule(
            id="rule_010",
            rule_name="Weekend Overtime",
            rule_description="Weekend work hours count as 1.5x regular hours for contractors.",
            severity=RuleSeverity.INFO
        ),
    ]
    return rules


def populate_database(
    num_technicians: int = 10,
    num_jobs: int = 50,
    num_work_logs: int = 200,
    num_expenses: int = 100,
    reset: bool = False
):
    """
    Populate database with mock data.
    
    Args:
        num_technicians: Number of technicians to generate
        num_jobs: Number of jobs to generate
        num_work_logs: Number of work logs to generate
        num_expenses: Number of expenses to generate
        reset: If True, drop and recreate all tables
    """
    logger.info("🔧 Starting database population...")
    
    # Initialize database
    if reset:
        drop_db()
    init_db()
    
    with get_db() as db:
        # Check if data already exists
        from ..models.domain import Technician as TechModel
        existing_count = db.query(TechModel).count()
        if existing_count > 0 and not reset:
            logger.warning(f"Database already has {existing_count} technicians. Use reset=True to clear.")
            return
        
        # Generate data
        logger.info(f"Generating {num_technicians} technicians...")
        technicians = generate_technicians(num_technicians)
        db.add_all(technicians)
        db.commit()
        logger.success(f"✓ Created {len(technicians)} technicians")
        
        logger.info(f"Generating {num_jobs} jobs...")
        jobs = generate_jobs(num_jobs)
        db.add_all(jobs)
        db.commit()
        logger.success(f"✓ Created {len(jobs)} jobs")
        
        logger.info(f"Generating {num_work_logs} work logs...")
        work_logs = generate_work_logs(technicians, jobs, num_work_logs)
        db.add_all(work_logs)
        db.commit()
        logger.success(f"✓ Created {len(work_logs)} work logs")
        
        logger.info(f"Generating {num_expenses} expenses...")
        expenses = generate_expenses(jobs, num_expenses)
        db.add_all(expenses)
        db.commit()
        logger.success(f"✓ Created {len(expenses)} expenses")
        
        logger.info("Generating schedule rules...")
        rules = generate_schedule_rules()
        db.add_all(rules)
        db.commit()
        logger.success(f"✓ Created {len(rules)} schedule rules")
    
    logger.success("🎉 Database population complete!")
    logger.info(f"Database location: {DB_PATH}")
    logger.info(f"Total records:")
    logger.info(f"  - Technicians: {num_technicians}")
    logger.info(f"  - Jobs: {num_jobs}")
    logger.info(f"  - Work Logs: {num_work_logs}")
    logger.info(f"  - Expenses: {num_expenses}")
    logger.info(f"  - Rules: {len(rules)}")


if __name__ == "__main__":
    # Run with: python -m src.services.mock_data
    populate_database(reset=True)
