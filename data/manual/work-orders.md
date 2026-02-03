# Work Orders Module - Detailed Functional Guide

**Module Package:** `@crewos/workorders`  
**Base Path:** `/packages/workorders/`  
**Version:** 1.0  
**Last Updated:** 2026-01-27

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Access & Permissions](#access--permissions)
3. [Navigation](#navigation)
4. [Main Pages](#main-pages)
5. [Modals & Drawers](#modals--drawers)
6. [Settings](#settings)
7. [Common Workflows](#common-workflows)
8. [Integration Points](#integration-points)
9. [Tips & Best Practices](#tips--best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

The **Work Orders** module is the primary operational hub for planning, executing, tracking, and reporting work delivered to customers. It provides:

- A searchable and exportable **work order list**
- A streamlined **create work order** flow (drawer-based)
- A comprehensive **work order details** experience with **12+ tabs** (work performed, assignments, time, expenses, equipment, inspections/safety/services templates, reports, PDF reports, close-out)
- Supporting **settings** for statuses, categories, job types, recurring rules, and dynamic attributes

### Key Features

- **Work Orders list** with search, pagination, CSV export, and quick refresh
- **Create Work Order** in a drawer with validation, auto-numbering support, internal work orders, service location selection, and dynamic attributes
- **Details header** with status badge, read-only indicator, recurring indicator, and a status timeline
- **Work performed** including crew-day breakdown, work day summary, notes, attachments/photos, and safe delete workflow
- **Assignments/Crews tab** plus related time/expenses/equipment tabs (package-dependent)
- **Inspections / Safety / Services**: assign templates and manage work-order linked items (package-dependent)
- **Reports** including labor reports and Smart Reports (package-dependent)
- **PDF Reports** with download and email-sending capability
- Optional **Work Orders Dashboard** (Super Admin + feature flag)
- Optional **Work Order Close Out** with signature viewer (feature flag)

### Required Settings / Feature Gates

Some Work Orders features are gated by tenant settings and installed packages:

- `DASHBOARDS_ENABLED` enables the Work Orders dashboard route.
- `RECURRING_WORK_ORDERS` enables recurring rule workflows.
- `SERVICE_LOCATIONS_ENABLED` enables the Service Location field in forms and some settings columns.
- `WORKORDER_AUTO_NUMBERING` enables auto-generated work order numbers.
- `WO_CLOSE_OUT_ENABLED` enables the “Closing Details” tab.
- Packages that enable tabs/components:
  - `worktimes` / `traveltimes` → Time tab and workday time sections
  - `expenses` → Expenses tab and workday expenses sections
  - `equipments` → Equipment tab
  - `inspections` / `safety` / `services` → template assignment tabs
  - `reports` → Reports tab and PDF Reports tab (PDF Reports is also shown for Customer Users)
  - `perdiems` → Per Diem tab
  - `invoices` → “Create Invoice” button in Job Details
  - `quotes` → Quote tab when the work order has quotes

---

## Access & Permissions

### Role Requirements (Routes)

**Work Orders list**
- **URL:** `/workorders` and `/workorders/all`
- **Typical roles:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`
- **Customer users:** can access list depending on tenant setup; creation is hidden for customer users in UI.

**Work Order details**
- **URL:** `/workorders/details/:workOrderId` and `/workorders/details/:workOrderId/:tab`
- **Roles (explicit):** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`, `IS_CUSTOMER_USER`

**Work Orders Dashboard**
- **URL:** `/workorders/dashboard`
- **Roles (explicit):** `IS_SUPER_ADMIN_USER`
- **Feature gate:** `DASHBOARDS_ENABLED`

**Settings (Work Orders)**
- **Work Order Settings:** `/settings/workorders/work-order` → `IS_SUPER_ADMIN_USER`
- **Work Order Status:** `/settings/workorders/work-order-status` → `IS_SUPER_ADMIN_USER`
- **Status Categories:** `/settings/workorders/work-order-status-categories` → `IS_SUPER_ADMIN_USER`
- **Job Types:** `/settings/workorders/job-types` → `IS_SUPER_ADMIN_USER`
- **Recurring Rules:** `/settings/workorders/recurring-rules` → `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER` + `RECURRING_WORK_ORDERS`

### Read-Only Work Orders

Work orders can become read-only based on their status:

- In settings, each Work Order Status can enable **WO Read Only**.
- In details, users that are **not** Super Admin see a **Read Only** badge when the current status is configured as read-only.
- Some actions are still allowed depending on component rules (for example: status updates may still be permitted depending on UI state).

---

## Navigation

### Sidebar Location

**Work Orders**
- **Icon:** `briefcase`
- **Label:** “Work Orders”
- **Base URL:** `/workorders`
- **Sub-menu items (dynamic):**
  - “All” → `/workorders/all`
  - One entry per configured Work Order Status (dynamic) → `/workorders/:workOrderStatusId`

**Work Orders Dashboard (optional)**
- **Label:** “Work Orders Dashboard”
- **URL:** `/workorders/dashboard`
- **Visibility:** Super Admin only + `DASHBOARDS_ENABLED`

### Settings → Work Orders

Under **Settings**, Work Orders contributes a “Work Orders” category:

1. **Work Orders Settings** → `/settings/workorders/work-order`
2. **Work Order Status** → `/settings/workorders/work-order-status`
3. **Status Categories** → `/settings/workorders/work-order-status-categories`
4. **Job Types** → `/settings/workorders/job-types`
5. **Recurring Rules** → `/settings/workorders/recurring-rules` (requires `RECURRING_WORK_ORDERS`)

---

## Main Pages

### Page: Work Orders List

**URL:** `/workorders/all` (default)  
**Purpose:** Browse, search, export, and open work orders; create new work orders (non-customer users).

#### Page Header

**Title:** “{Status Name} Work Orders” (or “All Work Orders”)  
**Record Count:** `({count})` in muted text

**Header Actions (right side)**

**Search input**
- **Placeholder:** “Search work orders”
- **Type:** Text, debounced input
- **Max length:** 50
- **Behavior:** typing resets pagination to page 1 and refetches results after debounce.

**Refresh button**
- **Icon:** `refresh-cw`
- **Style:** Small circular button
- **Test ID:** `refresh-button`
- **Action:** triggers a refetch with current params.

**Export**
- **Type:** Table export control injected into `#table-export`
- **Export name:** `WorkOrders.csv`
- **Formats:** depends on `AdvanceTable` export implementation (commonly CSV).

**Create button**
- **Label:** “Create”
- **Color:** Primary
- **Visibility:** hidden for Customer Users and some restricted “web user” roles.
- **Action:** opens the Work Order creation drawer.

#### Table

Work Orders are rendered in an exportable `AdvanceTable` with row click navigation (unless disabled for restricted roles).

**Columns (base)**

| Column | Accessor | Sortable | Notes |
|---|---:|:---:|---|
| Work Order # | `workOrderNumber` | Yes | Displays `-` if missing |
| Customer | `customer.customerName` | Yes | Displays `-` if missing |
| Location | `customerLocation.shipToName` | No | Displays `-` if missing |
| Lead | `crews` | No | Aggregates lead names from crew employees |
| Job Type | `jobType.name` | Yes | Shows “None” when missing |
| Status | `workOrderStatus.name` | No | Adds “Internal” badge if `isInternal` |
| Dates | `startDate` | Yes | Displays formatted start–end range |
| Service Location (optional) | `serviceLocation.name` | Yes/No | Only if `SERVICE_LOCATIONS_ENABLED` |
| Dynamic Attributes (optional) | `<dynamicAttribute.key>` | No | Rendered per configured dynamic attribute |

**Row click**
- Default navigation target:
  - Non-customer: opens details at the “Work Performed” tab.
  - Customer: opens details at the “PDF Reports” tab.

#### Screenshots

![Work Orders List](../screenshots/work-orders/work-orders-list.png)
![Work Orders Status Filter (Sidebar)](../screenshots/work-orders/work-orders-status-filter.png)
![Work Orders Search](../screenshots/work-orders/work-orders-search.png)
![Work Orders Refresh](../screenshots/work-orders/work-orders-refresh.png)
![Work Orders Export](../screenshots/work-orders/work-orders-export.png)
![Work Orders Pagination](../screenshots/work-orders/work-orders-pagination.png)
![Work Orders Columns](../screenshots/work-orders/work-orders-columns.png)
![Work Orders Empty State](../screenshots/work-orders/work-orders-empty-state.png)
![Work Orders Child Rows](../screenshots/work-orders/work-orders-child-row.png)

---

### Page: Work Order Details

**URL:** `/workorders/details/:workOrderId/:tab`  
**Purpose:** Execute and manage a single work order: work performed, job details/description, assignments, time, expenses, templates, reports, PDFs, and close-out.

#### Header (Top Area)

**Back button**
- **Icon:** `chevron-left`
- **Test ID:** `back-button`
- **Behavior:** attempts browser back; falls back to `/workorders` if navigation fails.

**Title**
- Primary: Work order number (or “No work order number provided”)
- Optional parent breadcrumb:
  - If the WO has a parent, the parent WO# appears as a link and the current WO is shown after `>`.

**Badges**
- **Status badge:** pill, primary color, shows current status name.
- **Recurring badge (optional):** pill, primary; visible when `RECURRING_WORK_ORDERS` is enabled and the work order has a recurring rule; clicking opens an information modal.
- **Read Only badge (conditional):** warning badge shown when current status is configured as read-only and user is not Super Admin.

**Customer metadata ribbon**
Shows customer and contact information (e.g. customer name, date range, job type, customer number, email, address, city, country, telephone). Some fields (dates) may be clickable for internal users to quickly select a date.

**Status timeline**
A horizontal timeline shows each status as a pill, plus a timestamp for when that status was reached.

#### Tabs (12+)

Tab availability depends on installed packages and tenant settings. Typical tabs include:

- Work Performed
- Job Details
- Job Description
- Quote info (only if the work order has quotes and Quotes package is enabled)
- Related Work Orders
- Crews / Assignments
- Time (Work Times + Travel Times)
- Per Diem
- Expenses
- Equipment (label depends on configuration)
- Inspections (with child tabs)
- Services (with child tabs)
- Safety (with child tabs)
- Reports (with child tabs, including Smart Reports)
- PDF Reports
- Closing Details (close-out/signature logs)

#### Screenshots

![Work Order Details Header](../screenshots/work-orders/wo-details-header.png)
![Work Order Status Timeline](../screenshots/work-orders/wo-status-timeline.png)
![Work Order Recurring Badge](../screenshots/work-orders/wo-recurring-badge.png)
![Work Order Read Only Badge](../screenshots/work-orders/wo-read-only-badge.png)

---

### Page: Work Orders Dashboard (optional)

**URL:** `/workorders/dashboard`  
**Access:** `IS_SUPER_ADMIN_USER` + `DASHBOARDS_ENABLED`  
**Purpose:** Analytics and insights over work orders, by status/location/job type, and activity trends.

#### Screenshots

![Work Orders Dashboard](../screenshots/work-orders/wo-dashboard.png)
![Work Orders Dashboard Charts](../screenshots/work-orders/wo-dashboard-charts.png)

---

## Modals & Drawers

### Drawer: Create Work Order

**Triggered by:** Work Orders list → “Create” button  
**Title:** “Work Order”  
**Primary action (footer):** “Save”

#### Fields

**Work Order #**
- **Type:** Text input
- **Required:** Yes
- **Auto-numbering:** when `WORKORDER_AUTO_NUMBERING` is enabled, the field is read-only and prefilled from `GET /api/work-order/next-number`.
- **Duplicate handling:** if the number conflicts, the UI shows an inline error and may suggest/auto-fetch next available number.

**Dates**
- **Type:** start + end date selector
- **Required:** Yes
- **Default:** today → today

**Status**
- **Type:** select
- **Required:** Yes
- **Source:** `authContext.userData.workOrderStatus`

**Job Type**
- **Type:** select
- **Required:** No
- **Source:** `GET /api/job-type/all`
- **Default:** auto-selects the job type where `isDefault=true` for new work orders (until user interacts).

**Service Location** (optional)
- **Type:** select
- **Required:** Yes when enabled
- **Visible when:** `SERVICE_LOCATIONS_ENABLED`

**Is Internal** (Super Admin only)
- **Type:** switch
- **Default:** true for Super Admins (when not explicitly set)
- **Effect:** when enabled, Customer and Customer Location fields are hidden and not required.

**Customer / Customer Location** (hidden when Is Internal is enabled)
- **Customer**
  - **Type:** async select
  - **Required:** Yes
  - **Placeholder:** “Search customers”
  - **Source:** Customers package (`useGetCustomers`)
- **Customer Location**
  - **Type:** select
  - **Required:** Yes
  - **Placeholder:** “Search customer locations”
  - **Options:** derived from selected customer’s locations

**Dynamic Attributes (Additional info)**
- **Type:** dynamic field set (text, number, currency, etc.)
- **Source:** `useGetAllDynamicAttributes({ entityName: "workOrder" })`
- **Behavior:** default values are auto-applied for new work orders when configured.

#### Validation (toast-based)

On Save, the drawer validates and shows warning toasts:
- “Work order status is required”
- “Start date is required”
- “End date is required”
- “Customer is required” (when not internal)
- “Customer location is required” (when not internal)

#### API

- Create: `POST /api/work-order`
- Auto-numbering: `GET /api/work-order/next-number`

#### Screenshots

![Create Work Order - Empty](../screenshots/work-orders/create-wo-empty.png)
![Create Work Order - Validation](../screenshots/work-orders/create-wo-validation.png)
![Create Work Order - Status Select](../screenshots/work-orders/create-wo-status-select.png)
![Create Work Order - Customer Select](../screenshots/work-orders/create-wo-customer-select.png)
![Create Work Order - Location Select](../screenshots/work-orders/create-wo-location-select.png)
![Create Work Order - Internal Toggle](../screenshots/work-orders/create-wo-internal-toggle.png)
![Create Work Order - Service Location](../screenshots/work-orders/create-wo-service-location.png)
![Create Work Order - Dynamic Attributes](../screenshots/work-orders/create-wo-dynamic-attributes.png)
![Create Work Order - Filled](../screenshots/work-orders/create-wo-filled.png)
![Create Work Order - Success Toast](../screenshots/work-orders/create-wo-success-toast.png)

---

### Modal: Delete Work Order (confirmation)

**Triggered by:** Work Order Details → Work Performed → “Delete”  
**Title:** “Delete Work Order”

**Body**
- If the work order has child work orders: the message warns that related work orders will also be deleted.
- Otherwise: a standard delete confirmation.

**Buttons**
- Cancel
- Delete (danger)

**API**
- `DELETE /api/work-order` (payload includes `id`)

#### Screenshot

![Delete Work Order Confirmation](../screenshots/work-orders/wo-delete-confirmation.png)

---

### Modal: Job Description (Rich Text Editor)

**Triggered by:** Work Order Details → Job Description → “Edit”  
**Editor:** `ReactQuill` rich text

**Buttons**
- Discard
- Save

**API**
- `PUT /api/work-order` (updates `description`)

#### Screenshot

![Job Description Modal](../screenshots/work-orders/wo-job-description-modal.png)

---

### Modal: Work Day Summary (information)

**Triggered by:** Work Performed → “Work Day Summary” (requires `AUTO_DAY_SUMMARY_ENABLED`)  
**API:** `GET /api/work-order/:id/work-day-summary` (with selected date)

#### Screenshot

![Work Day Summary](../screenshots/work-orders/wo-workday-summary-modal.png)

---

### Modal: Recurring Work Order Rule (create / edit)

**Triggered by:**
- Work Performed → “Make Recurring” (create; requires `RECURRING_WORK_ORDERS`)
- Settings → Recurring Rules → “Edit” (edit)

**Title:** “Create Recurring Work Order Rule” / “Edit Recurring Work Order Rule”

**Fields**
- Start Date (required; must be tomorrow or later unless unchanged in edit mode)
- End Date (optional; must be after start date)
- Frequency (Daily / Monthly / Quarterly / Yearly)
- Status (Active / Inactive; disabled if end date is in the past)
- Description (optional)

**API**
- Create: `POST /api/recurring-work-order`
- Update: `PUT /api/recurring-work-order`
- Delete: `DELETE /api/recurring-work-order`

#### Screenshots

![Recurring Rule Modal](../screenshots/work-orders/wo-recurring-modal.png)
![Recurring Info Modal](../screenshots/work-orders/wo-recurring-info.png)

---

### Drawer: Create Related Work Order

**Triggered by:**
- Work Performed → “Create related work order”
- Related Work Orders tab (Add/Create related work order)

**Behavior**
- Creates and links a related work order (child) under the current work order.

#### Screenshots

![Related Work Orders Tab](../screenshots/work-orders/wo-related-tab.png)
![Create Related Work Order Drawer](../screenshots/work-orders/wo-link-wo.png)

---

### PDF Reports Actions (Download + Email)

**Location:** Work Order Details → “PDF Reports”

**Download PDF**
- **Button:** “Download PDF”
- **Behavior:** requests a signed URL, downloads a PDF, caches PDF data in Work Order Details state.
- **API:** `GET /api/work-order/:id/report?browserTimeZone=...` → returns `{ ok, url }`

**Send by email** (not available to Customer Users)
- **Button:** “Send by email”
- **Behavior:** opens an email modal; on send, calls the email endpoint with document attachments.
- **API:** `POST /api/email/send-with-documents`

#### Screenshots

![PDF Reports Tab](../screenshots/work-orders/wo-pdf-reports-tab.png)
![Email PDF Modal](../screenshots/work-orders/wo-email-pdf-modal.png)

---

### Closing Details (Close Out) - Signature Viewer

**Tab:** “Closing Details” (requires `WO_CLOSE_OUT_ENABLED`)  
**Purpose:** View close-out actions and signatures captured for a work order.

**Signature icon**
- Displays a file icon; clicking opens a signature modal with the image.

**API**
- `GET /api/work-order-close-out` (with `workOrderId`)

#### Screenshots

![Closing Details Tab](../screenshots/work-orders/wo-closing-details-tab.png)
![Signature Modal](../screenshots/work-orders/wo-signature-modal.png)

---

## Settings

### Settings Page: Work Orders Settings

**URL:** `/settings/workorders/work-order`  
**Access:** Super Admin only  
**Purpose:** Manage Work Orders package settings and dynamic attributes for the `workOrder` entity.

**Header actions**
- Provides Dynamic Attributes management for entity `workOrder`.

#### Screenshots

![Work Order Settings](../screenshots/work-orders/wo-settings.png)
![Work Order Dynamic Attributes](../screenshots/work-orders/wo-dynamic-attributes.png)

---

### Settings Page: Work Order Status

**URL:** `/settings/workorders/work-order-status`  
**Access:** Super Admin only  
**Purpose:** Define the list of statuses used by work orders.

**Table columns**
- Name
- Order
- Work Order Category
- Listed in APP (Yes/No)
- Customer Enabled (Yes/No)
- Actions (Edit / Delete)

**Modal: Add/Edit Work Order Status**
- Name (required; max 50)
- Order (required; 1–999)
- Category (required)
- WO Read Only (checkbox)
- Listed in APP (checkbox)
- Customer Enabled (checkbox)

#### Screenshots

![Work Order Status List](../screenshots/work-orders/wo-status-list.png)
![Work Order Status Modal](../screenshots/work-orders/wo-status-modal.png)
![Work Order Status Delete Confirmation](../screenshots/work-orders/wo-status-delete-confirm.png)

---

### Settings Page: Status Categories

**URL:** `/settings/workorders/work-order-status-categories`  
**Access:** Super Admin only  
**Purpose:** Manage the status categories used to group work order statuses.

**Table columns**
- Name
- Order
- #Work Order Status
- Default Selected
- Actions (Edit / Delete)

**Modal: Add/Edit Work Order Status Category**
- Name (required; max 50)
- Order (required; 1–999)
- Default Selected (checkbox)

#### Screenshots

![Status Categories List](../screenshots/work-orders/wo-status-categories.png)
![Status Category Modal](../screenshots/work-orders/wo-status-category-modal.png)

---

### Settings Page: Job Types

**URL:** `/settings/workorders/job-types`  
**Access:** Super Admin only  
**Purpose:** Manage job types used in work orders and recurring rules.

**Table columns**
- Name
- Default (Yes/No)
- Work Orders (count; clickable → modal listing related WOs)
- Actions (Edit / Delete)

**Modal: Create/Edit Job Type**
- Name (required; max 50)
- Is Default (checkbox)

#### Screenshots

![Job Types List](../screenshots/work-orders/wo-job-types.png)
![Job Type Modal](../screenshots/work-orders/wo-job-type-modal.png)
![Job Type Work Orders Modal](../screenshots/work-orders/wo-job-types-workorders-modal.png)

---

### Settings Page: Recurring Rules

**URL:** `/settings/workorders/recurring-rules`  
**Access:** Super Admin and Admin (requires `RECURRING_WORK_ORDERS`)  
**Purpose:** Manage recurring work order rules, inspect rule-linked work orders, and edit rule schedule.

**Table columns**
- Customer
- Location
- Job Type
- Service Location (optional; if `SERVICE_LOCATIONS_ENABLED`)
- Frequency
- Start Date
- End Date
- Status (Active / Inactive)
- Work Orders (count; clickable → modal listing generated WOs)
- Actions (Edit / Delete)

#### Screenshots

![Recurring Rules List](../screenshots/work-orders/wo-recurring-rules.png)
![Recurring Rule Modal](../screenshots/work-orders/wo-recurring-modal.png)
![Recurring Rule Delete Confirmation](../screenshots/work-orders/wo-recurring-delete-confirm.png)

---

## Common Workflows

### Workflow: Create a Work Order

1. Navigate to **Work Orders** → **All** (`/workorders/all`).
2. Click **Create**.
3. Fill required fields:
   - Work Order #
   - Dates
   - Status
   - If not internal: Customer + Customer Location
4. (Optional) Set Job Type, Service Location, and dynamic attributes.
5. Click **Save**.
6. On success, a toast appears and the work order opens in a new tab.

**Screenshots**

![Create - Empty](../screenshots/work-orders/create-wo-empty.png)
![Create - Validation](../screenshots/work-orders/create-wo-validation.png)
![Create - Filled](../screenshots/work-orders/create-wo-filled.png)

---

### Workflow: Assign Crew / Assignments

1. Open a work order details page.
2. Go to **Crews / Assignments** tab.
3. Click the add button (varies by configuration) and select crew/assignees.
4. Save/confirm to attach crew(s) to the work order.

**Screenshots**

![Crews Tab](../screenshots/work-orders/wo-crews-tab.png)
![Add Crew Modal](../screenshots/work-orders/wo-add-crew-modal.png)

---

### Workflow: Log Time (Work + Travel)

1. Open work order details.
2. Go to **Time** tab.
3. Add work time entries and travel time entries as needed.

**Screenshots**

![Time Tab](../screenshots/work-orders/wo-times-tab.png)
![Add Work Time](../screenshots/work-orders/wo-add-work-time.png)
![Add Travel Time](../screenshots/work-orders/wo-add-travel-time.png)

---

### Workflow: Log Expenses

1. Open work order details.
2. Go to **Expenses** tab.
3. Click **Add** and enter required expense details.

**Screenshots**

![Expenses Tab](../screenshots/work-orders/wo-expenses-tab.png)
![Add Expense](../screenshots/work-orders/wo-add-expense.png)

---

### Workflow: Add Equipment

1. Open work order details.
2. Go to **Equipment** tab.
3. Click **Add** and select equipment for the work order.

**Screenshots**

![Equipment Tab](../screenshots/work-orders/wo-equipment-tab.png)
![Add Equipment](../screenshots/work-orders/wo-add-equipment.png)

---

### Workflow: Assign Templates (Inspections / Safety / Services)

1. Open work order details.
2. Open **Inspections**, **Safety**, or **Services** tab.
3. Switch to **Assigned Templates** (if applicable).
4. Assign templates and confirm.

**Screenshots**

![Inspections Tab](../screenshots/work-orders/wo-inspections-tab.png)
![Assign Inspection](../screenshots/work-orders/wo-assign-inspection.png)
![Safety Tab](../screenshots/work-orders/wo-safety-tab.png)
![Assign Safety](../screenshots/work-orders/wo-assign-safety.png)
![Services Tab](../screenshots/work-orders/wo-services-tab.png)

---

### Workflow: Work Performed (Notes + Attachments/Photos)

1. Open work order details.
2. Go to **Work Performed**.
3. Expand the crew work day section (“View more”).
4. Use:
   - **Notes** to record daily notes.
   - **Photos / Attachments** to upload or review workday photos.

**Screenshots**

![Work Performed Tab](../screenshots/work-orders/wo-work-performed-tab.png)
![Notes Section](../screenshots/work-orders/wo-notes-tab.png)
![Attachments/Photos Section](../screenshots/work-orders/wo-attachments-tab.png)

---

### Workflow: Change Work Order Status

1. Open work order details.
2. In the **Job Details** tab, change **Status**.
3. Depending on edit/read-only state, status may persist immediately or after saving.

**Screenshots**

![Job Details Status Change](../screenshots/work-orders/wo-job-details-status-change.png)

---

### Workflow: Link Related Work Orders

1. Open work order details.
2. Use **Work Performed → Create related work order** or the **Related Work Orders** tab.
3. Complete the drawer flow.

**Screenshots**

![Related Tab](../screenshots/work-orders/wo-related-tab.png)
![Link Work Order Drawer](../screenshots/work-orders/wo-link-wo.png)

---

### Workflow: Setup a Recurring Work Order

1. Open work order details.
2. Go to **Work Performed**.
3. Click **Make Recurring**.
4. Configure start date, frequency, status, and optional end date.
5. Save; verify the work order shows a **Recurring** badge in the header.

**Screenshots**

![Make Recurring Modal](../screenshots/work-orders/wo-recurring-modal.png)
![Recurring Badge](../screenshots/work-orders/wo-recurring-badge.png)

---

## Integration Points

Work Orders integrates across many modules:

- **Customers**: Customer and location selection, customer metadata on the details page.
- **Crews / Assignments**: Work performed records, crews tab, related work order drawer.
- **Work Times / Travel Times**: time logging and workday breakdowns.
- **Expenses**: workday expenses and expenses tab.
- **Notes**: workday notes section in Work Performed.
- **Attachments**: workday photos/attachments section in Work Performed.
- **Inspections / Safety / Services**: template assignment and linked lists under their tabs.
- **Reports**: labor reports, smart reports, PDF reports.
- **Invoices**: Create Invoice action from Job Details (if enabled).
- **Quotes**: Quote info tab when a work order has quotes.

### API Endpoints Used (Core)

Commonly used endpoints from this module:

- `GET /api/work-order` (list, details)
- `POST /api/work-order` (create)
- `PUT /api/work-order` (update)
- `PATCH /api/work-order/:id/status` (update status)
- `DELETE /api/work-order` (delete)
- `GET /api/work-order/next-number` (auto numbering)
- `GET /api/work-order/:id/work-performed` (work performed summary/cards)
- `GET /api/work-order/:id/work-day-summary` (daily summary)
- `POST /api/work-order/related` (create related WO)
- `POST /api/work-order/related/link` / `DELETE /api/work-order/related/unlink` (link/unlink)
- `GET /api/work-order-status` / `GET /api/work-order-status/all` (statuses)
- `GET /api/work-order-category` / `GET /api/work-order-category/all` (categories)
- `GET /api/job-type` / `GET /api/job-type/all` (job types)
- `GET/POST/PUT/DELETE /api/recurring-work-order` (recurring rules)
- `GET /api/work-order/:id/report` (PDF report signed URL)
- `POST /api/email/send-with-documents` (email PDF)

---

## Tips & Best Practices

### Do This

- Keep statuses ordered logically and use **WO Read Only** to lock down completed work orders.
- Use dynamic attributes for tenant-specific fields instead of hardcoding new form inputs.
- Prefer “Internal” work orders for non-customer maintenance work and internal-only tracking.

### Avoid This

- Avoid deleting work orders with children unless you truly need to remove the whole chain.
- Avoid setting recurring rules with an end date in the past (status changes may be disabled).

---

## Troubleshooting

### Common Issues

**Issue: “Work order status is required”**
- **Cause:** status not selected in create/edit forms.
- **Fix:** select a value in the Status dropdown and save again.

**Issue: Work Order number conflict**
- **Symptoms:** inline error “This Work Order number is already in use…”
- **Fix:** click Save again to auto-assign the next available number (when auto-numbering is enabled), or pick a different number.

**Issue: Work Order is Read Only**
- **Symptoms:** “Read Only” badge appears; Edit buttons disappear.
- **Cause:** current status is configured with “WO Read Only”.
- **Fix:** Super Admin can change status configuration, or move the WO to a non-read-only status (if permitted).

**Issue: Missing tabs (Time/Expenses/Equipment/Inspections/etc.)**
- **Cause:** required packages or settings are disabled for the tenant.
- **Fix:** enable the package and required settings under tenant/module configuration.

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-27  
