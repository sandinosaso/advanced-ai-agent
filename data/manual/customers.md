# Customers Module - Detailed Functional Guide

**Module Package:** `@crewos/customers`  
**Base Path:** `/packages/customers/`  
**Version:** 1.0  
**Last Updated:** January 27, 2026

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

The Customers module is the core component for managing customer relationships and assets in CrewOS. It enables field service organizations to:

- Manage customer master data (names, contact information, addresses)
- Track multiple service locations per customer
- Maintain contact information at both customer and location levels
- Register and track customer assets (equipment, machinery, etc.)
- Link work orders to specific customers, locations, and assets
- Categorize assets by customizable types
- View comprehensive customer work order history

### Key Features

- **Customer Management**: Complete CRUD operations for customer records with detailed information
- **Multi-Location Support**: Customers can have unlimited service locations with unique addresses
- **Location Contacts**: Each location can have multiple contacts with name, email, and phone
- **Asset Registry**: Track all customer equipment with serial numbers, models, and manufacturers
- **Asset Hierarchy**: Support for parent-child asset relationships
- **Asset Types**: Categorize assets and define custom attributes per type
- **Dynamic Attributes**: Custom fields for asset types that auto-populate on asset creation
- **Work Order Integration**: View all work orders associated with customers and filter by location
- **Search & Filter**: Advanced search across customers and assets
- **Active/Inactive Status**: Track customer lifecycle status
- **Export Capabilities**: Export customer and asset lists to CSV

### User Roles

*Who can access this module:*

- ✅ **Super Admin** - Full access including delete operations and settings
- ✅ **Admin User** - Full access except certain delete operations and settings
- ❌ **Customer User** - No access (internal tool only)
- ❌ **Technician** - No direct access (may view through work orders)

### Required Settings

*Package and module configuration:*

- **Package Enabled**: `customers` package must be enabled in user's packages
- **Optional Integrations**: 
  - `inspections` package - Enables inspection template assignment to asset types
  - `services` package - Enables service template assignment to asset types
  - `DASHBOARDS_ENABLED` setting - Shows Customers Dashboard menu item

---

## Access & Permissions

### Role Requirements

**Full Access (Super Admin):**
- **Roles**: `IS_SUPER_ADMIN_USER`
- **Can**: View, Create, Edit, Delete all customers, locations, contacts, assets, and asset types
- **Special Permissions**: 
  - Delete customers and assets
  - Access Asset Types settings
  - Configure dynamic attributes

**Full Access (Admin):**
- **Roles**: `IS_ADMIN_USER`
- **Can**: View, Create, Edit customers, locations, contacts, and assets
- **Restrictions**: 
  - Cannot delete customers (delete button hidden)
  - Cannot access Asset Types settings
  - Cannot configure dynamic attributes

**No Access:**
- **Roles**: `IS_CUSTOMER_USER`, `IS_TECHNICIAN_USER`, or unauthenticated users
- **Behavior**: Module routes not visible in sidebar, direct access redirected

### Feature-Specific Permissions

**Customer Delete:**
- **Permission Check**: `isSuperAdmin` helper checks user role
- **Location**: Customers list page, action column
- **Behavior**: Delete button only rendered if `isSuperAdmin` returns true

**Asset Types Management:**
- **Permission Check**: Route scopes restricted to `IS_SUPER_ADMIN_USER`
- **Location**: Settings → Assets → Asset Types
- **Behavior**: Menu item not visible to non-super-admin users

**Dynamic Attributes:**
- **Permission Check**: Button only shown in Asset Type modal when editing (asset type has ID) and user is super admin
- **Location**: Asset Type modal footer
- **Behavior**: "Dynamic Attributes" button only visible when editing existing asset types

---

## Navigation

### Sidebar Location

**Main Menu Entry:**
- **Icon**: `message-circle` (feather icon)
- **Label**: "Customers"
- **Order**: Determined by package configuration
- **Collapsed by default**: No (expandable menu)
- **Visibility**: Only when `customers` package is enabled

### Sub-menu Items

When expanded, the Customers menu shows:

1. **Dashboard** (conditional)
   - Path: `/customers/dashboard`
   - Visible when: `DASHBOARDS_ENABLED` setting is true
   - Icon: Inherited from parent
   
2. **All Customers**
   - Path: `/customers/all`
   - Visible when: Always (for authorized users)
   - Icon: Inherited from parent

3. **Assets**
   - Path: `/customers/assets`
   - Visible when: Always (for authorized users)
   - Icon: Inherited from parent

### Settings Menu Entry

**Asset Types:**
- **Location**: Settings → Assets (category) → Asset Types
- **Path**: `/asset-types`
- **Order**: 2 (within Assets category)
- **Icon**: None (uses category icon)
- **Access**: Super Admin only

### URL Paths

Primary routes:

- **All Customers List**: `/customers/all`
- **Customer Dashboard**: `/customers/dashboard` (if enabled)
- **Assets List**: `/customers/assets`
- **Customer Details**: `/customers/:customerId`
- **Location Assets**: `/customers/:customerId/locations/:locationId/assets`
- **Asset Details**: `/assets/:assetId`
- **Asset Types**: `/asset-types` (settings)

---

## Main Pages

### Page 1: All Customers List

**URL:** `/customers/all`  
**Access:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`  
**Purpose:** Display searchable, sortable table of all customers with quick actions

![Customers List](../screenshots/customers/customers-list.png)

#### Page Header

**Title:** "All customers"
- **Record Count:** Shows `(X)` where X is total customer count
- **Format**: `All customers (123)`

**Header Actions (Right Side):**

**1. Status Filter Dropdown**
- **Type**: Select dropdown
- **Label/Placeholder**: "Filter by status"
- **Position**: Leftmost in action row
- **Options**:
  - `Active` (default) - Shows active customers only
  - `Inactive` - Shows inactive customers only
- **Default**: Active
- **Behavior**:
  - Changes `showInactive` state
  - Reloads customer list with `isActive` parameter
  - Shows `false` for inactive, `true` for active
- **Width**: Auto (fits content)
- **Test ID**: `activeSelect`

**2. Search Input**
- **Type**: Debounced text input
- **Placeholder**: "Search customers"
- **Max Length**: 50 characters
- **Debounce**: 900ms
- **Position**: Center-right in action row
- **Action**: 
  1. Waits 900ms after user stops typing
  2. Triggers API call with search parameter
  3. Resets pagination to page 0
  4. Searches across customer name and number
- **Clear**: Backspace clears search, reloads all

**3. Refresh Button**
- **Label**: Icon only (no text)
- **Icon**: `refresh-cw` (circular arrows)
- **Color**: White background with primary text color
- **Shape**: Circle (custom-rounded-button class)
- **Size**: Small
- **Position**: Right of search, left of export
- **Action**: 
  1. Toggles `refresh` state boolean
  2. Triggers useEffect to reload customer data
  3. Maintains current filters, search, and pagination
- **Loading**: No spinner (instant toggle)

**4. Export Container**
- **Type**: Dynamic container for export functionality
- **ID**: `table-export`
- **Position**: Right of refresh, left of Create button
- **Behavior**: AdvanceTable component injects export button here
- **Export Format**: CSV
- **Filename**: `customers.csv`
- **Scope**: Exports currently visible filtered/searched customers

**5. Create Button**
- **Label**: "Create"
- **Icon**: None
- **Color**: Primary (blue)
- **Shape**: Rounded rectangle
- **Size**: Default
- **Position**: Far right
- **Test ID**: None
- **Action**: 
  1. Opens CustomerModal with empty customer object
  2. Default values: `{ isActive: true }`
  3. Modal shows "Create Customer" title
- **Permissions**: All users with module access

#### Main Content - Customers Table

**Table Type:** Sortable, paginated data table with row actions

**Table Features:**
- **Sorting**: Click column headers to sort (ascending/descending)
- **Striping**: Alternating row colors for readability
- **Pagination**: 15 rows per page (default), configurable
- **Export**: Yes - CSV format via export button in header
- **Row Click**: No navigation (actions via buttons only)
- **Loading State**: Shows loading spinner overlay
- **Empty State**: Default table empty message

**Columns:**

| Column Name | Accessor | Sortable | Width | Format |
|-------------|----------|----------|-------|--------|
| Name | customerName | Yes | 350px | Text |
| Customer No. | customerNo | Yes | 250px | Text |
| Locations | locations | No | Auto | Count |
| Work Orders | workOrders | No | Auto | Count |
| Actions | id | No | 300px | Buttons |

**Column Details:**

**1. Name Column**
- **Header Text**: "Name"
- **Accessor**: `customerName`
- **Sortable**: Yes (default sort column)
- **Default Sort**: Ascending
- **Width**: Max 350px
- **Cell Rendering**: Plain text, truncated with ellipsis if overflow
- **Empty State**: Shows "-" if no name
- **Header Classes**: `text-truncate`
- **Cell Classes**: `text-truncate`

**2. Customer No. Column**
- **Header Text**: "Customer No."
- **Accessor**: `customerNo`
- **Sortable**: Yes
- **Width**: Max 250px
- **Cell Rendering**: Plain text, truncated with ellipsis if overflow
- **Empty State**: Shows "-" if no customer number
- **Header Classes**: `text-truncate`
- **Cell Classes**: `text-truncate`

**3. Locations Column**
- **Header Text**: "Locations"
- **Accessor**: `locations`
- **Sortable**: No
- **Width**: Auto
- **Cell Rendering**: Count of locations array (integer)
- **Format**: `{locations.length}`
- **Empty State**: Shows `0` if no locations
- **Purpose**: Quick visibility of location count without opening details

**4. Work Orders Column**
- **Header Text**: "Work Orders"
- **Accessor**: `workOrders`
- **Sortable**: No
- **Width**: Auto
- **Cell Rendering**: Count of work orders array (integer)
- **Format**: `{workOrders.length}`
- **Empty State**: Shows `0` if no work orders
- **Purpose**: Quick visibility of work order history

**5. Actions Column**
- **Header Text**: Empty
- **Accessor**: `id`
- **Sortable**: No
- **Filterable**: No
- **Width**: Max 300px
- **Alignment**: Right-aligned
- **Header Classes**: `text-truncate`
- **Cell Classes**: `text-end text-truncate`

**Actions Column Buttons:**

**View Details Button**
- **Label**: "View Details"
- **Size**: Small
- **Color**: Primary
- **Position**: Leftmost
- **Action**: Navigate to `/customers/{id}` (Customer Details page)
- **Always Visible**: Yes

**Edit Button**
- **Label**: "Edit"
- **Size**: Small
- **Color**: None (text-primary class)
- **Position**: Center
- **Margin**: Left 2 (ms-2)
- **Action**: Opens CustomerModal with customer data pre-filled
- **Always Visible**: Yes

**Delete Button**
- **Label**: "Delete"
- **Size**: Small
- **Color**: None (text-danger class)
- **Position**: Rightmost
- **Margin**: Left 2 (ms-2)
- **Test ID**: `delete-button`
- **Visible**: Only if user is Super Admin
- **Action**: 
  1. Opens confirmation modal
  2. Shows: "Are you sure you want to delete {customerName}?"
  3. Confirm button: Red "Delete" button
  4. On confirm: Calls DELETE API, shows success toast, refreshes list
- **Permissions**: Super Admin only

#### Pagination

**Component**: AdvanceTablePagination

**Features:**
- **Total Count Display**: Shows total customers matching current filter
- **Page Numbers**: Clickable page numbers
- **Current Page**: Highlighted
- **Page Size Selector**: Dropdown to change rows per page
- **Available Sizes**: [10, 15, 25, 50, 100]
- **Default**: 15 rows per page
- **Behavior**: Changing page size resets to page 1

**Navigation:**
- Previous/Next buttons
- Direct page number selection
- First/Last page quick buttons

#### API Integration

**Endpoint**: `GET /api/customers`

**Query Parameters:**
- `search`: Search term (min 1 char)
- `page`: Page number (0-indexed)
- `pageSize`: Rows per page
- `sortBy`: Column to sort by
- `direction`: `asc` or `desc`
- `isActive`: `"true"` or `"false"` (string)

**Response Format:**
```json
{
  "data": [...customers],
  "count": 123,
  "totalPages": 9
}
```

#### Screenshots

![Customers List - Main View](../screenshots/customers/customers-list.png)
*Main customers list showing all active customers with search and filters*

![Customers List - Search Active](../screenshots/customers/customers-list-search.png)
*Search functionality filtering customers by name or number*

![Customers List - Inactive Filter](../screenshots/customers/customers-list-inactive.png)
*Viewing inactive customers using status filter*

---

### Page 2: Customer Details

**URL:** `/customers/:customerId`  
**Access:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`  
**Purpose:** View complete customer information, manage locations, and view associated work orders

