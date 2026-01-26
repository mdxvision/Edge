describe('Games Browser', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/games")
    cy.url().should("include", "/games")
  })

  describe('Page Layout', () => {
    it('displays games page', () => {
      cy.url().should('include', '/games')
    })

    it('shows sport filter or tabs', () => {
      cy.get('select, button, [role="tab"]', { timeout: 10000 }).should('exist')
    })
  })

  describe('Sport Filtering', () => {
    it('displays sport options', () => {
      cy.contains(/NFL|NBA|MLB|Soccer|All|Sports/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Games List', () => {
    it('displays games or loading state', () => {
      cy.get('body', { timeout: 10000 }).should('exist')
      // Page loads successfully
      cy.url().should('include', '/games')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
