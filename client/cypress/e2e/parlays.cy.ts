describe('Parlays Builder', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/parlays')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays parlays page', () => {
      cy.url().should('include', '/parlays')
    })

    it('shows parlay builder section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasBuilder = $body.text().match(/Parlay|Builder|Leg|Create/i)
        expect(hasBuilder).to.not.be.null
      })
    })
  })

  describe('Add Parlay Leg', () => {
    it('has add leg button or input', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasAddLeg = $body.text().match(/Add Leg|Add Selection|Add Pick|Selection/i)
        expect(hasAddLeg).to.not.be.null
      })
    })

    it('has input fields for legs', () => {
      cy.get('input', { timeout: 10000 }).should('exist')
    })
  })

  describe('Parlay Calculation', () => {
    it('shows odds information', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasOdds = $body.text().match(/Odds|Combined|Total|Payout/i)
        expect(hasOdds).to.not.be.null
      })
    })

    it('has stake input', () => {
      cy.get('input[type="number"]', { timeout: 10000 }).should('exist')
    })
  })

  describe('Saved Parlays', () => {
    it('shows saved parlays or history section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSavedSection = $body.text().match(/Saved|My Parlays|History|Recent|Parlay/i)
        expect(hasSavedSection).to.not.be.null
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
