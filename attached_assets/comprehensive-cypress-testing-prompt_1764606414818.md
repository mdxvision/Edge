# Comprehensive Cypress E2E Testing Prompt

## Instructions for Claude

Use this prompt at the start of any new project to generate comprehensive, production-ready Cypress E2E tests that cover every interaction a human would perform—and then some.

---

## PROMPT START

---

I need you to create **COMPREHENSIVE** end-to-end Cypress tests for my application. This is a production/mission-critical application requiring full test coverage.

### My Workflow Preferences:
- **Give me ONE step at a time**
- **Wait for my confirmation before moving to the next step**
- **Do not bundle multiple steps together**
- **When I need to paste code, give me the FULL file contents to replace**

---

## PROJECT CONTEXT

**Technology Stack:**
- [Framework: React/Vue/Angular/Flask/Django/etc.]
- [Language: TypeScript/JavaScript/Python/etc.]
- [UI Library: shadcn/ui, Material UI, Bootstrap, TailwindCSS, etc.]
- [State Management: React Query, Redux, Zustand, etc.]
- [Backend: Express, FastAPI, Django, etc.]
- [Database: PostgreSQL, MySQL, MongoDB, etc.]
- [Development Environment: Replit/Local/Docker/etc.]

**Application Type:**
- [Healthcare Platform / Legal Management / E-commerce / SaaS / etc.]

**Modules/Pages to Test:**
1. [Authentication - Login, Register, Password Reset, Session Management]
2. [Dashboard - Stats, Charts, Quick Actions, Recent Activity]
3. [User Management - CRUD, Roles, Permissions]
4. [Module 1 - List the features]
5. [Module 2 - List the features]
6. [Add all modules...]

---

## TESTING REQUIREMENTS

### Coverage Level: COMPREHENSIVE (30-50+ tests per page)

I need tests for EVERY interaction a human would perform:

#### 1. PAGE LOAD & VISIBILITY TESTS
For each page, test that:
- [ ] Page loads without errors
- [ ] All sections render correctly
- [ ] Loading states appear and disappear appropriately
- [ ] Empty states display when no data exists
- [ ] Error boundaries catch failures gracefully
- [ ] Page title and metadata are correct
- [ ] Responsive layout works at different viewport sizes

#### 2. ELEMENT INTERACTION TESTS
Test that every interactive element works:

**Buttons:**
- [ ] Every button is visible and clickable
- [ ] Every button triggers the correct action
- [ ] Disabled states work correctly
- [ ] Loading states during async operations
- [ ] Icon buttons work correctly
- [ ] Button groups and toggles function

**Forms:**
- [ ] All form fields are focusable
- [ ] Tab order is correct
- [ ] Required fields are enforced
- [ ] Field validation messages appear
- [ ] Field validation messages disappear when corrected
- [ ] Input masks work (phone, SSN, date, currency)
- [ ] Character limits are enforced
- [ ] Autocomplete/autofill works
- [ ] Form resets work
- [ ] Form submission works
- [ ] Form prevents double-submit

**Checkboxes:**
- [ ] Can check and uncheck each checkbox
- [ ] Checked state persists appropriately
- [ ] "Select All" works if present
- [ ] Indeterminate state works if applicable

**Radio Buttons:**
- [ ] Each option is selectable
- [ ] Only one can be selected at a time
- [ ] Selection triggers appropriate actions

**Dropdowns/Selects:**
- [ ] Opens and closes correctly
- [ ] All options are selectable
- [ ] Search/filter works if present
- [ ] Multi-select works if applicable
- [ ] Clear selection works
- [ ] Keyboard navigation works

**Date Pickers:**
- [ ] Opens calendar correctly
- [ ] Can select dates
- [ ] Date range selection works if applicable
- [ ] Disabled dates are not selectable
- [ ] Date format displays correctly

**File Uploads:**
- [ ] Drag and drop works
- [ ] Click to upload works
- [ ] File type restrictions work
- [ ] File size limits work
- [ ] Multiple file upload works if applicable
- [ ] Upload progress shows
- [ ] Cancel upload works

