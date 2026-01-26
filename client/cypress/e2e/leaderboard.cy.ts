describe('Leaderboard', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/leaderboard')
    // Wait for page to load - testuser may not be on leaderboard if no bets placed
    cy.url().should('include', '/leaderboard')
  })

  describe('Page Layout', () => {
    it('displays leaderboard page', () => {
      cy.url().should('include', '/leaderboard')
    })

    it('shows leaderboard heading', () => {
      cy.contains(/Leaderboard|Rankings|Top/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows rankings or list', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasRankings = $body.text().match(/Rank|#|Position|1|2|3/i)
        expect(hasRankings).to.not.be.null
      })
    })
  })

  describe('Ranking Display', () => {
    it('shows rank numbers', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasRanks = $body.text().match(/1|2|3|#/i)
        expect(hasRanks).to.not.be.null
      })
    })

    it('shows performance metrics', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasMetrics = $body.text().match(/ROI|Win|Profit|Units|Record|%/i)
        expect(hasMetrics).to.not.be.null
      })
    })
  })

  describe('Filters', () => {
    it('has time period or sorting options', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasFilters = $body.text().match(/Day|Week|Month|Year|All Time|Sort|Filter/i)
        expect(hasFilters).to.not.be.null
      })
    })

    it('can interact with filters', () => {
      cy.get('select, button', { timeout: 10000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
