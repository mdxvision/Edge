describe('Pricing', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/pricing")
    cy.url().should("include", "/pricing")
  })

  describe('Page Layout', () => {
    it('displays pricing page', () => {
      cy.url().should('include', '/pricing')
    })

    it('shows pricing heading', () => {
      cy.contains(/Choose Your Edge|Pricing|Plans/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows features tagline', () => {
      // Tagline is "Unlock powerful features to maximize your betting intelligence."
      cy.contains(/Unlock|powerful|betting/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Billing Toggle', () => {
    it('shows billing period options', () => {
      cy.contains(/Monthly|Yearly/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows savings badge', () => {
      cy.contains(/Save|%/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Pricing Tiers', () => {
    it('shows tier options', () => {
      cy.contains(/Free|Premium|Pro/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
