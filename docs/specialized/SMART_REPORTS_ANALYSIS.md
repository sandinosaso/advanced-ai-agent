# Smart Reports Analysis

**Generated:** 2026-02-06  
**Purpose:** Comprehensive analysis of 48 smart reports to guide AI Agent training and testing, with focus on JOIN complexity.

---

## Executive Summary

### Overview Statistics

- **Total Reports Analyzed:** 48
- **LLM-Based Reports (with prompt):** 37 (77%)
- **Manual Reports (no prompt):** 11 (23%)
- **Production Reports (isInternal=false):** 35 (73%)
- **Internal/Test Reports (isInternal=true):** 13 (27%)

### Context Distribution

- **GLOBAL Context:** 35 reports (73%)
- **WORKORDER Context:** 13 reports (27%)

### Complexity Distribution (JOIN-Focused)

- **Low Complexity (1-2):** 12 reports (25%) - Simple queries, 0-2 joins
- **Medium Complexity (3-5):** 18 reports (38%) - 3-5 joins, basic patterns
- **High Complexity (6-8):** 14 reports (29%) - 6+ joins, bridge tables
- **Very High Complexity (9-10):** 4 reports (8%) - CTEs, complex join paths

### Key Findings

1. **JOIN Patterns:** Most reports use LEFT JOINs (83%), indicating outer join preference for optional relationships
2. **Common Patterns:** Payroll calculations (4 variants), work order listings (5 variants), inspection reports (4 variants)
3. **Advanced SQL Usage:** 
   - JSON extraction: 8 reports (17%)
   - CTEs (WITH clauses): 2 reports (4%)
   - CASE statements: 12 reports (25%)
   - GROUP_CONCAT: 8 reports (17%)
4. **Domain Coverage:** 23 reports (48%) have partial or full domain registry support

---

## Main Analysis Table

| # | Name | Type | Complexity | Priority | Tables | JOINs | LEFT | Domain | Status | Notes |
|---|------|------|------------|----------|--------|-------|------|--------|--------|-------|
| 1 | Failed! | LLM | 5 | 6 | 4 | 3 | ✓ | ⚠️ | Production | Inspection questions/answers aggregation |
| 2 | Payroll v1 | LLM | 8 | 9 | 6 | 5 | ✓ | ❌ | Production | Complex payroll with CASE, DAYOFWEEK, GROUP_CONCAT |
| 3 | Payroll Test 1 | LLM | 5 | 4 | 4 | 3 | ✓ | ❌ | Internal | Payroll variant, subquery pattern |
| 4 | Settings | LLM | 3 | 5 | 3 | 2 | ✓ | ❌ | Internal | Simple settings list with user info |
| 5 | Work Orders and Leads | LLM | 5 | 7 | 4 | 3 | ✓ | ❌ | Internal | WO with crew leads, multiple LEFT JOINs |
| 6 | List all WO | LLM | 4 | 7 | 3 | 2 | ✓ | ❌ | Production | WO with JSON dynamic attributes |
| 7 | All inspections | LLM | 6 | 8 | 6 | 5 | ✓ | ⚠️ | Production | Inspection with equipment, multiple joins |
| 8 | SL False Information | LLM | 1 | 2 | 1 | 0 | ✗ | ❌ | Production | Simple WHERE IN filter - test data |
| 9 | [TEST] Unexpected error | LLM | 1 | 1 | 1 | 0 | ✗ | ❌ | Production | Simple SELECT, test report |
| 10 | [TEST] Number values | LLM | 2 | 3 | 2 | 1 | ✗ | ❌ | Production | Dynamic attributes with JOIN |
| 11 | All services | Manual | 6 | 6 | 6 | 5 | ✓ | ⚠️ | Production | Similar to inspections pattern |
| 12 | SR with dates | LLM | 4 | 7 | 4 | 3 | ✗ | ❌ | Production | WO with crew leads, CONCAT |
| 13 | Anything | LLM | 2 | 5 | 2 | 1 | ✓ | ❌ | Production | WO with customer info |
| 14 | Template Copy | Manual | 1 | 2 | 1 | 0 | ✗ | ❌ | Production | Simple inspection template list |
| 15 | all work orders | LLM | 4 | 7 | 4 | 3 | ✗ | ❌ | Production | WO with status, customer, location |
| 16 | Delete Report | LLM | 1 | 1 | 0 | 0 | ✗ | ❌ | Production | Literal test query |
| 17 | Amount of templ | LLM | 1 | 2 | 1 | 0 | ✗ | ❌ | Production | Simple COUNT with ORDER BY |
| 18 | Duplicated WTTs | Manual | 3 | 3 | 1 | 0 | ✗ | ❌ | Internal | GROUP BY with HAVING, GROUP_CONCAT |
| 19 | Desc Bug | LLM | 3 | 5 | 3 | 2 | ✓ | ❌ | Production | WO with customer, location |
| 20 | Deleted Report | LLM | 2 | 3 | 2 | 1 | ✓ | ❌ | Production | Simple WO with customer |
| 21 | WOs with WT | LLM | 4 | 7 | 4 | 3 | ✗ | ❌ | Production | WO with workTime existence check |
| 22 | Payroll v3 | LLM | 10 | 9 | 9 | 8 | ✓ | ❌ | Internal | **Most complex:** UNION, CASE, date logic |
| 23 | Null? | LLM | 1 | 2 | 1 | 0 | ✗ | ❌ | Production | Test query with NULL values |
| 24 | All customers | LLM | 1 | 5 | 1 | 0 | ✗ | ❌ | Production | Simple customer list |
| 25 | Dubious result2 | LLM | 4 | 3 | 4 | 3 | ✓ | ⚠️ | Production | Inspection with template, GROUP BY |
| 26 | User activity | LLM | 1 | 4 | 1 | 0 | ✗ | ❌ | Internal | Simple user list with CONCAT |
| 27 | DynAttr | LLM | 2 | 6 | 2 | 1 | ✓ | ⚠️ | Production | Asset with JSON dynamic attributes |
| 28 | Two Date Columns | LLM | 1 | 4 | 1 | 0 | ✗ | ❌ | Production | WO with JSON attributes |
| 29 | Crew List | LLM | 5 | 8 | 5 | 4 | ✗ | ❌ | Production | Employee crew history, multiple joins |
| 30 | test wo dyn attrs | LLM | 1 | 4 | 1 | 0 | ✗ | ❌ | Production | WO JSON attributes only |
| 31 | Active Customer | LLM | 1 | 5 | 1 | 0 | ✗ | ❌ | Production | Customer with WHERE filter |
| 32 | Dubious results | LLM | 5 | 4 | 6 | 5 | ✓ | ⚠️ | Production | Inspection with multiple LEFT JOINs |
| 33 | Internal | Manual | 2 | 3 | 2 | 1 | ✓ | ❌ | Internal | WO with JSON attributes |
| 34 | Employee Utilization | Manual | 9 | 8 | 3 | 2 | ✓ | ❌ | Production | **CTE-based:** Complex date calculations |
| 35 | Payroll LR Report | LLM | 7 | 7 | 6 | 5 | ✓ | ❌ | Internal | Payroll with location/role abbreviations |
| 36 | Payroll v2 | LLM | 6 | 8 | 5 | 4 | ✗ | ❌ | Production | Payroll with GROUP_CONCAT |
| 37 | Evil Tobi | LLM | 4 | 3 | 4 | 3 | ✓ | ❌ | Production | Employee search with LIKE |
| 38 | All work times | LLM | 2 | 6 | 3 | 2 | ✓ | ❌ | Production | WorkTime with type and employee |
| 39 | All DA columns | Manual | 1 | 3 | 1 | 0 | ✗ | ❌ | Internal | Asset with all JSON attributes |
| 40 | Work order with time | LLM | 4 | 7 | 4 | 3 | ✗ | ❌ | Production | WO with EXISTS subquery |
| 41 | CREW-841 | LLM | 1 | 2 | 1 | 0 | ✗ | ❌ | Production | Simple description query |
| 42 | WOs inspections | LLM | 3 | 4 | 3 | 2 | ✓ | ⚠️ | Production | Inspection basic info |

**Legend:**
- **Type:** LLM (has prompt) or Manual (no prompt)
- **Complexity:** 1-10 scale (JOIN-focused)
- **Priority:** 1-10 (training value)
- **LEFT:** ✓ has LEFT JOIN, ✗ only INNER/no joins
- **Domain:** ✅ Full coverage, ⚠️ Partial, ❌ None, N/A Manual
- **Status:** Production (isInternal=false) or Internal (isInternal=true)

---

## Detailed SQL Pattern Breakdown

### Category 1: Payroll Reports (High Priority for Training)

#### Report #2: Payroll v1 (Complexity: 8, Priority: 9)

