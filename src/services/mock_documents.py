"""
Enhanced mock data generator for Phase 3: Vector Store & RAG
Generates realistic long-form documents for chunking experiments:
- Company handbook
- Federal/state compliance documents
- Detailed work logs with technical narratives
- Realistic OCR receipt text
"""

from datetime import datetime, date, timedelta
from typing import List, Dict
import random
from faker import Faker

fake = Faker()

# ============================================================================
# COMPANY HANDBOOK - Long-form document for semantic chunking
# ============================================================================

COMPANY_HANDBOOK = """
# Field Service Solutions Inc. - Employee Handbook
## Effective Date: January 1, 2026

### Section 1: Introduction and Welcome

Welcome to Field Service Solutions Inc. (FSS). This handbook is designed to help you understand our company policies, procedures, and expectations. As a field service technician, you play a critical role in delivering exceptional service to our customers.

Our mission is to provide reliable, professional, and timely field service solutions while maintaining the highest standards of safety, quality, and customer satisfaction. Every member of our team contributes to this mission.

### Section 2: Employment Policies

#### 2.1 Equal Opportunity Employment
FSS is an equal opportunity employer. We do not discriminate based on race, color, religion, sex, national origin, age, disability, genetic information, or any other protected characteristic. All employment decisions are made based on qualifications, merit, and business needs.

#### 2.2 Background Checks and Drug Testing
All technicians must pass a background check and pre-employment drug screening. Random drug testing may be conducted in accordance with federal and state regulations, particularly for positions involving commercial vehicle operation or safety-sensitive duties.

#### 2.3 Employment Classification
Employees are classified as:
- Full-time: 40 hours per week with benefits
- Part-time: Less than 30 hours per week, limited benefits
- Contractor: Independent contractors with specific project agreements

### Section 3: Work Hours and Overtime

#### 3.1 Standard Work Hours
Full-time technicians work 8 hours per day, 40 hours per week. Standard business hours are Monday through Friday, 7:00 AM to 6:00 PM. However, field service work may require flexibility based on customer needs and emergency situations.

#### 3.2 Overtime Policy
Overtime work (hours exceeding 40 per week) must be approved in advance by your supervisor. Overtime is compensated at 1.5 times the regular hourly rate for non-exempt employees. Exempt employees may be eligible for compensatory time off in lieu of overtime pay.

#### 3.3 Daily Hour Limits
To ensure technician safety and prevent fatigue-related incidents, no technician may work more than 12 hours in a single day without explicit approval from a district manager. Daily work hours must be accurately logged in the time tracking system.

#### 3.4 Weekly Hour Limits
Full-time technicians are limited to 60 hours per week unless exceptional circumstances require additional hours. Any work exceeding 60 hours requires VP approval and must be documented with justification.

#### 3.5 Rest Periods
Technicians must take a minimum 30-minute unpaid lunch break for shifts exceeding 6 hours. Additionally, a 15-minute paid rest break is required for every 4 hours worked. Adequate rest between shifts (minimum 10 hours) is mandatory.

### Section 4: Time Tracking and Payroll

#### 4.1 Time Entry Requirements
All work hours must be logged daily in the FSS Mobile App before end of business. Late entries (more than 2 business days) require supervisor approval. Time entries must include:
- Start and end times (to the nearest 15 minutes)
- Job ID and customer information
- Detailed description of work performed
- Travel time (if applicable)
- Break times

#### 4.2 Billable vs Non-Billable Time
Billable hours are those spent directly on customer job sites performing service work. Non-billable hours include:
- Travel to/from the office
- Training and meetings
- Equipment maintenance
- Administrative tasks

Technicians should minimize non-billable time while ensuring quality service delivery.

#### 4.3 Payroll Schedule
Employees are paid bi-weekly on alternating Fridays. Paychecks are distributed via direct deposit. Pay stubs are available through the employee portal. Any discrepancies must be reported to HR within 5 business days.

### Section 5: Job Assignment and Scheduling

#### 5.1 Skill-Based Assignment
Jobs are assigned based on required skills and technician qualifications. Technicians must maintain current certifications in their skill areas. If assigned a job requiring skills you don't have, immediately notify your dispatcher.

#### 5.2 Schedule Changes
The dispatch team creates weekly schedules every Friday for the following week. Emergency jobs may be assigned with short notice. Technicians must respond to dispatch communications within 30 minutes during business hours.

#### 5.3 Job Refusal
Technicians may decline job assignments only for valid reasons:
- Safety concerns at the job site
- Lack of required certifications or skills
- Scheduling conflicts with approved time off
- Equipment unavailability

Unjustified job refusals may result in disciplinary action.

### Section 6: Safety and Compliance

#### 6.1 OSHA Compliance
All technicians must comply with Occupational Safety and Health Administration (OSHA) regulations. This includes:
- Using appropriate personal protective equipment (PPE)
- Following lockout/tagout procedures for electrical work
- Proper handling of hazardous materials
- Reporting unsafe conditions immediately

#### 6.2 Vehicle Safety
Technicians operating company vehicles must:
- Maintain a valid driver's license
- Follow all traffic laws and regulations
- Complete defensive driving training annually
- Conduct pre-trip vehicle inspections
- Never operate a vehicle while impaired or fatigued

#### 6.3 Customer Site Safety
When working at customer locations:
- Identify emergency exits upon arrival
- Use proper fall protection when working at heights
- Ensure proper ventilation in confined spaces
- Keep work areas clean and organized
- Report any hazards to the customer and your supervisor

#### 6.4 Incident Reporting
All workplace injuries, vehicle accidents, and safety hazards must be reported immediately to your supervisor, regardless of severity. Failure to report incidents may result in disciplinary action and affect workers' compensation claims.

### Section 7: Expense Reimbursement

#### 7.1 Approved Expenses
The company reimburses technicians for reasonable and necessary business expenses:
- Materials and parts (with itemized receipts)
- Fuel for company vehicles (company fuel card)
- Parking and tolls (with receipts)
- Tools under $50 (pre-approved only)
- Meals during overnight travel (per diem rates apply)

#### 7.2 Expense Submission
All expenses must be submitted within 15 days of incurrence through the expense management system. Required documentation:
- Original itemized receipts (no credit card slips alone)
- Business purpose description
- Customer/job ID
- Date and location

#### 7.3 Receipt Requirements
Receipts must clearly show:
- Vendor name and location
- Date of purchase
- Itemized list of purchases (not just total)
- Payment method
- Tax breakdown

Photos or scans of receipts are acceptable if legible. Lost receipts require a written explanation and may not be reimbursed.

#### 7.4 Non-Reimbursable Expenses
The following are NOT reimbursable:
- Personal meals (except during approved travel)
- Alcoholic beverages
- Personal vehicle maintenance
- Traffic tickets and parking violations
- Personal tools without prior approval
- Entertainment expenses

### Section 8: Equipment and Tools

#### 8.1 Company-Provided Equipment
FSS provides basic tools and equipment:
- Standard hand tool set
- Power tools specific to your trade
- Safety equipment (hard hat, safety glasses, gloves)
- Uniform shirts (3 per season)
- Company vehicle (for full-time field techs)

#### 8.2 Personal Tool Allowance
Technicians receive a $500 annual tool allowance for specialty tools. Tool purchases must be:
- Pre-approved by your supervisor
- Directly related to your job duties
- Submitted with itemized receipts

#### 8.3 Equipment Maintenance
Technicians are responsible for:
- Daily inspection of tools and equipment
- Reporting damaged or malfunctioning equipment
- Proper storage and transport of tools
- Return of equipment upon termination

Lost or damaged equipment due to negligence may be deducted from final paycheck in accordance with state law.

### Section 9: Customer Service Standards

#### 9.1 Professional Conduct
Technicians represent FSS at customer sites. Expected conduct includes:
- Arriving on time or notifying customer of delays
- Wearing clean, company-branded uniforms
- Speaking professionally and courteously
- Protecting customer property
- Cleaning work areas before leaving

#### 9.2 Communication
Keep customers informed throughout the job:
- Explain the work to be performed before starting
- Provide updates on progress
- Notify customer of any additional issues found
- Review completed work before leaving
- Obtain customer signature on work completion form

#### 9.3 Quality Workmanship
All work must meet industry standards and local building codes. Technicians must:
- Follow manufacturer specifications
- Use approved materials and methods
- Test systems before leaving
- Provide warranty information to customer
- Document work thoroughly

### Section 10: Leave and Time Off

#### 10.1 Paid Time Off (PTO)
Full-time employees accrue PTO based on tenure:
- Years 0-2: 10 days per year
- Years 3-5: 15 days per year
- Years 6+: 20 days per year

PTO requests must be submitted at least 2 weeks in advance for approval.

#### 10.2 Sick Leave
Employees may use PTO for illness. Absences of 3+ consecutive days require a doctor's note. Excessive unscheduled absences may result in disciplinary action.

#### 10.3 Holidays
FSS observes the following paid holidays:
- New Year's Day
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving (and day after)
- Christmas Day

#### 10.4 Family and Medical Leave
Eligible employees may take up to 12 weeks of unpaid leave under the Family and Medical Leave Act (FMLA) for qualifying reasons. Contact HR for FMLA eligibility and procedures.

### Section 11: Code of Conduct

#### 11.1 Harassment and Discrimination
FSS maintains a zero-tolerance policy for harassment and discrimination. This includes:
- Sexual harassment
- Racial discrimination
- Age discrimination
- Disability discrimination
- Retaliation against those who report violations

Report any violations to HR immediately. All reports are investigated promptly and confidentially.

#### 11.2 Workplace Violence
Threats, intimidation, or violence of any kind are strictly prohibited. This includes:
- Physical violence or threats
- Verbal abuse or intimidation
- Destruction of property
- Weapons on company property or in company vehicles

#### 11.3 Substance Abuse
Use, possession, or being under the influence of illegal drugs or alcohol during work hours is prohibited. This includes:
- At the office or customer sites
- In company vehicles
- During company events (except where alcohol is served at approved functions)

Violation may result in immediate termination.

#### 11.4 Confidentiality
Technicians may have access to customer information, trade secrets, and proprietary business information. This information must be kept confidential during and after employment.

### Section 12: Disciplinary Procedures

#### 12.1 Progressive Discipline
FSS uses progressive discipline for policy violations:
1. Verbal warning (documented)
2. Written warning
3. Suspension without pay
4. Termination

Serious violations may skip steps and result in immediate termination.

#### 12.2 Grounds for Immediate Termination
The following may result in immediate termination:
- Theft or dishonesty
- Falsifying time records or expense reports
- Violence or threats
- Drug or alcohol use on duty
- Gross negligence endangering others
- Sexual harassment
- Insubordination

### Section 13: Resignation and Termination

#### 13.1 Resignation
Employees should provide at least 2 weeks' written notice. Final paycheck includes:
- Wages through last day worked
- Unused PTO (where required by state law)
- Expense reimbursements (with proper documentation)

#### 13.2 Return of Property
Upon termination, return all company property:
- Company vehicle
- Tools and equipment
- Uniforms
- Credit cards and fuel cards
- Keys and access badges
- Mobile devices and tablets

#### 13.3 Exit Interview
Departing employees are asked to participate in an exit interview. Your feedback helps us improve our workplace.

---

This handbook provides general guidance and does not create an employment contract. FSS reserves the right to modify policies at any time. Employees will be notified of significant changes.

For questions about this handbook, contact Human Resources.

Last Updated: January 1, 2026
"""

