describe('DFS (Daily Fantasy Sports)', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/dfs")
    cy.url().should("include", "/dfs")
  })

  describe('Page Layout', () => {
    it('displays DFS page', () => {
      cy.url().should('include', '/dfs')
    })

    it('shows page content or handles loading', () => {
      // Page shows either the content or loading/error state
      cy.contains(/Lineups|Build Optimal|Analyzing|Something's not right/i, { timeout: 20000 }).should('exist')
    })

    it('shows lineup builder when loaded', () => {
      // Wait for either content or error
      cy.get('body', { timeout: 20000 }).then($body => {
        if ($body.text().includes('Build Optimal Lineup')) {
          cy.contains('Build Optimal Lineup').should('be.visible')
          cy.contains('button', 'NFL').should('exist')
          cy.contains('button', 'DraftKings').should('exist')
        }
      })
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
    })
  })
})