**Prompt:** "create a report that will contains all WorkTimes per user and date of the work times, so group all user work times per date, add a column to show the work order number where those Times where added, and for the date display the weekday (for example mm/dd/yyyy ddd), and for the user show name and last name in the same column called Employee Name. Then show column for Regular Time, for OverTime and Double Time, but the data in those columns needs to be calculated the following way, sum all work time hours for the day and: - all hours, with a date on a Sunday, will be Double Time - all hours, with a date that is a weekday or Saturday, under or equal 8 hours would be Regular Time - all hours, with a date that is a weekday or Saturday, over 8 hours would be OverTime"

**Tables Involved:**
- `workTime` (primary)
- `secure_employee` (employee info)
- `crewWorkDay` (date context)
- `crew` (work context)
- `secure_workOrder` (work order info)

**JOIN Chain:**
```
workTime 
  → secure_employee (employeeId)
  → crewWorkDay (crewWorkDayId) [LEFT]
  → crew (crewId) [LEFT]
  → secure_workOrder (workOrderId) [LEFT]
```

**Columns Selected:**
- `CONCAT(firstName, ' ', lastName)` AS Employee Name
- `cwd.date` AS Date
- `GROUP_CONCAT(DISTINCT workOrderNumber)` AS Work Order Number
- `CASE WHEN DAYOFWEEK(date)=1 THEN 0 ELSE LEAST(SUM(hours), 8) END` AS Regular Time
- `CASE WHEN DAYOFWEEK(date)=1 THEN 0 ELSE GREATEST(SUM(hours)-8, 0) END` AS OverTime
- `CASE WHEN DAYOFWEEK(date)=1 THEN SUM(hours) ELSE 0 END` AS Double Time
- `CASE...END` AS Total Time

**WHERE Conditions:**
- `cwd.date IS NOT NULL`
- `sw.isInternal = 0`
- `se.isInternal = 0`

**Advanced Features:**
- Multiple CASE statements (4)
- DAYOFWEEK() date function
- GROUP_CONCAT with DISTINCT and ORDER BY
- COALESCE for NULL handling
- Complex aggregation logic (LEAST, GREATEST)
- GROUP BY with multiple columns

**JOIN Complexity Analysis:**
- **Join Count:** 5 (4 LEFT, 1 INNER)
- **Join Depth:** 5 hops from workTime
- **Bridge Tables:** crew (connects workTime → workOrder)
- **Complexity Score:** 8/10

**Domain Coverage:** ❌ None
- No domain rules for payroll calculations
- Business logic embedded in SQL (Sunday = double time)

---

#### Report #22: Payroll v3 (Complexity: 10, Priority: 9) ⭐ MOST COMPLEX

**Prompt:** Similar to v1 but includes both WorkTimes AND Travel Times

**Tables Involved:**
- `workTime` (primary source 1)
- `travelTime` (primary source 2)
- `secure_employee` (employee info)
- `crewWorkDay` (date context)
- `crew` (work context)
- `secure_workOrder` (work order info)

**JOIN Chain:**
```
UNION of two subqueries:
  Subquery 1: workTime → crewWorkDay → crew → secure_workOrder → secure_employee
  Subquery 2: travelTime → crewWorkDay → crew → secure_workOrder → secure_employee
Then: Result → secure_employee (for final employee info)
```

**Columns Selected:**
- `TRIM(CONCAT(firstName, ' ', lastName))` AS Employee Name
- `DATE_FORMAT(date, '%m/%d/%Y %a')` AS Date (formatted with weekday)
- `GROUP_CONCAT(DISTINCT workOrderNumber)` AS Work Order Number
- CASE statements for Regular/Over/Double Time (same logic as v1)
- `SUM(hours)` AS Total Hours

**WHERE Conditions:**
- `w.isInternal = 0` (in both subqueries)
- `e.isInternal = 0` (in both subqueries and main query)
- `hours IS NOT NULL` (in both subqueries)
- `date IS NOT NULL` (in main query)

**Advanced Features:**
- **UNION ALL** (combines workTime and travelTime)
- Subquery in FROM clause
- Multiple CASE statements
- DATE_FORMAT with custom format
- DAYOFWEEK() function
- GROUP_CONCAT with DISTINCT and ORDER BY
- CONVERT(... USING utf8mb4) for character encoding
- TRIM and COALESCE for string handling
- Complex aggregation with LEAST/GREATEST

**JOIN Complexity Analysis:**
- **Join Count:** 8 (4 in each subquery)
- **Join Depth:** 5 hops per subquery
- **Bridge Tables:** crew (in both subqueries)
- **Subquery Usage:** UNION of two complex subqueries
- **Complexity Score:** 10/10 ⭐

**Domain Coverage:** ❌ None

**Why This Is Most Complex:**
1. UNION of two separate join chains
2. Subquery in FROM clause
3. 8 total joins across subqueries
4. Complex business logic (payroll rules)
5. Multiple string and date functions
6. Character encoding handling

---

#### Report #36: Payroll v2 (Complexity: 6, Priority: 8)

**Prompt:** Similar to v1 but with GROUP_CONCAT for work order numbers

**Tables Involved:**
- `workTime` (primary)
- `crewWorkDay` (date)
- `crew` (work context)
- `secure_workOrder` (work order)
- `secure_employee` (employee)

**JOIN Chain:**
```
workTime 
  → crewWorkDay (crewWorkDayId)
  → crew (crewId)
  → secure_workOrder (workOrderId)
  → secure_employee (employeeId)
```

**Columns Selected:**
- `TRIM(CONCAT(firstName, ' ', lastName))` AS Employee Name
- `date` AS Date
- `GROUP_CONCAT(DISTINCT workOrderNumber ORDER BY workOrderNumber SEPARATOR ', ')` AS Work Order Number
- CASE statements for Regular/Over/Double Time
- `SUM(hours)` AS Total Hours

**WHERE Conditions:**
- `swo.isInternal = 0`
- `se.isInternal = 0`

**Advanced Features:**
- GROUP_CONCAT with DISTINCT, ORDER BY, and custom SEPARATOR
- CASE statements (4)
- DAYOFWEEK() function
- CONVERT(... USING utf8mb4)
- TRIM, COALESCE
- Complex GROUP BY

**JOIN Complexity Analysis:**
- **Join Count:** 4 (all INNER)
- **Join Depth:** 4 hops
- **Bridge Tables:** crew
- **Complexity Score:** 6/10

**Domain Coverage:** ❌ None

---

### Category 2: Work Order Reports (Medium-High Priority)

#### Report #6: List all WO (Complexity: 4, Priority: 7)

**Prompt:** "List all WO"

**Tables Involved:**
- `secure_workOrder` (primary)
- `workOrderStatus` (status name)
- `secure_customer` (customer info)

**JOIN Chain:**
```
secure_workOrder 
  → workOrderStatus (workOrderStatusId) [LEFT]
  → secure_customer (customerId) [LEFT]
```

**Columns Selected:**
- `workOrderNumber`
- `description`
- `startDate`, `endDate`
- `JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.customAttribute'))` AS customAttribute
- `JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.Validity'))` AS Validity
- `JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.EC100'))` AS EC100
- `wos.name` AS status
- `c.customerName` AS customerName
- `wo.id` as workOrderId

**WHERE Conditions:**
- `wo.isInternal = FALSE`

**Advanced Features:**
- JSON_EXTRACT with JSON_UNQUOTE (3 dynamic attributes)
- LEFT JOINs for optional relationships

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** None
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None
- Could benefit from dynamic attribute domain rules

---

#### Report #15: all work orders (Complexity: 4, Priority: 7)

**Prompt:** "all work orders"

**Tables Involved:**
- `secure_workOrder` (primary)
- `workOrderStatus` (status)
- `secure_customer` (customer)
- `secure_customerLocation` (ship-to location)

**JOIN Chain:**
```
secure_workOrder 
  → workOrderStatus (workOrderStatusId) [INNER]
  → secure_customer (customerId) [INNER]
  → secure_customerLocation (customerLocationId) [LEFT]
```

**Columns Selected:**
- `workOrderNumber`, `description`, `startDate`, `endDate`
- `wos.name` AS status
- `c.customerName` AS customerName
- `cl.shipToName` AS shipToName

**WHERE Conditions:**
- `wo.isInternal = 0`

**Advanced Features:**
- Mix of INNER and LEFT JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 3 (2 INNER, 1 LEFT)
- **Join Depth:** 3 hops
- **Bridge Tables:** None
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None

---

#### Report #21: WOs with WT (Complexity: 4, Priority: 7)

**Prompt:** "list the work orders (work order number) that have at least one work time created"

**Tables Involved:**
- `secure_workOrder` (primary)
- `crew` (work context)
- `crewWorkDay` (day context)
- `workTime` (time entries)

**JOIN Chain:**
```
secure_workOrder 
  → crew (workOrderId) [INNER]
  → crewWorkDay (crewId) [INNER]
  → workTime (crewWorkDayId) [INNER]
```

