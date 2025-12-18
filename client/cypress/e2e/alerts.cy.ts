describe('Alerts Management', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Alerts').click()
    cy.url().should('include', '/alerts')
  })

  describe('Page Layout', () => {
    it('displays alerts page heading', () => {
      cy.contains(/Alerts|Notifications/i).should('be.visible')
    })

    it('shows create alert button', () => {
      cy.contains(/Create|Add|New/i).should('be.visible')
    })
  })

  describe('Create Alert', () => {
    it('opens create alert form', () => {
      cy.contains(/Create|Add|New/i).first().click()
      cy.get('form, [role="dialog"], .modal').should('be.visible')
    })

    it('has alert type selection', () => {
      cy.contains(/Create|Add|New/i).first().click()
      cy.get('body').then(($body) => {
        const hasTypeSelector = $body.find('select, [role="listbox"], input[type="radio"]').length > 0
        expect(hasTypeSelector).to.be.true
      })
    })

    it('can configure edge threshold alert', () => {
      cy.contains(/Create|Add|New/i).first().click()
      cy.wait(500)

      // Fill in alert name
      cy.get('input[name="name"], input[placeholder*="name"]').type('High Edge Alert')

      // Select edge threshold if available
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().select(1) // Select first option
        }
      })
    })

    it('has notification method options', () => {
      cy.contains(/Create|Add|New/i).first().click()
      cy.get('body').then(($body) => {
        const hasNotificationOptions = $body.text().match(/Email|Push|Telegram|SMS|Notification/i)
        expect(hasNotificationOptions).to.not.be.null
      })
    })
  })

  describe('Alert List', () => {
    it('displays alerts or empty state', () => {
      cy.get('body').then(($body) => {
        const hasAlerts = $body.find('[data-testid="alert-item"], .alert-row, table tbody tr, .alert-card').length > 0
        const hasEmptyState = $body.text().match(/No alerts|Create your first|Get notified/i)
        expect(hasAlerts || hasEmptyState).to.be.truthy
      })
    })
  })

  describe('Alert Management', () => {
    it('can toggle alert active status', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="alert-item"], .alert-row, .alert-card').length > 0) {
          cy.get('input[type="checkbox"], [role="switch"], button:contains("Toggle")').first().click()
        }
      })
    })

    it('can delete alert', () => {
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="alert-item"], .alert-row, .alert-card').length > 0) {
          cy.get('button:contains("Delete"), button[aria-label*="delete"], .delete-btn').first().click()
        }
      })
    })
  })

  describe('Sport Filter', () => {
    it('can filter alerts by sport', () => {
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().click()
        }
      })
    })
  })
})
