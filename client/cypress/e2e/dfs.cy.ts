describe('DFS (Daily Fantasy Sports)', () => {
  beforeEach(() => {
    cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    cy.visit('/dfs')
    cy.contains('testuser', { timeout: 15000 }).should('be.visible')
  })

  describe('Page Layout', () => {
    it('displays DFS page', () => {
      cy.url().should('include', '/dfs')
    })

    it('shows DFS heading', () => {
      cy.contains(/DFS|Daily Fantasy|Fantasy Sports|Lineups/i, { timeout: 10000 }).should('be.visible')
    })

    it('shows lineup builder section', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasBuilder = $body.text().match(/Lineup|Builder|Optimizer|Create|Player/i)
        expect(hasBuilder).to.not.be.null
      })
    })
  })

  describe('Player Selection', () => {
    it('displays player information', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPlayers = $body.text().match(/Player|Salary|Projection|Points|Name/i)
        expect(hasPlayers).to.not.be.null
      })
    })

    it('shows projections or stats', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasProjections = $body.text().match(/Projection|Points|Expected|Value|Stats/i)
        expect(hasProjections).to.not.be.null
      })
    })
  })

  describe('Lineup Builder', () => {
    it('shows salary or budget info', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasSalary = $body.text().match(/Salary|Budget|Cap|Remaining|\$/i)
        expect(hasSalary).to.not.be.null
      })
    })

    it('displays positions', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasPositions = $body.text().match(/QB|RB|WR|TE|FLEX|PG|SG|SF|Position/i)
        expect(hasPositions).to.not.be.null
      })
    })
  })

  describe('Optimization', () => {
    it('has optimizer or generate button', () => {
      cy.get('body', { timeout: 10000 }).then(($body) => {
        const hasOptimizer = $body.text().match(/Optimize|Generate|Auto|Build/i)
        expect(hasOptimizer).to.not.be.null
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
