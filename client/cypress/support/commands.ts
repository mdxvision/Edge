declare global {
  namespace Cypress {
    interface Chainable {
      login(name: string, bankroll: number): Chainable<void>
      logout(): Chainable<void>
      clearLocalStorage(): Chainable<void>
    }
  }
}

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

Cypress.Commands.add('logout', () => {
  window.localStorage.removeItem('client')
})

Cypress.Commands.add('clearLocalStorage', () => {
  window.localStorage.clear()
})

export {}