![Customer Details](../screenshots/customers/customer-details-overview.png)

#### Page Header

**Navigation:**
- **Back Button**: Chevron-left icon, navigates to previous page
- **Position**: Left side of header
- **Icon**: `chevron-left` in rounded circle
- **Classes**: `text-muted rounded-circle back-arrow bg-white fs-4`
- **Test ID**: `back-button`
- **Action**: `sharedHelper.goBack(navigate)` - intelligent back navigation

**Title Section:**
- **Title**: Customer name (dynamic)
- **Format**: `{customerData.customerName}`
- **Font**: H2, bold, dark text

**Customer Metadata (Horizontal Info Strip):**

Displayed in single row below title, separated by bullets (·):

1. **Customer #**: `{customerData.customerNo}`
2. **Email**: `{customerData.email}` or "-"
3. **Address**: `{customerData.address}` or "-"
4. **City**: `{customerData.city}` or "-"
5. **Zip Code**: `{customerData.zipCode}` or "-"
6. **Country**: `{customerData.countryCode}` or "-"
7. **Telephone**: `{customerData.phone}` or "-"
8. **Fax**: `{customerData.faxNo}` or "-"

**Styling:**
- **Size**: Small text
- **Labels**: Gray/muted color
- **Values**: Default dark color
- **Separator**: Gray bullet (·) with horizontal margin

#### Main Content Area

The Customer Details page is divided into two main sections displayed side by side:

**1. Customer Locations Section (Left/Full Width)**

![Customer Locations Section](../screenshots/customers/customer-details-locations.png)

**Section Header:**
- **Title**: "Customer Locations" (H2, bold)
- **Create Button**: "Create" button (primary color) on the right
- **Action**: Opens CustomerLocationModal for new location

**Empty State:**
- **Display**: When `customer.locations.length === 0`
- **Message**: "No locations"
- **Styling**: Muted small text, bordered rounded container

**Locations Grid:**
- **Layout**: Responsive grid
- **Columns**: 
  - Mobile (xs): 1 column (col-12)
  - Tablet (md): 2 columns (col-md-6)
  - Desktop (lg): 3 columns (col-lg-4)
  - Large (xl): 4 columns (col-xl-3)
- **Spacing**: Bottom margin 3 on each card
- **Sorting**: Default locations shown first

**Location Card:**

Each location displays as an interactive card:

**Card Header:**
- **Title**: `{location.shipToName}` or `Location {index + 1}`
- **Font**: H6, bold
- **Default Badge**: 
  - Shown if: `location.isDefault === true`
  - Text: "Default"
  - Color: Primary (blue)
  - Shape: Pill
  - Size: Small
- **Edit Button**:
  - Icon: `edit-2`
  - Color: Link/Primary
  - Size: Small
  - Test ID: `edit-button`
  - Action: Opens CustomerLocationModal with location data
- **Delete Button**:
  - Icon: `trash`
  - Color: Link/Danger
  - Size: Small
  - Test ID: `delete-button`
  - Action: Opens confirmation modal, deletes location on confirm

**Card Body:**
- **Background**: Transparent
- **Address Lines**: Each line of address on separate row
  - Generated by: `sharedHelper.getAddress(location, true)`
  - Skips first line (name, shown in header)
  - Shows: Address, City, State, Zip, Country (non-empty fields)
- **Font**: Small text
- **Color**: Default dark

**Card Footer Actions:**

Two buttons in flex layout (space-between):

1. **See Contacts Button**:
   - Label: "See Contacts"
   - Color: Primary
   - Size: Small
   - Action: Opens CustomerLocationContactsModal
   - Shows: Contact list for this location

2. **See Assets Button**:
   - Label: "See Assets"
   - Color: Primary
   - Size: Small
   - Margin: Left 2
   - Action: Navigate to `/customers/{customerId}/locations/{locationId}/assets`
   - Shows: Assets specific to this location

**Card Selection:**
- **Feature**: Clickable cards to filter work orders
- **Behavior**: Click card to toggle selection
- **Visual**: Selected cards have `bg-primarylight` background
- **Effect**: Work orders section filters to selected location
- **Deselect**: Click selected card again to show all work orders

**2. Work Orders Section (Right/Full Width)**

![Work Orders Section](../screenshots/customers/customer-details-workorders.png)

**Integration:**
- **Component**: `WorkOrders` from `@crewos/workorders` package
- **Props**:
  - `customerId`: Current customer ID
  - `customerLocationId`: Selected location ID (or undefined for all)
- **Behavior**: 
  - Shows all work orders for customer by default
  - Filters to specific location when location is selected
  - Real-time updates when location selection changes

**Display:**
- **Layout**: Full width table
- **Columns**: Based on WorkOrders component configuration
- **Typical Columns**: Work Order #, Title, Status, Scheduled Date, Assignee, etc.
- **Actions**: View, Edit work orders (per WorkOrders module permissions)

#### Loading States

**Initial Load:**
- **Display**: `<Loader />` component (full page spinner)
- **When**: `isLoadingCustomers === true`
- **Clears**: When customer data is loaded

**No Results:**
- **Display**: "No results" centered text
- **When**: Customer data loaded but empty/not found
- **Styling**: Centered text in card body

#### Screenshots

![Customer Details - Overview](../screenshots/customers/customer-details-overview.png)
*Customer details page showing customer information and locations*

![Customer Details - Location Cards](../screenshots/customers/customer-locations-cards.png)
*Grid of customer location cards with default location highlighted*

![Customer Details - Selected Location](../screenshots/customers/customer-location-selected.png)
*Location card selected (highlighted) filtering work orders to that location*

![Customer Details - Work Orders](../screenshots/customers/customer-workorders-filtered.png)
*Work orders filtered by selected location*

---

### Page 3: Assets List

**URL:** `/customers/assets` or `/customers/:customerId/locations/:locationId/assets`  
**Access:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`  
**Purpose:** View and manage all assets or assets for specific customer location

![Assets List](../screenshots/customers/assets-list.png)

#### Context Variations

**Global Assets View:**
- **URL**: `/customers/assets`
- **Shows**: All assets across all customers
- **Customer Column**: Visible (shows customer & location)
- **Back Button**: No back button
- **Title**: "Assets" (H2)

**Location Assets View:**
- **URL**: `/customers/:customerId/locations/:locationId/assets`
- **Shows**: Assets for specific location only
- **Customer Column**: Hidden (already known context)
- **Back Button**: Yes (returns to customer details)
- **Title**: "Assets" (H2)

**Child Assets View (Nested):**
- **Context**: Within Asset Detail page
- **Shows**: Child assets of parent asset
- **Title**: "Child Assets" (H4)
- **Header Styling**: Compact (no padding)
- **Body Styling**: Compact (minimal padding/margin)

#### Page Header

**Back Button** (Global/Location views only):
- **Shown**: When not nested (`!assetParentId`)
- **Icon**: `chevron-left`
- **Test ID**: `back-button`
- **Action**: Navigate back to previous page

**Title:**
- **Main View**: "Assets" (H2)
- **Child View**: "Child Assets" (H4)
- **Count Badge**: `({assets.count || 0})` in muted small text

**Header Actions:**

**1. Search Input**
- **Placeholder**: "Search assets"
- **Max Length**: 50 characters
- **Debounce**: 900ms
- **Min Length**: 1 character
- **Action**: 
  - Searches across: name, model number, serial number, manufacturer
  - Resets pagination to page 0
  - Maintains other filters (customer, location, parent)

**2. Refresh Button**
- **Icon**: `refresh-cw`
- **Color**: White background, primary text
- **Shape**: Circle
- **Size**: Small
- **Test ID**: `refresh-button`
- **Action**: Toggles refresh state, reloads assets

**3. Create Button**
- **Label**: "Create"
- **Color**: Primary
- **Action**: Opens AssetModal
- **Default Values**:
  - If location context: `customerLocationId` pre-filled
  - If parent context: `assetParentId` pre-filled
  - Otherwise: Empty form

#### Main Content - Assets Table

**Table Features:**
- **Striping**: Yes
- **Sortable**: No (basic table)
- **Pagination**: Yes (15 per page default)
- **Loading**: Spinner overlay
- **Row Click**: Navigate to `/assets/{assetId}` (asset details)
- **Cursor**: Pointer on rows to indicate clickability

**Columns (Global View):**

| Column | Header | Accessor | Width | Notes |
|--------|--------|----------|-------|-------|
| Name/ID | Name/ID | name | 150px | Truncated |
| Model # | Model # | modelNumber | 150px | Truncated |
| Serial # | Serial # | serialNumber | 150px | Truncated |
| Manufacturer | Manufacturer | manufacturer | 150px | Truncated |
| Type | Type | assetType.name | 150px | Not sortable |
| Customer & Location | Customer & Location | customerLocation.customer.customerName | Auto | Conditional |
| Templates | Templates | inspectionTemplateWorkOrders | Auto | If inspections enabled |
| Actions | (empty) | id | 300px | Buttons |

**Column Details:**

**Name/ID Column:**
- **Accessor**: `name`
- **Width**: Max 150px
- **Truncate**: Yes
- **Format**: Plain text
- **Required**: Yes (at creation)

**Model # Column:**
- **Accessor**: `modelNumber`
- **Width**: Max 150px
- **Truncate**: Yes
- **Format**: Plain text
- **Required**: Yes (at creation)

**Serial # Column:**
- **Accessor**: `serialNumber`
- **Width**: Max 150px
- **Truncate**: Yes
- **Format**: Plain text
- **Required**: Yes (at creation)

**Manufacturer Column:**
- **Accessor**: `manufacturer`
- **Width**: Max 150px
- **Truncate**: Yes
- **Format**: Plain text
- **Required**: Yes (at creation)

**Type Column:**
- **Accessor**: `assetType.name`
- **Width**: Max 150px
- **Sortable**: No
- **Filterable**: No
- **Format**: Asset type name (read-only reference)

**Customer & Location Column:**
- **Shown**: Only in global assets view (`!customerLocationId`)
- **Hidden**: In location-specific or child assets views
- **Accessor**: `customerLocation.customer.customerName`
- **Format**: `{customerName} - {locationName}` or just `{customerName}`
- **Empty**: Shows "-" if no customer
- **Truncate**: Yes

**Templates Column (Inspections):**
- **Shown**: Only if `inspections` package enabled
- **Accessor**: `inspectionTemplateWorkOrders`
- **Format**: Count of templates (integer)
- **Display**: `{inspectionTemplateWorkOrders.length}` or `0`
- **Purpose**: Show how many inspection templates assigned

**Templates Column (Services):**
- **Shown**: Only if `services` package enabled
- **Accessor**: `serviceTemplateWorkOrders`
- **Format**: Count of templates (integer)
- **Display**: `{serviceTemplateWorkOrders.length}` or `0`
- **Purpose**: Show how many service templates assigned

**Actions Column:**

Two action buttons per row:

1. **Add Child Button:**
   - **Label**: "Add Child"
   - **Size**: Small
   - **Color**: None (text-primary)
   - **Margin**: Left 2
   - **Action**: 
     - Stops event propagation (prevents row click)
     - Opens AssetModal
     - Pre-fills: `assetParentId` and `customerLocationId` from parent
   - **Purpose**: Create child asset under this asset

2. **Delete Button:**
   - **Label**: "Delete"
   - **Size**: Small
   - **Color**: None (text-danger)
   - **Margin**: Left 2
   - **Action**: 
     - Stops event propagation
     - Opens confirmation modal
     - Message: "Are you sure you want to delete {asset.name}?"
     - On confirm: DELETE API call, success toast, refresh list
   - **Permissions**: All users with module access (no super admin restriction)

#### Pagination

**Component**: AdvanceTablePagination

**Features:**
- Total count display
- Page size selector: [10, 15, 25, 50, 100]
- Default: 15 rows per page
- Current page highlighting
- Previous/Next/First/Last navigation

#### API Integration

**Endpoint**: `GET /api/assets`

**Query Parameters:**
- `search`: Search term
- `page`: Page number (0-indexed)
- `pageSize`: Rows per page
- `customerLocationId`: Filter by location (optional)
- `assetParentId`: Filter by parent asset (optional)

**Response Format:**
```json
{
  "data": [...assets],
  "count": 456,
  "totalPages": 31
}
```

#### Screenshots

![Assets List - Global View](../screenshots/customers/assets-list.png)
*All assets across all customers showing customer & location column*

![Assets List - Location Filtered](../screenshots/customers/assets-list-location.png)
*Assets filtered to specific customer location*

![Assets List - Search](../screenshots/customers/assets-list-search.png)
*Search functionality filtering assets by name, model, or serial*

---

### Page 4: Asset Details

**URL:** `/assets/:assetId`  
**Access:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`  
**Purpose:** View complete asset information, manage asset image, and view/manage child assets

