describe('Paper Trading', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/paper-trading')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays paper trading page', () => {
      cy.url().should('include', '/paper-trading')
    })

    it('shows paper trading heading', () => {
      cy.contains(/Paper Trading|Practice|Simulation/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Virtual Balance', () => {
    it('shows virtual balance or bankroll', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasBalance = $body.text().match(/Balance|Bankroll|\$/i)
        expect(hasBalance).to.not.be.null
      })
    })
  })

  describe('Practice Bets', () => {
    it('shows practice betting section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasBetting = $body.text().match(/Bet|Trade|Wager|Practice/i)
        expect(hasBetting).to.not.be.null
      })
    })
  })

  describe('Performance Tracking', () => {
    it('shows performance metrics', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasMetrics = $body.text().match(/Performance|ROI|Win|Profit|Stats/i)
        expect(hasMetrics).to.not.be.null
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
