describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
  })

  describe('Login Page', () => {
    it('displays login form when not authenticated', () => {
      cy.get('input[name="name"]').should('be.visible')
      cy.get('input[name="bankroll"]').should('be.visible')
      cy.get('button[type="submit"]').should('be.visible')
    })

    it('shows the EdgeBet branding', () => {
      cy.contains('EdgeBet').should('be.visible')
    })

    it('requires name field to be filled', () => {
      cy.get('input[name="bankroll"]').type('10000')
      cy.get('button[type="submit"]').click()
      cy.get('input[name="name"]:invalid').should('exist')
    })

    it('requires bankroll field to be filled', () => {
      cy.get('input[name="name"]').type('Test User')
      cy.get('input[name="bankroll"]').clear()
      cy.get('button[type="submit"]').click()
      cy.get('input[name="bankroll"]:invalid').should('exist')
    })

    it('successfully creates account and redirects to dashboard', () => {
      const testName = `Test User ${Date.now()}`
      cy.get('input[name="name"]').type(testName)
      cy.get('input[name="bankroll"]').clear().type('10000')
      cy.get('button[type="submit"]').click()
      
      cy.url().should('include', '/dashboard')
      cy.contains('Dashboard').should('be.visible')
    })
  })

  describe('Logout', () => {
    beforeEach(() => {
      const testName = `Test User ${Date.now()}`
      cy.get('input[name="name"]').type(testName)
      cy.get('input[name="bankroll"]').clear().type('10000')
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/dashboard')
    })

    it('logs out user and redirects to login', () => {
      cy.contains('Logout').click()
      cy.get('input[name="name"]').should('be.visible')
    })
  })

  describe('Session Persistence', () => {
    it('maintains session after page reload', () => {
      const testName = `Test User ${Date.now()}`
      cy.get('input[name="name"]').type(testName)
      cy.get('input[name="bankroll"]').clear().type('10000')
      cy.get('button[type="submit"]').click()
      
      cy.url().should('include', '/dashboard')
      
      cy.reload()
      
      cy.url().should('include', '/dashboard')
      cy.contains('Dashboard').should('be.visible')
    })
  })
})