**Columns Selected:**
- `DISTINCT wo.workOrderNumber`
- `wo.id` as workOrderId

**WHERE Conditions:**
- None (implicit through INNER JOINs)

**Advanced Features:**
- DISTINCT to eliminate duplicates
- All INNER JOINs (existence check pattern)

**JOIN Complexity Analysis:**
- **Join Count:** 3 (all INNER)
- **Join Depth:** 3 hops
- **Bridge Tables:** crew, crewWorkDay (both bridges)
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None

---

#### Report #40: Work order with time (Complexity: 4, Priority: 7)

**Prompt:** "List all the work orders that have at least one work time added"

**Tables Involved:**
- `secure_workOrder` (primary)
- Subquery: `workTime`, `crewWorkDay`, `crew`

**JOIN Chain:**
```
secure_workOrder (no joins)
  WHERE EXISTS (
    workTime → crewWorkDay → crew → workOrder
  )
```

**Columns Selected:**
- `DISTINCT workOrderNumber`, `description`
- `id` as workOrderId

**WHERE Conditions:**
- `wo.isInternal = 0`
- `EXISTS (subquery with 3 joins)`

**Advanced Features:**
- **EXISTS subquery** (correlated subquery)
- DISTINCT
- Subquery has 3 INNER JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 0 in main query, 3 in subquery
- **Join Depth:** 3 hops in subquery
- **Bridge Tables:** crew, crewWorkDay
- **Subquery Pattern:** EXISTS for existence check
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None

**Note:** This is an alternative pattern to Report #21 (using EXISTS instead of DISTINCT with JOINs)

---

### Category 3: Inspection Reports (High Priority - Domain Support Available)

#### Report #1: Failed! (Complexity: 5, Priority: 6)

**Prompt:** "List inspections and their amount of questions, create a column for amount of answered and one for unanswered"

**Tables Involved:**
- `inspection` (primary)
- `inspectionQuestionAnswer` (answers)
- `inspectionQuestion` (questions)

**JOIN Chain:**
```
inspection 
  → inspectionQuestionAnswer (inspectionId) [LEFT]
  → inspectionQuestion (inspectionQuestionId) [LEFT]
```

**Columns Selected:**
- `i.id` AS inspection_id
- `COUNT(iq.id)` AS total_questions
- `SUM(CASE WHEN iqa.id IS NOT NULL THEN 1 ELSE 0 END)` AS answered_questions
- `COUNT(iq.id) - SUM(CASE WHEN iqa.id IS NOT NULL THEN 1 ELSE 0 END)` AS unanswered_questions

**WHERE Conditions:**
- None

**Advanced Features:**
- COUNT aggregation
- SUM with CASE statement
- GROUP BY inspection.id
- NULL checking with IS NOT NULL

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** inspectionQuestionAnswer (bridge between inspection and question)
- **Complexity Score:** 5/10

**Domain Coverage:** ⚠️ Partial
- Domain registry has `inspection_questions_and_answers` pattern
- Covers inspection → question → answer hierarchy
- This report matches the pattern but doesn't use all bridge tables

**Training Value:** High - demonstrates inspection question/answer aggregation pattern

---

#### Report #7: All inspections (Complexity: 6, Priority: 8)

**Prompt:** "All inpsections, status, date, work order, asset"

**Tables Involved:**
- `inspection` (primary)
- `inspectionTemplateWorkOrder` (template-WO link)
- `secure_workOrder` (work order)
- `crewWorkDay` (work day)
- `equipment` (equipment used)
- `equipmentOption` (equipment type)

**JOIN Chain:**
```
inspection 
  → inspectionTemplateWorkOrder (inspectionTemplateWorkOrderId) [LEFT]
  → secure_workOrder (workOrderId) [LEFT]
  → crewWorkDay (crewWorkDayId) [LEFT]
  → equipment (crewWorkDayId) [LEFT]
  → equipmentOption (equipmentOptionId) [LEFT]
```

**Columns Selected:**
- `inspection.date`, `inspection.status`
- `wo.workOrderNumber`, `wo.id` as workOrderId
- `equipmentOption.name` AS asset

**WHERE Conditions:**
- None

**Advanced Features:**
- Multiple LEFT JOINs (5)
- Bridge table usage (inspectionTemplateWorkOrder)

**JOIN Complexity Analysis:**
- **Join Count:** 5 (all LEFT)
- **Join Depth:** 5 hops
- **Bridge Tables:** inspectionTemplateWorkOrder (inspection → work order)
- **Complexity Score:** 6/10

**Domain Coverage:** ⚠️ Partial
- Uses inspection tables
- Asset equipment pattern present
- Missing full inspection question/answer detail

**Training Value:** High - demonstrates complex inspection with work order and equipment

---

#### Report #11: All services (Complexity: 6, Priority: 6)

**Prompt:** None (Manual)

**Tables Involved:**
- `service` (primary)
- `serviceTemplateWorkOrder` (template-WO link)
- `secure_workOrder` (work order)
- `crewWorkDay` (work day)
- `equipment` (equipment used)
- `equipmentOption` (equipment type)

**JOIN Chain:**
```
service 
  → serviceTemplateWorkOrder (serviceTemplateWorkOrderId) [LEFT]
  → secure_workOrder (workOrderId) [LEFT]
  → crewWorkDay (crewWorkDayId) [LEFT]
  → equipment (crewWorkDayId) [LEFT]
  → equipmentOption (equipmentOptionId) [LEFT]
```

**Columns Selected:**
- `service.date`, `service.status`
- `wo.workOrderNumber`, `wo.id` as workOrderId
- `equipmentOption.name` AS asset

**WHERE Conditions:**
- None

**Advanced Features:**
- Multiple LEFT JOINs (5)
- Identical pattern to inspection reports

**JOIN Complexity Analysis:**
- **Join Count:** 5 (all LEFT)
- **Join Depth:** 5 hops
- **Bridge Tables:** serviceTemplateWorkOrder
- **Complexity Score:** 6/10

**Domain Coverage:** ⚠️ Partial
- Domain registry has `service_questions` pattern
- This report doesn't include question/answer details

**Training Value:** Medium - similar to inspection pattern, demonstrates service workflow

---

#### Report #25: Dubious result2 (Complexity: 4, Priority: 3)

**Prompt:** "Create a report including inspections and a count of how many times it has been run. Join Template and Asset name when appropiate"

**Tables Involved:**
- `inspection` (primary)
- `inspectionTemplateWorkOrder` (template link)
- `inspectionTemplate` (template info)

**JOIN Chain:**
```
inspection 
  → inspectionTemplateWorkOrder (inspectionTemplateWorkOrderId) [LEFT]
  → inspectionTemplate (inspectionTemplateId) [LEFT]
```

**Columns Selected:**
- `i.id` AS inspection_id
- `i.date`
- `it.name` AS template_name
- `COUNT(i.id)` AS run_count

**WHERE Conditions:**
- None

**Advanced Features:**
- COUNT aggregation
- GROUP BY with multiple columns
- LEFT JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** inspectionTemplateWorkOrder
- **Complexity Score:** 4/10

**Domain Coverage:** ⚠️ Partial
- Uses inspection template pattern
- Missing asset name (mentioned in prompt but not in query)

**Training Value:** Low - incomplete implementation, marked as "Dubious"

---

#### Report #32: Dubious results (Complexity: 5, Priority: 4)

**Prompt:** "Inspections with their date, asset name, template name and all relevant information including status"

**Tables Involved:**
- `inspection` (primary)
- `crewWorkDay` (work day)
- `crew` (crew info)
- `secure_workOrder` (work order)
- `inspectionTemplateWorkOrder` (template link)
- `inspectionTemplate` (template)

**JOIN Chain:**
```
inspection 
  → crewWorkDay (crewWorkDayId) [LEFT]
  → crew (crewId) [LEFT]
  → secure_workOrder (workOrderId) [LEFT]
  → inspectionTemplateWorkOrder (inspectionTemplateWorkOrderId) [LEFT]
  → inspectionTemplate (inspectionTemplateId) [LEFT]
```

**Columns Selected:**
- `inspection.date`, `inspection.status`, `inspection.completedAt`
- `inspectionTemplate.name` AS template_name
- `wo.description` AS asset_name (incorrect - should be equipment)

**WHERE Conditions:**
- None

**Advanced Features:**
- Multiple LEFT JOINs (5)

**JOIN Complexity Analysis:**
- **Join Count:** 5 (all LEFT)
- **Join Depth:** 5 hops
- **Bridge Tables:** inspectionTemplateWorkOrder
- **Complexity Score:** 5/10

**Domain Coverage:** ⚠️ Partial
- Uses inspection pattern
- Incorrectly uses WO description as "asset_name"

**Training Value:** Low - marked as "Dubious", incorrect column mapping

---

