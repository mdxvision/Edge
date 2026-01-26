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

// Login via API - more reliable than UI in CI
Cypress.Commands.add('loginWithCredentials', (email: string, password: string) => {
  // First try to login - if user doesn't exist, register first
  cy.request({
    method: 'POST',
    url: '/api/auth/login',
    body: {
      email: email,
      password: password
    },
    failOnStatusCode: false
  }).then((loginResponse) => {
    if (loginResponse.status === 200) {
      // Login successful
      const result = loginResponse.body
      cy.window().then((win) => {
        win.localStorage.setItem('session_token', result.access_token)
        win.localStorage.setItem('refresh_token', result.refresh_token)
        if (result.user?.client_id) {
          win.localStorage.setItem('clientId', result.user.client_id.toString())
        }
        win.localStorage.setItem('user', JSON.stringify(result.user))
      })
    } else {
      // User doesn't exist, register first
      cy.request({
        method: 'POST',
        url: '/api/auth/register',
        body: {
          email: email,
          username: 'testuser',
          password: password,
          confirm_password: password
        },
        failOnStatusCode: false
      }).then((registerResponse) => {
        if (registerResponse.status === 200) {
          const result = registerResponse.body
          cy.window().then((win) => {
            win.localStorage.setItem('session_token', result.access_token)
            win.localStorage.setItem('refresh_token', result.refresh_token)
            if (result.user?.client_id) {
              win.localStorage.setItem('clientId', result.user.client_id.toString())
            }
            win.localStorage.setItem('user', JSON.stringify(result.user))
          })
        }
      })
    }
  })
  // Navigate to dashboard after login
  cy.visit('/dashboard')
  cy.url({ timeout: 15000 }).should('include', '/dashboard')
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
