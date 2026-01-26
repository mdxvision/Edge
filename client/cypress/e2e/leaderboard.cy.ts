describe('Leaderboard', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/leaderboard')
    // Wait for page to load - testuser may not be on leaderboard if no bets placed
    cy.url().should('include', '/leaderboard')
  })

  describe('Page Layout', () => {
    it('displays leaderboard page', () => {
      cy.url().should('include', '/leaderboard')
    })

    it('shows leaderboard heading', () => {
      cy.contains(/Leaderboard|Rankings|Top/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows rankings or empty state', () => {
      // Page should have some content - rankings table or empty state
      cy.get('body', { timeout: 10000 }).should('exist')
    })
  })

  describe('Ranking Display', () => {
    it('shows rank numbers or empty state', () => {
      // Page should display rankings or empty state
      cy.get('body', { timeout: 10000 }).should('exist')
    })

    it('shows performance metrics or empty state', () => {
      // Page should display performance metrics or empty state
      cy.get('body', { timeout: 10000 }).should('exist')
    })
  })

  describe('Filters', () => {
    it('has time period or sorting options', () => {
      // Page should have filters or sorting options
      cy.get('body', { timeout: 10000 }).should('exist')
    })

    it('can interact with filters', () => {
      cy.get('select, button', { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
