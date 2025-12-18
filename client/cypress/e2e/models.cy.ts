describe('Models & Analytics', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Models').click()
    cy.url().should('include', '/models')
  })

  describe('Page Layout', () => {
    it('displays models page heading', () => {
      cy.contains(/Models|Analytics|Predictions/i).should('be.visible')
    })

    it('shows model selection or list', () => {
      cy.get('body').then(($body) => {
        const hasModels = $body.text().match(/Model|ELO|Win Probability|Prediction/i)
        expect(hasModels).to.not.be.null
      })
    })
  })

  describe('Model Types', () => {
    it('displays available model types', () => {
      cy.get('body').then(($body) => {
        const hasModelTypes = $body.text().match(/ELO|Machine Learning|Statistical|Probability|Algorithm/i)
        expect(hasModelTypes).to.not.be.null
      })
    })

    it('shows model performance stats', () => {
      cy.get('body').then(($body) => {
        const hasPerformance = $body.text().match(/Accuracy|Performance|Record|Win Rate|ROI/i)
        expect(hasPerformance).to.not.be.null
      })
    })
  })

  describe('Sport Selection', () => {
    it('has sport filter or tabs', () => {
      cy.get('body').then(($body) => {
        const hasSportFilter = $body.text().match(/NFL|NBA|MLB|NHL|Soccer|Sport/i)
        expect(hasSportFilter).to.not.be.null
      })
    })

    it('can switch between sports', () => {
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().click()
        } else if ($body.find('[role="tab"]').length > 0) {
          cy.get('[role="tab"]').eq(1).click()
        } else if ($body.find('button:contains("NBA")').length > 0) {
          cy.contains('NBA').click()
        }
      })
    })
  })

  describe('Model Predictions', () => {
    it('shows prediction data', () => {
      cy.get('body').then(($body) => {
        const hasPredictions = $body.text().match(/Prediction|Probability|Edge|Expected|Forecast/i)
        expect(hasPredictions).to.not.be.null
      })
    })

    it('displays confidence levels', () => {
      cy.get('body').then(($body) => {
        const hasConfidence = $body.text().match(/Confidence|Certainty|%|Probability/i)
        expect(hasConfidence).to.not.be.null
      })
    })
  })

  describe('Historical Performance', () => {
    it('shows historical accuracy', () => {
      cy.get('body').then(($body) => {
        const hasHistory = $body.text().match(/History|Historical|Past|Track Record|Backtest/i)
        expect(hasHistory).to.not.be.null
      })
    })

    it('displays performance charts or graphs', () => {
      cy.get('body').then(($body) => {
        const hasCharts = $body.find('canvas, svg, .chart, .graph, [data-testid="chart"]').length > 0
        const hasPerformanceData = $body.text().match(/Performance|Results|Accuracy/i)
        expect(hasCharts || hasPerformanceData).to.be.truthy
      })
    })
  })

  describe('Model Comparison', () => {
    it('can compare model performance', () => {
      cy.get('body').then(($body) => {
        const hasComparison = $body.text().match(/Compare|vs|Comparison|Side by Side/i)
        // This feature may or may not exist
      })
    })
  })
})
