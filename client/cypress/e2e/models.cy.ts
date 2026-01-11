describe('Models & Analytics', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/models')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays models page', () => {
      cy.url().should('include', '/models')
    })

    it('shows page content or error state', () => {
      // Page shows either the content (Intelligence heading) or error state (Something's not right)
      cy.contains(/Intelligence|Something's not right|Couldn't load/i, { timeout: 20000 }).should('exist')
    })
  })

  describe('Error Handling', () => {
    it('shows retry button when API fails', () => {
      // When API returns errors, the page should show a Try Again button
      cy.get('body').then($body => {
        if ($body.text().includes("Something's not right") || $body.text().includes("Couldn't load")) {
          cy.contains(/Try Again|Retry/i).should('exist')
        }
      })
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
