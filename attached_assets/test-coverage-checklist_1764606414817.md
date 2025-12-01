# Comprehensive Test Coverage Checklist

Use this checklist for EVERY page/module to ensure complete coverage.

---

## Per-Page Checklist

### ☐ PAGE FUNDAMENTALS
- [ ] Page loads without console errors
- [ ] Page title is correct
- [ ] All sections render
- [ ] Loading state appears/disappears
- [ ] Empty state displays when appropriate
- [ ] Error boundary catches failures

### ☐ ALL BUTTONS
For EVERY button on the page:
- [ ] Button is visible
- [ ] Button is clickable
- [ ] Button triggers correct action
- [ ] Disabled state works
- [ ] Loading state during async
- [ ] Keyboard accessible (Enter/Space)

### ☐ ALL FORM FIELDS
For EVERY input/select/textarea:
- [ ] Field is focusable
- [ ] Field accepts input
- [ ] Required validation fires
- [ ] Format validation fires (email, phone, etc.)
- [ ] Error message appears
- [ ] Error message clears when corrected
- [ ] Tab order is correct
- [ ] Placeholder text shows
- [ ] Max length enforced if applicable

### ☐ ALL CHECKBOXES
For EVERY checkbox:
- [ ] Can check
- [ ] Can uncheck
- [ ] State persists
- [ ] Label click toggles state
- [ ] Keyboard accessible

### ☐ ALL DROPDOWNS/SELECTS
For EVERY dropdown:
- [ ] Opens on click
- [ ] All options visible
- [ ] Each option selectable
- [ ] Selection shows in trigger
- [ ] Closes after selection
- [ ] Search/filter works (if present)
- [ ] Clear works (if present)
- [ ] Keyboard navigation works

### ☐ ALL MODALS/DIALOGS
For EVERY modal:
- [ ] Opens correctly
- [ ] X button closes
- [ ] Cancel button closes
- [ ] Overlay click closes (if applicable)
- [ ] Escape key closes
- [ ] Form inside submits correctly
- [ ] Success closes modal
- [ ] Error keeps modal open with message

### ☐ ALL TABLES/LISTS
For EVERY table or list:
- [ ] Data renders correctly
- [ ] Sorting works (each column)
- [ ] Filtering works (each filter)
- [ ] Search works
- [ ] Pagination works
  - [ ] Next page
  - [ ] Previous page
  - [ ] First/last page
  - [ ] Page size change
  - [ ] Page number display
- [ ] Row selection works (if applicable)
- [ ] Row actions work (edit, delete, view)
- [ ] Empty state shows when no data
- [ ] Loading skeleton shows

### ☐ ALL TABS
For EVERY tab set:
- [ ] Each tab clickable
- [ ] Correct content per tab
- [ ] Active state indicator
- [ ] Keyboard navigation (arrow keys)

### ☐ ALL NAVIGATION
- [ ] Each nav link works
- [ ] Active state shows
- [ ] Mobile menu toggle (if applicable)
- [ ] Breadcrumbs work
- [ ] Browser back/forward work

---

## Per-Entity CRUD Checklist

### ☐ CREATE
- [ ] Create button visible
- [ ] Create form/modal opens
- [ ] All required fields validated
- [ ] All optional fields work
- [ ] Submit creates record
- [ ] Success message shows
- [ ] New record appears in list
- [ ] Form clears/closes after success
- [ ] Error handling works
- [ ] Duplicate detection (if applicable)

### ☐ READ
- [ ] List shows all records
- [ ] Each record shows correct data
- [ ] View/detail page loads
- [ ] All fields display correctly
- [ ] Related data shows
- [ ] Refresh updates data

### ☐ UPDATE
- [ ] Edit button visible
- [ ] Edit form opens with existing data
- [ ] All fields editable
- [ ] Save updates record
- [ ] Success message shows
- [ ] List reflects changes
- [ ] Cancel discards changes
- [ ] Validation works on edit

### ☐ DELETE
- [ ] Delete button visible
- [ ] Confirmation dialog appears
- [ ] Cancel stops deletion
- [ ] Confirm deletes record
- [ ] Success message shows
- [ ] Record removed from list
- [ ] Cascade effects work (if applicable)
- [ ] Undo works (if applicable)

