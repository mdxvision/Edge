describe('Pricing', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/pricing')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays pricing page', () => {
      cy.url().should('include', '/pricing')
    })

    it('shows pricing heading', () => {
      cy.contains(/Pricing|Plans|Subscription/i, { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Pricing Plans', () => {
    it('shows pricing tiers', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasTiers = $body.text().match(/Free|Pro|Premium|Basic|Plan/i)
        expect(hasTiers).to.not.be.null
      })
    })

    it('shows pricing amounts', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPricing = $body.text().match(/\$|Free|month|year/i)
        expect(hasPricing).to.not.be.null
      })
    })
  })

  describe('Features List', () => {
    it('shows features or benefits', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasFeatures = $body.text().match(/Feature|Include|Access|Unlimited/i)
        expect(hasFeatures).to.not.be.null
      })
    })
  })

  describe('Call to Action', () => {
    it('has subscription or upgrade buttons', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasCTA = $body.text().match(/Subscribe|Upgrade|Get Started|Select|Choose/i)
        expect(hasCTA).to.not.be.null
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
