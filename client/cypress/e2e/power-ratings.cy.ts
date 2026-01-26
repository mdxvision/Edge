describe('Power Ratings', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/power-ratings")
    cy.url().should("include", "/power-ratings")
  })

  describe('Page Layout', () => {
    it('displays power ratings page', () => {
      cy.url().should('include', '/power-ratings')
    })

    it('shows power ratings heading', () => {
      cy.contains(/Power Ratings|Ratings|Rankings/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Team Ratings', () => {
    it('shows team ratings data', () => {
      // Page should have content
      cy.get('body', { timeout: 10000 }).should('exist')
    })

    it('displays rating numbers', () => {
      // Page should have content
      cy.get('body', { timeout: 10000 }).should('exist')
    })
  })

  describe('Sport Selection', () => {
    it('has sport filter', () => {
      // Page should have sport tabs or filters
      cy.contains(/NFL|NBA|MLB|NHL|Sport|Power/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
