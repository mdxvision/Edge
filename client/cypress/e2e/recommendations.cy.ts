describe('Recommendations', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/recommendations')
    cy.url().should('include', '/dashboard')
  })

  describe('Page Layout', () => {
    it('displays recommendations page heading', () => {
      cy.contains(/Curated Picks|Recommendations|Picks/i, { timeout: 15000 }).should('be.visible')
    })

    it('shows generate recommendations button', () => {
      cy.contains(/Generate Picks|Generate|Refresh/i, { timeout: 15000 }).should('be.visible')
    })

    it('shows personalized tagline', () => {
      cy.contains(/Intelligent edge|Personalized/i, { timeout: 15000 }).should('be.visible')
    })
  })

  describe('Filters', () => {
    it('has sport filter', () => {
      cy.contains('Sport', { timeout: 10000 }).should('be.visible')
    })

    it('has filter dropdown', () => {
      cy.get('select', { timeout: 10000 }).should('exist')
    })
  })

  describe('Stats Cards', () => {
    it('shows Curated Picks count', () => {
      cy.contains(/Curated Picks/i, { timeout: 15000 }).should('be.visible')
    })

    it('shows Precision Rate', () => {
      cy.contains(/Precision Rate/i, { timeout: 15000 }).should('be.visible')
    })

    it('shows Total Stake', () => {
      cy.contains(/Total Stake/i, { timeout: 15000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
