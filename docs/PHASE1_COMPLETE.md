# Phase 1 Complete: Domain Model & Mock Data ✅

## What We Built

### 1. Database Models (`src/models/domain.py`)
- **Technician** - Field workers with skills, contracts, and hourly limits
- **Job** - Customer work orders with schedules and budgets
- **WorkLog** - Hours logged by technicians on jobs
- **Expense** - Job-related costs with receipts
- **ScheduleRule** - Business rules for validation

### 2. Database Setup (`src/models/database.py`)
- SQLAlchemy engine with SQLite
- Session management with context managers
- Initialize and drop database functions
- Database location: `apps/backend/data/db/fsia.db`

### 3. Mock Data Generator (`src/services/mock_data.py`)
- Realistic data using Faker library
- **10 technicians** with varied skills and contracts
- **50 jobs** spread over 3 months
- **200 work logs** (some with violations for testing)
- **100 expenses** (some over budget)
- **10 schedule rules** for business logic

### 4. Initialization Script (`init_db.py`)
- Easy database population
- Run with: `npm run backend:init-db`

## Database Schema

```sql
-- Technicians
CREATE TABLE technicians (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    skills JSON NOT NULL,  -- ["HVAC", "Electrical", ...]
    contract_type VARCHAR(20),  -- full_time, part_time, contractor
    max_daily_hours INTEGER,
    max_weekly_hours INTEGER,
    hourly_rate FLOAT,
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME
);

-- Jobs
CREATE TABLE jobs (
    id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    customer_name VARCHAR(100),
    site_location VARCHAR(200),
    description TEXT,  -- Long text (will be embedded)
    scheduled_start DATETIME,
    scheduled_end DATETIME,
    required_skills JSON,
    status VARCHAR(20),  -- pending, in_progress, completed, cancelled
    budget FLOAT,
    created_at DATETIME
);

-- Work Logs
CREATE TABLE work_logs (
    id VARCHAR(50) PRIMARY KEY,
    technician_id VARCHAR(50) REFERENCES technicians(id),
    job_id VARCHAR(50) REFERENCES jobs(id),
    date DATE,
    hours_logged FLOAT,
    description TEXT,  -- Long text (will be embedded)
    approved BOOLEAN DEFAULT FALSE,
    created_at DATETIME
);

-- Expenses
CREATE TABLE expenses (
    id VARCHAR(50) PRIMARY KEY,
    job_id VARCHAR(50) REFERENCES jobs(id),
    type VARCHAR(50),  -- materials, travel, equipment, tools
    amount FLOAT,
    description TEXT,
    receipt_text TEXT,  -- OCR text (will be embedded)
    status VARCHAR(20),  -- pending, approved, rejected
    submitted_date DATETIME
);

-- Schedule Rules
CREATE TABLE schedule_rules (
    id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(100),
    rule_description TEXT,  -- Will be embedded
    severity VARCHAR(20),  -- error, warning, info
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME
);
```

## Sample Data Overview

### Technicians
```python
# Example: Full-time HVAC technician
{
    "id": "tech_001",
    "name": "John Smith",
    "skills": ["HVAC", "Electrical", "Plumbing"],
    "contract_type": "full_time",
    "max_daily_hours": 8,
    "max_weekly_hours": 40,
    "hourly_rate": 35.00
}
```

### Jobs
```python
# Example: HVAC installation job
{
    "id": "job_0015",
    "customer_name": "TechStart Inc",
    "site_location": "123 Main St, Boston MA",
    "description": "Install new HVAC system in office building...",
    "required_skills": ["HVAC", "Electrical"],
    "budget": 1200.00,
    "status": "in_progress"
}
```

### Work Logs (with intentional violations)
```python
# Example: Overtime violation for testing
{
    "id": "wlog_00042",
    "technician_id": "tech_001",
    "job_id": "job_0015",
    "date": "2026-01-20",
    "hours_logged": 9.5,  # Exceeds 8-hour limit!
    "description": "Completed HVAC installation and tested all systems...",
    "approved": False
}
```

## Test Queries

You can now query the database:

```python
from src.models.database import get_db
from src.models.domain import Technician, Job, WorkLog

with get_db() as db:
    # Get all technicians
    techs = db.query(Technician).all()
    
    # Find HVAC specialists
    hvac_techs = db.query(Technician).filter(
        Technician.skills.contains(["HVAC"])
    ).all()
    
    # Get pending jobs
    pending = db.query(Job).filter(
        Job.status == "pending"
    ).all()
    
    # Find overtime violations
    from sqlalchemy import func
    violations = db.query(WorkLog).join(Technician).filter(
        WorkLog.hours_logged > Technician.max_daily_hours
    ).all()
```

## Edge Cases Included

Our mock data includes realistic edge cases for testing:

1. **Overtime Violations** - 10% of work logs exceed daily limits
2. **Budget Overruns** - Some jobs have expenses > 80% of budget
3. **Skill Mismatches** - Occasional assignments without perfect skill match
4. **Pending Approvals** - 25% of work logs not yet approved
5. **Missing Receipts** - Some expenses lack receipt text
6. **Weekend Work** - Jobs scheduled on weekends
7. **Multi-day Jobs** - Work spanning several days

## What's Next?

With the database populated, you're ready for **Phase 2: Basic RAG - SQL Tool Integration**

Phase 2 will include:
- SQL query agent using LangChain
- Safe query validation
- Basic Q&A like "How many hours did John work this week?"
- Error handling and logging

## Commands Reference

```bash
# Initialize/reset database
npm run backend:init-db

# Run main application
npm run backend:start

# Install dependencies
npm run backend:install
```

## Learning Achieved ✅

- [x] Designed realistic domain models
- [x] Set up SQLAlchemy ORM
- [x] Created relationships between entities
- [x] Generated mock data with edge cases
- [x] Understood field service domain
- [x] Added enums for type safety
- [x] Implemented database session management

**Phase 1 Duration**: ~30 minutes  
**Next Phase**: SQL Tool Integration for RAG