![Asset Details](../screenshots/customers/asset-details.png)

#### Page Header

**Back Button:**
- **Icon**: `chevron-left`
- **Test ID**: `back-button`
- **Action**: Navigate back to previous page

**Title:**
- **Format**: `{customerName} - {assetName}`
- **Example**: "Acme Corp - Chiller Unit A"
- **Font**: H2

**Header Actions:**

**Refresh Button:**
- **Icon**: `refresh-cw`
- **Color**: White background, primary text
- **Shape**: Circle
- **Test ID**: `refresh-button`
- **Action**: Reload asset data

**Edit Button:**
- **Label**: "Edit"
- **Color**: Primary
- **Margin**: Right 3
- **Action**: Opens AssetModal with current asset data

#### Main Content

**Layout**: Flexbox with image on left, info on right

**Left Section - Asset Image:**

**Container:**
- **Width**: Min 200px
- **Position**: Relative (for absolute edit button)
- **Margin**: Right 4

**Image Display:**
- **With Image**: 
  - Component: ImagesViewer
  - Mode: Preview
  - Size: 200x200px
  - Actions: Hidden
  - Caption: Hidden
  - Clickable: Yes (opens full-size modal)
- **Without Image**:
  - Shows: Placeholder image (`ImgPlaceholder`)
  - Size: 200px wide, auto height
  - Style: Rounded corners
  - Not clickable

**Edit Image Button:**
- **Position**: Absolute (top: 5px, right: 5px)
- **Icon**: `edit-2`
- **Color**: White background, primary text
- **Shape**: Circle
- **Size**: Small
- **Test ID**: `edit-image-button`
- **Action**: Opens UploadPhotosModal for image update

**Right Section - Asset Information:**

**Section Title:**
- **Text**: "Information"
- **Font**: H4, bold

**Information Grid:**

Layout: Bootstrap Row/Col responsive grid

**Row 1:**
1. **Name/ID** (Col md-4)
   - Label: "Name/ID"
   - Value: `{asset.name}`
   - Styling: Muted text

2. **Model #** (Col md-4)
   - Label: "Model #"
   - Value: `{asset.modelNumber}`
   - Styling: Muted text

3. **Serial #** (Col md-4)
   - Label: "Serial #"
   - Value: `{asset.serialNumber}`
   - Styling: Muted text

**Row 2** (margin-top 4):
1. **Manufacturer** (Col md-4)
   - Label: "Manufacturer"
   - Value: `{asset.manufacturer}`
   - Styling: Muted text

2. **Customer Location** (Col md-4)
   - Label: "Customer Location"
   - Value: `{asset.customerLocation.shipToName}`
   - Styling: Muted text

3. **Asset Type** (Col md-4)
   - Label: "Asset Type"
   - Value: `{asset.assetType.name}`
   - Styling: Muted text

**Custom Fields Section:**

**Visibility:** Only shown if `dynamicAttributes.length > 0`

**Section Divider:** Horizontal rule (`<hr />`)

**Section Title:**
- **Text**: "Custom Fields"
- **Font**: H4, bold

**Fields Grid:**
- **Layout**: Flex wrap with row gap
- **Each Field**: Col md-3 (4 columns on desktop)
- **Structure**:
  - Label: `{dynamicAttribute.label}`
  - Value: Formatted dynamic attribute value
  - Format Function: `dynamicAttributeHelper.formatDynamicAttributeValue()`
  - Empty State: "Not set" (muted text)

**Dynamic Attribute Types:**
- Text: Plain text
- Number: Formatted number
- Date: Formatted date
- Boolean: Yes/No
- Select: Selected option label

**Child Assets Section:**

**Section Divider:** Horizontal rule (`<hr />`)

**Component:** Nested `<Assets />` component

**Props:**
- `assetParentId`: Current asset ID
- `defaultCustomerLocationId`: Current asset's location ID
- `HeaderActions`: Rendered but not used (could show "Add New" button)

**Display:**
- Full assets table (as described in Assets List page)
- Compact styling for nested view
- Shows only children of current asset
- All child asset actions available (add child of child, delete, etc.)

#### Loading States

**Page Load:**
- **Display**: `<Loader />` full page spinner
- **When**: `isLoading || !asset`

**Image Update:**
- **Display**: No visible spinner (handled by modal)
- **Toast**: "Asset image saved" on success

**Error Handling:**
- **Asset Not Found**: Redirects to `/customers/assets`
- **When**: `getAssetsError` is truthy

#### Modals

**1. AssetModal (Edit):**
- **Trigger**: Edit button
- **Props**: 
  - `defaultCustomerLocationId`: Current location
  - `defaultAsset`: Current asset data
- **On Submit**: Closes modal, shows success toast, refreshes asset

**2. UploadPhotosModal:**
- **Trigger**: Edit image button
- **Title**: "Update asset image"
- **On Submit**: 
  - Updates asset with new image URL
  - Shows "Asset image saved" toast
  - Refreshes asset data

**3. ImagesViewerModal:**
- **Trigger**: Click on asset image
- **Title**: "Asset image"
- **Content**: Full-size asset image
- **Actions**: Close only (no edit in viewer)

#### Screenshots

![Asset Details - Main View](../screenshots/customers/asset-details.png)
*Asset details page showing all information and image*

![Asset Details - Custom Fields](../screenshots/customers/asset-details-custom-fields.png)
*Custom dynamic attributes for asset type displayed*

![Asset Details - Child Assets](../screenshots/customers/asset-details-child-assets.png)
*Child assets table showing nested equipment*

![Asset Details - Image Upload](../screenshots/customers/asset-image-upload.png)
*Upload photo modal for updating asset image*

---

### Page 5: Asset Types (Settings)

**URL:** `/asset-types`  
**Access:** `IS_SUPER_ADMIN_USER` only  
**Purpose:** Configure asset type catalog and default templates

![Asset Types List](../screenshots/customers/asset-types-list.png)

#### Page Header

**Title:** "Asset Types"
- **Count Badge**: `({assetTypes.count})` in muted small text

**Header Actions:**

**1. Search Input**
- **Placeholder**: "Search types"
- **Max Length**: 50 characters
- **Debounce**: 900ms
- **Min Length**: 1 character
- **Action**: Search asset types by name

**2. Refresh Button**
- **Icon**: `refresh-cw`
- **Test ID**: `refresh-button`
- **Action**: Reload asset types list

**3. Create Button**
- **Label**: "Create"
- **Color**: Primary
- **Action**: Opens AssetTypeModal (empty)

#### Main Content - Asset Types Table

**Table Features:**
- **Striping**: Yes
- **Sortable**: No
- **Pagination**: Yes (15 per page default)
- **Loading**: Spinner overlay
- **Row Click**: No navigation (actions via buttons)

**Columns:**

| Column | Header | Accessor | Type | Width |
|--------|--------|----------|------|-------|
| Name | Name | name | Text | Auto |
| Assets | Assets | assets | Number | Auto |
| Default Type | Default Type | isDefault | Boolean | Auto |
| Inspection Template | Inspection Template | defaultInspectionTemplate | Text | Auto (conditional) |
| Service Template | Service Template | defaultServiceTemplate | Text | Auto (conditional) |
| Actions | (empty) | id | Buttons | 300px |

**Column Details:**

**Name Column:**
- **Accessor**: `name`
- **Cell**: Plain text, asset type name

**Assets Column:**
- **Accessor**: `assets`
- **Format**: Count of assets using this type
- **Display**: `{assets.length}`
- **Type**: Number

**Default Type Column:**
- **Accessor**: `isDefault`
- **Format**: Badge with Yes/No
- **Yes Badge**:
  - Text: "Yes"
  - Color: Success (green)
  - Value attribute: "Yes"
- **No Badge**:
  - Text: "No"
  - Color: Dark (gray)
  - Value attribute: "No"

**Inspection Template Column:**
- **Shown**: Only if `inspections` package enabled
- **Accessor**: `defaultInspectionTemplate`
- **Format**: Template name or "No template assigned"
- **Styling**: Muted text
- **Purpose**: Shows default inspection template for assets of this type
- **Position**: Inserted before Actions column

**Service Template Column:**
- **Shown**: Only if `services` package enabled
- **Accessor**: `defaultServiceTemplate`
- **Format**: Template name or "No template assigned"
- **Styling**: Muted text
- **Purpose**: Shows default service template for assets of this type
- **Position**: Inserted before Actions column

**Actions Column:**

Two action buttons per row:

1. **Edit Button:**
   - **Label**: "Edit"
   - **Size**: Small
   - **Color**: None (text-primary)
   - **Margin**: Left 2
   - **Action**: Opens AssetTypeModal with asset type data

2. **Delete Button:**
   - **Label**: "Delete"
   - **Size**: Small
   - **Color**: None (text-danger)
   - **Margin**: Left 2
   - **Action**: 
     - Opens confirmation modal
     - Message: "Are you sure you want to delete {assetType.name}?"
     - Confirm: Red "Delete" button
     - On confirm: DELETE API, success toast, refresh list

#### Pagination

Standard AdvanceTablePagination component with:
- Total count
- Page size selector
- Page navigation

#### API Integration

**Endpoint**: `GET /api/asset-types`

**Query Parameters:**
- `search`: Search term
- `page`: Page number (0-indexed)
- `pageSize`: Rows per page

**Response:**
```json
{
  "data": [...assetTypes],
  "count": 45,
  "totalPages": 3
}
```

#### Screenshots

![Asset Types List](../screenshots/customers/asset-types-list.png)
*Asset types configuration table with templates*

![Asset Types - With Templates](../screenshots/customers/asset-types-with-templates.png)
*Asset types showing inspection and service template assignments*

---

## Modals & Drawers

### Modal 1: Create/Edit Customer

**Type:** Modal (center)  
**Triggered By:** "Create" button on customers list or "Edit" button in actions column  
**Size:** Large (`lg`)  
**Can be closed by:** X button, Cancel button, outside click (default modal behavior)

![Create Customer Modal](../screenshots/customers/create-customer-modal-empty.png)

#### Modal Header

**Title:** Dynamic based on mode
- **Create Mode**: "Create Customer"
- **Edit Mode**: "Edit Customer"
- **Detection**: If `customerData.id` exists, edit mode

**Close Button:**
- **Icon**: X (default modal close)
- **Position**: Top right corner
- **Action**: Closes modal without saving

#### Modal Body

**Component:** CustomerForm

**Layout:** Two-column responsive form

**Form Fields:**

**Row 1:**

**1. Name Field**
- **Label**: "Name"
- **Required**: Yes (red asterisk *)
- **Type**: Text input
- **ID**: `customerName`
- **Class**: `form-control-redesign`
- **Max Length**: 50 characters
- **Placeholder**: "Enter a customer name"
- **Validation**: Required (HTML5 validation)
- **Default**: Empty string or existing name
- **Column**: 6 (half width)

**2. Customer # Field**
- **Label**: "Customer #"
- **Required**: Yes (red asterisk *)
- **Type**: Text input
- **ID**: `customerNo`
- **Class**: `form-control-redesign`
- **Max Length**: 255 characters
- **Placeholder**: "Enter a customer #"
- **Validation**: Required (HTML5 validation)
- **Default**: Empty string or existing number
- **Column**: 6 (half width)
- **Note**: Should be unique per customer

**Row 2:**

**3. Address Field**
- **Label**: "Address"
- **Required**: No
- **Type**: Text input
- **ID**: `address`
- **Max Length**: 50 characters
- **Placeholder**: "Enter an address"
- **Default**: Empty or existing address
- **Column**: 6

**4. City Field**
- **Label**: "City"
- **Required**: No
- **Type**: Text input
- **ID**: `city`
- **Max Length**: 50 characters
- **Placeholder**: "Enter a city"
- **Default**: Empty or existing city
- **Column**: 6

**Row 3:**

**5. State Field**
- **Label**: "State"
- **Required**: No
- **Type**: Text input
- **ID**: `state`
- **Max Length**: 25 characters
- **Placeholder**: "Enter a state"
- **Default**: Empty or existing state
- **Column**: 6

**6. Zip Code Field**
- **Label**: "Zip Code"
- **Required**: No
- **Type**: Text input
- **ID**: `zipCode`
- **Max Length**: 50 characters
- **Placeholder**: "Enter a zip code"
- **Default**: Empty or existing zip
- **Column**: 6

**Row 4:**