**Modals/Dialogs:**
- [ ] Opens correctly on trigger
- [ ] Closes on X button
- [ ] Closes on Cancel button
- [ ] Closes on overlay click (if applicable)
- [ ] Closes on Escape key
- [ ] Form inside modal submits correctly
- [ ] Prevents background scroll when open
- [ ] Focus trap works correctly

**Tables/Lists:**
- [ ] Data renders correctly
- [ ] Sorting works (ascending/descending)
- [ ] Filtering works
- [ ] Pagination works (next, previous, specific page, page size)
- [ ] Row selection works (single and multi)
- [ ] Row actions work (edit, delete, view, etc.)
- [ ] Empty state displays when no results
- [ ] Loading skeleton appears during data fetch
- [ ] Column visibility toggle works if present
- [ ] Column reordering works if present
- [ ] Inline editing works if present

**Tabs:**
- [ ] Each tab is clickable
- [ ] Correct content displays for each tab
- [ ] Active state is visually indicated
- [ ] Keyboard navigation works

**Accordions/Expandable Sections:**
- [ ] Expands on click
- [ ] Collapses on click
- [ ] Multiple sections can be open (or only one, depending on design)
- [ ] Keyboard navigation works

**Search:**
- [ ] Search input works
- [ ] Search triggers on enter
- [ ] Search triggers on button click
- [ ] Search results display correctly
- [ ] Clear search works
- [ ] No results state displays
- [ ] Recent searches work if applicable
- [ ] Autocomplete suggestions work if applicable

**Navigation:**
- [ ] All navigation links work
- [ ] Active state shows for current page
- [ ] Mobile menu toggle works
- [ ] Breadcrumbs work and navigate correctly
- [ ] Back/Forward browser buttons work
- [ ] Deep linking works

**Notifications/Toasts:**
- [ ] Success messages appear and auto-dismiss
- [ ] Error messages appear
- [ ] Warning messages appear
- [ ] Info messages appear
- [ ] Manual dismiss works
- [ ] Multiple notifications stack correctly

#### 3. CRUD OPERATION TESTS
For each entity (Users, Projects, Items, etc.):

**Create:**
- [ ] Create button/link is visible
- [ ] Create form/modal opens
- [ ] All fields can be filled
- [ ] Required validation works
- [ ] Format validation works (email, phone, etc.)
- [ ] Submit creates item
- [ ] Success message appears
- [ ] New item appears in list
- [ ] Form/modal closes after success
- [ ] Error handling for failed creation
- [ ] Duplicate detection works if applicable

**Read:**
- [ ] List displays all items
- [ ] List displays correct data for each item
- [ ] View/detail page loads
- [ ] Detail page shows all fields
- [ ] Related data displays correctly
- [ ] Refresh updates data

**Update:**
- [ ] Edit button/link is visible
- [ ] Edit form/modal opens with existing data
- [ ] All fields can be modified
- [ ] Submit saves changes
- [ ] Success message appears
- [ ] List reflects updated data
- [ ] Cancel returns to previous state without saving
- [ ] Optimistic updates work if applicable
- [ ] Conflict detection works if applicable

**Delete:**
- [ ] Delete button/link is visible
- [ ] Confirmation dialog appears
- [ ] Cancel stops deletion
- [ ] Confirm executes deletion
- [ ] Success message appears
- [ ] Item removed from list
- [ ] Cascade effects work correctly
- [ ] Undo works if applicable

**Bulk Operations:**
- [ ] Multi-select works
- [ ] Bulk delete works
- [ ] Bulk status change works
- [ ] Bulk export works if applicable

#### 4. VALIDATION & ERROR TESTS

**Field Validation:**
- [ ] Required field errors
- [ ] Email format errors
- [ ] Phone format errors
- [ ] URL format errors
- [ ] Password strength errors
- [ ] Minimum length errors
- [ ] Maximum length errors
- [ ] Numeric range errors
- [ ] Date range errors
- [ ] Custom validation errors
- [ ] Cross-field validation (password confirmation, date ranges)

