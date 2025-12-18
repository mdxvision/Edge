declare global {
  namespace Cypress {
    interface Chainable {
      login(name: string, bankroll: number): Chainable<void>
      loginWithCredentials(email: string, password: string): Chainable<void>
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

// JWT-based login
Cypress.Commands.add('loginWithCredentials', (email: string, password: string) => {
  cy.request({
    method: 'POST',
    url: '/api/auth/login',
    body: {
      email_or_username: email,
      password: password
    }
  }).then((response) => {
    const { access_token, refresh_token, user } = response.body
    window.localStorage.setItem('access_token', access_token)
    window.localStorage.setItem('refresh_token', refresh_token)
    window.localStorage.setItem('user', JSON.stringify(user))
  })
})

// Register new user and login
Cypress.Commands.add('registerAndLogin', (email: string, username: string, password: string) => {
  cy.request({
    method: 'POST',
    url: '/api/auth/register',
    body: {
      email: email,
      username: username,
      password: password,
      initial_bankroll: 10000,
      risk_profile: 'balanced'
    },
    failOnStatusCode: false
  }).then((response) => {
    if (response.status === 200) {
      const { access_token, refresh_token, user } = response.body
      window.localStorage.setItem('access_token', access_token)
      window.localStorage.setItem('refresh_token', refresh_token)
      window.localStorage.setItem('user', JSON.stringify(user))
    } else {
      // User might already exist, try login
      cy.loginWithCredentials(email, password)
    }
  })
})

Cypress.Commands.add('logout', () => {
  window.localStorage.removeItem('client')
  window.localStorage.removeItem('access_token')
  window.localStorage.removeItem('refresh_token')
  window.localStorage.removeItem('user')
})

Cypress.Commands.add('clearLocalStorage', () => {
  window.localStorage.clear()
})

export {}
