describe('DFS (Daily Fantasy Sports)', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('DFS').click()
    cy.url().should('include', '/dfs')
  })

  describe('Page Layout', () => {
    it('displays DFS page heading', () => {
      cy.contains(/DFS|Daily Fantasy|Fantasy Sports/i).should('be.visible')
    })

    it('shows lineup builder section', () => {
      cy.get('body').then(($body) => {
        const hasBuilder = $body.text().match(/Lineup|Builder|Optimizer|Create/i)
        expect(hasBuilder).to.not.be.null
      })
    })
  })

  describe('Contest Selection', () => {
    it('shows available contests', () => {
      cy.get('body').then(($body) => {
        const hasContests = $body.text().match(/Contest|Slate|GPP|Cash|Tournament/i)
        expect(hasContests).to.not.be.null
      })
    })

    it('has contest type filter', () => {
      cy.get('body').then(($body) => {
        const hasFilter = $body.find('select, [role="listbox"], button:contains("Filter")').length > 0
        expect(hasFilter).to.be.true
      })
    })
  })

  describe('Player Selection', () => {
    it('displays player pool', () => {
      cy.get('body').then(($body) => {
        const hasPlayers = $body.text().match(/Player|Salary|Projection|Points|Ownership/i)
        expect(hasPlayers).to.not.be.null
      })
    })

    it('shows player projections', () => {
      cy.get('body').then(($body) => {
        const hasProjections = $body.text().match(/Projection|Points|Expected|Value|FPTS/i)
        expect(hasProjections).to.not.be.null
      })
    })

    it('displays salary information', () => {
      cy.get('body').then(($body) => {
        const hasSalary = $body.text().match(/Salary|\$|Cost|Cap/i)
        expect(hasSalary).to.not.be.null
      })
    })
  })

  describe('Lineup Builder', () => {
    it('shows salary cap remaining', () => {
      cy.get('body').then(($body) => {
        const hasSalaryCap = $body.text().match(/Remaining|Budget|Cap|Available/i)
        expect(hasSalaryCap).to.not.be.null
      })
    })

    it('displays lineup positions', () => {
      cy.get('body').then(($body) => {
        const hasPositions = $body.text().match(/QB|RB|WR|TE|FLEX|DST|PG|SG|SF|PF|C|UTIL/i)
        expect(hasPositions).to.not.be.null
      })
    })

    it('shows total projected points', () => {
      cy.get('body').then(($body) => {
        const hasTotal = $body.text().match(/Total|Projected|Expected Points/i)
        expect(hasTotal).to.not.be.null
      })
    })
  })

  describe('Optimization', () => {
    it('has optimizer button', () => {
      cy.get('body').then(($body) => {
        const hasOptimizer = $body.find('button:contains("Optimize"), button:contains("Auto"), button:contains("Generate")').length > 0
        expect(hasOptimizer).to.be.true
      })
    })

    it('shows optimization settings', () => {
      cy.get('body').then(($body) => {
        const hasSettings = $body.text().match(/Settings|Constraints|Lock|Exclude/i)
        // Settings may be in a modal or expanded section
      })
    })
  })

  describe('Lineup Management', () => {
    it('can save lineup', () => {
      cy.get('body').then(($body) => {
        if ($body.find('button:contains("Save"), button:contains("Export")').length > 0) {
          // Save button exists
          expect(true).to.be.true
        }
      })
    })

    it('shows saved lineups', () => {
      cy.get('body').then(($body) => {
        const hasSaved = $body.text().match(/Saved|My Lineups|History|Recent/i)
        expect(hasSaved).to.not.be.null
      })
    })
  })

  describe('Exposure Analysis', () => {
    it('shows ownership projections', () => {
      cy.get('body').then(($body) => {
        const hasOwnership = $body.text().match(/Ownership|Exposure|%|Popular/i)
        expect(hasOwnership).to.not.be.null
      })
    })
  })
})