**7. Country Field**
- **Label**: "Country"
- **Required**: No
- **Type**: Text input
- **ID**: `countryCode`
- **Max Length**: 10 characters
- **Placeholder**: "Enter a country code"
- **Default**: Empty or existing country code
- **Column**: 6
- **Note**: Typically 2-letter country code (US, CA, MX, etc.)

**8. Telephone Field**
- **Label**: "Telephone"
- **Required**: No
- **Type**: Text input
- **ID**: `phone`
- **Max Length**: 25 characters
- **Placeholder**: "Enter a telephone number"
- **Default**: Empty or existing phone
- **Column**: 6

**Row 5:**

**9. Fax Field**
- **Label**: "Fax"
- **Required**: No
- **Type**: Text input
- **ID**: `faxNo`
- **Max Length**: 25 characters
- **Placeholder**: "Enter a fax number"
- **Default**: Empty or existing fax
- **Column**: 6

**10. Email Field**
- **Label**: "Email"
- **Required**: No
- **Type**: Text input (not email type for flexibility)
- **ID**: `email`
- **Max Length**: 100 characters
- **Placeholder**: "Enter an email address"
- **Default**: Empty or existing email
- **Column**: 6
- **Processing**: Value is trimmed on change

**Row 6:**

**11. Status Field**
- **Label**: "Status"
- **Required**: Yes (red asterisk *)
- **Type**: Select dropdown (react-select)
- **ID**: `statusSelect`
- **Input ID**: `statusSelectSearch`
- **Test ID**: `statusSelect`
- **Options**:
  - `{ label: "Active", value: true }`
  - `{ label: "Inactive", value: false }`
- **Default**: Active (`true`) for new customers
- **Validation**: Required
- **Column**: 6
- **Purpose**: Track customer lifecycle status

#### Modal Footer

**Layout:** Space-between (buttons on left and right)

**Cancel Button:**
- **Label**: "Cancel"
- **Color**: Secondary (gray)
- **Position**: Left
- **Text Color**: Dark
- **Action**: Close modal without saving

**Save Button:**
- **Label**: "Save"
- **Color**: Primary (blue)
- **Type**: Submit
- **Position**: Right
- **Action**: 
  1. Validates form (HTML5 + required fields)
  2. Calls create or update API
  3. Shows success toast
  4. Closes modal
  5. Refreshes customer list

#### Validation

**Client-Side:**
- Name: Required, max 50 chars
- Customer #: Required, max 255 chars
- Status: Required
- All other fields: Optional with max length limits

**Server-Side:**
- Should validate customer # uniqueness
- Email format validation (if provided)
- Phone number format (if enforced)

#### Success Behavior

**Create Customer:**
1. API: `POST /api/customers`
2. Toast: "Customer created"
3. Modal closes
4. List refreshes with new customer visible

**Edit Customer:**
1. API: `PUT /api/customers/{id}`
2. Toast: "Customer saved"
3. Modal closes
4. List refreshes with updated data

#### Loading State

**Display:** `<Loader size="sm" />` in modal body
**When:** `isLoadingCreateCustomer || isLoadingUpdateCustomer`
**Behavior:** Form hidden while loading, spinner centered

#### Screenshots

![Create Customer Modal - Empty](../screenshots/customers/create-customer-modal-empty.png)
*Empty create customer form*

![Create Customer Modal - Filled](../screenshots/customers/create-customer-modal-filled.png)
*Create customer form with all fields filled*

![Edit Customer Modal](../screenshots/customers/edit-customer-modal.png)
*Edit existing customer with data pre-filled*

![Customer Modal - Validation](../screenshots/customers/customer-modal-validation.png)
*Required field validation in customer form*

---

### Modal 2: Create/Edit Customer Location

**Type:** Modal (center)  
**Triggered By:** "Create" button on Customer Locations section or "Edit" icon on location card  
**Size:** Large (`lg`)  
**Can be closed by:** X button, Cancel button

![Add Location Modal](../screenshots/customers/add-location-modal.png)

#### Modal Header

**Title:** Dynamic
- **Create**: "Create Customer Location"
- **Edit**: "Edit Customer Location"
- **Detection**: If `customerLocationData.id` exists

**Close Button:** X in top right

#### Modal Body

**Component:** CustomerLocationForm

**Layout:** Two-column responsive form

**Form Fields:**

**Row 1:**

**1. Ship To Name**
- **Label**: "Ship To Name"
- **Required**: Yes (red asterisk *)
- **Type**: Text input
- **Max Length**: 50 characters
- **Placeholder**: "Enter a ship to name"
- **Name**: `shipToName`
- **Validation**: Required
- **Column**: 6
- **Purpose**: Primary identifier for location

**2. Ship To Code**
- **Label**: "Ship To Code"
- **Required**: No
- **Type**: Text input
- **Max Length**: 50 characters
- **Placeholder**: "Enter a ship to code"
- **Name**: `shipToCode`
- **Column**: 6
- **Purpose**: Optional location code/ID

**Row 2:**

**3. Ship To Address**
- **Label**: "Ship To Address"
- **Required**: No
- **Type**: Text input
- **Max Length**: 50 characters
- **Placeholder**: "Enter a ship to address"
- **Name**: `shipToAddres` (note: typo in name attribute)
- **Column**: 6

**4. Ship To City**
- **Label**: "Ship To City"
- **Required**: No
- **Type**: Text input
- **Max Length**: 50 characters
- **Placeholder**: "Enter a ship to city"
- **Name**: `shipToCity`
- **Column**: 6

**Row 3:**

**5. Ship To State**
- **Label**: "Ship To State"
- **Required**: No
- **Type**: Text input
- **Max Length**: 25 characters
- **Placeholder**: "Enter a ship to state"
- **Name**: `shipToState`
- **Column**: 6

**6. Ship To Zip Code**
- **Label**: "Ship To Zip Code"
- **Required**: No
- **Type**: Text input
- **Max Length**: 25 characters
- **Placeholder**: "Enter a ship to zip code"
- **Name**: `shipToZipCode`
- **Column**: 6

**Row 4:**

**7. Ship To Country Code**
- **Label**: "Ship To Country Code"
- **Required**: No
- **Type**: Text input
- **Max Length**: 10 characters
- **Placeholder**: "Enter a ship to country code"
- **Name**: `shipToCountryCode`
- **Column**: 6

**8. Phone**
- **Label**: "Phone"
- **Required**: No
- **Type**: Text input
- **Max Length**: 25 characters
- **Placeholder**: "Enter a phone"
- **Name**: `phone`
- **Column**: 6

#### Modal Footer

**Cancel Button:**
- **Label**: "Cancel"
- **Color**: Secondary
- **Text**: Dark
- **Position**: Left

**Save Button:**
- **Label**: "Save"
- **Color**: Primary
- **Type**: Submit
- **Position**: Right

#### Validation

**Required:**
- Ship To Name only

**Optional:**
- All other fields with max length constraints

#### Success Behavior

**Create:**
1. API: `POST /api/customer-locations`
2. Toast: "Customer location created"
3. Modal closes
4. Customer details refreshes
5. New location appears in grid

**Edit:**
1. API: `PUT /api/customer-locations/{id}`
2. Toast: "Customer location saved"
3. Modal closes
4. Customer details refreshes
5. Updated location reflects changes

#### Loading State

Loader shown while `isLoadingCreateCustomerLocation || isLoadingUpdateCustomerLocation`

#### Screenshots

![Add Location Modal - Empty](../screenshots/customers/add-location-modal.png)
*Empty create location form*

![Add Location Modal - Filled](../screenshots/customers/add-location-modal-filled.png)
*Create location form with data filled*

![Edit Location Modal](../screenshots/customers/edit-location-modal.png)
*Edit existing location*

---

### Modal 3: Location Contacts Manager

**Type:** Modal (center)  
**Triggered By:** "See Contacts" button on location card  
**Size:** Large (`lg`)  
**Can be closed by:** X button, Discard button

![Customer Contacts Modal](../screenshots/customers/customer-contacts-modal.png)

#### Modal Header

**Title:** "Contacts for Location"
**Close Button:** X in top right

#### Modal Body

**Layout:** Table display of contacts

**Table Structure:**

**Headers:**
- Name
- Email
- Phone
- Actions (if contacts exist)

**Rows:**

Each contact shows:
- **Name Column**: Contact name (plain text)
- **Email Column**: Contact email (plain text)
- **Phone Column**: Contact phone number (plain text)
- **Actions Column**: 
  - Delete icon (`trash`)
  - Color: Danger (red)
  - Clickable: Yes
  - Action: Remove contact from list (local state)

**Empty State:**
- **Display**: When no contacts
- **Message**: "No customer contacts"
- **Colspan**: 4 (spans all columns)
- **Styling**: Muted small text

#### Modal Footer

**Layout:** Two groups - left controls and right confirm

**Left Group:**

**Discard Button:**
- **Label**: "Discard"
- **Color**: Secondary-DS
- **Action**: Close modal without saving changes

**Create New Button:**
- **Label**: "Create New"
- **Color**: Primary-DS
- **Margin**: Left 2
- **Action**: Opens NewCustomerLocationContactsModal

**Right Side:**

**Confirm Button:**
- **Label**: "Confirm"
- **Color**: Primary
- **Action**: 
  1. Saves all contacts to location
  2. API: `PUT /api/customer-locations/{id}/contacts`
  3. Shows success toast (via parent onSubmit)
  4. Closes modal
  5. Refreshes customer data

**Loading State:**
- **When**: `isLoadingUpdateCustomerContacts`
- **Display**: `<Loader size="sm" />` replaces Confirm button

#### Workflow

**Adding Contact:**
1. Click "Create New"
2. NewCustomerLocationContactsModal opens
3. Fill contact info (name, email, phone)
4. Click "Save" in sub-modal
5. Contact added to table (local state)
6. Sub-modal closes
7. Repeat for more contacts

**Removing Contact:**
1. Click trash icon on contact row
2. Contact removed immediately (local state)
3. No confirmation needed (not saved yet)

**Saving All Changes:**
1. Click "Confirm"
2. All contacts (added/removed) saved at once
3. Success toast: "Location customer contacts saved"
4. Modal closes
5. Customer details refreshes

**Discarding Changes:**
1. Click "Discard" or X
2. Modal closes
3. No API call
4. All local changes lost

#### Screenshots

![Customer Contacts Modal](../screenshots/customers/customer-contacts-modal.png)
*Contacts manager showing list of contacts*

![Customer Contacts - Empty](../screenshots/customers/customer-contacts-empty.png)
*Empty contacts list with Create New button*

![Customer Contacts - With Data](../screenshots/customers/customer-contacts-filled.png)
*Multiple contacts displayed in table*

---

### Modal 4: New Contact (Sub-Modal)

**Type:** Modal (center)  
**Triggered By:** "Create New" button in Location Contacts Manager  
**Size:** Large (`lg`)  
**Can be closed by:** X button, Discard button

![Add Contact Modal](../screenshots/customers/add-contact-modal.png)

#### Modal Header

**Title:** "Add Contact for Location"
**Close Button:** X

#### Modal Body

**Layout:** Single-row table with input fields

**Table Headers:**
- Name
- Email
- Phone

**Table Row:**

Three inline input fields:

**1. Name Input**
- **Type**: Text input
- **Class**: `border-0` (borderless for inline look)
- **Required**: Yes
- **Placeholder**: "Enter a name"
- **Validation**: HTML5 required

**2. Email Input**
- **Type**: Email input
- **Class**: `border-0`
- **Required**: Yes
- **Placeholder**: "Enter an email"
- **Validation**: HTML5 email + required
- **Processing**: Trimmed on input

**3. Phone Input**
- **Type**: Text input
- **Class**: `border-0`
- **Required**: Yes
- **Placeholder**: "Enter a phone"
- **Validation**: HTML5 required

#### Modal Footer

**Discard Button:**
- **Label**: "Discard"
- **Color**: Secondary
- **Action**: Close sub-modal without adding contact

**Save Button:**
- **Label**: "Save"
- **Color**: Primary
- **Type**: Submit
- **Action**: 
  1. Validates all three fields
  2. Passes contact object to parent modal
  3. Parent adds to local contacts array
  4. Closes sub-modal
  5. Returns to contacts list

#### Validation

All three fields required:
- Name: Text, any format
- Email: Valid email format
- Phone: Text, any format (no strict format enforced)

#### Success Behavior

1. Form submits
2. Contact object created: `{ name, email, phone }`
3. Passed to parent via `onSubmit` callback
4. Parent adds `customerLocationId` to object
5. Contact appears in parent modal table
6. Sub-modal closes
7. User can add another or confirm all

