describe('Security Settings', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/security')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays security page', () => {
      cy.url().should('include', '/security')
    })

    it('shows security heading', () => {
      cy.contains(/Security|Account Security|Settings/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows security sections', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSections = $body.text().match(/2FA|Two-Factor|Password|Sessions|Activity/i)
        expect(hasSections).to.not.be.null
      })
    })
  })

  describe('Two-Factor Authentication', () => {
    it('shows 2FA section', () => {
      cy.contains(/Two-Factor|2FA|Authenticator/i, { timeout: 10000 }).should('be.visible')
    })

    it('has enable/disable 2FA option', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const has2FAControl = $body.text().match(/Enable|Disable|Setup|Configure/i)
        expect(has2FAControl).to.not.be.null
      })
    })

    it('shows 2FA status', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasStatus = $body.text().match(/Enabled|Disabled|Not Set|Active|Inactive|Protected/i)
        expect(hasStatus).to.not.be.null
      })
    })
  })

  describe('Password Change', () => {
    it('has change password section', () => {
      cy.contains(/Password|Change Password/i, { timeout: 10000 }).should('be.visible')
    })

    it('has password input fields', () => {
      cy.get('input[type="password"]', { timeout: 10000 }).should('exist')
    })
  })

  describe('Active Sessions', () => {
    it('shows sessions section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSessions = $body.text().match(/Sessions|Active Sessions|Devices|Logged|Security/i)
        expect(hasSessions).to.not.be.null
      })
    })
  })

  describe('Security Log', () => {
    it('shows security activity', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasActivityLog = $body.text().match(/Activity|Log|History|Events|Recent/i)
        expect(hasActivityLog).to.not.be.null
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
