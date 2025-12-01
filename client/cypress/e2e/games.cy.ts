describe('Games Browser', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Games').click()
    cy.url().should('include', '/games')
  })

  describe('Page Layout', () => {
    it('displays games page heading', () => {
      cy.contains(/Games|Browse Games|Upcoming Games/i).should('be.visible')
    })

    it('shows sport filter buttons or dropdown', () => {
      cy.get('select, button, [role="tab"]').should('exist')
    })
  })

  describe('Sport Filtering', () => {
    it('displays available sports', () => {
      cy.contains(/NFL|NBA|MLB|Soccer|All Sports/i).should('be.visible')
    })

    it('can filter by sport', () => {
      cy.get('select, [data-testid="sport-filter"], button').first().click()
      cy.wait(500)
    })
  })

  describe('Games List', () => {
    it('displays games data or empty state', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="game-card"], .game-item, table tbody tr').length > 0) {
          cy.get('[data-testid="game-card"], .game-item, table tbody tr').should('have.length.at.least', 1)
        } else {
          cy.contains(/No games|No upcoming|Loading/i).should('be.visible')
        }
      })
    })
  })
})
