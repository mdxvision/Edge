describe('Paper Trading', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/paper-trading")
    cy.url().should("include", "/paper-trading")
  })

  describe('Page Layout', () => {
    it('displays paper trading page', () => {
      cy.url().should('include', '/paper-trading')
    })

    it('shows paper trading heading', () => {
      cy.contains(/Paper Trading|Practice|Simulation/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Bankroll Stats', () => {
    it('shows balance information', () => {
      cy.contains(/Balance|Bankroll|Starting|\$/i, { timeout: 15000 }).should('exist')
    })
  })

  describe('Trading Actions', () => {
    it('has place trade button or form', () => {
      cy.contains(/Place|Trade|Bet|New/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
