"""
Realistic OCR receipt text and detailed work log descriptions
Part 2 of mock documents for Phase 3
"""

import random
from datetime import datetime
from faker import Faker

fake = Faker()

# ============================================================================
# REALISTIC RECEIPT OCR TEXT - Various vendor types
# ============================================================================

def generate_receipt_ocr_text(expense_type: str, amount: float, date: datetime) -> str:
    """Generate realistic OCR text from receipts based on expense type"""
    
    if expense_type == "materials":
        return generate_hardware_store_receipt(amount, date)
    elif expense_type == "travel":
        return generate_fuel_receipt(amount, date)
    elif expense_type == "equipment":
        return generate_equipment_receipt(amount, date)
    elif expense_type == "tools":
        return generate_tool_receipt(amount, date)
    else:
        return generate_generic_receipt(amount, date)

def generate_hardware_store_receipt(amount: float, date: datetime) -> str:
    """Hardware/electrical supply store receipt"""
    stores = [
        ("Home Depot", "1401 Main Street", "Orlando, FL 32801"),
        ("Lowe's", "2890 Commercial Blvd", "Tampa, FL 33619"),
        ("Grainger", "567 Industrial Way", "Miami, FL 33142"),
        ("Menards", "3401 Highway 51", "Madison, WI 53704"),
        ("Ace Hardware", "789 Oak Street", "Phoenix, AZ 85012")
    ]
    
    store_name, street, city_state = random.choice(stores)
    
    # Generate line items that add up to total
    items = []
    remaining = amount * 0.92  # 92% for items, 8% for tax
    
    electrical_items = [
        ("Wire 12/2 NM-B 250ft", 45.99),
        ("Outlet GFCI 20A White", 18.95),
        ("Circuit Breaker 20A", 12.50),
        ("Conduit EMT 1/2\" 10ft", 8.75),
        ("Junction Box 4\" Square", 3.25),
        ("Wire Nuts Assorted Pk", 6.99),
        ("Electrical Tape Black", 4.50),
        ("Romex Cable Staples", 7.25),
        ("Toggle Switch 15A", 5.95),
        ("Light Fixture LED 60W", 32.99),
        ("Dimmer Switch", 22.50),
        ("Extension Cord 50ft", 28.99),
    ]
    
    plumbing_items = [
        ("PVC Pipe 1\" SCH40 10ft", 12.95),
        ("PVC Elbow 90deg 1\"", 2.25),
        ("PVC Cement 16oz", 8.50),
        ("Copper Pipe 1/2\" 10ft", 24.99),
        ("SharkBite Coupling 1/2\"", 7.95),
        ("Faucet Aerator", 4.99),
        ("Pipe Tape PTFE", 3.25),
        ("Pipe Wrench 18\"", 35.99),
        ("Basin Wrench", 18.75),
    ]
    
    hvac_items = [
        ("HVAC Filter 20x25x1", 16.99),
        ("Refrigerant R-410A 1lb", 45.00),
        ("Condensate Pump", 89.99),
        ("Thermostat Wire 18/5", 28.50),
        ("Duct Tape 2\" x 60yd", 12.95),
        ("Flex Duct 6\" x 25ft", 38.75),
    ]
    
    all_items = electrical_items + plumbing_items + hvac_items
    random.shuffle(all_items)
    
    # Select items that fit budget
    for item_name, item_price in all_items:
        if remaining >= item_price:
            qty = random.randint(1, min(3, int(remaining / item_price)))
            line_total = item_price * qty
            if line_total <= remaining:
                items.append((item_name, qty, item_price, line_total))
                remaining -= line_total
        if len(items) >= 5 or remaining < 3:
            break
    
    # Calculate tax
    subtotal = sum(item[3] for item in items)
    tax = amount - subtotal
    
    receipt = f"""
{store_name}
{street}
{city_state}
Phone: (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}

Date: {date.strftime('%m/%d/%Y')}
Time: {date.strftime('%I:%M %p')}
Store #: {random.randint(1000, 9999)}
Register: {random.randint(1, 12)}
Cashier: {fake.first_name()}
Receipt #: {random.randint(100000, 999999)}

{'ITEM':<30} {'QTY':>3} {'PRICE':>8} {'TOTAL':>8}
{'-' * 53}
"""
    
    for item_name, qty, price, total in items:
        receipt += f"{item_name:<30} {qty:>3} ${price:>7.2f} ${total:>7.2f}\n"
    
    receipt += f"""
{'-' * 53}
{'Subtotal:':<42} ${subtotal:>8.2f}
{'Tax (8.5%):':<42} ${tax:>8.2f}
{'TOTAL:':<42} ${amount:>8.2f}

Payment Method: VISA ****{random.randint(1000, 9999)}
Approval Code: {random.randint(100000, 999999)}

Thank you for shopping at {store_name}!
Pro Xtra Rewards Member #: {random.randint(1000000, 9999999)}

Return Policy: 90 days with receipt
Items purchased for commercial use

---OCR Quality: 94%---
Scanned: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return receipt.strip()

def generate_fuel_receipt(amount: float, date: datetime) -> str:
    """Fuel/gas station receipt"""
    stations = [
        "Shell", "BP", "Chevron", "ExxonMobil", "Sunoco", 
        "Circle K", "7-Eleven", "Speedway", "Wawa"
    ]
    station = random.choice(stations)
    
    gallons = amount / random.uniform(3.20, 4.50)  # price per gallon
    price_per_gallon = amount / gallons
    
    receipt = f"""
{station} Gas Station
{fake.street_address()}
{fake.city()}, {fake.state_abbr()} {fake.zipcode()}