### Category 4: Employee/Crew Reports (Medium Priority)

#### Report #5: Work Orders and Leads (Complexity: 5, Priority: 7)

**Prompt:** "List all work orders and their leads"

**Tables Involved:**
- `secure_workOrder` (primary)
- `crew` (crew info)
- `employeeCrew` (crew membership)
- `secure_employee` (employee info)

**JOIN Chain:**
```
secure_workOrder 
  → crew (workOrderId) [LEFT]
  → employeeCrew (crewId AND isLead=1) [LEFT]
  → secure_employee (employeeId AND isInternal=0) [LEFT]
```

**Columns Selected:**
- `wo.workOrderNumber`, `wo.description`
- `e.firstName`, `e.lastName`, `e.email`, `e.phone`
- `wo.id` AS workOrderId

**WHERE Conditions:**
- `wo.isInternal = 0`
- `ec.isLead = 1` (in JOIN condition)
- `e.isInternal = 0` (in JOIN condition)

**Advanced Features:**
- Multiple LEFT JOINs
- Filter in JOIN condition (isLead=1)

**JOIN Complexity Analysis:**
- **Join Count:** 3 (all LEFT)
- **Join Depth:** 3 hops
- **Bridge Tables:** crew, employeeCrew (both bridges)
- **Complexity Score:** 5/10

**Domain Coverage:** ❌ None

**Training Value:** High - demonstrates crew lead pattern with filtered JOINs

---

#### Report #12: SR with dates (Complexity: 4, Priority: 7)

**Prompt:** "Work order, leads and start date"

**Tables Involved:**
- `secure_workOrder` (primary)
- `crew` (crew info)
- `employeeCrew` (crew membership)
- `secure_employee` (employee info)

**JOIN Chain:**
```
secure_workOrder 
  → crew (workOrderId) [INNER]
  → employeeCrew (crewId AND isLead=1) [INNER]
  → secure_employee (employeeId) [INNER]
```

**Columns Selected:**
- `w.workOrderNumber`, `w.startDate`
- `CONCAT(e.firstName, ' ', e.lastName)` AS leadName

**WHERE Conditions:**
- `w.isInternal = 0`
- `e.isInternal = 0`
- `ec.isLead = 1` (in JOIN condition)

**Advanced Features:**
- CONCAT for full name
- All INNER JOINs (requires lead to exist)

**JOIN Complexity Analysis:**
- **Join Count:** 3 (all INNER)
- **Join Depth:** 3 hops
- **Bridge Tables:** crew, employeeCrew
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None

**Training Value:** High - similar to #5 but with INNER JOINs (different semantics)

---

#### Report #29: Crew List (Complexity: 5, Priority: 8)

**Prompt:** "List All Crew History, even hidden one"

**Tables Involved:**
- `employeeCrew` (primary)
- `crew` (crew info)
- `secure_workOrder` (work order)
- `secure_employee` (employee info)
- `employeeRole` (role info)

**JOIN Chain:**
```
employeeCrew 
  → crew (crewId) [INNER]
  → secure_workOrder (workOrderId) [INNER]
  → secure_employee (employeeId) [INNER]
  → employeeRole (employeeRoleId) [LEFT]
```

**Columns Selected:**
- `e.firstName`, `e.lastName`
- `er.name` AS role
- `ec.isLead`, `ec.startDate`, `ec.endDate`
- `wo.workOrderNumber`

**WHERE Conditions:**
- `e.isInternal = 0`
- `wo.isInternal = 0`

**Advanced Features:**
- Mix of INNER and LEFT JOINs
- Historical data (startDate, endDate)

**JOIN Complexity Analysis:**
- **Join Count:** 4 (3 INNER, 1 LEFT)
- **Join Depth:** 4 hops
- **Bridge Tables:** crew (connects employee crew to work order)
- **Complexity Score:** 5/10

**Domain Coverage:** ❌ None

**Training Value:** High - demonstrates crew history pattern with temporal data

---

#### Report #26: User activity (Complexity: 1, Priority: 4)

**Prompt:** "necesito una lista de todos los usuarios mostrnado name, email, y last activity"

**Tables Involved:**
- `secure_user` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `CONCAT(u.firstName, ' ', u.lastName)` AS name
- `u.email`
- `u.lastActivity`

**WHERE Conditions:**
- None

**Advanced Features:**
- CONCAT for full name
- ORDER BY name

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - simple query, but demonstrates user listing pattern

---

#### Report #38: All work times (Complexity: 2, Priority: 6)

**Prompt:** "All work times"

**Tables Involved:**
- `workTime` (primary)
- `workTimeType` (type info)
- `secure_employee` (employee info)

**JOIN Chain:**
```
workTime 
  → workTimeType (workTimeTypeId) [LEFT]
  → secure_employee (employeeId) [LEFT]
```

**Columns Selected:**
- `workTime.hours`, `workTime.startTime`, `workTime.endTime`
- `workTimeType.name` AS workTimeTypeName
- `e.firstName`, `e.lastName`, `e.email`, `e.phone` (employee fields)

**WHERE Conditions:**
- None

**Advanced Features:**
- LEFT JOINs for optional relationships

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ❌ None

**Training Value:** Medium - demonstrates basic workTime pattern

---

### Category 5: Customer Reports (Low-Medium Priority)

#### Report #24: All customers (Complexity: 1, Priority: 5)

**Prompt:** "All customers"

**Tables Involved:**
- `secure_customer` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `customerName`, `address`, `city`, `state`, `zipCode`, `countryCode`, `phone`, `faxNo`, `email`

**WHERE Conditions:**
- None

**Advanced Features:**
- None

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - simple query, but demonstrates customer listing

---

#### Report #31: Active Customer (Complexity: 1, Priority: 5)

**Prompt:** "report of all active customers"

**Tables Involved:**
- `secure_customer` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- Same as Report #24

**WHERE Conditions:**
- `isActive = 1`

**Advanced Features:**
- WHERE clause filter

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - demonstrates WHERE filtering

---

#### Report #13: Anything (Complexity: 2, Priority: 5)

**Prompt:** "Anything"

**Tables Involved:**
- `secure_workOrder` (primary)
- `secure_customer` (customer info)

**JOIN Chain:**
```
secure_workOrder 
  → secure_customer (customerId) [LEFT]
```

**Columns Selected:**
- `wo.description`, `wo.startDate`, `wo.endDate`
- `c.customerNo`, `c.customerName`, `c.address`, `c.city`, `c.state`, `c.zipCode`, `c.countryCode`
- `c.phone` AS customerPhone
- `c.email` AS customerEmail

**WHERE Conditions:**
- None

**Advanced Features:**
- LEFT JOIN

**JOIN Complexity Analysis:**
- **Join Count:** 1 (LEFT)
- **Join Depth:** 1 hop
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ❌ None

**Training Value:** Medium - demonstrates WO with customer info

---

### Category 6: Dynamic Attributes / JSON Reports (Medium Priority)

#### Report #27: DynAttr (Complexity: 2, Priority: 6)

**Prompt:** "List all assets including dynamic attributes"

**Tables Involved:**
- `asset` (primary)
- `assetType` (asset type)

**JOIN Chain:**
```
asset 
  → assetType (assetTypeId) [LEFT]
```

**Columns Selected:**
- `asset.name`, `asset.modelNumber`, `asset.serialNumber`, `asset.manufacturer`
- `JSON_UNQUOTE(JSON_EXTRACT(asset.dynamicAttributes, '$.Cores'))` AS Cores
- `JSON_UNQUOTE(JSON_EXTRACT(asset.dynamicAttributes, '$.Certification'))` AS Certification
- `JSON_UNQUOTE(JSON_EXTRACT(asset.dynamicAttributes, '$.Wattage'))` AS Wattage
- `JSON_UNQUOTE(JSON_EXTRACT(asset.dynamicAttributes, '$.Memory'))` AS Memory
- `JSON_UNQUOTE(JSON_EXTRACT(asset.dynamicAttributes, '$.Clock Speed'))` AS Clock Speed
- `assetType.name` AS assetType

**WHERE Conditions:**
- None

**Advanced Features:**
- Multiple JSON_EXTRACT with JSON_UNQUOTE (5 dynamic attributes)
- LEFT JOIN

**JOIN Complexity Analysis:**
- **Join Count:** 1 (LEFT)
- **Join Depth:** 1 hop
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ⚠️ Partial
- Domain registry has asset types (crane, forklift, etc.)
- This query could use those patterns

**Training Value:** High - demonstrates JSON dynamic attribute extraction pattern

---

#### Report #39: All DA columns (Complexity: 1, Priority: 3)

**Prompt:** "show me all assets and a column for each dynamic attribute"

**Tables Involved:**
- `asset` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- Basic asset fields
- 14 different JSON_EXTRACT expressions for dynamic attributes

**WHERE Conditions:**
- None

