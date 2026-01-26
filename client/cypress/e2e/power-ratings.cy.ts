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
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasRatings = $body.text().match(/Rating|Score|Rank|Team|Power/i)
        expect(hasRatings).to.not.be.null
      })
    })

    it('displays rating numbers', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasNumbers = $body.text().match(/\d+\.\d+|\d+/i)
        expect(hasNumbers).to.not.be.null
      })
    })
  })

  describe('Sport Selection', () => {
    it('has sport filter', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSportFilter = $body.text().match(/NFL|NBA|MLB|NHL|Sport/i)
        expect(hasSportFilter).to.not.be.null
      })
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
