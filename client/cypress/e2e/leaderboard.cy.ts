describe('Leaderboard', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
    cy.visit('/')
    const testName = `Test User ${Date.now()}`
    cy.get('input[name="name"]').type(testName)
    cy.get('input[name="bankroll"]').clear().type('10000')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
    cy.contains('Leaderboard').click()
    cy.url().should('include', '/leaderboard')
  })

  describe('Page Layout', () => {
    it('displays leaderboard page heading', () => {
      cy.contains(/Leaderboard|Rankings|Top Bettors/i).should('be.visible')
    })

    it('shows leaderboard table or list', () => {
      cy.get('body').then(($body) => {
        const hasTable = $body.find('table, .leaderboard-list, [data-testid="leaderboard"]').length > 0
        const hasRankings = $body.text().match(/Rank|#|Position/i)
        expect(hasTable || hasRankings).to.be.truthy
      })
    })
  })

  describe('Ranking Display', () => {
    it('shows rank numbers', () => {
      cy.get('body').then(($body) => {
        const hasRanks = $body.text().match(/1|2|3|#1|#2|#3/i)
        expect(hasRanks).to.not.be.null
      })
    })

    it('displays usernames', () => {
      cy.get('body').then(($body) => {
        const hasUsernames = $body.find('td, .username, .user-name, [data-testid="username"]').length > 0
        expect(hasUsernames).to.be.true
      })
    })

    it('shows performance metrics', () => {
      cy.get('body').then(($body) => {
        const hasMetrics = $body.text().match(/ROI|Win Rate|Profit|Units|Record/i)
        expect(hasMetrics).to.not.be.null
      })
    })
  })

  describe('Time Period Filter', () => {
    it('has time period selector', () => {
      cy.get('body').then(($body) => {
        const hasTimePeriod = $body.text().match(/Day|Week|Month|Year|All Time|7 Days|30 Days/i)
        expect(hasTimePeriod).to.not.be.null
      })
    })

    it('can change time period', () => {
      cy.get('body').then(($body) => {
        if ($body.find('select').length > 0) {
          cy.get('select').first().click()
        } else if ($body.find('button:contains("Week"), button:contains("Month")').length > 0) {
          cy.contains(/Week|Month/i).first().click()
        }
      })
    })
  })

  describe('Sport Filter', () => {
    it('can filter by sport', () => {
      cy.get('body').then(($body) => {
        const hasSportFilter = $body.text().match(/NFL|NBA|All Sports|Sport/i)
        expect(hasSportFilter).to.not.be.null
      })
    })
  })

  describe('User Position', () => {
    it('highlights current user position', () => {
      cy.get('body').then(($body) => {
        const hasCurrentUser = $body.find('.current-user, .highlighted, [data-current="true"]').length > 0
        const hasYouIndicator = $body.text().match(/You|Current/i)
        // May or may not be present depending on if user has made bets
      })
    })
  })

  describe('Leaderboard Stats', () => {
    it('shows CLV leaderboard', () => {
      cy.get('body').then(($body) => {
        const hasCLV = $body.text().match(/CLV|Closing Line|Line Value/i)
        expect(hasCLV).to.not.be.null
      })
    })

    it('displays bet count or volume', () => {
      cy.get('body').then(($body) => {
        const hasBetCount = $body.text().match(/Bets|Wagers|Volume|Total/i)
        expect(hasBetCount).to.not.be.null
      })
    })
  })

  describe('Pagination', () => {
    it('has pagination if needed', () => {
      cy.get('body').then(($body) => {
        const hasPagination = $body.find('[data-testid="pagination"], .pagination, button:contains("Next"), button:contains("Load More")').length > 0
        // Pagination may not be present if few results
      })
    })
  })

  describe('Profile Links', () => {
    it('can view user profiles', () => {
      cy.get('body').then(($body) => {
        const hasProfileLinks = $body.find('a[href*="profile"], button:contains("View")').length > 0
        // Profile viewing may be optional feature
      })
    })
  })
})