#### Screenshots

![Add Contact Modal](../screenshots/customers/add-contact-modal.png)
*New contact form with inline table inputs*

![Add Contact - Validation](../screenshots/customers/add-contact-validation.png)
*Required field validation*

---

### Modal 5: Create/Edit Asset

**Type:** Modal (center)  
**Triggered By:** "Create" button on assets list, "Add Child" button on asset row, "Edit" button on asset details  
**Size:** Extra Large (`xl`)  
**Can be closed by:** X button, Discard button

![Add Asset Modal](../screenshots/customers/add-asset-modal.png)

#### Modal Header

**Title:** Dynamic
- **Create**: "Add Asset"
- **Edit**: "Edit Asset"
- **Detection**: If `asset.id` exists

**Close Button:** X

#### Modal Body

**Layout:** Multi-table horizontal layout for complex data entry

**Loading State:**
- **When**: `isLoadingCreateAsset || isLoadingUpdateAsset`
- **Display**: Centered loader with spinner

**Table 1: Selection Fields**

**Table Styling:**
- **Striped**: Yes
- **Fixed Layout**: Yes (equal column widths)
- **Full Width**: Col-12

**Headers Row (Gray Background):**

Columns shown conditionally:
1. **Customer** - Only if `!defaultCustomerLocationId`
2. **Customer Location** - Only if `!defaultCustomerLocationId`
3. **Type** - Always shown
4. **Parent** - Always shown

**Data Row:**

**Customer Select** (if shown):
- **Type**: Searchable select (react-select)
- **Placeholder**: "Search customers"
- **Test ID**: `customer-select`
- **Required**: Yes (red asterisk in header)
- **Options**: Customer list with default customer + searched results
- **Search**: Debounced, fetches customers as user types
- **Loading**: Shows spinner when searching
- **Disabled**: Yes if `asset.assetParentId` exists (inherited from parent)
- **Auto-select**: Default customer if none selected
- **No Options**: "No customers found"
- **On Change**: 
  - Updates `customerId`
  - Clears `customerLocationId` (must re-select location)
  - Updates `lastSelectedCustomer` state

**Customer Location Select** (if shown):
- **Type**: Select dropdown
- **Placeholder**: "Search customer locations"
- **Test ID**: `customer-location-select`
- **Required**: Yes (red asterisk in header)
- **Options**: Locations of selected customer
- **Format**: Full address via `sharedHelper.getAddress()`
- **Loading**: Shows spinner when loading customer data
- **Disabled**: Yes if `asset.assetParentId` exists
- **Auto-select**: Default location of customer
- **No Options**: "No locations found"

**Type Select:**
- **Type**: Select dropdown
- **ID**: `assetTypeSelect`
- **Placeholder**: "Select the type"
- **Required**: Yes (red asterisk in header)
- **Clearable**: Yes
- **Options**: All asset types (name)
- **On Change**: 
  - Updates `assetTypeId` and `assetType` object
  - Clears `dynamicAttributes` (reloaded for new type)
  - If parent exists: Resets touched fields for auto-population
- **On Clear**: 
  - Sets `assetTypeId` and `assetType` to null
  - Clears dynamic attributes

**Parent Select:**
- **Type**: Select dropdown
- **ID**: `assetParentSelect`
- **Placeholder**: "Select the parent"
- **Required**: No
- **Clearable**: Yes
- **Options**: All assets except current (prevents circular reference)
- **Format**: `{name} / {modelNumber} / {serialNumber}`
- **Filter**: Excludes current asset by ID
- **On Select**: 
  - Updates `assetParentId` and `assetParent` object
  - Inherits `customerId` and `customerLocationId` from parent
  - Resets field touched states for auto-population
- **On Clear**: 
  - Clears `assetParentId` and `assetParent`
  - Resets touched states
  - Clears auto-populated fields (if not manually edited)

**Table 2: Basic Information**

**Visibility:** Only shown if `asset.assetTypeId` is selected

**Headers Row:**
- Name/ID (required)
- Model # (required)
- Serial # (required)
- Manufacturer (required)

**Data Row:**

**Name/ID Input:**
- **Type**: Text input
- **Class**: `border-0` (borderless inline)
- **Required**: Yes
- **Placeholder**: "Enter a name"
- **Max Length**: 50
- **Auto-populate**: 
  - **When**: Parent selected and type selected (new asset)
  - **Value**: Asset type name
  - **Clears**: When parent removed and not manually edited
- **On Change**: Marks field as "touched by user" (prevents auto-clear)

**Model # Input:**
- **Type**: Text input
- **Required**: Yes
- **Placeholder**: "Enter a model #"
- **Max Length**: 50
- **Auto-populate**: 
  - **When**: Parent selected (new asset)
  - **Value**: "N/A"
  - **Clears**: When parent removed and not manually edited
- **On Change**: Marks as touched

**Serial # Input:**
- **Type**: Text input
- **Required**: Yes
- **Placeholder**: "Enter a serial #"
- **Max Length**: 50
- **Auto-populate**: 
  - **When**: Parent selected (new asset)
  - **Value**: "N/A"
  - **Clears**: When parent removed and not manually edited
- **On Change**: Marks as touched

**Manufacturer Input:**
- **Type**: Text input
- **Required**: Yes
- **Placeholder**: "Enter a manufacturer"
- **Max Length**: 50
- **Auto-populate**: 
  - **When**: Parent selected (new asset)
  - **Value**: "N/A"
  - **Clears**: When parent removed and not manually edited
- **On Change**: Marks as touched

**Table 3: Dynamic Attributes**

**Visibility:** Only if `asset.assetTypeId` selected AND `dynamicAttributes.length > 0`

**Layout:** Scrollable horizontal table for many attributes

**Headers Row:**
- One column per dynamic attribute
- Header content: `<DynamicAttributeLabel />` component
- **Min Width**: 200px per column
- **Label**: Centered
- **Shows**: Label, required indicator, help text

**Data Row:**
- One cell per dynamic attribute
- **Input**: `<DynamicAttributeInput />` component
- **Class**: `form-control border-0`
- **Type**: Based on attribute definition
  - Text: Text input
  - Number: Number input
  - Date: Date picker
  - Boolean: Checkbox
  - Select: Dropdown
- **Default Values**: Applied on type selection (from attribute config)
- **Required**: Based on attribute definition
- **Validation**: Type-specific validation

#### Modal Footer

**Layout:** Space-between

**Discard Button:**
- **Label**: "Discard"
- **Color**: Secondary
- **Position**: Left
- **Action**: Close without saving

**Save Button:**
- **Label**: "Save"
- **Color**: Primary
- **Margin**: Left 2
- **Type**: Submit
- **Position**: Right
- **Action**: 
  1. Validates all required fields
  2. Calls create or update API
  3. Shows success toast
  4. Closes modal
  5. Refreshes asset list or details

#### Validation

**Required Fields:**
- Type (always)
- Customer (if not inherited)
- Customer Location (if not inherited)
- Name/ID
- Model #
- Serial #
- Manufacturer
- Any required dynamic attributes

**Constraints:**
- Max lengths on all text fields
- Type-specific validation on dynamic attributes
- Customer location must belong to selected customer

#### Success Behavior

**Create:**
1. API: `POST /api/assets`
2. Toast: "Asset created"
3. Modal closes
4. List/details refreshes

**Update:**
1. API: `PUT /api/assets/{id}`
2. Toast: "Asset saved"
3. Modal closes
4. Details refreshes

#### Special Behaviors

**Auto-population Logic:**

When parent asset is selected:
1. Customer and location inherited (fields disabled)
2. If type also selected:
   - Name auto-fills with type name
   - Model, Serial, Manufacturer auto-fill with "N/A"
3. Auto-populated values clear if parent removed (unless user edited)
4. Tracked via `fieldsTouchedByUser` state object

**Default Customer/Location:**

For new assets without parent:
1. Default customer auto-selected (if exists)
2. Default location of customer auto-selected
3. User can change both

#### Screenshots

![Add Asset Modal - Step 1](../screenshots/customers/add-asset-modal.png)
*Asset modal showing customer and type selection*

![Add Asset Modal - Step 2](../screenshots/customers/add-asset-modal-basic-info.png)
*Basic information fields after type selected*

![Add Asset Modal - Step 3](../screenshots/customers/add-asset-modal-dynamic-attrs.png)
*Dynamic attributes for selected asset type*

![Add Asset - With Parent](../screenshots/customers/add-asset-with-parent.png)
*Creating child asset with parent selected (customer/location disabled)*

![Edit Asset Modal](../screenshots/customers/edit-asset-modal.png)
*Editing existing asset*

---

### Modal 6: Create/Edit Asset Type

**Type:** Modal (center)  
**Triggered By:** "Create" button on asset types list or "Edit" button on type row  
**Size:** Medium (`md`)  
**Can be closed by:** X button, Cancel button

![Asset Type Modal](../screenshots/customers/asset-type-modal.png)

#### Modal Header

**Title:** Dynamic
- **Create**: "Add Asset Type"
- **Edit**: "Edit Asset Type"

**Close Button:** X

#### Modal Body

**Form Test ID:** `asset-type-form`

**Fields:**

**1. Name Field**
- **Label**: "Name"
- **Required**: Yes (red asterisk)
- **Type**: Text input
- **Class**: `form-control-redesign`
- **Max Length**: 50 characters
- **Placeholder**: "Enter a name"
- **Validation**: Required

**2. Default Inspection Template** (conditional)
- **Shown**: Only if `inspections` package enabled
- **Label**: "Default Inspection Template"
- **Required**: No
- **Type**: SelectAdvance (advanced searchable select)
- **Component**: Custom select with search
- **Placeholder**: "Select an inspection template"
- **Options**: Published inspection templates only
- **Filter**: `status === "PUBLISHED"`
- **Format**: `{ value: template.id, label: template.name }`
- **Loading**: Shows spinner while fetching templates
- **No Options**: "No published templates found"
- **Clearable**: Yes (can remove selection)
- **On Select**: Updates `defaultInspectionTemplateId`
- **On Clear**: Sets `defaultInspectionTemplateId` to empty string

**3. Default Service Template** (conditional)
- **Shown**: Only if `services` package enabled
- **Label**: "Default Service Template"
- **Required**: No
- **Type**: SelectAdvance
- **Placeholder**: "Select an service template"
- **Options**: Published service templates only
- **Filter**: `status === "PUBLISHED"`
- **Loading**: Shows spinner while fetching
- **No Options**: "No published templates found"
- **Clearable**: Yes
- **On Select**: Updates `defaultServiceTemplateId`

**4. Image Section**
- **Position**: Below form fields
- **Min Width**: 200px

**Image Display:**
- **With Image**: 
  - Component: ImagesViewer
  - Mode: Preview
  - Size: 200x200px
  - Actions: Hidden
  - Caption: Hidden
  - Clickable: Opens full-size modal
- **Without Image**: 
  - Placeholder image shown
  - Size: 200px wide, auto height
  - Rounded corners
  - Not clickable

**Edit Image Button:**
- **Icon**: `edit-2`
- **Position**: Absolute (top: 5px, right: 5px)
- **Color**: White background, primary text
- **Shape**: Circle
- **Size**: Small
- **Test ID**: `edit-image-button`
- **Action**: Opens UploadPhotosModal

#### Modal Footer

**Layout:** Complex with conditional buttons

**Loading State:**
- **When**: `isLoadingCreateAssetType || isLoadingUpdateAssetType`
- **Display**: `<Loader size="sm" />` in min-width container
- **Hides**: All buttons

**Normal State (Left to Right):**

**Cancel Button:**
- **Label**: "Cancel"
- **Color**: Secondary
- **Position**: Leftmost
- **Action**: Close without saving

**Dynamic Attributes Button:** (Edit mode only)
- **Label**: "Dynamic Attributes"
- **Color**: Secondary
- **Margin**: Left 2
- **Visible**: Only when `assetType.id` exists (editing)
- **Action**: Opens DynamicAttributesModal
- **Purpose**: Configure custom fields for this asset type

**Confirm Button:**
- **Label**: "Confirm"
- **Color**: Primary
- **Margin**: Left 2
- **Type**: Submit
- **Position**: Rightmost
- **Action**: Save asset type

#### Validation

**Required:**
- Name (text, max 50 chars)

**Optional:**
- Default Inspection Template
- Default Service Template
- Image

#### Success Behavior

**Create:**
1. API: `POST /api/asset-types`
2. Payload: `{ name, imageUrl, dynamicAttributes, defaultInspectionTemplateId?, defaultServiceTemplateId? }`
3. Toast: "Asset type created"
4. Modal closes
5. List refreshes