**API Error Handling:**
- [ ] 400 Bad Request handling
- [ ] 401 Unauthorized handling (redirect to login)
- [ ] 403 Forbidden handling (show access denied)
- [ ] 404 Not Found handling
- [ ] 422 Validation Error handling
- [ ] 500 Server Error handling
- [ ] Network timeout handling
- [ ] Network offline handling
- [ ] Retry mechanisms work

**Edge Cases:**
- [ ] Empty data handling
- [ ] Special characters in input
- [ ] Very long text input
- [ ] HTML/script injection prevention
- [ ] Unicode characters
- [ ] Whitespace-only input
- [ ] Zero values vs null values
- [ ] Boundary conditions (min/max values)
- [ ] Concurrent edit conflicts

#### 5. AUTHENTICATION & AUTHORIZATION TESTS

**Login:**
- [ ] Valid credentials succeed
- [ ] Invalid email shows error
- [ ] Invalid password shows error
- [ ] Empty fields show validation
- [ ] Remember me works if applicable
- [ ] Redirect to intended page after login
- [ ] Session persists on refresh

**Logout:**
- [ ] Logout button works
- [ ] Session is cleared
- [ ] Redirect to login page
- [ ] Protected pages inaccessible after logout

**Session Management:**
- [ ] Session expires correctly
- [ ] Session refresh works
- [ ] Multiple tab handling
- [ ] Forced logout on password change

**Role-Based Access (RBAC):**
- [ ] Admin sees admin features
- [ ] Regular user doesn't see admin features
- [ ] Role-specific navigation items
- [ ] Role-specific actions on entities
- [ ] Permission denied handling

**Password Reset:**
- [ ] Forgot password link works
- [ ] Email validation works
- [ ] Reset email sent confirmation
- [ ] Reset link works
- [ ] New password validation
- [ ] Successful reset redirects to login

#### 6. STATE MANAGEMENT TESTS

- [ ] Data persists correctly between page navigations
- [ ] Form data persists during multi-step wizards
- [ ] Filters persist on page return
- [ ] Sort order persists
- [ ] Pagination state persists
- [ ] Local storage/session storage works correctly
- [ ] State resets on logout

#### 7. REAL-TIME FEATURES TESTS (if applicable)

- [ ] WebSocket connection establishes
- [ ] Real-time updates appear
- [ ] Reconnection works after disconnect
- [ ] Notifications push correctly
- [ ] Collaborative editing works
- [ ] Online status indicators update

#### 8. INTEGRATION TESTS

- [ ] Third-party authentication (OAuth, SSO)
- [ ] Payment processing
- [ ] Email sending
- [ ] File storage (S3, etc.)
- [ ] External API calls
- [ ] Webhook handling

---

## DATA-TESTID NAMING CONVENTIONS

Use this consistent naming pattern across all projects:

### Pattern: `{element-type}-{context}-{action/name}`

```
# Buttons
data-testid="button-create-{entity}"     → button-create-hospital
data-testid="button-submit-{form}"       → button-submit-login
data-testid="button-delete-{entity}"     → button-delete-user
data-testid="button-edit-{entity}"       → button-edit-project
data-testid="button-cancel"
data-testid="button-save"
data-testid="button-close"

# Inputs
data-testid="input-{field-name}"         → input-email, input-password
data-testid="input-search"
data-testid="input-filter-{name}"        → input-filter-status

# Selects/Dropdowns
data-testid="select-{name}"              → select-hospital, select-role
data-testid="filter-{name}"              → filter-status, filter-date

# Checkboxes
data-testid="checkbox-{name}"            → checkbox-active, checkbox-required

# Tables/Lists
data-testid="{entity}-table"             → hospitals-table, users-table
data-testid="{entity}-list"              → projects-list, consultants-list
data-testid="{entity}-row-{id}"          → hospital-row-123, user-row-456
data-testid="{entity}-card"              → project-card, consultant-card

# Modals
data-testid="modal-{action}-{entity}"    → modal-create-hospital
data-testid="modal-confirm-delete"
data-testid="modal-close"

# Navigation
data-testid="nav-{page}"                 → nav-dashboard, nav-hospitals
data-testid="nav-menu"
data-testid="nav-user-menu"

# Tabs
data-testid="tab-{name}"                 → tab-details, tab-settings

# Forms
data-testid="form-{name}"                → form-login, form-create-hospital

# Sections
data-testid="section-{name}"             → section-stats, section-recent

# Alerts/Messages
data-testid="alert-success"
data-testid="alert-error"
data-testid="error-message"
data-testid="success-message"

# Stats/Metrics
data-testid="stat-{name}"                → stat-total-users, stat-active
data-testid="metric-{name}"              → metric-revenue, metric-growth

# Actions (row-level)
data-testid="action-edit-{id}"           → action-edit-123
data-testid="action-delete-{id}"         → action-delete-123
data-testid="action-view-{id}"           → action-view-123
```

