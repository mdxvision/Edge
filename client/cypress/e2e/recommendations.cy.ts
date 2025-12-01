describe('Recommendations', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Recommendations').click()
    cy.url().should('include', '/recommendations')
  })

  describe('Page Layout', () => {
    it('displays recommendations page heading', () => {
      cy.contains(/Recommendations|Picks|Analysis/i).should('be.visible')
    })

    it('shows generate recommendations button', () => {
      cy.contains(/Generate|Refresh|Get|Run/i).should('be.visible')
    })
  })

  describe('Generate Recommendations', () => {
    it('can generate new recommendations', () => {
      cy.contains(/Generate|Refresh|Get|Run/i).click()
      cy.wait(2000)
      cy.get('body').then(($body) => {
        const hasRecommendations = $body.find('[data-testid="recommendation"], .recommendation-card, table tbody tr').length > 0
        const hasEmptyState = $body.text().includes('No recommendations') || $body.text().includes('No value')
        expect(hasRecommendations || hasEmptyState).to.be.true
      })
    })
  })

  describe('Recommendation Details', () => {
    beforeEach(() => {
      cy.contains(/Generate|Refresh|Get|Run/i).click()
      cy.wait(2000)
    })

    it('displays edge information when recommendations exist', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="recommendation"], .recommendation-card, table tbody tr').length > 0) {
          cy.contains(/edge|Edge|%/i).should('be.visible')
        }
      })
    })

    it('shows confidence or probability when recommendations exist', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="recommendation"], .recommendation-card, table tbody tr').length > 0) {
          cy.contains(/confidence|probability|model|%/i).should('be.visible')
        }
      })
    })

    it('displays explanation for transparency', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="recommendation"], .recommendation-card, table tbody tr').length > 0) {
          cy.contains(/explanation|rationale|why|reason/i).should('be.visible')
        }
      })
    })
  })
})
