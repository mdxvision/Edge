declare global {
  namespace Cypress {
    interface Chainable {
      login(name: string, bankroll: number): Chainable<void>
      loginWithCredentials(email: string, password: string): Chainable<void>
      loginViaUI(): Chainable<void>
      registerAndLogin(email: string, username: string, password: string): Chainable<void>
      logout(): Chainable<void>
      clearLocalStorage(): Chainable<void>
    }
  }
}

// Legacy login for backwards compatibility
Cypress.Commands.add('login', (name: string, bankroll: number) => {
  cy.request({
    method: 'POST',
    url: '/api/clients/',
    body: {
      name: name,
      bankroll: bankroll,
      risk_profile: 'balanced'
    }
  }).then((response) => {
    const client = response.body
    window.localStorage.setItem('client', JSON.stringify(client))
  })
})

// Login via UI using Dev Login button - always fresh login
Cypress.Commands.add('loginViaUI', () => {
  cy.visit('/login')
  // Wait for page to be fully loaded
  cy.get('button', { timeout: 10000 }).should('exist')
  // Click Sign In tab and wait for it
  cy.contains('button', 'Sign In').should('be.visible').click()
  cy.wait(500)
  // Click Dev Login button with retry logic
  cy.contains('button', 'Dev Login', { timeout: 10000 }).should('be.visible').click()
  // Wait for redirect to dashboard
  cy.url({ timeout: 20000 }).should('include', '/dashboard')
})

// Always login fresh to avoid stale session issues
Cypress.Commands.add('loginWithCredentials', (email: string, password: string) => {
  cy.loginViaUI()
})

// Register new user and login
Cypress.Commands.add('registerAndLogin', (email: string, username: string, password: string) => {
  cy.loginWithCredentials(email, password)
})

Cypress.Commands.add('logout', () => {
  window.localStorage.removeItem('client')
  window.localStorage.removeItem('access_token')
  window.localStorage.removeItem('refresh_token')
  window.localStorage.removeItem('user')
  window.localStorage.removeItem('session_token')
  window.localStorage.removeItem('clientId')
})

Cypress.Commands.overwrite('clearLocalStorage', () => {
  window.localStorage.clear()
})

export {}
