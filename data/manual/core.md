# Core Module - Detailed Functional Guide

**Module Package:** `@crewos/core`  
**Base Path:** `/packages/core/`  
**Version:** 1.0  
**Last Updated:** 2026-01-27

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Access & Permissions](#access--permissions)
3. [Navigation](#navigation)
4. [Main Pages](#main-pages)
5. [Modals & Confirmations](#modals--confirmations)
6. [Settings](#settings)
7. [Common Workflows](#common-workflows)
8. [Integration Points](#integration-points)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose
The **Core** module provides foundational system capabilities for CrewOS web, including:
- Authentication UI (sign-in + 2FA experience)
- Tenant/module management (enable/disable modules, update module cost)
- Core settings administration (settings tables, branding logo uploads)
- Service Locations management (if enabled)
- Billing reporting (Users/Modules/Summary)
- Data inspection (Super Admin-only “Data” page for model data exploration)

### Key Features
- Module management via **Settings → Modules**
- System settings management via **Settings → Core**
- Optional **Service Locations** administration
- Billing reports with search, month selection, CSV export, and detail modals
- Super Admin-only **Data** page with model selector and JSON viewer

---

## Access & Permissions

### Role Requirements

**Full access (Core Admin screens):**
- Roles: `IS_SUPER_ADMIN_USER`
- Pages:
  - `/settings/core/packages` (Modules)
  - `/settings/core` (Core Settings)
  - `/settings/core/service-locations` (Service Locations; requires setting)
  - `/data` (Data)
  - `/sa-billing/*` (Billing for Super Admin)

**Limited access (Billing only, optional):**
- Roles: `IS_ADMIN_USER` (and **not** `IS_SUPER_ADMIN_USER`)
- Pages:
  - `/a-billing/users`
  - `/a-billing/modules`
  - `/a-billing/summary`
- Gate: `BILLING_SECTION_REGULAR_ADMINS` must be enabled

### Feature Flags / Settings Gates
- **Service Locations menu**: `SERVICE_LOCATIONS_ENABLED`
- **Billing menu for regular admins**: `BILLING_SECTION_REGULAR_ADMINS`

---

## Navigation

### Sidebar (Core Routes)

**Data**
- **Label**: “Data”
- **Icon**: `database`
- **URL**: `/data`
- **Roles**: Super Admin only

**Billing (Super Admin)**
- **Label**: “Billing”
- **Icon**: `dollar-sign`
- **Base URL**: `/sa-billing`
- **Sub-pages**:
  - Users Report: `/sa-billing/users`
  - Modules Report: `/sa-billing/modules`
  - Summary Report: `/sa-billing/summary`

**Billing (Admin / Regular)**
- **Label**: “Billing”
- **Icon**: `dollar-sign`
- **Base URL**: `/a-billing`
- **Setting gate**: `BILLING_SECTION_REGULAR_ADMINS`
- **Sub-pages**:
  - Users Report: `/a-billing/users`
  - Modules Report: `/a-billing/modules`
  - Summary Report: `/a-billing/summary`

### Settings Menu (Core Settings Routes)
- **Modules**: `/settings/core/packages` (Super Admin)
- **Core**: `/settings/core` (Super Admin)
- **Service Locations**: `/settings/core/service-locations` (Super Admin + `SERVICE_LOCATIONS_ENABLED`)

---

## Main Pages

### Page: Login (Sign In)

**URL:** `/auth/sign-in`  
**Access:** Public (no session required)  
**Purpose:** Authenticate a user into CrewOS web; supports 2FA and 2FA setup flows.

#### UI
![Login Page](../screenshots/core/core-login-page.png)

#### Fields

**Email**
- **Label:** “Email”
- **Type:** Email input (`type="email"`)
- **Required:** Yes (`required`)
- **Max length:** 50
- **Placeholder:** “Enter your email”
- **Behavior:**
  - Trims whitespace on change
  - Lowercased before submit

**Password**
- **Label:** “Password”
- **Type:** Password input (`type="password"`)
- **Required:** Yes (`required`)
- **Max length:** 50
- **Placeholder:** “Enter your password”
- **Show/Hide toggle:** Not present in this login form (password is always masked)

#### Buttons / Actions

**LOGIN (Primary)**
- **Label:** “LOGIN”
- **Style:** `color="primary"`, `size="lg"`, full-width
- **Action:** Submits credentials and authenticates the user
- **API call:** `POST /api/auth/w/sign-in`
- **Loading state:** Replaces button with a small loader/spinner while request is in-flight
- **Success behavior:**
  - If authenticated and no `twoFABlock`: stores user session context and redirects
  - If `twoFABlock`: switches UI to a 2FA step (see below)
- **Error behavior:** Displays a toast with error details

#### Validation
Login uses native required-field validation (browser-managed). Screenshot after attempting submit with empty fields:

![Login Validation](../screenshots/core/core-login-validation.png)

#### Login Logo
- **Purpose:** The logo is loaded dynamically to support tenant branding.
- **API call:** `GET /api/auth/login-logo`
- **Fallback:** If fetch fails or returns nothing, a default brand logo is shown

#### NFC Login
- **Availability (Web):** Not available in the CrewOS web login UI.
- **UI elements:** There is no “NFC”, “Tap”, “Badge”, or “Scan” option on `/auth/sign-in`.
- **Implementation note:** The Core web package implements **Email + Password** authentication, with optional **2FA**. No NFC login flow/endpoints are referenced in the web code for this module.

#### 2FA Flow (if triggered)
If the authentication response includes `twoFABlock`, the login flow branches:
- **2FA verification**: the UI renders a 2FA form for entering a code
- **Forced 2FA setup**: if `twoFAForced` is true, the UI renders a 2FA setup modal using the provided `qrcode` and `secret`

Related API endpoints:
- `POST /api/auth/2fa/setup`
- `POST /api/auth/2fa/verify`
- `POST /api/auth/2fa/disable`

#### Redirect Behavior After Login
- If the URL includes a `return-url` query parameter, the app redirects to it
- Otherwise, default redirect target is `/workorders`

Additional screenshot after successful login:

![Post-login Redirect](../screenshots/core/core-after-login-redirect.png)

---

### Page: Settings → Modules (Packages)

**URL:** `/settings/core/packages`  
**Access:** Super Admin  
**Purpose:** View all modules/packages, enable/disable modules, and update module monthly cost.

![Modules List](../screenshots/core/core-modules-list.png)

#### Header
**Title:** “Modules” with record count

**Refresh Button**
- **Icon:** refresh (`refresh-cw`)
- **Color:** white background (`color="white"`) with primary icon
- **Test ID:** `refresh-button`
- **Action:** Reloads the list (re-fetches packages)

#### Table
Rendered via `AdvanceTable` with pagination.

**Columns**
- **Module**: module/package display name
- **Status**: toggle (not shown for core package rows)
- **Monthly Cost**: formatted currency (not shown for core package rows)
- **Parent**: parent package/module name (or “-”)
- **Actions**: “See More” (not shown for core package rows)

**Pagination**
- **Default page size:** 15
- **Controls:** page number and page size selector (via `AdvanceTablePagination`)

#### Status Toggle (Enable/Disable Module)
- **Control:** checkbox toggle (`CustomCheckbox`)
- **Shown:** only for non-core modules (`row.isCore === false`)
- **Action:** opens a confirmation modal before updating
- **API call on confirm:** `PUT /api/package` with updated `isActive`
- **Success behavior:** shows toast “Setting saved” and refreshes auth context

Confirmation screenshot:

![Toggle Confirmation](../screenshots/core/core-package-toggle-confirmation.png)

Post-update screenshot:

![Toggle Success](../screenshots/core/core-package-toggle-success.png)

#### “See More” (Package Detail)
- **Button:** “See More” (text-primary, `color="none"`)
- **Action:** opens Package Detail modal (see below)

---

### Page: Settings → Core (Core Settings)

**URL:** `/settings/core`  
**Access:** Super Admin  
**Purpose:** Manage configuration settings for the `core` package and upload branding assets.

![Core Settings](../screenshots/core/core-settings.png)

This page uses the shared **Settings** screen, which renders settings as tables with:
- A **Setting** column (with tooltip info icon when a description exists)
- A **Status** toggle column (ON/OFF)
- A **Value** input column (input type depends on setting `valueType`)

---

### Page: Settings → Service Locations (if enabled)

**URL:** `/settings/core/service-locations`  
**Access:** Super Admin  
**Setting gate:** `SERVICE_LOCATIONS_ENABLED`  
**Purpose:** Manage Service Locations used across the platform.

![Service Locations](../screenshots/core/core-service-locations.png)

#### Header Controls
- **Search input**
  - **Placeholder:** “Search something”
  - **Debounce:** 900ms
  - **Behavior:** resets pagination to page 1 when changed
- **Refresh button**
  - **Icon:** refresh (`refresh-cw`)
  - **Color:** white
- **Create button**
  - **Label:** “Create”
  - **Color:** primary
  - **Action:** opens Create Service Location modal

#### Table Columns
- **Name**
- **# Work Orders**
- **# Users**
- **# Employees**
- **Actions**
  - **See Details** (primary): opens edit modal
  - **Delete** (text-danger): opens delete confirmation

#### API Calls
- List: `GET /api/service-location`
- Create: `POST /api/service-location`
- Update: `PUT /api/service-location`
- Delete: `DELETE /api/service-location` with `{ id }`

---

### Page: Billing → Users Report

**URL (Super Admin):** `/sa-billing/users`  
**Purpose:** Review user billing cost per month, search, export, and drill down into per-user details.

![Billing Users](../screenshots/core/core-billing-users.png)

**API call:** `GET /api/billing/users`
- Params: `search`, `monthStart`, `page`, `pageSize`

**Key UI**
- Month selector (6-month window)
- Search (“Search users”) with debounce
- Refresh button (icon refresh)
- CSV export: `UsersBilling.csv`
- Summary cards: Total Cost, Active Users, Cost per User, and optional “minimum users” adjustment card

---

### Page: Billing → Modules Report

**URL (Super Admin):** `/sa-billing/modules`  
**Purpose:** Review module billing cost per month, search, export, and view module cost breakdowns.

![Billing Modules](../screenshots/core/core-billing-modules.png)

**API call:** `GET /api/billing/modules`
- Params: `search`, `monthStart`, `page`, `pageSize`

**Key UI**
- Month selector, search, refresh
- CSV export: `ModulesBilling.csv`
- Summary cards: Total Cost, Active Modules, “See cost per module” link

---

### Page: Billing → Summary Report

**URL (Super Admin):** `/sa-billing/summary`  
**Purpose:** High-level billing summary with collapsible line details and PDF download.

![Billing Summary](../screenshots/core/core-billing-summary.png)

**API call:** `GET /api/billing/general`
- Params: `month`

**Actions**
- **Download (icon download)**: generates a PDF snapshot of the report (via `react-to-pdf`)
- **Refresh (icon refresh)**: re-fetches the report

Expanded sections:

![Core Features Expanded](../screenshots/core/core-billing-summary-corefeatures-expanded.png)
![Modules Expanded](../screenshots/core/core-billing-summary-modules-expanded.png)
![Users Expanded](../screenshots/core/core-billing-summary-users-expanded.png)

---

### Page: Data

**URL:** `/data`  
**Access:** Super Admin  
**Purpose:** Inspect raw model data returned by the backend, with model selection and search.

![Data Management](../screenshots/core/core-data-management.png)

**Model selector**
- **Placeholder:** “Choose a model”
- **Behavior:** loads data only after a model is selected

**Search**
- **Placeholder:** “Search something”
- **Debounce:** 900ms
- **Behavior:** resets pagination to page 1

**Refresh**
- **Icon:** refresh (`refresh-cw`)
- **Action:** toggles internal refresh and re-fetches

**API calls**
- `GET /api/data/models` (load available model names)
- `GET /api/data` (load data)
  - Params: `model`, `search`, `page`, `pageSize`

Additional states:

![Data With Model](../screenshots/core/core-data-management-with-model.png)
![Data Search](../screenshots/core/core-data-management-search.png)

---

## Modals & Confirmations

### Modal: Package Detail

**Triggered by:** “See More” on Modules list  
**Purpose:** View package details and update monthly cost.

![Package Detail Modal](../screenshots/core/core-package-detail-modal.png)

**Fields**
- **Monthly Cost**
  - Type: Currency input
  - Required: Yes
  - Decimals: 2
  - Max: 999,999,999
  - Placeholder: “Enter a cost”
  - Save action: `PUT /api/package` (updates package `cost`)

**Active Periods**
- Table columns: Period (#), Start, End
- Date format: `YYYY/MM/DD`
- Empty state: “No periods”

**Buttons**
- **Close** (secondary): closes modal without saving
- **Save** (primary): submits new monthly cost

---

### Modal: Confirmation (Module Enable/Disable)

**Triggered by:** toggling “Status” on a module row  
**Title:** “Update module”  
**Body:** “Are you sure you want to change this module status?”

![Package Toggle Confirmation](../screenshots/core/core-package-toggle-confirmation.png)

**Buttons**
- **Update** (primary): applies change via `PUT /api/package`
- **Cancel/Close**: closes without changes

---

### Modal: Service Location (Create/Edit)

**Triggered by:** “Create” or “See Details”  
**Purpose:** Create or update a service location.

![Service Location Modal](../screenshots/core/core-service-location-modal.png)

**Fields**
- **Name**
  - Type: text
  - Required: Yes
  - Max length: 50
  - Placeholder: “Enter a name”
- **Locale**
  - Type: searchable select
  - Placeholder: “Choose a locale”
  - Default: if empty, prefilled from `CLIENT_TIMEZONE` setting (when available)

**Buttons**
- **Cancel** (secondary): closes modal without saving
- **Save** (primary): creates/updates via `/api/service-location`

Edit screenshot:

![Service Location Edit Modal](../screenshots/core/core-service-location-edit-modal.png)

Delete confirmation screenshot:

![Service Location Delete Confirmation](../screenshots/core/core-service-location-delete-confirmation.png)

---

### Modal: Settings Header “Upload Logo”

**Triggered by:** “Sidebar Logo”, “PDF Logo”, “Login Logo” buttons on Core Settings  
**Purpose:** Upload image(s) and apply them to settings (branding).

![Sidebar Logo Upload Modal](../screenshots/core/core-settings-sidebar-logo-modal.png)

**Flow**
1. Open upload modal
2. Upload/select an image
3. Confirmation modal: “Update logo”
4. On confirm: updates setting via `PUT /api/setting` with `value = attachmentUrl`
5. Auth context refresh so the UI reflects changes

---

## Settings

### Settings Page: Core

**URL:** `/settings/core`  
**Package:** `core`  
**Data source:** `GET /api/setting` with `packageId` of the `core` package

#### Table Columns
- **Setting**
  - Shows setting name
  - If `description` exists, shows an info tooltip icon
- **Status**
  - Toggle switch (unless `valueOnly` is true)
  - Updates local state immediately; changes are saved only when clicking **Save**
- **Value**
  - Input type depends on `valueType` (see below)

#### Value Input Types (by `valueType`)
- **WORK_ORDER_STATUS**: dropdown (“Select the status”)
- **COMBO_BOX**: dropdown (“Select something”)
- **CURRENCY**: currency input (“Enter value”)
- **UPLOAD_PDF**: file upload/download widget
- **NUMBER**: numeric input (debounced)
- **DECIMAL**: numeric input with decimals (debounced)
- **PASSWORD**:
  - normal password input, or
  - large password textarea with **Show/Hide** (eye / eye-slash) for very large values
- **TEXT (large)**: textarea (monospace) when max length is large

#### Save / Discard Workflow
- **Discard** (secondary): reloads settings to discard local edits
- **Save** (primary): opens confirmation modal “Save setting”
  - Saves only touched settings
  - Calls `PUT /api/setting` per changed row
  - Success: toast “Setting saved”
  - Error: toast “Failed to save settings”

---

## Common Workflows

### Workflow 1: Login (with optional 2FA)

**Screenshots:**  
- Login page: `core-login-page.png`  
- Validation: `core-login-validation.png`  
- Error toast: `core-login-error-toast.png`

**Steps**
1. Go to `/auth/sign-in`
2. Enter **Email** and **Password**
3. Click **LOGIN**
4. If prompted, complete **2FA** (verify or setup)
5. User is redirected to the `return-url` if present, otherwise `/workorders`

---

### Workflow 2: Enable/Disable a Module

**Screenshots:**  
- Modules list: `core-modules-list.png`  
- Confirmation: `core-package-toggle-confirmation.png`  
- Post-update: `core-package-toggle-success.png`

**Steps**
1. Go to **Settings → Modules**
2. Toggle **Status** for a module
3. Confirm in the modal by clicking **Update**
4. Expect a success toast and updated status in the table

---

### Workflow 3: Update Module Monthly Cost

**Screenshots:**  
- Package detail modal: `core-package-detail-modal.png`  
- After save: `core-package-cost-updated.png`

**Steps**
1. Go to **Settings → Modules**
2. Click **See More** on a module
3. Update **Monthly Cost**
4. Click **Save**
5. Expect a success toast and updated cost when the list refreshes

---

### Workflow 4: View Billing Reports

**Screenshots:**  
- Users report: `core-billing-users.png`  
- Modules report: `core-billing-modules.png`  
- Summary report: `core-billing-summary.png`

**Steps**
1. Open Billing → **Users Report** or **Modules Report**
2. Select a month (report window covers last 6 months)
3. Use search to filter users/modules
4. Optionally export CSV from the export control
5. Open detail modals by clicking non-zero values (when available)
6. In Summary Report, expand sections and optionally download a PDF

---

## Integration Points

### API Endpoints Used (Core)
- Auth:
  - `GET /api/auth/login-logo`
  - `POST /api/auth/w/sign-in`
- 2FA:
  - `POST /api/auth/2fa/setup`
  - `POST /api/auth/2fa/verify`
  - `POST /api/auth/2fa/disable`
- Modules:
  - `GET /api/package` (paginated list)
  - `PUT /api/package` (update `isActive`, `cost`, etc.)
  - `GET /api/package/all` (used by core export in other contexts)
- Core settings:
  - `GET /api/setting` (by `packageId`)
  - `PUT /api/setting` (update setting values/status; supports upload value types via `FormData`)
- Service locations:
  - `GET|POST|PUT|DELETE /api/service-location`
- Billing:
  - `GET /api/billing/users`
  - `GET /api/billing/modules`
  - `GET /api/billing/general`
- Data:
  - `GET /api/data/models`
  - `GET /api/data`

### Shared UI/State
Core relies heavily on shared providers/components from `@crewos/shared`:
- Auth context updates after login and after module/settings updates (refresh action)
- Shared tables, pagination, confirmation/information modals, toasts, and inputs

---

## Troubleshooting

### Common Issues

**Issue: After saving a setting, the UI does not reflect changes**
- **Cause:** The app may require an auth/context refresh.
- **Expected behavior:** Core triggers a refresh after successful saves; if the sidebar/logo does not update immediately, try refreshing the page or clicking the **Refresh** button on the Settings header.

**Issue: Billing menu not visible for regular admins**
- **Cause:** `BILLING_SECTION_REGULAR_ADMINS` is disabled or user lacks `IS_ADMIN_USER`.
- **Fix:** Enable the setting and ensure the user role is correct.

**Issue: Service Locations menu not visible**
- **Cause:** `SERVICE_LOCATIONS_ENABLED` is disabled or user lacks Super Admin role.
- **Fix:** Enable the setting and verify role permissions.

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-27  