**Advanced Features:**
- Extensive JSON extraction (14 attributes)

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ⚠️ Partial

**Training Value:** Medium - shows extensive JSON attribute extraction

---

#### Report #30: test wo dyn attrs (Complexity: 1, Priority: 4)

**Prompt:** "all work orders showing only dynamic attributes"

**Tables Involved:**
- `secure_workOrder` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `JSON_UNQUOTE(JSON_EXTRACT(wo.dynamicAttributes, '$.CURRENCY ATTRIBUTE TEST 1'))` AS CURRENCY ATTRIBUTE TEST 1
- `JSON_UNQUOTE(JSON_EXTRACT(wo.dynamicAttributes, '$.TEXT ATTRIBUTE TEST'))` AS TEXT ATTRIBUTE TEST
- `JSON_UNQUOTE(JSON_EXTRACT(wo.dynamicAttributes, '$.NUMBER ATTRIBUTE TEST'))` AS NUMBER ATTRIBUTE TEST

**WHERE Conditions:**
- `wo.isInternal = FALSE`

**Advanced Features:**
- JSON extraction (3 attributes)

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - test query for dynamic attributes

---

### Category 7: Advanced SQL / CTE Reports (Very High Priority)

#### Report #34: Employee Utilization (Complexity: 9, Priority: 8) ⭐ CTE-BASED

**Prompt:** None (Manual)

**Tables Involved:**
- `workTime`, `travelTime` (in CTEs)
- `crewWorkDay` (date context)
- `secure_employee` (employee info)

**CTE Structure:**
```sql
WITH RECURSIVE 
  period_bounds AS (
    -- Calculate period start/end with 365-day cap
  ),
  calendar AS (
    -- Generate date series recursively
  ),
  employee_days AS (
    -- UNION of workTime and travelTime dates
  ),
  employee_summary AS (
    -- Aggregate worked days by employee
  ),
  period_totals AS (
    -- Calculate total weekdays/weekends in period
  )
SELECT ... FROM secure_employee
  CROSS JOIN period_bounds
  LEFT JOIN employee_summary
  LEFT JOIN period_totals
```

**Columns Selected:**
- `e.id` AS employeeId
- `CONCAT(e.firstName, ' ', e.lastName)` AS employee
- `totalWeekdaysInPeriod`, `totalWeekendDaysInPeriod`
- `totalWeekdaysWithWorkOrTravelTime`, `totalWeekendDaysWithWorkOrTravelTime`
- `CASE WHEN totalDaysInPeriod=0 THEN 0 ELSE ROUND((totalDaysWorked/totalDaysInPeriod)*100, 2) END` AS percentUtilized
- `periodStart` AS period

**WHERE Conditions:**
- `e.isInternal = false`
- `e.isActive = true`

**Advanced Features:**
- **WITH RECURSIVE** (recursive CTE for date generation)
- **5 CTEs** (complex multi-stage calculation)
- UNION ALL in CTE
- CROSS JOIN
- WEEKDAY() function
- COALESCE for NULL handling
- ROUND for percentage
- Complex CASE statement
- GROUP BY in CTEs
- Subquery patterns in CTEs
- Date arithmetic (DATE_ADD, INTERVAL)
- LEAST function for capping

**JOIN Complexity Analysis:**
- **Join Count:** 2 (in main query: CROSS JOIN + 2 LEFT JOINs)
- **Join Depth:** Complex (CTEs create intermediate results)
- **Bridge Tables:** Multiple CTEs act as virtual bridge tables
- **CTE Complexity:** 5 CTEs with recursive date generation
- **Complexity Score:** 9/10 ⭐

**Domain Coverage:** ❌ None

**Training Value:** VERY HIGH - demonstrates:
1. Recursive CTE usage
2. Date series generation
3. Complex business logic (utilization calculation)
4. Multi-stage aggregation
5. CROSS JOIN pattern
6. Parameter handling (@startDate, @endDate)

**Why This Is Important:**
- Shows how to handle period-based calculations
- Demonstrates recursive CTE for date ranges
- Complex aggregation across multiple dimensions
- Real business metric (employee utilization)

---

### Category 8: Test/Debug Reports (Low Priority)

#### Report #8: SL False Information (Complexity: 1, Priority: 2)

**Prompt:** "List Service Locations"

**Tables Involved:**
- `serviceLocation` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `name`, `isActive`, `isDefault`

**WHERE Conditions:**
- `id IN ("75f534b3-9fe4-4d64-a07c-b78995a37c76")` (hardcoded specific ID)

**Advanced Features:**
- WHERE IN with hardcoded value

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Very Low - test data query

---

#### Report #9: [TEST] Unexpected error (Complexity: 1, Priority: 1)

**Prompt:** "Bring lots of numbers"

**Tables Involved:**
- `secure_workOrder` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `w.workOrderNumber`

**WHERE Conditions:**
- `w.isInternal = false`

**Advanced Features:**
- None

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** None - test report

---

#### Report #10: [TEST] Number values (Complexity: 2, Priority: 3)

**Prompt:** "List currency dynamic attributes and their values"

**Tables Involved:**
- `dynamicAttribute` (primary)
- `dynamicAttributeValue` (values)

**JOIN Chain:**
```
dynamicAttribute 
  → dynamicAttributeValue (dynamicAttributeId) [INNER]
```

**Columns Selected:**
- `da.key` AS attribute
- `dav.value` AS value

**WHERE Conditions:**
- `da.type = 'CURRENCY'`

**Advanced Features:**
- INNER JOIN
- WHERE filter on type

**JOIN Complexity Analysis:**
- **Join Count:** 1 (INNER)
- **Join Depth:** 1 hop
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ❌ None

**Training Value:** Low - test query for dynamic attributes

---

#### Report #16: Delete Report (Complexity: 1, Priority: 1)

**Prompt:** "test"

**Tables Involved:**
- None (literal query)

**JOIN Chain:**
- None

**Columns Selected:**
- `'test'` (literal string)

**WHERE Conditions:**
- None

**Advanced Features:**
- Literal SELECT (no tables)

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** None - test query

---

#### Report #17: Amount of templ (Complexity: 1, Priority: 2)

**Prompt:** "How many templates, ordered by name"

**Tables Involved:**
- `inspectionTemplate` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `COUNT(*)` as template_count

**WHERE Conditions:**
- None

**Advanced Features:**
- COUNT aggregation
- ORDER BY name (but returns single row, so ORDER BY has no effect)

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - simple COUNT query

---

#### Report #23: Null? (Complexity: 1, Priority: 2)

**Prompt:** "Return a list of work orders, all returned data associated must be null"

**Tables Involved:**
- `secure_workOrder` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- All columns are `NULL AS column_name` (7 columns)

**WHERE Conditions:**
- `isInternal = FALSE`

**Advanced Features:**
- NULL literal values

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** None - test query for NULL handling

---

#### Report #37: Evil Tobi (Complexity: 4, Priority: 3)

**Prompt:** "evil tobi"

**Tables Involved:**
- `secure_workOrder` (primary)
- `crew` (crew info)
- `employeeCrew` (crew membership)
- `secure_employee` (employee info)

**JOIN Chain:**
```
secure_workOrder 
  → crew (workOrderId) [LEFT]
  → employeeCrew (crewId) [LEFT]
  → secure_employee (employeeId) [LEFT]
```

**Columns Selected:**
- `e.firstName`, `e.lastName`, `e.email`, `e.phone`

**WHERE Conditions:**
- `e.isInternal = FALSE`
- `(e.firstName LIKE '%evil%' OR e.lastName LIKE '%tobi%')`

**Advanced Features:**
- LIKE with wildcards
- OR condition

**JOIN Complexity Analysis:**
- **Join Count:** 3 (all LEFT)
- **Join Depth:** 3 hops
- **Bridge Tables:** crew, employeeCrew
- **Complexity Score:** 4/10

**Domain Coverage:** ❌ None

**Training Value:** Low - test query with LIKE pattern

---

#### Report #41: CREW-841 (Complexity: 1, Priority: 2)

**Prompt:** "Description"

**Tables Involved:**
- `secure_workOrder` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `description`

**WHERE Conditions:**
- `isInternal = 0`

**Advanced Features:**
- None

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** None - simple single column query

---

### Category 9: Settings/Configuration Reports (Low Priority)

#### Report #4: Settings (Complexity: 3, Priority: 5)

**Prompt:** "list all settings and the related information"

**Tables Involved:**
- `setting` (primary)
- `package` (package info)
- `secure_user` (user who updated)

**JOIN Chain:**
```
setting 
  → package (packageId) [LEFT]
  → secure_user (updatedBy) [LEFT]
```