---

## TEST FILE STRUCTURE

```
cypress/
├── e2e/
│   ├── 01-authentication.cy.js
│   ├── 02-{module1}.cy.js
│   ├── 03-{module2}.cy.js
│   ├── ...
│   └── XX-integration.cy.js
├── fixtures/
│   ├── users.json
│   ├── {entity1}.json
│   └── {entity2}.json
├── support/
│   ├── commands.js          # Custom Cypress commands
│   └── e2e.js               # Global configuration
└── cypress.config.js
```

---

## REQUIRED DELIVERABLES

For this project, please provide:

1. **Complete test files** for every module (comprehensive coverage)
2. **Custom Cypress commands** (`cypress/support/commands.js`)
3. **Fixture files** with demo/test data
4. **Seed script** to populate database with test data
5. **data-testid mapping document** - List of all required test IDs by component
6. **CI/CD configuration** for automated test runs
7. **Test coverage report setup**

---

## DEMO DATA REQUIREMENTS

Create realistic demo data including:

**Users (various roles):**
- Admin user
- Manager user
- Regular user
- Inactive user
- User pending approval

**For each entity type:**
- At least 10-20 records for pagination testing
- Records in various states (active, inactive, pending, etc.)
- Records with edge cases (long names, special characters)
- Records for date range testing (past, current, future dates)
- Records for filtering/sorting testing

---

## EXECUTION PROCESS

For each module, follow this process:

### Step 1: Audit Current Component
Share the component code. Identify:
- All interactive elements
- Current selectors/test IDs
- Missing test IDs

### Step 2: Add data-testid Attributes
Provide updated component with all necessary data-testid attributes.

### Step 3: Create Test File
Write comprehensive tests covering:
- Happy path (everything works)
- Error path (things fail gracefully)
- Edge cases (boundary conditions)
- Accessibility (keyboard navigation)

### Step 4: Create Fixtures
Generate realistic test data for the module.

### Step 5: Run and Verify
Execute tests and fix any failures.

### Step 6: Move to Next Module
Repeat for all modules.

---

## CI/CD SETUP

After all tests pass, set up:

1. **GitHub Actions / Replit CI** to run tests on every push
2. **Pre-commit hooks** to run tests before commits
3. **Test coverage reporting**
4. **Slack/Discord notifications** for test failures

---

## READY TO START

Please begin by:

1. Asking me to share my project structure or Replit link
2. Identifying the first module to test
3. Walking me through the process ONE STEP AT A TIME

Remember: Wait for my confirmation after each step before proceeding!

---

## PROMPT END

---

## Usage Notes

### How to Use This Prompt:

1. **Copy everything between "PROMPT START" and "PROMPT END"**
2. **Fill in the bracketed sections** with your project-specific details
3. **Paste into a new Claude chat**
4. **Follow the step-by-step process**

### Customization Tips:

- Add project-specific modules to the "Modules/Pages to Test" section
- Add any custom validation rules your app uses
- Include any third-party integrations that need testing
- Specify any accessibility requirements (WCAG compliance level)

### For Maximum Coverage:

- Run this prompt for each major module
- Save the test files and patterns for reuse
- Update tests as new features are added
- Set up CI/CD to run tests automatically
