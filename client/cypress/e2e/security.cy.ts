describe('Security Settings', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/security')
    // Wait for page to load
    cy.url().should('include', '/security')
  })

  describe('Page Layout', () => {
    it('displays security page', () => {
      cy.url().should('include', '/security')
    })

    it('shows security heading', () => {
      cy.contains(/Security/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows protected tagline', () => {
      cy.contains(/Protected/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Two-Factor Authentication', () => {
    it('shows 2FA section', () => {
      cy.contains(/Two-Factor|2FA|Authenticator/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows 2FA status', () => {
      cy.contains(/Enabled|Disabled|Not Set|Active|Inactive|Protected|Setup/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Active Sessions', () => {
    it('shows sessions section', () => {
      cy.contains(/Sessions|Active Sessions|Devices/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows session info', () => {
      cy.contains(/Current|Browser|Chrome|Safari|Device/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Security Log', () => {
    it('shows security activity section', () => {
      cy.contains(/Activity|Log|History|Recent/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
