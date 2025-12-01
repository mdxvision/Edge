describe('Dashboard', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('15000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
  })

  describe('Layout', () => {
    it('displays the sidebar navigation', () => {
      cy.get('nav').should('be.visible')
      cy.contains('Dashboard').should('be.visible')
      cy.contains('Games').should('be.visible')
      cy.contains('Recommendations').should('be.visible')
      cy.contains('Profile').should('be.visible')
    })

    it('displays stats cards', () => {
      cy.get('[data-testid="stats-card"], .grid > div').should('have.length.at.least', 1)
    })

    it('shows welcome message or dashboard heading', () => {
      cy.contains(/Dashboard|Welcome/i).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('navigates to games page', () => {
      cy.contains('Games').click()
      cy.url().should('include', '/games')
    })

    it('navigates to recommendations page', () => {
      cy.contains('Recommendations').click()
      cy.url().should('include', '/recommendations')
    })

    it('navigates to profile page', () => {
      cy.contains('Profile').click()
      cy.url().should('include', '/profile')
    })

    it('navigates back to dashboard', () => {
      cy.contains('Games').click()
      cy.url().should('include', '/games')
      cy.contains('Dashboard').click()
      cy.url().should('include', '/dashboard')
    })
  })

  describe('Theme Toggle', () => {
    it('toggles between light and dark mode', () => {
      cy.get('body').then(($body) => {
        const initialHasDark = $body.hasClass('dark')
        cy.get('[data-testid="theme-toggle"], button[aria-label*="theme"], .theme-toggle, button:has(svg)').first().click()
        cy.get('body').should(initialHasDark ? 'not.have.class' : 'have.class', 'dark')
      })
    })
  })
})