# ============================================================================
# FEDERAL AND STATE COMPLIANCE DOCUMENTS
# ============================================================================

FEDERAL_COMPLIANCE_OSHA = """
# OSHA Compliance Guide for Field Service Technicians
## Occupational Safety and Health Administration Requirements

### Overview of OSHA Standards Applicable to Field Service Work

The Occupational Safety and Health Act of 1970 (OSH Act) requires employers to provide a workplace free from recognized hazards. Field service technicians face unique risks including electrical hazards, falls, vehicle accidents, and exposure to hazardous materials.

### General Duty Clause (Section 5(a)(1))

The General Duty Clause requires employers to provide employment and a place of employment "free from recognized hazards that are causing or are likely to cause death or serious physical harm." This applies even when specific OSHA standards don't exist for a particular hazard.

For field service work, this means:
- Assessing customer sites for hazards before work begins
- Providing appropriate training and equipment
- Implementing safety procedures for common field service hazards
- Maintaining records of hazard assessments

### Electrical Safety Standards (29 CFR 1910 Subpart S)

#### 1910.137 - Electrical Protective Equipment
Technicians working on or near energized electrical equipment must use appropriate protective equipment:
- Insulated gloves rated for voltage levels encountered
- Face shields or safety glasses with side shields
- Non-conductive footwear
- Flame-resistant clothing for arc flash hazards

The employer must ensure all electrical PPE is:
- Inspected before each use
- Tested periodically according to manufacturer specifications
- Replaced immediately if damaged
- Properly stored when not in use

#### 1910.147 - Control of Hazardous Energy (Lockout/Tagout)
Before servicing or maintaining equipment, technicians must:
1. Notify affected employees
2. Shut down equipment using normal stopping procedures
3. Isolate energy sources (electrical disconnects, valves, etc.)
4. Apply lockout/tagout devices
5. Verify zero energy state
6. Perform necessary work
7. Remove lockout/tagout devices only when safe

Each technician must use their own lock and tag. Group lockout procedures apply when multiple workers are involved.

#### 1910.333 - Selection and Use of Work Practices
Energized electrical work is permitted only when:
- De-energization creates greater hazards, or
- Work is on intrinsically safe equipment, or
- Infeasibility of de-energization is documented

When working on energized equipment:
- Use insulated tools
- Maintain approach distances based on voltage
- Wear arc-rated clothing and PPE
- Have a second person present for high-voltage work
- Use non-conductive ladders

### Fall Protection (29 CFR 1910.28 and 1926 Subpart M)

#### Requirements for Working at Heights
Fall protection is required when working 4 feet or more above a lower level. Options include:
- Guardrail systems
- Safety net systems
- Personal fall arrest systems (PFAS)

For field service technicians:
- Roof work requires guardrails or PFAS
- Ladder work over 6 feet requires stabilization
- Aerial lifts require harnesses attached to boom
- Walking/working surfaces must be inspected before use

#### Personal Fall Arrest Systems
Components must be certified and include:
- Full-body harness (never use belt-style harnesses)
- Shock-absorbing lanyard or self-retracting lifeline
- Anchor point rated for 5,000 lbs per person
- Connectors (carabiners, D-rings) rated for fall forces

Systems must limit free fall to 6 feet or less and arrest within 3.5 feet. After a fall, all components must be removed from service and inspected by qualified person.

#### Ladder Safety
Portable ladders must:
- Be inspected before each use
- Have non-slip feet
- Extend 3 feet above landing surface
- Be placed at proper angle (4:1 ratio for extension ladders)
- Have workers maintain 3-point contact
- Never be used as work platforms

Step ladders must not be used in folded position or as straight ladders.

### Respiratory Protection (29 CFR 1910.134)

When technicians may be exposed to harmful dusts, fumes, vapors, or gases:
- Conduct exposure assessment
- Provide medical evaluation for respirator users
- Fit-test each worker for their specific respirator
- Train on proper use, maintenance, and limitations
- Establish written respiratory protection program

Common field service scenarios requiring respirators:
- Spray painting or coating application
- Work in confined spaces with poor ventilation
- Asbestos-containing material disturbance
- Welding in enclosed areas
- Mold remediation

### Confined Space Entry (29 CFR 1910.146)

A confined space has limited entry/exit, is not designed for continuous occupancy, and may contain hazards. Permit-required confined spaces have additional hazards like:
- Hazardous atmospheres
- Engulfment hazards
- Configuration that could trap/asphyxiate
- Other recognized serious hazards

Before confined space entry:
1. Test atmosphere for oxygen (19.5-23.5%), flammability (<10% LEL), and toxins
2. Purge/ventilate if needed
3. Post attendant at opening
4. Establish rescue procedures
5. Issue entry permit
6. Continuous atmospheric monitoring during entry

Field service technicians commonly encounter confined spaces in:
- Utility vaults and manholes
- Crawl spaces with limited ventilation
- Large equipment interiors (boilers, tanks)
- Underground electrical rooms

### Hazard Communication (29 CFR 1910.1200)

Employers must:
- Maintain Safety Data Sheets (SDS) for all hazardous chemicals
- Label containers with product identifier and hazard warnings
- Train employees on chemical hazards before exposure
- Have written Hazard Communication program

Technicians have the right to:
- Access SDS for any chemical they may be exposed to
- Receive training in their primary language
- Know what chemicals are in products (no trade secret exception for health hazards)

Training must cover:
- How to read labels and SDS
- Physical and health hazards of chemicals
- Protective measures (PPE, ventilation, etc.)
- Emergency procedures for spills and exposure

### Vehicle and Driving Safety

While OSHA doesn't specifically regulate vehicle operation, employers must address driving hazards under the General Duty Clause. Best practices include:
- Motor vehicle safety policy
- Defensive driving training
- Vehicle inspection programs
- Cellphone use restrictions while driving
- Fatigue management (limit consecutive driving hours)
- Maintenance schedules

State traffic laws and DOT regulations may apply to company vehicles.

### Personal Protective Equipment (PPE) - 29 CFR 1910.132

Employers must:
1. Assess workplace for hazards
2. Select appropriate PPE for identified hazards
3. Provide PPE at no cost to employees
4. Train employees on proper use and maintenance
5. Require use of PPE

Common PPE for field service:
- Safety glasses with side shields (always)
- Hard hats (construction sites, overhead hazards)
- Safety-toe boots (heavy equipment, crushing hazards)
- Cut-resistant gloves (sharp edges, metalwork)
- Hearing protection (noise >85 dBA)

### Recordkeeping and Reporting (29 CFR 1904)

Employers must:
- Record work-related injuries and illnesses on OSHA 300 Log
- Classify injuries as days away from work, restricted duty, or other
- Post annual summary (Form 300A) from February 1 to April 30
- Report fatalities within 8 hours
- Report inpatient hospitalizations within 24 hours
- Maintain records for 5 years

Work-related injuries are those occurring in the work environment and resulting from work activities.

### Employee Rights Under OSHA

Workers have the right to:
- A safe workplace free from recognized hazards
- Receive training in a language they understand
- Review injury and illness records
- Request an OSHA inspection
- Report unsafe conditions without retaliation
- Receive information on chemical hazards
- Access their medical and exposure records

Employers cannot discriminate or retaliate against employees who exercise these rights. Complaints can be filed with OSHA's Whistleblower Protection Program.

### State OSHA Programs

States may run their own occupational safety programs if approved by federal OSHA. State plans must be at least as effective as federal OSHA. Currently, 22 states and jurisdictions have state plans covering private sector and public sector workers.

State plans may have:
- Different or additional standards
- Higher penalties
- More frequent inspections
- Different recordkeeping requirements

Field service companies operating in multiple states must comply with the standards in each state where they have employees.

### Penalties for Violations

OSHA violation types and maximum penalties (2026):
- Other-than-serious: Up to $15,625 per violation
- Serious: Up to $15,625 per violation
- Willful: $11,162 to $156,259 per violation
- Repeat: Up to $156,259 per violation
- Failure to abate: Up to $15,625 per day beyond abatement date

Penalties are adjusted annually for inflation. Willful violations resulting in death can lead to criminal prosecution.

---

This guide summarizes key OSHA requirements but is not comprehensive. Employers should consult specific OSHA standards and seek competent safety professionals for compliance assistance.

For more information: www.osha.gov or call 1-800-321-OSHA (6742)
"""