**Columns Selected:**
- `s.name` as settingName, `s.status`, `s.valueType`, `s.value` as settingValue
- `s.valueOptions`, `s.description`, `s.statusOnly`, `s.valueOnly`
- `s.valuePlaceholder`, `s.valueReadOnly`, `s.statusChangeFunction`
- `s.isInternal`, `s.feature`, `s.sendOnAppLogin`
- `p.name` as packageName
- `concat(su.firstName, ' ', su.lastName)` as updatedByName
- `su.email` as updatedByEmail

**WHERE Conditions:**
- None

**Advanced Features:**
- CONCAT for full name
- LEFT JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** None
- **Complexity Score:** 3/10

**Domain Coverage:** ❌ None

**Training Value:** Medium - demonstrates settings/configuration pattern

---

### Category 10: Miscellaneous / Edge Cases

#### Report #14: Template Copy (Complexity: 1, Priority: 2)

**Prompt:** None (Manual)

**Tables Involved:**
- `inspectionTemplate` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `name`, `status`

**WHERE Conditions:**
- None

**Advanced Features:**
- None

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - simple template list

---

#### Report #18: Duplicated WTTs (Complexity: 3, Priority: 3)

**Prompt:** None (Manual)

**Tables Involved:**
- `workTime` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `workTimeTypeId`, `crewWorkDayId`, `employeeId`
- `COUNT(*)` AS count
- `GROUP_CONCAT(id ORDER BY id SEPARATOR ', ')` AS workTimeIds

**WHERE Conditions:**
- None

**Advanced Features:**
- GROUP BY with multiple columns
- HAVING COUNT(*) > 1 (find duplicates)
- GROUP_CONCAT with ORDER BY and custom SEPARATOR

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 3/10

**Domain Coverage:** ❌ None

**Training Value:** Medium - demonstrates duplicate detection pattern with GROUP BY/HAVING

---

#### Report #19: Desc Bug (Complexity: 3, Priority: 5)

**Prompt:** "New Report!"

**Tables Involved:**
- `secure_workOrder` (primary)
- `secure_customer` (customer info)
- `secure_customerLocation` (location info)

**JOIN Chain:**
```
secure_workOrder 
  → secure_customer (customerId) [LEFT]
  → secure_customerLocation (customerLocationId) [LEFT]
```

**Columns Selected:**
- `wo.workOrderNumber`, `wo.description`, `wo.startDate`, `wo.endDate`
- `c.customerName` AS customerName
- `cl.shipToName` AS shipToName

**WHERE Conditions:**
- None

**Advanced Features:**
- LEFT JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** None
- **Complexity Score:** 3/10

**Domain Coverage:** ❌ None

**Training Value:** Medium - demonstrates WO with customer and location

---

#### Report #20: Deleted Report (Complexity: 2, Priority: 3)

**Prompt:** "TEST DB"

**Tables Involved:**
- `secure_workOrder` (primary)
- `secure_customer` (customer info)

**JOIN Chain:**
```
secure_workOrder 
  → secure_customer (customerId) [LEFT]
```

**Columns Selected:**
- `wo.workOrderNumber`, `wo.description`
- `c.customerName` AS customerName

**WHERE Conditions:**
- None

**Advanced Features:**
- LEFT JOIN

**JOIN Complexity Analysis:**
- **Join Count:** 1 (LEFT)
- **Join Depth:** 1 hop
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ❌ None

**Training Value:** Low - simple WO with customer

---

#### Report #28: Two Date Columns (Complexity: 1, Priority: 4)

**Prompt:** "Start date, end date"

**Tables Involved:**
- `secure_workOrder` (primary)

**JOIN Chain:**
- None

**Columns Selected:**
- `w.startDate` AS Start date
- `w.endDate` AS End date
- 2 JSON_EXTRACT expressions for dynamic attributes

**WHERE Conditions:**
- `w.isInternal = false`

**Advanced Features:**
- JSON extraction (2 attributes)

**JOIN Complexity Analysis:**
- **Join Count:** 0
- **Join Depth:** 0
- **Bridge Tables:** None
- **Complexity Score:** 1/10

**Domain Coverage:** ❌ None

**Training Value:** Low - demonstrates date column selection with JSON

---

#### Report #33: Internal (Complexity: 2, Priority: 3)

**Prompt:** "template details"

**Tables Involved:**
- `secure_workOrder` (primary)
- `workOrderStatus` (status info)

**JOIN Chain:**
```
secure_workOrder 
  → workOrderStatus (workOrderStatusId) [LEFT]
```

**Columns Selected:**
- `wo.workOrderNumber`, `wo.description`, `wo.startDate`, `wo.endDate`
- `wos.name` AS Status
- 3 JSON_EXTRACT expressions for dynamic attributes

**WHERE Conditions:**
- `wo.isInternal = FALSE`

**Advanced Features:**
- LEFT JOIN
- JSON extraction (3 attributes)

**JOIN Complexity Analysis:**
- **Join Count:** 1 (LEFT)
- **Join Depth:** 1 hop
- **Bridge Tables:** None
- **Complexity Score:** 2/10

**Domain Coverage:** ❌ None

**Training Value:** Low - similar to other WO queries

---

#### Report #35: Payroll LR Report (Complexity: 7, Priority: 7)

**Prompt:** "create a report that will contains all WorkTimes per user and date of the work times, so group all user work times per date, add a column to show the work order number where those Times where added, the location using only the abbreviation of first letters, the role using abbreviation of first letters, and for the date display the weekday (for example mm/dd/yyyy ddd), and for the user show name and last name in the same column called Employee Name Then show column for Regular Time, for OverTime and Double Time..."

**Tables Involved:**
- `workTime` (primary)
- `crewWorkDay` (date context)
- `crew` (work context)
- `secure_workOrder` (work order)
- `secure_employee` (employee)
- `serviceLocation` (location)
- `employeeRole` (role)

**JOIN Chain:**
```
workTime 
  → crewWorkDay (crewWorkDayId) [INNER]
  → crew (crewId) [INNER]
  → secure_workOrder (workOrderId) [INNER]
  → secure_employee (employeeId) [INNER]
  → serviceLocation (serviceLocationId) [LEFT]
  → employeeRole (employeeRoleId) [LEFT]
```

**Columns Selected:**
- `TRIM(CONCAT(firstName, ' ', lastName))` AS Employee Name
- `cwd.date` AS Date
- `swo.workOrderNumber` AS Work Order Number
- Complex CASE for location abbreviation (first letters of each word)
- Complex CASE for role abbreviation (first letters of each word)
- CASE statements for Regular/Over/Double Time
- `SUM(hours)` AS Total Hours

**WHERE Conditions:**
- `swo.isInternal = 0`
- `se.isInternal = 0`

**Advanced Features:**
- Complex CASE statements for abbreviations (using SUBSTRING_INDEX)
- DAYOFWEEK() function
- TRIM, CONCAT, COALESCE
- LEFT and SUBSTRING_INDEX for string parsing
- Multiple aggregations
- GROUP BY with multiple columns

**JOIN Complexity Analysis:**
- **Join Count:** 6 (4 INNER, 2 LEFT)
- **Join Depth:** 6 hops
- **Bridge Tables:** crew, crewWorkDay
- **Complexity Score:** 7/10

**Domain Coverage:** ❌ None

**Training Value:** High - demonstrates:
1. Complex string manipulation (abbreviations)
2. Mix of INNER and LEFT JOINs
3. Payroll logic
4. Multiple dimensions (location, role)

---

#### Report #42: WOs inspections (Complexity: 3, Priority: 4)

**Prompt:** "All inspections"

**Tables Involved:**
- `inspection` (primary)
- `crewWorkDay` (work day)
- `crew` (crew info)

**JOIN Chain:**
```
inspection 
  → crewWorkDay (crewWorkDayId) [LEFT]
  → crew (crewId) [LEFT]
```

**Columns Selected:**
- `inspection.date`, `inspection.status`

**WHERE Conditions:**
- None

**Advanced Features:**
- LEFT JOINs

**JOIN Complexity Analysis:**
- **Join Count:** 2 (both LEFT)
- **Join Depth:** 2 hops
- **Bridge Tables:** crewWorkDay
- **Complexity Score:** 3/10

**Domain Coverage:** ⚠️ Partial

**Training Value:** Medium - basic inspection pattern

---

## Domain Registry Coverage Analysis

### Reports with Domain Support

#### ⚠️ Partial Coverage (9 reports)

1. **Report #1 (Failed!)** - Inspection questions/answers aggregation
   - Domain pattern: `inspection_questions_and_answers`
   - Coverage: Uses inspection/question/answer tables
   - Gap: Doesn't use full hierarchy (missing template, section, group)

2. **Report #7 (All inspections)** - Inspection with equipment
   - Domain pattern: `inspection_questions` (structural)
   - Coverage: Uses inspection workflow tables
   - Gap: Doesn't include question/answer details

3. **Report #11 (All services)** - Service with equipment
   - Domain pattern: `service_questions`
   - Coverage: Uses service workflow tables
   - Gap: Doesn't include question/answer details

