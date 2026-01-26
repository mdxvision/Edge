describe('Dashboard', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit("/dashboard")
    cy.url().should("include", "/dashboard")
    // Wait for loading to complete (shows "Analyzing..." while loading)
    cy.url().should('include', '/dashboard')
  })

  describe('Layout', () => {
    it('displays the sidebar navigation', () => {
      cy.get('nav, aside').should('be.visible')
      cy.contains('Today').should('be.visible')
      cy.contains('Matchups').should('be.visible')
      cy.contains('Picks').should('be.visible')
    })

    it('displays stats cards after loading', () => {
      // Wait for dashboard to load past "Analyzing..."
      cy.get('[data-testid="stats-card"]', { timeout: 20000 }).should('have.length.at.least', 1)
    })

    it('shows greeting message after loading', () => {
      cy.contains(/Good (morning|afternoon|evening)/i, { timeout: 20000 }).should('be.visible')
    })

    it('shows bankroll', () => {
      cy.contains('Bankroll', { timeout: 20000 }).should('be.visible')
    })

    it('shows curated picks stat', () => {
      cy.contains('Curated Picks', { timeout: 20000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('navigates to games page', () => {
      cy.contains('Matchups').click()
      cy.url().should('include', '/games')
    })

    it('navigates to recommendations page', () => {
      cy.contains('Picks').click()
      cy.url().should('include', '/recommendations')
    })

    it('navigates to profile page', () => {
      // Profile link may be covered by nav element on certain screen sizes
      cy.contains(/Profile|Settings/i).first().click({ force: true })
      cy.url().should('include', '/profile')
    })

    it('navigates back to dashboard', () => {
      cy.contains('Matchups').click()
      cy.url().should('include', '/games')
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })

  describe('Quick Picks Section', () => {
    it('displays Quick Picks section', () => {
      cy.contains('Quick Picks', { timeout: 20000 }).should('be.visible')
    })

    it('has See All link', () => {
      cy.contains('See All', { timeout: 20000 }).should('be.visible')
    })
  })

  describe('Theme Toggle', () => {
    it('has theme toggle option', () => {
      cy.contains(/Light Mode|Dark Mode/i).should('exist')
    })
  })
})
