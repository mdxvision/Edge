describe('DFS (Daily Fantasy Sports)', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/dfs')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
    // Wait for page to load (either content or error state)
    cy.contains(/Lineups|Analyzing|error/i, { timeout: 20000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays DFS page', () => {
      cy.url().should('include', '/dfs')
    })

    it('shows DFS heading', () => {
      cy.contains(/DFS|Daily Fantasy|Fantasy Sports|Lineups/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows lineup builder section', () => {
      cy.contains(/Lineups|Build|Optimal/i, { timeout: 15000 }).should('exist')
    })
  })

  describe('Sport Selection', () => {
    it('displays sport options', () => {
      cy.contains(/NFL|NBA|MLB|NHL/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows platform options', () => {
      cy.contains(/DraftKings|FanDuel/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Lineup Types', () => {
    it('shows lineup type options', () => {
      cy.contains(/Balanced|Cash|GPP|Tournament/i, { timeout: 15000 }).should('exist')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
