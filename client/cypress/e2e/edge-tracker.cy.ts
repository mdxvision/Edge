describe('Edge Tracker', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/edge-tracker')
    cy.url().should('include', '/dashboard')
  })

  describe('Page Layout', () => {
    it('displays edge tracker page', () => {
      cy.url().should('include', '/edge-tracker')
    })

    it('shows edge tracker heading', () => {
      cy.contains(/Edge Validation|Edge Tracker|Tracker/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Stats Display', () => {
    it('shows performance metrics', () => {
      cy.contains(/Win|ROI|Edge|Rate|Picks/i, { timeout: 15000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
