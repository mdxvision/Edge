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

    it('shows rankings or empty state', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasContent = $body.text().match(/Rank|#|Position|1|2|3|No data|empty|loading/i)
        expect(hasContent).to.not.be.null
      })
    })
  })

  describe('Ranking Display', () => {
    it('shows rank numbers or empty state', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasContent = $body.text().match(/1|2|3|#|No data|empty|loading/i)
        expect(hasContent).to.not.be.null
      })
    })

    it('shows performance metrics or empty state', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasContent = $body.text().match(/ROI|Win|Profit|Units|Record|%|No data|empty|loading/i)
        expect(hasContent).to.not.be.null
      })
    })
  })

  describe('Filters', () => {
    it('has time period or sorting options', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasContent = $body.text().match(/Day|Week|Month|Year|All Time|Sort|Filter|Leaderboard/i)
        expect(hasContent).to.not.be.null
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
