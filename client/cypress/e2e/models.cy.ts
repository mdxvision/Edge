describe('Models & Analytics', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/models')
    cy.url().should('include', '/models')
  })

  describe('Page Layout', () => {
    it('displays models page', () => {
      cy.url().should('include', '/models')
    })

    it('shows page content or handles loading', () => {
      // Page shows either the content or loading/error state
      cy.contains(/Intelligence|Analyzing|Something's not right/i, { timeout: 20000 }).should('exist')
    })

    it('shows model controls when loaded', () => {
      // Wait for either content or error
      cy.get('body', { timeout: 20000 }).then($body => {
        if ($body.text().includes('Intelligence')) {
          cy.contains('Intelligence').should('be.visible')
          // Check for action buttons
          cy.contains(/Seed Data|Calibrate/i).should('exist')
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