**Update:**
1. API: `PUT /api/asset-types/{id}`
2. Same payload structure
3. Toast: "Asset type saved"
4. Modal closes
5. List refreshes

#### Sub-Modals

**UploadPhotosModal:**
- **Title**: "Update asset type image"
- **On Submit**: Updates `imageUrl` state, closes modal
- **Allows**: Single image upload

**ImagesViewerModal:**
- **Title**: "Asset type image"
- **Content**: Full-size image view
- **Trigger**: Click on image

**DynamicAttributesModal:**
- **Purpose**: Create/edit/delete custom fields for asset type
- **Entity**: `assetType`
- **Entity ID**: Current asset type ID
- **On Submit**: Updates local `dynamicAttributes` array
- **On Delete**: Removes attribute from array
- **On Close**: Optionally refreshes data if changes made

#### Screenshots

![Asset Type Modal - Create](../screenshots/customers/asset-type-modal.png)
*Create new asset type with name and template selection*

![Asset Type Modal - With Image](../screenshots/customers/asset-type-modal-with-image.png)
*Asset type with image uploaded*

![Asset Type Modal - Edit](../screenshots/customers/asset-type-modal-edit.png)
*Edit asset type showing Dynamic Attributes button*

![Asset Type - Image Upload](../screenshots/customers/asset-type-image-upload.png)
*Upload image modal for asset type*

---

### Modal 7: Dynamic Attributes Configuration

**Type:** Modal (from shared components)  
**Triggered By:** "Dynamic Attributes" button in Asset Type modal (edit mode)  
**Size:** Large  
**Can be closed by:** X button, close action

#### Purpose

Configure custom fields that will be available for all assets of this type. These fields auto-populate on the asset creation modal.

#### Features

- **Create Attribute**: Add new custom field
- **Edit Attribute**: Modify existing field definition
- **Delete Attribute**: Remove field (if not in use)
- **Field Types**: Text, Number, Date, Boolean, Select
- **Properties**:
  - Key (unique identifier)
  - Label (display name)
  - Type (data type)
  - Required (yes/no)
  - Default Value
  - Options (for select type)
  - Help Text
  - Validation Rules

#### Workflow

1. Click "Dynamic Attributes" in Asset Type modal
2. Modal opens showing current attributes
3. Create/edit/delete attributes as needed
4. Changes saved to local state
5. Click close (with or without saving flag)
6. If changes made: Parent refreshes to show updated attributes
7. Return to Asset Type modal

#### Impact

When dynamic attributes are defined for an asset type:
1. Asset creation modal shows third table with these fields
2. Each attribute renders appropriate input type
3. Default values auto-fill
4. Required attributes validated
5. Asset details page shows "Custom Fields" section
6. Values displayed with proper formatting

---

## Settings

### Settings Page: Asset Types

**URL:** `/asset-types`  
**Access:** Super Admin only (`IS_SUPER_ADMIN_USER`)  
**Location:** Settings → Assets → Asset Types  
**Purpose:** System-wide configuration of asset categories

#### Settings Available

**Asset Type Registry:**

Each asset type can configure:

**1. Type Name**
- **Type**: Text
- **Required**: Yes
- **Max Length**: 50 characters
- **Effect**: Categorizes assets, shown in asset lists and details
- **Unique**: Should be unique per type

**2. Type Image**
- **Type**: Image upload
- **Required**: No
- **Effect**: Visual identifier for asset type
- **Display**: Shown in asset type list, can be shown on assets

**3. Default Inspection Template**
- **Type**: Template selection (dropdown)
- **Required**: No
- **Available When**: Inspections package enabled
- **Options**: Published inspection templates only
- **Effect**: 
  - When asset of this type is created, default template can be auto-assigned
  - Standardizes inspection procedures for asset category
- **Dependencies**: Inspections package

**4. Default Service Template**
- **Type**: Template selection (dropdown)
- **Required**: No
- **Available When**: Services package enabled
- **Options**: Published service templates only
- **Effect**: 
  - Auto-assigns service template to assets of this type
  - Standardizes service procedures
- **Dependencies**: Services package

**5. Dynamic Attributes**
- **Type**: Complex attribute configuration
- **Required**: No
- **Available**: Edit mode only (existing asset types)
- **Effect**: 
  - Defines custom fields for all assets of this type
  - Fields appear in asset creation/edit modals
  - Values stored in `asset.dynamicAttributes` JSON object
  - Displayed in asset details page
- **Configuration**: Via DynamicAttributesModal

**6. Default Type Flag**
- **Type**: Boolean
- **Display**: Badge in asset types list
- **Effect**: Marks one type as system default
- **Usage**: May be used for default selection in certain contexts

#### How to Configure

**Create New Asset Type:**

1. Navigate to Settings → Assets → Asset Types
2. Click "Create" button
3. Fill in:
   - Name (required)
   - Default Inspection Template (if needed)
   - Default Service Template (if needed)
   - Upload image (optional)
4. Click "Confirm"
5. Asset type created and available immediately

**Edit Existing Asset Type:**

1. Find asset type in list
2. Click "Edit" button
3. Modify fields as needed
4. Click "Dynamic Attributes" to add custom fields
5. Click "Confirm" to save
6. Changes apply to future asset creation/editing

**Configure Dynamic Attributes:**

1. Edit existing asset type
2. Click "Dynamic Attributes" button in footer
3. In Dynamic Attributes modal:
   - Click "Create" to add new attribute
   - Fill attribute properties:
     - Key (e.g., "serial_prefix")
     - Label (e.g., "Serial Number Prefix")
     - Type (Text, Number, Date, Boolean, Select)
     - Required (yes/no)
     - Default Value (optional)
   - Click "Save" on attribute
4. Repeat for all needed attributes
5. Close Dynamic Attributes modal
6. Click "Confirm" on Asset Type modal
7. Custom fields now appear when creating assets of this type

**Delete Asset Type:**

1. Find asset type in list
2. Click "Delete" button
3. Confirm deletion
4. **Warning**: Cannot delete if assets exist with this type
5. Consider marking as inactive instead

#### Required Restart

No restart required - changes take effect immediately.

#### Dependencies

- Inspections package: Enables inspection template selection
- Services package: Enables service template selection
- Asset types required before creating assets (enforced in asset modal)

---

## Common Workflows

### Workflow 1: Create New Customer with Location

**Purpose:** Onboard a new customer into the system with their primary service location  
**Prerequisites:** User has Admin or Super Admin access  
**Roles:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`

**Steps:**

**1. Create Customer Record**
- Navigate to Customers → All Customers
- Click "Create" button (top right)
- Result: Customer modal opens

**2. Fill Customer Information**
- Enter required fields:
  - Customer Name: Full business name
  - Customer #: Unique identifier (account number, etc.)
  - Status: Active (default)
- Fill optional fields:
  - Address: Street address of main office
  - City, State, Zip Code: Location details
  - Country: Country code
  - Telephone: Main phone number
  - Email: Main contact email
  - Fax: Fax number (if applicable)
- Click "Save"
- Result: Customer created, modal closes, success toast shown

**3. Open Customer Details**
- Locate new customer in list (may need to refresh or search)
- Click "View Details" button
- Result: Navigate to Customer Details page

**4. Create Primary Location**
- In Customer Locations section
- Click "Create" button
- Result: Location modal opens

**5. Fill Location Information**
- Required field:
  - Ship To Name: Location identifier (e.g., "Main Office", "Warehouse A")
- Optional fields:
  - Ship To Code: Internal location code
  - Ship To Address: Full street address
  - Ship To City, State, Zip Code, Country Code
  - Phone: Location-specific phone
- Click "Save"
- Result: Location created, appears in locations grid, marked as default

**6. Add Location Contacts (Optional)**
- Click "See Contacts" on the location card
- Result: Contacts modal opens (empty)
- Click "Create New"
- Fill contact fields:
  - Name: Contact person name
  - Email: Contact email
  - Phone: Contact phone
- Click "Save"
- Result: Contact added to list
- Repeat for additional contacts
- Click "Confirm" when done
- Result: All contacts saved to location

**Expected Outcome:**
- Customer created with complete information
- Primary location established with address
- Contacts configured for easy communication
- Customer ready for work order assignment
- Customer visible in all customers list
- Location available in work order location selection

**Common Issues:**

**Issue: Customer # already exists**
- **Solution**: Use a different, unique customer number

**Issue: Can't save customer - validation error**
- **Solution**: Ensure Name, Customer #, and Status are filled

**Issue: Location doesn't show as default**
- **Solution**: First location is automatically default; additional locations need explicit default flag

---

### Workflow 2: Register Customer Asset

**Purpose:** Add equipment/machinery to a customer location for tracking and work order assignment  
**Prerequisites:** Customer and location already exist  
**Roles:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`

**Steps:**

**1. Navigate to Customer Location**
- Option A: 
  - Go to Customers → All Customers
  - Find and open customer
  - Click "See Assets" on desired location card
- Option B:
  - Go to Customers → Assets
  - Will create asset, can select customer/location in modal
- Result: Assets page or modal opens

**2. Open Asset Creation Modal**
- Click "Create" button
- Result: Asset modal opens (extra-large size)

**3. Select Customer & Location** (if not pre-filled)
- In first table row:
  - Customer: Search and select customer
  - Customer Location: Select location from dropdown
- Result: Customer and location locked in

**4. Select Asset Type**
- Type: Search and select asset type (e.g., "HVAC Unit", "Chiller", "Elevator")
- Result: Second table appears with basic info fields

**5. Fill Basic Asset Information**
- Required fields:
  - Name/ID: Unique identifier for asset (e.g., "Chiller Unit A")
  - Model #: Equipment model number
  - Serial #: Manufacturer serial number
  - Manufacturer: Equipment manufacturer name
- All fields required
- Max 50 characters each

**6. Fill Dynamic Attributes** (if configured for asset type)
- Third table appears if asset type has custom fields
- Fill all shown fields:
  - Examples: Capacity, Installation Date, Warranty Expiration, etc.
  - Required attributes marked with asterisk
  - Default values may be pre-filled
- Result: All asset-specific data captured

**7. Optional: Set Parent Asset**
- If this is a component of larger equipment:
  - Parent: Select parent asset from dropdown
  - Result: Customer/location inherited from parent (fields disabled)
  - Example: "Compressor A" parent is "Chiller Unit A"

**8. Save Asset**
- Click "Save" button
- Result: 
  - Asset created
  - Success toast: "Asset created"
  - Modal closes
  - Asset appears in list
  - Available for work order assignment

**Expected Outcome:**
- Asset registered in system
- Linked to customer and location
- Type categorization applied
- Custom fields captured
- Asset appears in:
  - Customer → Location → See Assets
  - Customers → Assets (global list)
  - Work order asset selection dropdowns
- Asset detail page accessible
- Ready for inspection/service work orders

**Common Issues:**

**Issue: Can't save - all fields required**
- **Solution**: Fill Name/ID, Model #, Serial #, and Manufacturer (all required)

**Issue: Asset type not available**
- **Solution**: Super Admin must create asset type in Settings first