Date: {date.strftime('%m/%d/%Y')}
Time: {date.strftime('%I:%M %p')}

Pump #: {random.randint(1, 12)}
Receipt #: {random.randint(10000, 99999)}

FUEL SALE - REGULAR UNLEADED

Gallons: {gallons:>10.3f}
Price/Gal: ${price_per_gallon:>9.3f}
Fuel Total: ${amount:>9.2f}

Payment: FLEET CARD ****{random.randint(1000, 9999)}
Vehicle ID: {random.randint(100, 999)}
Odometer: {random.randint(35000, 95000)} mi

Thank you!
Rewards points earned: {int(gallons * 10)}

---OCR Quality: 96%---
Note: Some text blurred from thermal fade
"""
    return receipt.strip()

def generate_equipment_receipt(amount: float, date: datetime) -> str:
    """Equipment rental or purchase receipt"""
    vendors = [
        ("Tool Rentals Plus", "Industrial equipment"),
        ("Sunbelt Rentals", "Construction equipment"),
        ("United Rentals", "Power tools & equipment"),
        ("HD Supply", "Professional equipment")
    ]
    vendor, tagline = random.choice(vendors)
    
    equipment_types = [
        ("Aerial Lift - JLG 40ft", 285.00, "daily"),
        ("Generator 7500W Honda", 95.00, "daily"),
        ("Pressure Washer 3000PSI", 65.00, "daily"),
        ("Concrete Saw 14\"", 75.00, "daily"),
        ("Jackhammer Electric", 55.00, "daily"),
        ("Scaffolding 6' x 10'", 125.00, "weekly"),
        ("Laser Level Rotary", 45.00, "daily"),
    ]
    
    equipment, base_rate, rental_type = random.choice(equipment_types)
    days = int(amount / base_rate)
    if days < 1:
        days = 1
    
    subtotal = base_rate * days
    damage_waiver = subtotal * 0.15
    tax = (subtotal + damage_waiver) * 0.08
    total = subtotal + damage_waiver + tax
    
    receipt = f"""
{vendor}
{tagline}
{fake.street_address()}
{fake.city()}, {fake.state_abbr()} {fake.zipcode()}
Phone: (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}

RENTAL AGREEMENT
Contract #: {random.randint(100000, 999999)}
Date: {date.strftime('%m/%d/%Y %I:%M %p')}

Customer: Field Service Solutions Inc
Account #: FSS{random.randint(1000, 9999)}
PO Number: {random.randint(10000, 99999)}

EQUIPMENT RENTED:
{equipment}
Serial #: {random.choice(['JLG', 'CAT', 'HON', 'DWT'])}{random.randint(100000, 999999)}

