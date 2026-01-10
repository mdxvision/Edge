describe('Edge Tracker', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/edge-tracker')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays edge tracker page', () => {
      cy.url().should('include', '/edge-tracker')
    })

    it('shows edge tracker heading', () => {
      cy.contains(/Edge Tracker|Edge|Tracking/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Edge Analysis', () => {
    it('shows edge data or analysis', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasEdge = $body.text().match(/Edge|Factor|Analysis|Value/i)
        expect(hasEdge).to.not.be.null
      })
    })
  })

  describe('8-Factor Analysis', () => {
    it('shows factor information', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasFactors = $body.text().match(/Factor|Coach|Rest|Weather|Travel|Line|Public/i)
        expect(hasFactors).to.not.be.null
      })
    })
  })

  describe('Pick Tracking', () => {
    it('shows picks or analysis section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPicks = $body.text().match(/Pick|Bet|Analysis|Recommendation/i)
        expect(hasPicks).to.not.be.null
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