**Issue: Customer/location disabled (can't change)**
- **Solution**: Parent asset is selected, remove parent to select different customer/location

**Issue: Dynamic attributes not showing**
- **Solution**: Select asset type first, then configure dynamic attributes for that type in Settings

---

### Workflow 3: Create Work Order for Customer Asset

**Purpose:** Schedule service or inspection work for customer equipment  
**Prerequisites:** Customer, location, and asset already exist  
**Roles:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`

**Steps:**

**1. Navigate to Work Orders Module**
- Click Work Orders in sidebar
- Click "Create" or "New Work Order"
- Result: Work order creation modal/page opens

**2. Select Customer**
- In customer field, search and select customer
- Result: Customer locations become available

**3. Select Location**
- In location field, select customer location
- Result: Assets at that location become available

**4. Select Asset** (Optional but Recommended)
- In asset field, select specific asset
- Result: Work order linked to asset
- Benefit: Asset work history tracked

**5. Fill Work Order Details**
- Title, description, scheduled date, assignee, etc.
- Configure per work orders module

**6. Save Work Order**
- Click "Save" or "Create"
- Result: Work order created

**Expected Outcome:**
- Work order created and assigned
- Linked to customer, location, and asset
- Visible in:
  - Work Orders list
  - Customer details page (work orders section)
  - Filtered by selected location
- Technician can access asset details from work order
- Work order history tracked on asset and customer

**Common Issues:**

**Issue: Asset not appearing in dropdown**
- **Solution**: Ensure asset is assigned to selected location

**Issue: Can't see work orders on customer details**
- **Solution**: Work orders module must be enabled

---

### Workflow 4: Add Child Asset to Parent Equipment

**Purpose:** Create hierarchical asset relationships (e.g., compressor within chiller)  
**Prerequisites:** Parent asset already exists  
**Roles:** `IS_SUPER_ADMIN_USER`, `IS_ADMIN_USER`

**Steps:**

**1. Navigate to Parent Asset**
- Option A: 
  - Go to Customers → Assets
  - Find parent asset in list
  - Click row to open details
- Option B:
  - Go to Customer → Location → See Assets
  - Click parent asset
- Result: Asset details page opens

**2. Add Child Asset**
- Scroll to "Child Assets" section at bottom
- Click "Create" button
- Result: Asset modal opens with parent pre-selected

**3. Notice Pre-filled Fields**
- Customer: Inherited from parent (disabled)
- Customer Location: Inherited from parent (disabled)
- Parent: Pre-selected (current asset)
- Note: These cannot be changed for child assets

**4. Select Asset Type**
- Choose appropriate type for child component
- Result: Basic info fields appear
- Auto-population may occur:
  - Name: Type name
  - Model, Serial, Manufacturer: "N/A" (can override)

**5. Fill/Override Basic Information**
- Override auto-populated fields if needed:
  - Name/ID: Specific identifier for this child
  - Model #: Actual model if different from "N/A"
  - Serial #: Actual serial if available
  - Manufacturer: Actual manufacturer

**6. Fill Dynamic Attributes**
- If asset type has custom fields, fill them
- May be different attributes than parent type

**7. Save Child Asset**
- Click "Save"
- Result: 
  - Child asset created
  - Appears in Child Assets table
  - Linked to parent asset
  - Shares customer/location with parent

**8. View Hierarchy**
- Parent asset details page shows child in table
- Child asset details page shows parent reference
- Result: Equipment hierarchy established

**Expected Outcome:**
- Child asset created and linked to parent
- Customer/location inherited automatically
- Work orders can target parent or child specifically
- Hierarchy visible in asset details
- Example: "Chiller A" → "Compressor 1", "Compressor 2", "Evaporator"

**Common Issues:**

**Issue: Can't change customer/location for child**
- **Solution**: This is by design - children inherit parent's customer/location

**Issue: Want to move child to different parent**
- **Solution**: Edit child asset, clear parent, select new parent

**Issue: Child not appearing in parent's table**
- **Solution**: Refresh asset details page

---

### Workflow 5: Configure Asset Type with Custom Fields

**Purpose:** Set up a new asset category with specialized data fields  
**Prerequisites:** Super Admin access  
**Roles:** `IS_SUPER_ADMIN_USER` only

**Steps:**

**1. Navigate to Asset Types Settings**
- Go to Settings (sidebar)
- Expand "Assets" category
- Click "Asset Types"
- Result: Asset types list page opens

**2. Create Asset Type**
- Click "Create" button
- Result: Asset Type modal opens

**3. Fill Basic Information**
- Name: Enter type name (e.g., "HVAC Unit", "Fire Suppression System")
- Required: Yes
- Max 50 characters

**4. Upload Image** (Optional)
- Click edit icon on placeholder image
- Select image file
- Result: Image uploaded, preview shown
- Benefit: Visual identification in lists

**5. Select Default Templates** (Optional)
- If Inspections enabled:
  - Default Inspection Template: Select template
  - Result: Auto-assigns to new assets of this type
- If Services enabled:
  - Default Service Template: Select template
  - Result: Auto-assigns to new assets of this type

**6. Save Asset Type**
- Click "Confirm"
- Result: Asset type created, modal closes

**7. Reopen to Configure Dynamic Attributes**
- Find newly created type in list
- Click "Edit"
- Result: Modal reopens

**8. Open Dynamic Attributes Configuration**
- Click "Dynamic Attributes" button (only visible in edit mode)
- Result: Dynamic Attributes modal opens

**9. Create First Custom Field**
- Click "Create" or "Add Attribute"
- Fill attribute properties:
  - **Key**: Unique identifier (e.g., "cooling_capacity")
    - Use snake_case
    - No spaces or special characters
  - **Label**: Display name (e.g., "Cooling Capacity")
  - **Type**: Select data type:
    - Text: Free-form text input
    - Number: Numeric input
    - Date: Date picker
    - Boolean: Yes/No checkbox
    - Select: Dropdown with predefined options
  - **Required**: Check if field must be filled
  - **Default Value**: Optional pre-fill value
  - **Help Text**: Optional guidance for users
  - **Options** (if Select type): 
    - Add each option (value and label)
- Click "Save" on attribute
- Result: Attribute added to list

**10. Add More Attributes**
- Repeat step 9 for each custom field needed
- Examples for HVAC:
  - Cooling Capacity (Number, required)
  - Heating Capacity (Number, required)
  - Refrigerant Type (Select, required)
  - Installation Date (Date)
  - Warranty Expiration (Date)
  - Maintenance Frequency (Number, default: 90 days)

**11. Save All Attributes**
- Review all attributes in list
- Edit or delete as needed
- Close Dynamic Attributes modal
- Result: Returns to Asset Type modal

**12. Confirm Asset Type**
- Click "Confirm"
- Result: Asset type saved with custom fields

**13. Test in Asset Creation**
- Go to Customers → Assets
- Click "Create"
- Select the new asset type
- Result: 
  - Third table appears
  - Shows all configured custom fields
  - Default values pre-filled
  - Required fields marked

**Expected Outcome:**
- Asset type configured with custom data requirements
- Custom fields appear automatically when creating assets
- Data captured consistently across all assets of this type
- Asset details page shows custom fields in separate section
- Standardized data collection for asset category
- Better reporting and filtering capabilities

**Common Issues:**

**Issue: Dynamic Attributes button not visible**
- **Solution**: Must save asset type first (edit mode only)

**Issue: Attribute not showing in asset creation**
- **Solution**: Refresh page, ensure asset type selection is correct

**Issue: Can't delete attribute**
- **Solution**: May be in use by existing assets, mark as inactive instead

**Issue: Wrong data type selected**
- **Solution**: Delete attribute and recreate (changing type not supported)

---

## Integration Points

### Connections to Other Modules

**Work Orders Module:**
- **Integration Type**: Bi-directional data link
- **Connection Point**: 
  - Work orders can be assigned to customers, locations, and assets
  - Customer details page embeds work orders list
- **Data Shared**: 
  - Customer ID, Location ID, Asset ID
  - Work order counts (shown in customer list)
  - Work order history (shown in customer details)
- **User Action**: 
  - Select location on customer details to filter work orders
  - Click work order to view details (navigates to work orders module)
  - Create work order from customer context (customer pre-selected)

**Inspections Module** (if enabled):
- **Integration Type**: Template assignment
- **Connection Point**: Asset types can have default inspection templates
- **Data Shared**: 
  - Inspection template ID
  - Template assignment to assets
- **User Action**: 
  - Configure default inspection template in asset type settings
  - When asset is created, inspection template auto-assigned
  - Inspections can reference customer assets

**Services Module** (if enabled):
- **Integration Type**: Template assignment
- **Connection Point**: Asset types can have default service templates
- **Data Shared**: 
  - Service template ID
  - Template assignment to assets
- **User Action**: 
  - Configure default service template in asset type settings
  - Service work orders automatically use appropriate template
  - Service history tracked per asset

**Technician/Scheduling** (implied):
- **Integration Type**: Reference data
- **Connection Point**: Work orders link to customer assets
- **Data Shared**: 
  - Customer location addresses
  - Asset details and specifications
  - Custom field data (dynamic attributes)
- **User Action**: 
  - Technicians access asset info through assigned work orders
  - View asset specifications and history
  - Update asset information after service

**Reporting/Analytics** (implied):
- **Integration Type**: Data source
- **Connection Point**: Customer and asset data feeds reports
- **Data Shared**: 
  - Customer demographics
  - Asset inventory
  - Work order volumes
  - Service history
- **User Action**: 
  - Generate customer reports
  - Asset utilization reports
  - Service frequency analysis

---

## Tips & Best Practices

### 👍 Do This

**Customer Management:**
- ✅ Use unique, meaningful customer numbers (account IDs, not sequential)
- ✅ Keep customer information updated (especially contact details)
- ✅ Mark customers inactive instead of deleting (preserves history)
- ✅ Use consistent naming conventions for customers (legal business names)
- ✅ Fill in all address fields for accurate location-based features

**Location Management:**
- ✅ Create separate locations for each service site (not just main office)
- ✅ Use descriptive location names ("Warehouse A", "Main Office", "Plant 2")
- ✅ Always set one location as default (typically main office or billing address)
- ✅ Add contacts for each location (on-site personnel, not just main office)
- ✅ Include full addresses for accurate mapping and routing

**Asset Management:**
- ✅ Register all customer equipment, even small items (builds complete inventory)
- ✅ Use serial numbers exactly as printed on equipment (for warranty lookups)
- ✅ Choose specific asset types (not generic "Equipment" type)
- ✅ Fill in all dynamic attributes (critical for maintenance scheduling)
- ✅ Upload asset photos (helps technicians identify equipment)
- ✅ Use parent-child relationships for complex equipment hierarchies
- ✅ Link work orders to specific assets (not just customer/location)

**Asset Type Configuration:**
- ✅ Create specific asset types for different equipment categories
- ✅ Configure dynamic attributes before creating many assets of that type
- ✅ Use default values for common fields (saves data entry time)
- ✅ Assign default inspection/service templates to standardize procedures
- ✅ Use meaningful key names in snake_case (e.g., "refrigerant_type")
- ✅ Provide help text for complex or technical fields

**Data Quality:**
- ✅ Use search before creating (avoid duplicates)
- ✅ Export data regularly for backups
- ✅ Review and clean up inactive customers periodically
- ✅ Standardize data entry (e.g., state abbreviations, phone formats)

### 👎 Avoid This

**Customer Management:**
- ❌ Don't delete customers with work order history (mark inactive instead)
- ❌ Don't use generic names like "Test Customer" or "ABC Company"
- ❌ Don't skip customer # field (use account ID or other unique identifier)
- ❌ Don't leave status blank (always set Active or Inactive)

**Location Management:**
- ❌ Don't create one "Main" location for multi-site customers
- ❌ Don't skip location addresses (needed for technician routing)
- ❌ Don't delete locations with assigned assets or work orders
- ❌ Don't forget to update location contacts when personnel changes

**Asset Management:**
- ❌ Don't skip model and serial numbers (critical for parts ordering)
- ❌ Don't use "N/A" unless truly not applicable (not as lazy data entry)
- ❌ Don't create assets without selecting proper type
- ❌ Don't ignore dynamic attributes (may be required for compliance)
- ❌ Don't create duplicate assets (search first)
- ❌ Don't delete assets with work order history

**Asset Type Configuration:**
- ❌ Don't create one generic "Equipment" type for everything
- ❌ Don't add dynamic attributes after creating hundreds of assets (retrofit is tedious)
- ❌ Don't use unclear attribute labels (users won't understand)
- ❌ Don't make non-critical fields required (frustrates users)
- ❌ Don't use spaces or special characters in attribute keys

**Workflow:**
- ❌ Don't create work orders without linking to assets (loses tracking)
- ❌ Don't change customer/location of assets with work order history
- ❌ Don't bypass required fields (causes data quality issues)

### 💡 Pro Tips

**Efficiency:**
- 💡 Use keyboard shortcuts: Tab through form fields, Enter to submit
- 💡 Use browser back button after viewing customer details (returns to list)
- 💡 Export customer list to Excel for bulk analysis or external sharing
- 💡 Use search debouncing (wait 900ms after typing to let search trigger)
- 💡 Bookmark frequently accessed customers in browser

**Data Entry:**
- 💡 Copy-paste serial numbers from photos or documents (avoid typos)
- 💡 Pre-configure asset types with defaults to speed up asset creation
- 💡 Use parent asset feature to batch-enter components (inherits customer/location)
- 💡 Fill dynamic attributes during asset creation (harder to add later)

**Organization:**
- 💡 Establish naming conventions for locations (e.g., "City - Building - Room")
- 💡 Use asset naming that matches customer's internal system (easier for them)
- 💡 Create asset type hierarchy: Categories → Specific types → Sub-types
- 💡 Use status filter to separate active work from archived customers

**Troubleshooting:**
- 💡 If asset doesn't appear in work order dropdown, check customer/location match
- 💡 Use browser console to debug API errors (for admins)
- 💡 Clear browser cache if dropdowns don't update after creating data
- 💡 Refresh customer details page to see newly created locations/assets

**Advanced:**
- 💡 Use dynamic attributes for compliance tracking (warranty dates, certifications)
- 💡 Configure asset type images for visual asset identification in lists
- 💡 Link inspection/service templates to automate work order creation
- 💡 Use child assets to track component replacement history
- 💡 Filter work orders by location to analyze site-specific service patterns

---

## Troubleshooting

### Common Issues

**Issue: Can't see Customers menu in sidebar**
- **Symptoms**: Customers menu item missing from left sidebar
- **Cause**: `customers` package not enabled for user's account
- **Solution**:
  1. Contact system administrator
  2. Admin must enable `customers` package for user or user's role
  3. Log out and log back in
  4. Customers menu should appear

**Issue: Delete button missing on customers list**
- **Symptoms**: Edit and View Details buttons visible, but no Delete button
- **Cause**: User is not Super Admin (only Super Admins can delete customers)
- **Solution**:
  - This is expected behavior for Admin users
  - To delete customers, must have Super Admin role
  - Alternative: Mark customer as Inactive instead of deleting

**Issue: Asset Types menu not visible in Settings**
- **Symptoms**: Settings menu doesn't show Asset Types option
- **Cause**: User is not Super Admin
- **Solution**:
  - Asset Types configuration is Super Admin only
  - Contact Super Admin to create/configure asset types
  - Admin users can use existing asset types but not modify them

**Issue: Can't save customer - form won't submit**
- **Symptoms**: Click Save but nothing happens
- **Cause**: Required fields not filled (Name, Customer #, Status)
- **Solution**:
  1. Check for red asterisk (*) fields
  2. Ensure Customer Name is filled
  3. Ensure Customer # is filled
  4. Ensure Status is selected
  5. Check browser console for validation errors

**Issue: Customer location not showing in asset dropdown**
- **Symptoms**: Creating asset but customer location not available
- **Cause**: Customer has no locations created
- **Solution**:
  1. Go to customer details page
  2. Create at least one location
  3. Return to asset creation
  4. Location should now appear in dropdown

**Issue: Dynamic attributes not appearing in asset modal**
- **Symptoms**: Select asset type but no custom fields table shows
- **Cause**: Asset type has no dynamic attributes configured
- **Solution**:
  1. Contact Super Admin
  2. Admin must edit asset type and configure dynamic attributes
  3. Or select different asset type that has attributes

**Issue: Asset not appearing in work order dropdown**
- **Symptoms**: Asset exists but can't select it in work order creation
- **Cause**: Work order customer/location doesn't match asset's customer/location
- **Solution**:
  1. Verify customer selected in work order matches asset's customer
  2. Verify location selected matches asset's location
  3. If wrong location, edit asset to correct location or select correct location in work order

**Issue: Can't change customer/location when adding child asset**
- **Symptoms**: Customer and location fields are disabled
- **Cause**: Child assets inherit parent's customer/location (by design)
- **Solution**:
  - This is expected behavior
  - To assign to different customer/location, don't select parent
  - Or move parent asset first, then child will follow

**Issue: Export button not appearing**
- **Symptoms**: No CSV export option visible
- **Cause**: Table still loading or export feature not enabled
- **Solution**:
  1. Wait for table to fully load
  2. Check that `exportable` prop is true on table
  3. Look for export container in header (may be icon-only button)

**Issue: Images not uploading**
- **Symptoms**: Upload photo modal opens but upload fails
- **Cause**: File too large, wrong format, or permissions issue
- **Solution**:
  1. Check file size (max 5MB typically)
  2. Use supported formats: JPG, PNG, GIF
  3. Check network connection
  4. Try different browser if persists

**Issue: Search not working or very slow**
- **Symptoms**: Type in search box but no results or long delay
- **Cause**: Network latency or database slow
- **Solution**:
  1. Wait at least 900ms after typing (debounce delay)
  2. Type at least 1 character minimum
  3. Clear search and try again
  4. Check network connection
  5. Contact admin if persists (may be server issue)

**Issue: Pagination showing wrong counts**
- **Symptoms**: "Showing 1-15 of 1500" but only 10 rows visible
- **Cause**: Filter or search active, or data sync issue
- **Solution**:
  1. Clear search and filters
  2. Refresh page
  3. Check that page size matches displayed rows
  4. If persists, contact support

---

### Error Messages

**Error: "Customer deleted"**
- **Context**: After clicking Delete and confirming
- **Meaning**: Customer successfully removed from system
- **Fix**: This is success message, not error (green toast)
- **Note**: Only Super Admins see delete option

**Error: "Customer created" or "Customer saved"**
- **Context**: After saving customer modal
- **Meaning**: Success - customer data saved
- **Fix**: Not an error (green toast)

**Error: "Asset type deleted"**
- **Context**: After deleting asset type
- **Meaning**: Success - asset type removed
- **Fix**: Not an error
- **Note**: Only possible if no assets use this type

**Error: "Asset created" or "Asset saved"**
- **Context**: After saving asset modal
- **Meaning**: Success - asset data saved
- **Fix**: Not an error

**Error: "Location customer contacts saved"**
- **Context**: After confirming contacts modal
- **Meaning**: Success - contact list updated
- **Fix**: Not an error

**Error: "Customer location created" or "Customer location saved"**
- **Context**: After saving location modal
- **Meaning**: Success
- **Fix**: Not an error

**Error: "No results"**
- **Context**: Customer details page after load
- **Meaning**: Customer ID not found or access denied
- **Fix**: 
  1. Check URL - ensure customer ID is valid
  2. Customer may have been deleted
  3. Navigate back to customer list and find correct customer

**Error: "No customers found"**
- **Context**: Customer select dropdown in asset modal
- **Meaning**: Search returned no matching customers
- **Fix**: 
  1. Clear search and try different term
  2. Ensure customers exist in system
  3. Check spelling

**Error: "No locations found"**
- **Context**: Location select dropdown in asset modal
- **Meaning**: Selected customer has no locations
- **Fix**: 
  1. Go to customer details
  2. Create at least one location
  3. Return to asset creation

**Error: "No published templates found"**
- **Context**: Template select in asset type modal
- **Meaning**: No inspection/service templates in PUBLISHED status
- **Fix**: 
  1. Go to Inspections/Services module
  2. Publish at least one template
  3. Return to asset type configuration

**Error: Network/API Errors**
- **Context**: Various save/load operations
- **Meaning**: Connection to server failed
- **Fix**: 
  1. Check internet connection
  2. Refresh page
  3. Try again
  4. If persists, contact IT support
  5. Check browser console for details

---

## Appendix

### Glossary

- **Customer**: Business or individual receiving field service, primary entity in module
- **Customer Location**: Physical service site associated with a customer (ship-to address)
- **Customer Contact**: Individual person at a customer location with name, email, phone
- **Asset**: Equipment, machinery, or other items owned by customer that require service
- **Asset Type**: Category of asset with shared characteristics (e.g., "HVAC Unit", "Elevator")
- **Child Asset**: Asset that is component or part of another (parent) asset
- **Parent Asset**: Asset that contains or comprises other (child) assets
- **Dynamic Attribute**: Custom field defined for an asset type, stored as JSON key-value pairs
- **Default Location**: Primary or main location for a customer (marked with badge)
- **Ship To Name**: Display name for customer location
- **Ship To Code**: Optional internal code/identifier for location
- **Active Status**: Customer or location currently in service/operation
- **Inactive Status**: Customer or location no longer active but retained for historical data
- **Default Inspection Template**: Template auto-assigned to assets when created (if inspections enabled)
- **Default Service Template**: Template auto-assigned to assets when created (if services enabled)
- **Work Order**: Service request or scheduled job linked to customer/location/asset
- **Super Admin**: User role with full system access including delete and settings
- **Admin User**: User role with most access but limited delete and settings capabilities
- **Package**: Module enablement flag controlling feature visibility (customers, inspections, services)

### Related Documentation

- [Work Orders Module](./workorders.md) - Creating and managing work orders
- [Inspections Module](./inspections.md) - Inspection templates and scheduling
- [Services Module](./services.md) - Service templates and PM scheduling
- [User Management](./users.md) - Roles and permissions configuration
- [Settings Guide](./settings.md) - System configuration and package management

### Field Reference

**Customer Fields:**
- `customerName` (string, max 50, required): Business or individual name
- `customerNo` (string, max 255, required): Unique customer identifier
- `address` (string, max 50): Street address
- `city` (string, max 50): City name
- `state` (string, max 25): State or province
- `zipCode` (string, max 50): Postal code
- `countryCode` (string, max 10): Country code (e.g., US, CA)
- `phone` (string, max 25): Primary phone number
- `faxNo` (string, max 25): Fax number
- `email` (string, max 100): Email address
- `isActive` (boolean, required): Active/inactive status

**Customer Location Fields:**
- `shipToName` (string, max 50, required): Location name
- `shipToCode` (string, max 50): Location code
- `shipToAddress` (string, max 50): Street address
- `shipToCity` (string, max 50): City
- `shipToState` (string, max 25): State
- `shipToZipCode` (string, max 25): Zip code
- `shipToCountryCode` (string, max 10): Country code
- `phone` (string, max 25): Location phone
- `customerId` (integer, required): Parent customer ID
- `isDefault` (boolean): Default location flag

**Location Contact Fields:**
- `name` (string, required): Contact person name
- `email` (string, required): Email address
- `phone` (string, required): Phone number
- `customerLocationId` (integer): Parent location ID

**Asset Fields:**
- `name` (string, max 50, required): Asset name/identifier
- `modelNumber` (string, max 50, required): Model number
- `serialNumber` (string, max 50, required): Serial number
- `manufacturer` (string, max 50, required): Manufacturer name
- `assetTypeId` (integer, required): Asset type reference
- `customerLocationId` (integer, required): Location reference
- `customerId` (integer, required): Customer reference
- `assetParentId` (integer, optional): Parent asset reference
- `imageUrl` (string, optional): Asset image URL
- `dynamicAttributes` (JSON object): Custom field values

**Asset Type Fields:**
- `name` (string, max 50, required): Type name
- `imageUrl` (string, optional): Type image
- `isDefault` (boolean): Default type flag
- `defaultInspectionTemplateId` (integer, optional): Default template
- `defaultServiceTemplateId` (integer, optional): Default template
- `dynamicAttributes` (array): Custom field definitions

**Dynamic Attribute Definition:**
- `key` (string, required): Unique identifier (snake_case)
- `label` (string, required): Display name
- `type` (enum, required): text|number|date|boolean|select
- `required` (boolean): Required field flag
- `defaultValue` (any, optional): Default value
- `helpText` (string, optional): User guidance
- `options` (array, for select type): Dropdown options

### API Reference

**Customer Endpoints:**
- `GET /api/customers` - List customers (paginated, searchable, filterable)
- `GET /api/customers/:id` - Get customer details
- `POST /api/customers` - Create customer
- `PUT /api/customers/:id` - Update customer
- `DELETE /api/customers/:id` - Delete customer (Super Admin only)

**Customer Location Endpoints:**
- `GET /api/customer-locations` - List locations
- `GET /api/customer-locations/:id` - Get location details
- `POST /api/customer-locations` - Create location
- `PUT /api/customer-locations/:id` - Update location
- `PUT /api/customer-locations/:id/contacts` - Update location contacts
- `DELETE /api/customer-locations/:id` - Delete location

**Asset Endpoints:**
- `GET /api/assets` - List assets (paginated, searchable, filterable)
- `GET /api/assets/:id` - Get asset details
- `POST /api/assets` - Create asset
- `PUT /api/assets/:id` - Update asset
- `DELETE /api/assets/:id` - Delete asset

**Asset Type Endpoints:**
- `GET /api/asset-types` - List asset types (paginated, searchable)
- `GET /api/asset-types/:id` - Get asset type details
- `POST /api/asset-types` - Create asset type (Super Admin)
- `PUT /api/asset-types/:id` - Update asset type (Super Admin)
- `DELETE /api/asset-types/:id` - Delete asset type (Super Admin)

**Dynamic Attributes Endpoints:**
- `GET /api/dynamic-attributes?entityName=assetType&entityId=:id` - Get attributes for entity
- `POST /api/dynamic-attributes` - Create attribute
- `PUT /api/dynamic-attributes/:id` - Update attribute
- `DELETE /api/dynamic-attributes/:id` - Delete attribute

---

**Document Version:** 1.0  
**Last Updated:** January 27, 2026  
**Contributors:** AI Documentation Assistant  
**Feedback:** Send to documentation@crewos.com

**Screenshots Status:** 📸 Placeholder references included - Screenshots need to be captured from running application at http://localhost:3005

**Note:** This documentation was created based on comprehensive code analysis. Screenshot placeholders indicate where visual references should be inserted after capturing them from the live application.