Rental Period: {days} {rental_type}{'s' if days > 1 else ''}
Out: {date.strftime('%m/%d/%Y')}
Due: {(date + timedelta(days=days)).strftime('%m/%d/%Y')}

Charges:
Equipment Rental ({rental_type}): ${base_rate:>8.2f}
Days/Periods: {days:>14}
Subtotal: ${subtotal:>19.2f}
Damage Waiver (15%): ${damage_waiver:>13.2f}
Tax (8%): ${tax:>23.2f}
{'=' * 38}
TOTAL AMOUNT: ${total:>21.2f}

Payment Method: Company Check #{random.randint(1000, 9999)}
Authorized By: {fake.name()}
Signature: _______________

Equipment condition: GOOD
Fuel level: FULL

Return clean and fueled or additional charges apply
Late return: ${base_rate * 1.5}/day after due date

---OCR Quality: 91%---
Some characters unclear due to carbon copy
"""
    return receipt.strip()

def generate_tool_receipt(amount: float, date: datetime) -> str:
    """Tool purchase receipt"""
    vendors = [
        "Harbor Freight Tools",
        "Northern Tool + Equipment",
        "Tool Depot",
        "Pro Tool Supply"
    ]
    vendor = random.choice(vendors)
    
    tools = [
        ("Milwaukee M18 Drill Kit", 179.99),
        ("DeWalt Impact Driver", 149.99),
        ("Klein Electrician Tool Set", 89.95),
        ("Fluke Digital Multimeter", 229.00),
        ("Channellock Pliers Set", 54.99),
        ("Irwin Vise-Grip Set", 42.50),
        ("Milwaukee Sawzall", 199.00),
        ("Ridgid Pipe Threader", 385.00),
        ("Lenox Hole Saw Kit", 67.99),
        ("Greenlee Knockout Set", 425.00),
    ]
    
    # Select one main tool
    tool_name, tool_price = random.choice(tools)
    
    subtotal = tool_price
    tax = subtotal * 0.085
    total = subtotal + tax
    
    receipt = f"""
{vendor}
{fake.street_address()}
{fake.city()}, {fake.state_abbr()} {fake.zipcode()}

Date: {date.strftime('%m/%d/%Y')}
Time: {date.strftime('%I:%M:%S %p')}
Transaction #: {random.randint(1000000, 9999999)}

SALE
{'-' * 45}

{tool_name}
SKU: {random.randint(100000, 999999)}
Price: ${tool_price:.2f}

{'-' * 45}
Subtotal: ${subtotal:>18.2f}
Sales Tax (8.5%): ${tax:>12.2f}
TOTAL: ${total:>21.2f}

VISA ****{random.randint(1000, 9999)}
Approval: {random.randint(100000, 999999)}

Items: 1
Cashier: {fake.first_name()}

*** APPROVED - THANK YOU ***

Lifetime Warranty on Hand Tools
Returns accepted within 90 days with receipt

Pro Account #: FSS{random.randint(10000, 99999)}

---OCR Quality: 98%---
High quality thermal print
"""
    return receipt.strip()

def generate_generic_receipt(amount: float, date: datetime) -> str:
    """Generic vendor receipt"""
    receipt = f"""
BUSINESS EXPENSE RECEIPT

Vendor: {fake.company()}
Location: {fake.city()}, {fake.state_abbr()}
Date: {date.strftime('%m/%d/%Y')}
Receipt #: {random.randint(1000, 9999)}

Description: Professional Services
Amount: ${amount:.2f}

Payment: Company Credit Card
Card ending: {random.randint(1000, 9999)}

Authorized by: {fake.name()}

