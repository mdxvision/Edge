describe('Models & Analytics', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/models')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays models page', () => {
      cy.url().should('include', '/models')
    })

    it('shows models or analytics heading', () => {
      cy.contains(/Intelligence|Models|Analytics|Predictions/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows model information', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasModels = $body.text().match(/Model|ELO|Probability|Prediction|Factor/i)
        expect(hasModels).to.not.be.null
      })
    })
  })

  describe('Model Types', () => {
    it('displays model types or categories', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasModelTypes = $body.text().match(/ELO|Machine Learning|Statistical|Algorithm|Factor/i)
        expect(hasModelTypes).to.not.be.null
      })
    })

    it('shows model performance or accuracy', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPerformance = $body.text().match(/Accuracy|Performance|Record|Win|ROI|%/i)
        expect(hasPerformance).to.not.be.null
      })
    })
  })

  describe('Sport Selection', () => {
    it('has sport filter or tabs', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSportFilter = $body.text().match(/NFL|NBA|MLB|NHL|Soccer|Sport/i)
        expect(hasSportFilter).to.not.be.null
      })
    })
  })

  describe('Predictions Display', () => {
    it('shows prediction data', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPredictions = $body.text().match(/Prediction|Probability|Edge|Expected|Confidence/i)
        expect(hasPredictions).to.not.be.null
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
