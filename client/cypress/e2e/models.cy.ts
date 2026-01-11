describe('Models & Analytics', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/models')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
    // Wait for page to load
    cy.contains(/Intelligence|Analyzing|error/i, { timeout: 20000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays models page', () => {
      cy.url().should('include', '/models')
    })

    it('shows models or analytics heading', () => {
      cy.contains(/Intelligence|Models|Analytics/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows precision tagline', () => {
      cy.contains(/Precision|power ratings|performance/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Sport Cards', () => {
    it('displays sport options', () => {
      cy.contains(/NFL|NBA|MLB|NHL/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows model status', () => {
      cy.contains(/Calibrated|Pending/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows team count', () => {
      cy.contains(/Teams/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Actions', () => {
    it('has seed data button', () => {
      cy.contains(/Seed Data|Seed/i, { timeout: 10000 }).should('be.visible')
    })

    it('has calibrate button', () => {
      cy.contains(/Calibrate|Train/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