### ☐ BULK OPERATIONS (if applicable)
- [ ] Multi-select works
- [ ] Select all works
- [ ] Bulk delete works
- [ ] Bulk status change works
- [ ] Bulk export works

---

## Validation Tests

### ☐ FIELD VALIDATIONS
- [ ] Required field - empty submission
- [ ] Email field - invalid format
- [ ] Phone field - invalid format
- [ ] URL field - invalid format
- [ ] Password - too short
- [ ] Password - missing requirements
- [ ] Password confirmation - mismatch
- [ ] Number field - out of range
- [ ] Date field - invalid date
- [ ] Date field - out of range
- [ ] Text - exceeds max length
- [ ] Text - special characters handled
- [ ] Text - whitespace-only rejected

### ☐ API ERROR HANDLING
- [ ] 400 - Bad Request displays error
- [ ] 401 - Redirects to login
- [ ] 403 - Shows access denied
- [ ] 404 - Shows not found
- [ ] 422 - Shows validation errors
- [ ] 500 - Shows server error
- [ ] Timeout - Shows timeout message
- [ ] Network error - Shows offline message

---

## Authentication Tests

### ☐ LOGIN
- [ ] Valid credentials - success
- [ ] Invalid email - error
- [ ] Invalid password - error
- [ ] Empty fields - validation
- [ ] Remember me works
- [ ] Redirect to intended page
- [ ] Session persists on refresh

### ☐ LOGOUT
- [ ] Logout button works
- [ ] Session cleared
- [ ] Redirect to login
- [ ] Protected pages blocked

### ☐ PASSWORD RESET
- [ ] Forgot password link works
- [ ] Email validation
- [ ] Success message
- [ ] Reset link works
- [ ] New password validation
- [ ] Success redirects to login

### ☐ RBAC/PERMISSIONS
- [ ] Admin sees admin features
- [ ] Non-admin doesn't see admin features
- [ ] Role-specific navigation
- [ ] Role-specific actions
- [ ] Permission denied handled

---

## Edge Cases

### ☐ DATA EDGE CASES
- [ ] Empty database - empty states show
- [ ] Single record - pagination hidden
- [ ] Max records - performance OK
- [ ] Special characters in data
- [ ] Very long text
- [ ] Unicode/emoji
- [ ] HTML in text (escaped)
- [ ] Null vs empty string
- [ ] Zero vs null numbers

### ☐ TIMING EDGE CASES
- [ ] Rapid clicks handled (no double-submit)
- [ ] Slow network - loading states
- [ ] Race conditions - correct data shows
- [ ] Concurrent edits - conflict handling

---

## Accessibility Tests

### ☐ KEYBOARD NAVIGATION
- [ ] All elements reachable by Tab
- [ ] Focus indicator visible
- [ ] Escape closes modals
- [ ] Enter submits forms
- [ ] Arrow keys in dropdowns
- [ ] Skip links work

### ☐ SCREEN READER
- [ ] All images have alt text
- [ ] Form fields have labels
- [ ] Error messages announced
- [ ] Page regions labeled
- [ ] Dynamic content announced

---

## Quick Test Count Estimator

For each module, estimate tests needed:

| Category | Tests per Item |
|----------|----------------|
| Buttons | 4 tests each |
| Form fields | 5 tests each |
| CRUD operations | 15 tests per entity |
| Modals | 6 tests each |
| Tables | 10-15 tests each |
| Filters | 3 tests each |
| Navigation items | 2 tests each |
| Error scenarios | 8+ tests |
| Edge cases | 10+ tests |

**Example: User Management Page**
- 5 buttons × 4 = 20 tests
- 8 form fields × 5 = 40 tests
- 1 CRUD entity × 15 = 15 tests
- 2 modals × 6 = 12 tests
- 1 table × 12 = 12 tests
- 3 filters × 3 = 9 tests
- Error scenarios = 8 tests
- Edge cases = 10 tests
- **Total: ~126 tests**

---

## Test Naming Convention

```javascript
describe('Module Name', () => {
  describe('Feature/Section', () => {
    describe('Sub-feature', () => {
      it('should [action] when [condition]', () => {
        // test code
      });
    });
  });
});

// Examples:
it('should display validation error when email is invalid')
it('should create new user when form is submitted with valid data')
it('should close modal when X button is clicked')
it('should show loading spinner while fetching data')
it('should redirect to login when session expires')
```