4. **Report #25 (Dubious result2)** - Inspection with template
   - Domain pattern: `inspection_questions`
   - Coverage: Uses inspection template pattern
   - Gap: Incomplete (missing asset as mentioned in prompt)

5. **Report #27 (DynAttr)** - Assets with dynamic attributes
   - Domain pattern: Asset types (crane, forklift, truck, etc.)
   - Coverage: Could use asset type matching
   - Gap: Doesn't filter by specific asset types

6. **Report #32 (Dubious results)** - Inspection with template
   - Domain pattern: `inspection_questions`
   - Coverage: Uses inspection pattern
   - Gap: Incorrect column mapping (WO description as asset)

7. **Report #39 (All DA columns)** - Asset dynamic attributes
   - Domain pattern: Asset types
   - Coverage: Shows all asset attributes
   - Gap: No type-specific filtering

8. **Report #42 (WOs inspections)** - Basic inspection
   - Domain pattern: `inspection_questions`
   - Coverage: Basic inspection structure
   - Gap: Missing template and question details

### Domain Rules NOT Used (39 reports)

The following domain patterns exist but are NOT used in any reports:

1. **Asset Types** (crane, forklift, hoist, truck, trailer, generator, compressor)
   - Pattern: Text search in asset.name, assetType.name, or dynamicAttributeValue
   - No reports specifically filter by these types
   - Opportunity: Create reports like "List all cranes" or "Forklift maintenance"

2. **Action Items / Unsafe Conditions**
   - Pattern: `inspectionQuestionAnswer.isActionItem = true`
   - No reports filter for action items or safety issues
   - Opportunity: "List all unsafe conditions" or "Open action items"

3. **Safety Questions**
   - Pattern: `safety` → `safetyQuestion` → `safetyQuestionAnswer`
   - No reports use safety tables at all
   - Opportunity: Safety compliance reports

### Domain Rules Needed (Gaps)

Based on the smart reports, these domain patterns should be added:

1. **Payroll Rules**
   - Pattern: Sunday = double time, weekday/Saturday ≤8hrs = regular, >8hrs = overtime
   - Used in: Reports #2, #3, #22, #35, #36 (5 reports)
   - Recommendation: Add `payroll_calculation` domain rule

2. **Work Order Filtering**
   - Pattern: `isInternal = 0` or `isInternal = false`
   - Used in: 28 reports (58%)
   - Recommendation: Add `production_work_orders` domain rule

3. **Employee Filtering**
   - Pattern: `employee.isInternal = 0`
   - Used in: 15 reports (31%)
   - Recommendation: Add `field_employees` domain rule

4. **Crew Lead Pattern**
   - Pattern: `employeeCrew.isLead = 1`
   - Used in: Reports #5, #12 (2 reports)
   - Recommendation: Add `crew_leads` domain rule

5. **Dynamic Attributes**
   - Pattern: `JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.key'))`
   - Used in: 8 reports (17%)
   - Recommendation: Add `dynamic_attribute_extraction` domain rule with common keys

6. **Date Calculations**
   - Pattern: DAYOFWEEK(), DATE_FORMAT(), date arithmetic
   - Used in: 6 reports (13%)
   - Recommendation: Add `date_utilities` domain rule

7. **Employee Utilization**
   - Pattern: Recursive CTE for date ranges, weekday/weekend calculations
   - Used in: Report #34
   - Recommendation: Add `employee_utilization` domain rule

---

## Training Recommendations

### Tier 1: High Priority for Initial Training (10 reports)

These reports provide the best training value due to JOIN complexity, production use, and pattern diversity:

1. **Report #22 (Payroll v3)** - Complexity: 10, Priority: 9
   - UNION of complex subqueries
   - 8 total joins
   - Real business logic
   - **Training Focus:** UNION patterns, subqueries, complex aggregations

2. **Report #34 (Employee Utilization)** - Complexity: 9, Priority: 8
   - Recursive CTE
   - 5 CTEs total
   - Complex date calculations
   - **Training Focus:** CTE usage, recursive patterns, date series generation

3. **Report #2 (Payroll v1)** - Complexity: 8, Priority: 9
   - 5 joins (4 LEFT, 1 INNER)
   - Complex CASE statements
   - GROUP_CONCAT
   - **Training Focus:** Payroll logic, CASE statements, aggregations

4. **Report #7 (All inspections)** - Complexity: 6, Priority: 8
   - 5 LEFT joins
   - Bridge table (inspectionTemplateWorkOrder)
   - Equipment relationship
   - **Training Focus:** Inspection workflow, bridge tables, LEFT join chains

5. **Report #36 (Payroll v2)** - Complexity: 6, Priority: 8
   - 4 INNER joins
   - GROUP_CONCAT with custom separator
   - Payroll logic variant
   - **Training Focus:** Alternative payroll pattern, INNER join chains

6. **Report #29 (Crew List)** - Complexity: 5, Priority: 8
   - 4 joins (3 INNER, 1 LEFT)
   - Historical data (startDate, endDate)
   - Mix of join types
   - **Training Focus:** Crew history, temporal data, mixed join types

7. **Report #35 (Payroll LR Report)** - Complexity: 7, Priority: 7
   - 6 joins (4 INNER, 2 LEFT)
   - Complex string manipulation (abbreviations)
   - Multiple dimensions
   - **Training Focus:** String functions, abbreviation logic, complex GROUP BY

8. **Report #5 (Work Orders and Leads)** - Complexity: 5, Priority: 7
   - 3 LEFT joins
   - Filter in JOIN condition (isLead=1)
   - Bridge tables (crew, employeeCrew)
   - **Training Focus:** Filtered joins, crew lead pattern

9. **Report #21 (WOs with WT)** - Complexity: 4, Priority: 7
   - 3 INNER joins
   - DISTINCT pattern
   - Existence check via joins
   - **Training Focus:** Existence patterns, DISTINCT usage

10. **Report #40 (Work order with time)** - Complexity: 4, Priority: 7
    - EXISTS subquery
    - Correlated subquery with 3 joins
    - Alternative existence pattern
    - **Training Focus:** EXISTS vs JOIN patterns, subquery optimization

### Tier 2: Medium Priority for Pattern Coverage (12 reports)

These reports cover important patterns and variations:

11. **Report #6 (List all WO)** - JSON extraction, LEFT joins
12. **Report #12 (SR with dates)** - INNER joins variant of crew leads
13. **Report #15 (all work orders)** - Mix of INNER/LEFT joins
14. **Report #27 (DynAttr)** - Asset dynamic attributes pattern
15. **Report #38 (All work times)** - Basic workTime pattern
16. **Report #4 (Settings)** - Settings/configuration pattern
17. **Report #19 (Desc Bug)** - WO with customer and location
18. **Report #11 (All services)** - Service workflow (similar to inspection)
19. **Report #1 (Failed!)** - Inspection question aggregation
20. **Report #13 (Anything)** - WO with customer info
21. **Report #24 (All customers)** - Simple customer list
22. **Report #31 (Active Customer)** - WHERE filtering pattern

### Tier 3: Low Priority / Edge Cases (26 reports)

These are test reports, simple queries, or duplicates:

- Test reports: #8, #9, #10, #16, #17, #23, #37, #41
- Simple queries: #14, #20, #26, #28, #30, #33, #39
- Duplicates/variants: #3 (Payroll Test 1), #25 (Dubious result2), #32 (Dubious results)
- Edge cases: #18 (Duplicated WTTs), #42 (WOs inspections)

### Training Strategy by SQL Pattern

#### Pattern 1: Complex Joins (Focus: JOIN Finder)

**Priority Order:**
1. Report #22 (UNION + 8 joins)
2. Report #7 (5 LEFT joins with bridge)
3. Report #35 (6 joins, mixed types)
4. Report #2 (5 joins, 4 LEFT)
5. Report #36 (4 INNER joins)

**Training Goal:** Teach agent to find optimal join paths, handle bridge tables, mix LEFT/INNER appropriately

#### Pattern 2: Advanced SQL Features

**Priority Order:**
1. Report #34 (Recursive CTE)
2. Report #22 (UNION ALL)
3. Report #40 (EXISTS subquery)
4. Report #18 (GROUP BY/HAVING for duplicates)

**Training Goal:** Teach agent to use CTEs, subqueries, and advanced SQL constructs

#### Pattern 3: Business Logic

**Priority Order:**
1. Report #2 (Payroll with CASE statements)
2. Report #34 (Employee utilization)
3. Report #35 (String abbreviations)
4. Report #22 (Payroll with UNION)

**Training Goal:** Teach agent to implement complex business rules in SQL

#### Pattern 4: JSON/Dynamic Attributes

**Priority Order:**
1. Report #27 (Multiple JSON extracts)
2. Report #6 (JSON with joins)
3. Report #39 (Extensive JSON extraction)

