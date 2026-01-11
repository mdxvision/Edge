describe('Parlays Builder', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/parlays')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays parlays page', () => {
      cy.url().should('include', '/parlays')
    })

    it('shows parlay lab heading', () => {
      cy.contains(/Parlay Lab|Parlay|Builder/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows correlation tagline', () => {
      cy.contains(/correlation|edge|detection/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Add Parlay Leg', () => {
    it('has selection input', () => {
      cy.get('input', { timeout: 10000 }).should('exist')
    })

    it('has add leg button', () => {
      cy.contains(/Add|Leg|Selection/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Analysis', () => {
    it('has analyze button', () => {
      cy.contains(/Analyze|Calculate|Check/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