FEDERAL_COMPLIANCE_FLSA = """
# Fair Labor Standards Act (FLSA) Compliance Guide
## Wage and Hour Requirements for Field Service Employers

### FLSA Overview

The Fair Labor Standards Act, enacted in 1938 and enforced by the Wage and Hour Division of the Department of Labor, establishes:
- Minimum wage requirements
- Overtime pay rules
- Recordkeeping obligations
- Child labor protections

The FLSA applies to employers engaged in interstate commerce or with annual gross volume of sales of $500,000 or more. Individual employees may be covered even if their employer isn't, if the employee engages in interstate commerce.

### Minimum Wage Requirements

The federal minimum wage is currently $7.25 per hour (since 2009). Covered nonexempt workers must receive at least minimum wage for all hours worked. States may set higher minimum wages, and employers must pay the higher of federal or state minimum wage.

#### Tipped Employees
Field service technicians are not typically tipped employees, but if tips are received:
- Employer can pay as little as $2.13/hour (tip credit)
- Tips plus direct wages must equal at least $7.25/hour
- Employer must inform employees of tip credit provisions
- Tips belong to the employee, not the employer

#### Training and Meeting Time
Time spent in training, meetings, and lectures must be paid if:
- During normal working hours
- Attendance is mandatory
- Directly related to current job

Voluntary training outside normal hours for different job/skill development may be unpaid if all four criteria are met.

### Overtime Pay Requirements

Covered nonexempt employees must receive overtime pay at 1.5 times regular rate for hours worked over 40 in a workweek. A workweek is a fixed, recurring 168-hour period (not necessarily Sunday-Saturday).

#### Calculating Overtime
Regular rate includes:
- Hourly wages
- Salary divided by hours worked
- Piecework earnings
- Bonuses and shift differentials
- Commission earnings

Excluded from regular rate:
- Gifts and discretionary bonuses
- Reimbursed business expenses
- Premium pay for weekend/holiday work
- Certain benefit plan contributions

#### Common Overtime Calculation Examples

**Example 1: Hourly Worker**
- Regular rate: $20/hour
- Week hours: 48 hours
- Straight time: 48 × $20 = $960
- Overtime premium: 8 × ($20 × 0.5) = $80
- Total pay: $960 + $80 = $1,040

**Example 2: Salaried Nonexempt**
- Weekly salary: $800
- Week hours: 50 hours
- Regular rate: $800 ÷ 50 = $16/hour
- Overtime: 10 × ($16 × 1.5) = $240
- Total pay: $800 + $240 = $1,040

**Example 3: Multiple Pay Rates**
If employee works at different rates (e.g., $25 for skilled work, $20 for general labor):
- Calculate weighted average regular rate
- Apply 1.5× multiplier to overtime hours
- Some states prohibit this practice and require 1.5× highest rate

### Exempt Employees

Certain employees are exempt from minimum wage and/or overtime requirements if they meet specific tests for:
- Executive exemption
- Administrative exemption
- Professional exemption
- Computer employee exemption
- Outside sales exemption

#### Executive Exemption
Must meet ALL criteria:
- Paid salary of at least $684/week ($35,568 annually)
- Primary duty is managing enterprise or department
- Regularly directs work of 2+ full-time employees
- Authority to hire/fire or significant weight given to recommendations

Field service managers may qualify if they spend >50% time on management duties.

#### Administrative Exemption
Must meet ALL criteria:
- Paid salary of at least $684/week
- Primary duty is office/non-manual work related to management/business operations
- Exercise discretion and independent judgment on significant matters

Dispatchers, schedulers, and planners may qualify depending on duties.

#### Professional Exemption
Must meet ALL criteria:
- Paid salary of at least $684/week
- Primary duty is work requiring advanced knowledge
- In field of science or learning
- Acquired through prolonged, specialized instruction

Licensed engineers may qualify. Most technicians do NOT qualify even if highly skilled, because field service work is learned through experience and apprenticeship, not prolonged academic instruction.

#### Highly Compensated Employees
Employees earning $107,432+ annually are exempt if they:
- Perform office/non-manual work, and
- Customarily and regularly perform at least one exempt duty

#### Technicians Are Usually Nonexempt
Most field service technicians do not qualify for any exemption because:
- Work is manual/physical (installing, repairing)
- Not managing others
- Not exercising business discretion
- Skills learned through experience, not academic degree

Therefore, technicians must receive overtime pay for hours over 40/week.

### Hours Worked - What Counts

#### Compensable Work Time
Time is considered "hours worked" if:
- Employee must be on premises
- Employee is engaged to be waiting (not waiting to be engaged)
- On-call and cannot use time for personal purposes
- Performing any work for employer's benefit

#### Travel Time
Rules vary by situation:

**Home to Work** - Generally NOT compensable
- Normal commuting time is not hours worked
- Even if carrying tools or making stops

**Home to Work on Special Assignment** - COMPENSABLE
- Travel to customer site outside normal area
- One-day assignment in another city
- Travel time beyond normal commute counts

**Travel Away From Home** - PARTIALLY COMPENSABLE
- Travel during normal working hours counts (even on weekends)
- Travel as passenger outside working hours may not count
- Time performing work during travel always counts

**Between Job Sites** - COMPENSABLE
- Travel from one customer to another during workday
- Return to office between assignments
- Any travel during principal working hours

#### On-Call Time
Whether on-call time is compensable depends on restrictions:

**Compensable on-call:**
- Must remain on premises
- Cannot pursue personal activities
- Must respond within very short timeframe
- Severely restricted geographic area

**Non-compensable on-call:**
- Can go about personal business
- Reasonable response time allowed
- No geographic restrictions
- Just needs to be available by phone

#### Waiting Time
- "Engaged to wait" = compensable (waiting for next task)
- "Waiting to be engaged" = not compensable (completely relieved of duty)

#### Meal Periods
Meal periods of 30+ minutes are not compensable if:
- Employee is completely relieved of duty
- Free to leave premises
- Does not perform any work

Shorter breaks (5-20 minutes) must be paid.

### Recordkeeping Requirements

Employers must maintain accurate records for each nonexempt employee:
- Personal information (name, SSN, address)
- Hours worked each day and week
- Total wages paid each period
- Regular and overtime rates
- Basis of pay (hourly, weekly, piecework)
- Dates of payment and pay periods

#### Daily Time Records
For field service technicians, records must show:
- Time work began and ended
- Meal and break periods
- Total hours worked each day
- Total hours worked each week

Records must be kept for 3 years. Time cards and rate tables must be kept for 2 years.

#### Best Practices
- Use electronic time tracking systems
- Require daily time entry by technicians
- Supervisor review and approval
- Prohibit off-the-clock work
- Document all time worked, including brief tasks

### Deductions from Pay

#### Permitted Deductions
Can deduct from wages for:
- Federal/state/local taxes
- Social Security and Medicare
- Court-ordered garnishments
- Employee-authorized deductions (health insurance, 401k)
- Advances and loans (with written agreement)

#### Prohibited Deductions
Cannot deduct from minimum wage for:
- Tools and equipment
- Uniforms (unless decorative/optional)
- Cash shortages or breakage (unless due to dishonesty)
- Customer walkouts
- Required medical exams

Some states prohibit these deductions entirely, even from wages above minimum.

#### Improper Deductions from Exempt Employees
Making improper deductions from exempt employees' salaries can destroy the exemption, making them eligible for overtime:
- Partial day absences (except FMLA, first/last week)
- Jury duty, witness fees
- Full-week suspensions for reasons other than workplace conduct rule violations

### Retaliation Protections

FLSA prohibits retaliation against employees who:
- File wage complaints with DOL
- Testify in FLSA proceedings
- Inform management of FLSA violations
- Refuse to work if not paid properly

Retaliation includes:
- Termination or demotion
- Reduced hours or pay
- Unfavorable schedule changes
- Threats or intimidation

Employees have 2-3 years to file FLSA complaints (3 years if willful violation).

### Penalties for Violations

#### Civil Penalties
- Minimum wage violations: Back pay + equal amount in liquidated damages
- Overtime violations: Back pay + liquidated damages
- Recordkeeping violations: Up to $2,074 per violation
- Child labor violations: Up to $15,138 per violation
- Repeated/willful violations: Up to $2,074 per violation

#### Criminal Penalties
Willful violations may result in:
- Fines up to $10,000
- Imprisonment (for repeat offenders)

#### Statute of Limitations
- 2 years for non-willful violations
- 3 years for willful violations

### State Wage and Hour Laws

Many states have laws that are more protective than FLSA:
- Higher minimum wages
- Daily overtime (e.g., California: >8 hours/day)
- More restrictive exemptions
- Stronger recordkeeping requirements
- Greater penalties

When state and federal law differ, employers must follow the law most favorable to the employee.

---

This guide summarizes FLSA requirements. Consult the Department of Labor Wage and Hour Division and state labor agencies for specific situations.

For more information: www.dol.gov/whd or call 1-866-4-US-WAGE
"""