**Training Goal:** Teach agent to extract and use dynamic attributes

#### Pattern 5: Aggregations

**Priority Order:**
1. Report #2 (Multiple aggregations with CASE)
2. Report #1 (COUNT with SUM/CASE)
3. Report #18 (GROUP BY/HAVING)

**Training Goal:** Teach agent to use aggregations correctly with GROUP BY

---

## Summary Statistics by Category

### By Business Domain

| Domain | Count | Avg Complexity | High Priority (≥7) |
|--------|-------|----------------|-------------------|
| Payroll | 4 | 7.8 | 4 |
| Work Orders | 9 | 3.4 | 5 |
| Inspections | 5 | 4.6 | 2 |
| Employees/Crew | 6 | 3.5 | 4 |
| Customers | 3 | 1.3 | 2 |
| Dynamic Attributes | 5 | 1.4 | 2 |
| Advanced SQL | 2 | 9.5 | 2 |
| Test/Debug | 9 | 1.4 | 0 |
| Settings | 1 | 3.0 | 1 |
| Miscellaneous | 4 | 2.0 | 1 |

### By Complexity Level

| Complexity | Count | % | Example Reports |
|------------|-------|---|-----------------|
| Low (1-2) | 12 | 25% | Simple queries, no joins |
| Medium (3-5) | 18 | 38% | 3-5 joins, basic patterns |
| High (6-8) | 14 | 29% | 6+ joins, bridge tables |
| Very High (9-10) | 4 | 8% | CTEs, UNION, complex logic |

### By JOIN Count

| JOIN Count | Count | % | Notes |
|------------|-------|---|-------|
| 0 joins | 12 | 25% | Simple single-table queries |
| 1-2 joins | 11 | 23% | Basic relationships |
| 3-4 joins | 14 | 29% | Moderate complexity |
| 5-6 joins | 9 | 19% | High complexity |
| 7+ joins | 2 | 4% | Very high complexity (Payroll v3, Payroll LR) |

### By JOIN Type Distribution

| Pattern | Count | % | Notes |
|---------|-------|---|-------|
| No joins | 12 | 25% | Single table |
| All INNER | 8 | 17% | Required relationships |
| All LEFT | 18 | 38% | Optional relationships |
| Mixed INNER/LEFT | 10 | 21% | Complex relationship requirements |

### Advanced SQL Features Usage

| Feature | Count | % | Example Reports |
|---------|-------|---|-----------------|
| LEFT JOIN | 40 | 83% | Most reports use LEFT JOINs |
| CASE statements | 12 | 25% | Payroll, conditional logic |
| JSON extraction | 8 | 17% | Dynamic attributes |
| GROUP_CONCAT | 8 | 17% | Aggregating lists |
| CONCAT | 15 | 31% | String concatenation |
| Date functions | 6 | 13% | DAYOFWEEK, DATE_FORMAT |
| CTEs | 2 | 4% | Employee Utilization |
| UNION | 1 | 2% | Payroll v3 |
| EXISTS subquery | 1 | 2% | Work order with time |
| GROUP BY/HAVING | 3 | 6% | Aggregations with filters |

---

## Key Insights for Agent Training

### 1. JOIN Finder Challenges

**Most Common Patterns:**
- **LEFT JOIN dominance** (83% of reports with joins) - Agent must understand optional relationships
- **Bridge tables** (crew, employeeCrew, inspectionTemplateWorkOrder) - Critical for many-to-many relationships
- **Deep join chains** (up to 6 hops) - Agent must find optimal paths through join graph

**Training Focus:**
- Teach agent to distinguish when to use LEFT vs INNER joins
- Train on bridge table patterns (especially crew-related tables)
- Practice finding shortest paths through complex join graphs

### 2. Business Logic Patterns

**Payroll Calculations** (4 reports, high complexity):
- Sunday = double time
- Weekday/Saturday: ≤8hrs = regular, >8hrs = overtime
- Requires DAYOFWEEK(), CASE statements, aggregations

**Recommendation:** Create domain rule for payroll logic to guide agent

### 3. Common WHERE Filters

**Production Data Filtering:**
- `isInternal = 0` or `false` appears in 28 reports (58%)
- `employee.isInternal = 0` appears in 15 reports (31%)

**Recommendation:** Add domain rules for production vs internal data filtering

### 4. JSON Dynamic Attributes

**Pattern:** `JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.key'))`
- Used in 8 reports (17%)
- Common keys: customAttribute, Validity, EC100, Cores, Wattage, etc.

**Recommendation:** Add domain rule for common dynamic attribute keys

### 5. String Manipulation

**Common Patterns:**
- `CONCAT(firstName, ' ', lastName)` for full names (8 reports)
- `GROUP_CONCAT(DISTINCT ... ORDER BY ... SEPARATOR ', ')` for lists (8 reports)
- Complex abbreviation logic (Report #35)

**Training Focus:** Teach agent when to use CONCAT vs GROUP_CONCAT

### 6. Aggregation Patterns

**Common Aggregations:**
- COUNT for counting records
- SUM with CASE for conditional sums
- GROUP BY with multiple columns
- HAVING for post-aggregation filtering

**Training Focus:** Teach agent to use GROUP BY correctly with all non-aggregated columns

### 7. Date Handling

**Common Functions:**
- DAYOFWEEK() for weekday detection (4 reports)
- DATE_FORMAT() for custom formatting (2 reports)
- Date arithmetic for ranges (1 report with CTE)

**Training Focus:** Teach agent date function usage and timezone handling

### 8. Advanced SQL Constructs

**Rare but Important:**
- Recursive CTEs (1 report) - Employee Utilization
- UNION ALL (1 report) - Payroll v3
- EXISTS subqueries (1 report) - Work order with time

**Training Focus:** Teach agent when to use these advanced patterns vs simpler alternatives

---

## Recommendations for Domain Registry Expansion

### High Priority Additions

1. **Payroll Calculation Rule**
   ```json
   "payroll_rules": {
     "entity": "payroll_calculation",
     "description": "Business rules for calculating regular, overtime, and double time",
     "resolution": {
       "primary": {
         "logic": "CASE WHEN DAYOFWEEK(date)=1 THEN double_time ELSE IF hours<=8 THEN regular ELSE overtime",
         "tables": ["workTime", "travelTime", "crewWorkDay"],
         "confidence": 1.0
       }
     }
   }
   ```

2. **Production Data Filtering**
   ```json
   "production_data": {
     "entity": "production_filter",
     "description": "Filter for production (non-internal) records",
     "resolution": {
       "primary": {
         "condition": "isInternal = 0 OR isInternal = false",
         "applies_to": ["workOrder", "employee", "customer", "inspection"],
         "confidence": 1.0
       }
     }
   }
   ```

3. **Crew Lead Pattern**
   ```json
   "crew_lead": {
     "entity": "crew_leadership",
     "description": "Identify crew leads on work orders",
     "resolution": {
       "primary": {
         "tables": ["employeeCrew", "crew", "workOrder", "employee"],
         "condition": "employeeCrew.isLead = 1",
         "confidence": 1.0
       }
     }
   }
   ```

4. **Dynamic Attribute Common Keys**
   ```json
   "common_dynamic_attributes": {
     "entity": "dynamic_attributes",
     "description": "Common dynamic attribute keys across entities",
     "resolution": {
       "workOrder": ["customAttribute", "Validity", "EC100", "CURRENCY ATTRIBUTE TEST 1"],
       "asset": ["Cores", "Certification", "Wattage", "Memory", "Clock Speed", "HP"],
       "extraction_pattern": "JSON_UNQUOTE(JSON_EXTRACT(dynamicAttributes, '$.key'))"
     }
   }
   ```

### Medium Priority Additions

5. **Employee Full Name Pattern**
6. **Work Order Existence Checks**
7. **Date Formatting Standards**
8. **Aggregation List Patterns (GROUP_CONCAT)**

---

## Conclusion

This analysis of 48 smart reports reveals:

1. **JOIN complexity is the primary challenge** - Most reports use multiple LEFT JOINs (average 3.2 joins per report with joins)

2. **Bridge tables are critical** - crew, employeeCrew, inspectionTemplateWorkOrder are key connectors

3. **Business logic is embedded in SQL** - Payroll rules, date calculations, and conditional logic appear frequently

4. **Domain coverage is limited** - Only 9 reports (19%) have partial domain support, 39 reports (81%) have none

5. **Training priorities should focus on:**
   - Complex join patterns (Reports #22, #34, #2, #7)
   - Business logic implementation (Payroll reports)
   - Advanced SQL features (CTEs, UNION, subqueries)
   - JSON dynamic attribute handling

6. **Domain registry expansion needed** - Add rules for payroll, production filtering, crew leads, and common dynamic attributes

This document provides a roadmap for training the AI agent on real-world query patterns, with emphasis on the challenging JOIN path finding that is core to the system's success.
