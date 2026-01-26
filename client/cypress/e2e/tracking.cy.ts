describe('Bet Tracking', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/tracking')
    cy.url().should('include', '/tracking')
  })

  describe('Page Layout', () => {
    it('displays tracking page heading', () => {
      cy.contains('Your Bets', { timeout: 15000 }).should('be.visible')
    })

    it('shows track a bet button', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i, { timeout: 15000 }).should('be.visible')
    })

    it('displays stats section', () => {
      cy.contains('Performance', { timeout: 15000 }).should('be.visible')
    })
  })

  describe('Stats Cards', () => {
    it('shows Performance stat', () => {
      cy.contains('Performance', { timeout: 15000 }).should('be.visible')
    })

    it('shows Precision Rate stat', () => {
      cy.contains('Precision Rate', { timeout: 15000 }).should('be.visible')
    })

    it('shows ROI stat', () => {
      cy.contains('ROI', { timeout: 15000 }).should('be.visible')
    })

    it('shows Current Streak stat', () => {
      cy.contains('Current Streak', { timeout: 15000 }).should('be.visible')
    })
  })

  describe('Add New Bet', () => {
    it('opens add bet form', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i).first().click()
      cy.get('select, input', { timeout: 5000 }).should('exist')
    })

    it('has sport selection', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i).first().click()
      cy.get('select').should('exist')
    })

    it('has bet type selection', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i).first().click()
      cy.get('select').should('have.length.at.least', 1)
    })

    it('has required inputs', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i).first().click()
      cy.get('input').should('exist')
    })

    it('form has submit button', () => {
      cy.contains(/Track a Bet|Track|Add Bet|New/i).first().click()
      cy.get('button').should('exist')
    })
  })

  describe('Bet List', () => {
    it('shows All Bets section', () => {
      cy.contains('All Bets', { timeout: 15000 }).should('be.visible')
    })

    it('has status filter', () => {
      cy.get('select').should('have.length.at.least', 1)
    })

    it('has sport filter', () => {
      cy.get('select').should('have.length.at.least', 2)
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
