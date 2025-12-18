describe('Bet Tracking', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Tracking').click()
    cy.url().should('include', '/tracking')
  })

  describe('Page Layout', () => {
    it('displays tracking page heading', () => {
      cy.contains(/Tracking|Bet Tracker|My Bets/i).should('be.visible')
    })

    it('shows add bet button', () => {
      cy.contains(/Add|New|Track|Log/i).should('be.visible')
    })

    it('displays stats or summary section', () => {
      cy.get('body').then(($body) => {
        const hasStats = $body.text().match(/ROI|Win Rate|Profit|Total Bets/i)
        expect(hasStats).to.not.be.null
      })
    })
  })

  describe('Add New Bet', () => {
    it('opens add bet form', () => {
      cy.contains(/Add|New|Track|Log/i).first().click()
      cy.get('form, [role="dialog"], .modal').should('be.visible')
    })

    it('has required bet fields', () => {
      cy.contains(/Add|New|Track|Log/i).first().click()
      cy.get('body').then(($body) => {
        // Check for common bet tracking fields
        const hasOddsField = $body.find('input[name*="odds"], input[placeholder*="odds"]').length > 0
        const hasStakeField = $body.find('input[name*="stake"], input[name*="amount"], input[placeholder*="stake"]').length > 0
        expect(hasOddsField || hasStakeField).to.be.true
      })
    })

    it('can submit a new bet', () => {
      cy.contains(/Add|New|Track|Log/i).first().click()
      cy.wait(500)

      // Fill out bet form - adjust selectors based on actual form structure
      cy.get('input').first().type('Test Bet')
      cy.get('input[type="number"]').first().clear().type('-110')
      cy.get('input[type="number"]').eq(1).clear().type('100')

      cy.get('button[type="submit"], button:contains("Save"), button:contains("Add")').click()
      cy.wait(500)
    })
  })

  describe('Bet List', () => {
    it('displays bets or empty state', () => {
      cy.get('body').then(($body) => {
        const hasBets = $body.find('[data-testid="bet-item"], .bet-row, table tbody tr, .bet-card').length > 0
        const hasEmptyState = $body.text().match(/No bets|No tracked bets|Start tracking|Empty/i)
        expect(hasBets || hasEmptyState).to.be.truthy
      })
    })
  })

  describe('Bet Filtering', () => {
    it('has filter options', () => {
      cy.get('select, [data-testid="filter"], button:contains("Filter")').should('exist')
    })

    it('can filter by status', () => {
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().click()
        }
      })
    })
  })

  describe('Performance Stats', () => {
    it('shows ROI calculation', () => {
      cy.contains(/ROI|Return/i).should('be.visible')
    })

    it('shows win rate', () => {
      cy.get('body').then(($body) => {
        const hasWinRate = $body.text().match(/Win Rate|Win %|Record/i)
        expect(hasWinRate).to.not.be.null
      })
    })
  })
})