# ============================================================================
# STATE COMPLIANCE - Example for California (commonly referenced)
# ============================================================================

STATE_COMPLIANCE_EXAMPLE = """
# California Labor Laws for Field Service Companies
## Additional Requirements Beyond Federal Law

### Daily Overtime in California

Unlike federal law (which only requires overtime after 40 hours/week), California requires:

**Daily Overtime:** 
- 1.5× pay for hours over 8 in a workday
- 2× pay for hours over 12 in a workday

**7th Day Overtime:**
- 1.5× pay for first 8 hours on 7th consecutive day
- 2× pay for hours over 8 on 7th consecutive day

**Example:** Technician works Monday-Friday (10 hours each day) + Saturday (8 hours) + Sunday (4 hours)
- Mon-Fri: 5 days × (8 hours straight + 2 hours at 1.5×)
- Saturday: 8 hours at 1.5× (7th day)
- Sunday: 4 hours at 2× (7th day, over 8 hours total for week)

### Meal and Rest Break Requirements

#### Meal Breaks
- 30-minute unpaid meal break for shifts over 5 hours
- Second meal break for shifts over 10 hours
- Can waive first meal if shift ≤6 hours (written agreement)
- Can waive second meal if shift ≤12 hours and first meal taken

Employer must "provide" break (relieve of duty), not just "permit." If not provided, owe 1 hour pay at regular rate per violation.

#### Rest Breaks
- 10-minute paid rest break for every 4 hours worked (or major fraction thereof)
- Should be in middle of work period
- Cannot combine with meal break or leave early instead

**Example:** 8-hour shift should have:
- 10-minute rest break at ~2 hours
- 30-minute meal break at ~4 hours
- 10-minute rest break at ~6 hours

### Wage Payment Requirements

#### Payday Frequency
- Semimonthly (twice per month) for most employees
- Weekly or biweekly permissible with approval
- Must designate regular paydays

#### Final Wages
- Terminated: Immediately due (at termination meeting)
- Resigned without notice: Within 72 hours
- Resigned with 72+ hours notice: On last day

Failure to pay timely results in "waiting time penalty" - full day's wage for each day late (up to 30 days).

#### Wage Statements
Must provide itemized wage statement showing:
- Gross and net wages
- All deductions
- Hourly rates and hours worked
- Piece-rate units and rates
- Available sick leave balance

### Expense Reimbursement

California requires reimbursement of ALL necessary business expenses:
- Mileage (if using personal vehicle)
- Cell phone use (if required for work)
- Tools required for job
- Uniforms and safety equipment
- Internet/home office expenses (if remote work required)

Cannot require employees to bear any business expenses.

### Classifications and Licensing

#### Contractor License Requirements
Businesses performing field service work over $500 must have California Contractor License:
- C-10 Electrical
- C-20 Warm Air Heating/HVAC
- C-36 Plumbing
- C-46 Solar
- Other specialty classifications

Technicians performing work must be employed by licensed contractor or be licensed themselves.

#### Prevailing Wage
Public works projects require payment of prevailing wage rates (higher than minimum wage) determined by occupation and region. Must register with Department of Industrial Relations and follow strict reporting rules.

### Independent Contractor vs Employee (AB5)

California's AB5 law (effective 2020) established "ABC test" for independent contractor classification. Worker is employee unless employer proves ALL three:
- (A) Free from control and direction in performance
- (B) Performs work outside usual course of hiring entity's business
- (C) Customarily engaged in independently established trade

Most field service technicians cannot be classified as independent contractors under this test, as they:
- Receive job assignments and supervision (fails A)
- Perform company's core business (fails B)
- Work primarily/exclusively for one company (fails C)

Misclassification penalties: $5,000-$25,000 per violation, plus back wages, benefits, and taxes.

### Workers' Compensation

Required for ALL employees (including part-time, seasonal, family members). Must post notice of carrier and employee rights.

#### Injury Reporting
- Employee reports injury within 30 days
- Employer provides claim form within 1 day
- Employer files report to insurer within 5 days
- Insurer accepts/denies within 90 days

#### Retaliation Prohibition
Cannot terminate or discriminate against employee for:
- Filing workers' comp claim
- Being injured at work
- Testifying in comp proceeding

### Cal/OSHA - Additional Safety Requirements

California has state OSHA plan with additional requirements:

#### Heat Illness Prevention
When temperature ≥80°F (or 75°F if heavy work), employers must:
- Provide shade for cooldown breaks
- Provide sufficient fresh water (1 quart per hour per employee)
- Train on heat illness prevention
- Monitor for signs of heat illness

#### Injury and Illness Prevention Program (IIPP)
All employers must have written IIPP including:
- Hazard identification and correction
- Safety training program
- Recordkeeping of inspections and training
- Regular safety communications

#### Permit Required Confined Space Program
Must have comprehensive program including:
- Confined space inventory
- Atmospheric testing procedures
- Attendant and rescue procedures
- Annual review and updates

### Leave Laws

#### Sick Leave (AB 1522 / SB 616)
All employees accrue at least 1 hour sick leave per 30 hours worked:
- Minimum 40 hours accrual per year
- Can limit use to 40 hours per year
- Accrual begins on first day of employment
- Use after 90 days of employment

Use for:
- Employee illness/medical care
- Family member care
- Victim of domestic violence services

#### Family Rights Act (CFRA)
Eligible employees (1+ year, 1,250 hours) can take up to 12 weeks unpaid leave for:
- Serious health condition (employee or family)
- Baby bonding
- Military family needs

CFRA runs concurrent with FMLA but covers more family members.

#### Pregnancy Disability Leave (PDL)
Up to 4 months leave for disability due to pregnancy/childbirth. Separate from and in addition to CFRA baby bonding leave.

### Anti-Discrimination and Harassment Laws

California Fair Employment and Housing Act (FEHA) provides broader protections than federal law:

**Protected Characteristics:**
- Race, color, national origin, ancestry
- Religion (requires accommodation)
- Sex, gender, gender identity, expression
- Sexual orientation
- Pregnancy, childbirth, breastfeeding
- Age (40+)
- Disability (physical or mental)
- Medical condition
- Genetic information
- Marital status
- Military/veteran status

**Employer Obligations:**
- Applies to employers with 5+ employees (not 15 like federal)
- Must provide harassment training to all employees
  - Supervisors: 2 hours within 6 months of hire, then every 2 years
  - Non-supervisors: 1 hour within 6 months, then every 2 years
- Training must include abusive conduct/bullying prevention

### Privacy Rights

California Constitution provides explicit privacy rights:

#### Personnel Records
Employees can inspect personnel files:
- Within 30 days of written request
- Can get copies at own expense
- Can request corrections to inaccurate info

#### Background Checks and Arrests
- Cannot ask about criminal history on application
- Can only inquire after conditional offer
- Cannot consider:
  - Arrests not resulting in conviction
  - Convictions more than 7 years old (in most cases)
  - Marijuana convictions over 2 years old

#### Social Media
Cannot require employees to:
- Provide social media passwords
- Add employer/supervisor to personal accounts
- Access personal social media in employer's presence

### Wage Theft Prevention Act

Employers must provide written notice to new employees containing:
- Rate of pay
- Pay day
- Employer's legal name and contact info
- Workers' compensation carrier

Must update within 7 days of any change. Failure to provide can result in penalties.

### Local Ordinances

Many California cities have additional requirements:
- Higher minimum wages (e.g., San Francisco $18.07, Los Angeles $16.78)
- Paid sick leave beyond state requirements
- Fair scheduling/predictive scheduling laws
- Additional anti-discrimination protections

Field service companies must comply with laws in each jurisdiction where employees work.

---

California laws change frequently. Consult employment law attorney or Department of Industrial Relations for current requirements.

Resources:
- DIR: www.dir.ca.gov
- DLSE: www.dir.ca.gov/dlse
- DFEH: www.dfeh.ca.gov
"""
