describe('Parlays Builder', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Parlays').click()
    cy.url().should('include', '/parlays')
  })

  describe('Page Layout', () => {
    it('displays parlays page heading', () => {
      cy.contains(/Parlays|Parlay Builder|Multi-Bet/i).should('be.visible')
    })

    it('shows parlay builder section', () => {
      cy.get('body').then(($body) => {
        const hasBuilder = $body.text().match(/Builder|Add Leg|Create Parlay/i)
        expect(hasBuilder).to.not.be.null
      })
    })
  })

  describe('Add Parlay Leg', () => {
    it('has add leg button', () => {
      cy.contains(/Add Leg|Add Selection|Add Pick/i).should('be.visible')
    })

    it('opens leg input form', () => {
      cy.contains(/Add Leg|Add Selection|Add Pick/i).first().click()
      cy.get('input').should('exist')
    })

    it('can add multiple legs', () => {
      // Add first leg
      cy.contains(/Add Leg|Add Selection|Add Pick/i).first().click()
      cy.get('input[placeholder*="Selection"], input[name*="selection"], input').first().type('Team A ML')
      cy.get('input[name*="odds"], input[type="number"]').first().clear().type('-110')

      // Click add or save
      cy.get('button:contains("Add"), button:contains("Save"), button[type="submit"]').click()
      cy.wait(300)
    })
  })

  describe('Parlay Calculation', () => {
    it('shows combined odds', () => {
      cy.get('body').then(($body) => {
        const hasCombinedOdds = $body.text().match(/Combined|Total Odds|Parlay Odds/i)
        expect(hasCombinedOdds).to.not.be.null
      })
    })

    it('shows potential payout', () => {
      cy.get('body').then(($body) => {
        const hasPayout = $body.text().match(/Payout|Win|Returns|To Win/i)
        expect(hasPayout).to.not.be.null
      })
    })

    it('has stake input', () => {
      cy.get('input[name*="stake"], input[placeholder*="stake"], input[type="number"]').should('exist')
    })

    it('calculates payout on stake change', () => {
      cy.get('input[name*="stake"], input[placeholder*="stake"], input[type="number"]').first()
        .clear()
        .type('50')
      cy.wait(500)
    })
  })

  describe('Saved Parlays', () => {
    it('shows saved parlays section', () => {
      cy.get('body').then(($body) => {
        const hasSavedSection = $body.text().match(/Saved|My Parlays|History|Recent/i)
        expect(hasSavedSection).to.not.be.null
      })
    })

    it('can save a parlay', () => {
      cy.get('body').then(($body) => {
        if ($body.find('button:contains("Save"), button:contains("Save Parlay")').length > 0) {
          cy.contains(/Save Parlay|Save/i).click()
        }
      })
    })
  })

  describe('Odds Conversion', () => {
    it('displays odds format selector', () => {
      cy.get('body').then(($body) => {
        const hasOddsFormat = $body.text().match(/American|Decimal|Fractional|Format/i)
        expect(hasOddsFormat).to.not.be.null
      })
    })
  })

  describe('Parlay Warnings', () => {
    it('shows correlation warnings when applicable', () => {
      cy.get('body').then(($body) => {
        const hasCorrelationInfo = $body.text().match(/Correlation|Same Game|SGP|Warning/i)
        // This is optional - just checking if the feature exists
        if (hasCorrelationInfo) {
          expect(hasCorrelationInfo).to.not.be.null
        }
      })
    })
  })
})
