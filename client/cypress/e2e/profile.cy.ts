describe('Profile Settings', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/profile')
    // Wait for page to load
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays profile page', () => {
      cy.url().should('include', '/profile')
    })

    it('shows profile heading', () => {
      cy.contains('Profile', { timeout: 10000 }).should('be.visible')
    })

    it('shows preferences tagline', () => {
      cy.contains('Your preferences', { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Personal Information', () => {
    it('shows personal information section', () => {
      cy.contains(/Personal Information|Client Name/i, { timeout: 10000 }).should('be.visible')
    })

    it('has name input field', () => {
      cy.get('input').should('exist')
    })
  })

  describe('Bankroll Management', () => {
    it('shows bankroll section', () => {
      cy.contains(/Bankroll/i, { timeout: 10000 }).should('be.visible')
    })

    it('has bankroll input', () => {
      cy.get('input[type="number"]').should('exist')
    })
  })

  describe('Risk Profile', () => {
    it('shows risk profile section', () => {
      cy.contains(/Risk Profile/i, { timeout: 10000 }).should('be.visible')
    })

    it('has risk profile selector', () => {
      cy.get('select').should('exist')
    })

    it('shows risk profile description', () => {
      cy.contains(/stake|bankroll/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Save Changes', () => {
    it('has save button', () => {
      cy.contains(/Save/i).should('exist')
    })

    it('can click save button', () => {
      cy.contains('button', /Save/i).click()
      // Wait for success or just verify no error
      cy.wait(1000)
      cy.url().should('include', '/profile')
    })
  })

  describe('Currency Preferences', () => {
    it('shows currency section', () => {
      cy.contains(/Currency/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Telegram Integration', () => {
    it('shows telegram section', () => {
      cy.contains(/Telegram/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Navigation', () => {
    it('can navigate back to dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })
  })
})
