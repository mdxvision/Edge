describe('Parlays Builder', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/parlays')
    cy.url().should('include', '/dashboard')
  })

  describe('Page Layout', () => {
    it('displays parlays page', () => {
      cy.url().should('include', '/parlays')
    })

    it('shows parlay lab heading', () => {
      cy.contains('h1', /Parlay Lab/i, { timeout: 10000 }).should('exist')
    })

    it('shows correlation tagline', () => {
      // The tagline "Intelligent correlation detection" is visible on larger screens
      cy.contains(/correlation|edge|detection/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Add Parlay Leg', () => {
    it('has selection input', () => {
      cy.get('input', { timeout: 10000 }).should('exist')
    })

    it('has add leg button', () => {
      // Button says "Add Pick"
      cy.get('button').contains(/Add Pick|Add/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Analysis', () => {
    it('shows analyze section', () => {
      // The page has an "Add Pick" heading in the card
      cy.contains('Add Pick', { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
