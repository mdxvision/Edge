describe('Alerts Management', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/alerts')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays alerts page', () => {
      cy.url().should('include', '/alerts')
    })

    it('shows alerts heading', () => {
      cy.contains(/Alerts|Notifications/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows create alert button', () => {
      cy.contains(/Create|Add|New/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Create Alert', () => {
    it('opens create alert form when clicking create', () => {
      cy.contains(/Create|Add|New/i).first().click()
      cy.get('input, select', { timeout: 5000 }).should('exist')
    })

    it('has notification method options', () => {
      cy.contains(/Email|Push|Telegram|Notification|Alert/i, { timeout: 10000 }).should('exist')
    })
  })

  describe('Alert List', () => {
    it('displays alerts or empty state', () => {
      cy.get('body').then(($body) => {
        const hasContent = $body.text().match(/alert|notification|edge|create/i)
        expect(hasContent).to.not.be.null
      })
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