---OCR Quality: 85%---
Faded ink, some text illegible
"""
    return receipt.strip()

# ============================================================================
# DETAILED WORK LOG DESCRIPTIONS - Technical narratives
# ============================================================================

def generate_detailed_work_description(job_type: str, skills: list) -> str:
    """Generate realistic, detailed work log descriptions"""
    
    descriptions = {
        "HVAC": [
            """Responded to emergency call for complete HVAC system failure at customer site. Upon arrival, found
            that the condenser unit was not running at all. Performed initial diagnostics and discovered that
            the contactor was welded shut, indicating a severe electrical issue. Checked the compressor windings
            with megger and found they were grounded. Further investigation revealed that the system had been
            running low on refrigerant for an extended period, causing the compressor to overheat and eventually
            fail. The low refrigerant was due to a slow leak in the evaporator coil that had gone undetected.
            
            Recommended complete compressor replacement along with evaporator coil replacement to address the
            root cause. Customer approved the work. Recovered remaining refrigerant using recovery machine per
            EPA regulations. Removed failed compressor and installed new scroll compressor with matching tonnage.
            Replaced evaporator coil with higher efficiency model. Installed new filter drier and performed
            vacuum test for 2 hours to ensure system held at 500 microns. System passed leak test.
            
            Charged system with manufacturer-specified amount of R-410A refrigerant. Started system and monitored
            for 45 minutes. Measured superheat at 8°F and subcooling at 12°F, both within normal operating range.
            Verified that supply air temperature was 55°F with return air at 75°F, indicating proper cooling.
            Cleaned up work area and provided customer with detailed explanation of work performed and warranty
            information. Customer satisfied with repair. Total time: 7.5 hours including travel.""",
            
            """Performed scheduled quarterly maintenance on rooftop HVAC unit serving 15,000 sq ft office building.
            Accessed unit via roof ladder and set up fall protection per OSHA requirements. Began with visual
            inspection of all components. Noted some corrosion on condenser coil fins but not severe enough to
            affect performance. Economizer dampers showed signs of binding - lubricated actuator linkage and
            verified full range of motion.
            
            Checked and tightened all electrical connections - found two loose terminal connections on contactor
            which could have led to future failure. Measured voltage and amperage on compressor: 231V at 28.4 amps,
            within normal range for this model. Replaced air filters (24x24x2) with MERV 13 filters per building
            specifications. Previous filters were approximately 60% loaded but not restricting airflow significantly.
            
            Cleaned condenser coils using coil cleaner and pressure washer, taking care not to bend fins. Improved
            heat transfer efficiency noticeably. Checked refrigerant charge using superheat/subcooling method.
            Superheat measured 10°F, subcooling 10°F - both ideal for this system. No refrigerant addition needed.
            Verified that all safety controls were functioning: high pressure cutout, low pressure cutout, freeze
            stat all tested within spec.
            
            Tested economizer operation in all modes (cooling, free cooling, heating). Dampers opened and closed
            smoothly after earlier lubrication. Temperature sensors reading accurately. Replaced belt on supply
            fan as it showed signs of cracking. Adjusted belt tension to proper deflection of 1/2 inch.
            Documented all findings on service report and recommended budget for condenser coil replacement within
            next 12-18 months due to advancing corrosion. Customer acknowledged recommendations.""",
        ],
        
        "Electrical": [
            """Dispatched to commercial property for report of partial power outage. Customer stated that half of
            the lights and outlets in the building were not working. Upon arrival, verified that circuits 1, 3, 5,
            7, and 9 (all odd-numbered circuits) were dead while even-numbered circuits were energized. This
            pattern immediately suggested loss of one leg of the 240V service.
            
            Checked main panel and confirmed that one of the two 120V legs was reading 0V while the other showed
            normal 122V. Voltmeter reading between the two legs showed only 122V instead of expected 240V, confirming
            lost neutral or lost phase. Notified customer that this was a utility company issue affecting the
            service entrance. However, customer requested I investigate further to rule out any issues on their side.
            
            Inspected meter base and service entrance conductors. Found that one of the main service entrance
            conductors had broken inside the weatherhead due to fatigue from wind movement over many years. The
            broken conductor was hanging loose and not making proper contact. This was causing the loss of one phase.
            Immediately shut off main disconnect for safety and red-tagged the panel.
            
            Coordinated with utility company to temporarily disconnect service at the transformer. Once power was
            confirmed off and locked out, accessed weatherhead and found severe corrosion in addition to the broken
            conductor. Recommended complete service entrance upgrade to prevent future failures. Customer approved
            emergency repair to restore power immediately, with full upgrade scheduled for following week.
            
            Installed new weatherhead, service entrance conductors, and proper strain relief to prevent future
            fatigue failures. Utility company reconnected service and I verified proper voltage on both legs:
            121V and 123V, with 244V across them. Tested all circuits and confirmed power restored throughout
            building. Provided customer with written quote for permanent service upgrade including new panel,
            meter base, and properly rated disconnect. Total emergency repair time: 4.5 hours.""",
            
            """Performed electrical rough-in for commercial tenant improvement project. Reviewed architectural and
            electrical plans prior to arriving on site. Project consists of converting 3,200 sq ft of raw retail
            space into medical office with multiple exam rooms, lab area, and reception.
            
            Began by laying out all outlet and switch locations per plans. Used chalk line and laser level to
            ensure alignment and proper heights. Installed boxes at 18 inches AFF for outlets and 48 inches AFF
            for switches per client specifications (standard is 12" and 48" respectively, but medical office
            requested higher outlets for easier access). All boxes stubbed out 1/2 inch from finished wall per
            plan notes for drywall thickness.
            
            Ran conduit for main power distribution. Installed 2-inch EMT from main panel location to first junction
            box, then reduced to 1-inch for branch circuits. All conduit runs secured with appropriate hangers
            every 6 feet and within 3 feet of boxes per NEC requirements. Pulled 12/2 and 12/3 Romex for standard
            circuits. Used 10/2 for dedicated 20A circuits serving medical equipment in lab area.
            
            Installed dedicated circuits as specified: two 20A circuits for lab equipment, one 20A circuit for
            refrigerator, two 20A circuits for computer/network equipment, and separate 20A circuit for server
            room HVAC. All circuits properly labeled at panel with circuit directory. Kitchen area received two
            20A small appliance circuits and one 20A circuit for future dishwasher per code.
            
            Rough-in included installation of 3/4 inch conduit for network cabling, though network cables will be
            pulled by low-voltage contractor. Installed boxes and conduit for (12) LED can lights in exam rooms,
            (8) LED troffers in reception area, and emergency exit lights at both exits. All circuits tested for
            continuity and shorts before closing walls. Passed rough-in inspection with no deficiencies noted.
            Coordinated with GC regarding drywall schedule.""",
        ],
        
        "Plumbing": [
            """Emergency service call for water leak in commercial building. Customer reported water dripping from
            ceiling in second-floor bathroom. Arrived on site and immediately shut off water main to prevent further
            damage. Accessed ceiling cavity and found that a 1/2 inch copper cold water supply line had split due
            to freezing. The pipe was located near an exterior wall where insulation was insufficient.
            
            The split was approximately 3 inches long and water had been leaking for several hours based on the
            amount of water damage visible. Removed section of damaged pipe and measured for replacement. Found
            that the pipe run was from the 1960s original construction and showed signs of corrosion throughout,
            suggesting that this was not the only potential failure point.
            
            Recommended to customer that we replace the entire run from the main line to the bathroom fixtures
            rather than just patching the split, as the pipe was at the end of its service life. Customer approved
            the expanded scope to prevent future leaks. Drained all lines and removed approximately 25 feet of
            old copper piping. Installed new 1/2 inch Type L copper pipe with lead-free solder connections.
            
            Added proper insulation around all pipes near exterior walls to prevent future freezing. Installed
            new angle stops at toilet and sink as the old ones were corroded and difficult to operate. Pressure
            tested the new installation at 100 PSI for 30 minutes with no leaks detected. Restored water service
            and verified proper flow and no leaks at all connections. Cleaned up work area and disposed of old
            piping properly. Customer satisfied with thorough repair. Recommended they have building insulation
            improved to prevent future freeze issues.""",
        ],
    }
    
    # Select random description from available ones for this job type
    if job_type in descriptions:
        return random.choice(descriptions[job_type])
    else:
        # Generic technical description if specific type not found
        return f"""Completed service call at customer site. Performed diagnostic assessment of reported issue.
        Identified root cause and explained findings to customer. Obtained approval for recommended repairs.
        Completed work according to manufacturer specifications and local codes. Tested system operation and
        verified proper function. Cleaned work area and reviewed completed work with customer. All work performed
        professionally and to customer satisfaction. Total time including travel: {random.uniform(2.5, 8.5):.1f} hours."""

from datetime import timedelta
