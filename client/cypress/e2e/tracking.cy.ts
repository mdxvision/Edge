describe('Bet Tracking', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/tracking')
    // Wait for page to load
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays tracking page heading', () => {
      cy.contains('Your Bets', { timeout: 15000 }).should('be.visible')
    })

    it('shows track a bet button', () => {
      cy.contains('Track a Bet', { timeout: 15000 }).should('be.visible')
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
      cy.contains('Track a Bet').click()
      cy.get('select[name="sport"]', { timeout: 5000 }).should('be.visible')
    })

    it('has sport selection', () => {
      cy.contains('Track a Bet').click()
      cy.get('select[name="sport"]').should('exist')
    })

    it('has bet type selection', () => {
      cy.contains('Track a Bet').click()
      cy.get('select[name="bet_type"]').should('exist')
    })

    it('has required inputs', () => {
      cy.contains('Track a Bet').click()
      cy.get('input[name="selection"]').should('exist')
      cy.get('input[name="odds"]').should('exist')
      cy.get('input[name="stake"]').should('exist')
    })

    it('form has Track This button', () => {
      cy.contains('Track a Bet').click()
      cy.contains('button', 'Track This').should('exist')
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
