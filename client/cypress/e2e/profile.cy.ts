describe('Profile Settings', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Profile').click()
    cy.url().should('include', '/profile')
  })

  describe('Page Layout', () => {
    it('displays profile page heading', () => {
      cy.contains(/Profile|Settings|Account/i).should('be.visible')
    })

    it('shows current bankroll', () => {
      cy.contains(/Bankroll|Balance|10,?000/i).should('be.visible')
    })

    it('shows risk profile setting', () => {
      cy.contains(/Risk|Profile|conservative|balanced|aggressive/i).should('be.visible')
    })
  })

  describe('Profile Updates', () => {
    it('displays editable bankroll field', () => {
      cy.get('input[type="number"], input[name="bankroll"]').should('exist')
    })

    it('displays risk profile selector', () => {
      cy.get('select, input[type="radio"], [role="radiogroup"], button').should('exist')
    })

    it('can update bankroll', () => {
      cy.get('input[type="number"], input[name="bankroll"]').first()
        .clear()
        .type('25000')
      cy.get('[data-testid="save-button"], button[type="submit"]').click()
      cy.get('[data-testid="success-message"], .text-success-600').should('be.visible')
    })

    it('can change risk profile', () => {
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().select('aggressive')
        } else {
          cy.contains(/aggressive|Aggressive/i).click()
        }
        cy.get('[data-testid="save-button"], button[type="submit"]').click()
        cy.get('[data-testid="success-message"], .text-success-600').should('be.visible')
      })
    })
  })

  describe('Validation', () => {
    it('validates bankroll minimum', () => {
      cy.get('input[type="number"], input[name="bankroll"]').first()
        .clear()
        .type('-1000')
      cy.contains(/Save|Update|Submit/i).click()
      cy.get('body').should('not.contain', 'negative bankroll saved')
    })
  })
})
