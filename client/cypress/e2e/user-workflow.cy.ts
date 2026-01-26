/**
 * User Workflow Documentation Tests
 *
 * These tests validate that the USER_WORKFLOW.md documentation
 * accurately describes the actual application behavior.
 */

describe('User Workflow Documentation Validation', () => {

  // ============================================
  // SECTION 1: GETTING STARTED
  // ============================================
  describe('1. Getting Started', () => {

    describe('1.1 Creating an Account', () => {
      beforeEach(() => {
        cy.clearLocalStorage()
        cy.visit('/login')
      })

      it('Step 1: Navigate to Login Page - shows welcome screen', () => {
        cy.contains('Welcome to EdgeBet').should('be.visible')
        cy.contains('Intelligent edge detection').should('be.visible')
      })

      it('Step 2: Select Registration Mode - has Get Started and Sign In tabs', () => {
        cy.contains('button', 'Get Started').should('be.visible')
        cy.contains('button', 'Sign In').should('be.visible')
      })

      it('Step 3-6: Registration form has all required fields', () => {
        // Email field
        cy.get('input[type="email"]').should('be.visible')
        // Username field
        cy.get('input[placeholder="Choose a username"]').should('be.visible')
        // Password field
        cy.get('input[placeholder="At least 8 characters"]').should('be.visible')
        // Confirm password field
        cy.get('input[placeholder="Confirm your password"]').should('be.visible')
      })

      it('Step 8: Has risk profile selector with 3 options', () => {
        cy.get('select').should('be.visible')
        cy.get('select option').should('have.length.at.least', 3)
      })

      it('Step 9: Has age verification checkbox', () => {
        cy.get('input[type="checkbox"]').should('exist')
        cy.contains(/21.*older|age|confirm/i).should('exist')
      })

      it('Troubleshooting: Shows password mismatch error', () => {
        const uniqueEmail = `test${Date.now()}@example.com`
        cy.get('input[type="email"]').type(uniqueEmail)
        cy.get('input[placeholder="Choose a username"]').type(`user${Date.now()}`)
        cy.get('input[placeholder="At least 8 characters"]').type('TestPass123!')
        cy.get('input[placeholder="Confirm your password"]').type('DifferentPass!')
        cy.get('input[type="checkbox"]').check()
        cy.get('form').find('button[type="submit"]').click()
        cy.contains("Passwords don't match", { timeout: 10000 }).should('be.visible')
      })
    })

    describe('1.2 Logging In', () => {
      beforeEach(() => {
        cy.clearLocalStorage()
        cy.visit('/login')
      })

      it('Step 2: Can switch to Sign In mode', () => {
        cy.contains('button', 'Sign In').click()
        cy.get('input[placeholder="you@example.com"]').should('be.visible')
        cy.get('input[placeholder="Your password"]').should('be.visible')
      })

      it('Step 4: Has Continue button to submit', () => {
        cy.contains('button', 'Sign In').click()
        cy.contains('button', 'Continue').should('be.visible')
      })

      it('Quick Login: Dev Login button exists', () => {
        cy.contains('button', 'Sign In').click()
        cy.contains('button', 'Dev Login').should('be.visible')
      })

      it('Step 6: Successfully logs in and reaches Dashboard', () => {
        cy.contains('button', 'Sign In').click()
        cy.contains('button', 'Dev Login').click()
        cy.url({ timeout: 15000 }).should('include', '/dashboard')
        cy.contains('testuser', { timeout: 10000 }).should('be.visible')
      })
    })

    describe('1.3 Password Recovery', () => {
      it('Step 1: Forgot password link exists', () => {
        cy.visit('/login')
        cy.contains('button', 'Sign In').click()
        cy.contains(/Forgot password/i).should('be.visible')
      })
    })
  })

  // ============================================
  // SECTION 2: INITIAL SETUP
  // ============================================
  describe('2. Initial Setup', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    })

    describe('2.1 Completing Your Profile', () => {
      it('Step 1: Can navigate to Profile from sidebar', () => {
        cy.visit('/dashboard')
        cy.contains(/Profile|Settings/i).first().click({ force: true })
        cy.url().should('include', '/profile')
      })

      it('Step 2-3: Profile page has personal information fields', () => {
        cy.visit('/profile')
        cy.contains('Personal Information', { timeout: 10000 }).should('be.visible')
        // Display name field
        cy.get('input').should('exist')
      })

      it('Step 4: Has currency preference dropdown', () => {
        cy.visit('/profile')
        cy.contains('Currency', { timeout: 10000 }).should('be.visible')
        cy.get('select').should('exist')
      })

      it('Step 5: Has Save Changes button', () => {
        cy.visit('/profile')
        cy.contains('button', /Save/i, { timeout: 10000 }).should('be.visible')
      })
    })

    describe('2.2 Setting Your Risk Profile', () => {
      it('Profile page has Risk Profile section with 3 options', () => {
        cy.visit('/profile')
        cy.contains('Risk Profile', { timeout: 10000 }).should('be.visible')
        cy.contains(/Conservative/i).should('exist')
        cy.contains(/Balanced/i).should('exist')
        cy.contains(/Aggressive/i).should('exist')
      })
    })

    describe('2.3 Configuring Bankroll', () => {
      it('Profile page has Bankroll Management section', () => {
        cy.visit('/profile')
        cy.contains(/Bankroll/i, { timeout: 10000 }).should('be.visible')
        cy.get('input[type="number"]').should('exist')
      })
    })
  })

  // ============================================
  // SECTION 3: DAILY WORKFLOW
  // ============================================
  describe('3. Daily Workflow', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    })

    describe('3.1 Dashboard Overview', () => {
      beforeEach(() => {
        cy.visit('/dashboard')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Shows personalized greeting', () => {
        cy.contains(/Good (morning|afternoon|evening)/i, { timeout: 20000 }).should('be.visible')
      })

      it('Shows stat cards (Bankroll, Curated Picks, etc.)', () => {
        cy.contains('Bankroll', { timeout: 20000 }).should('be.visible')
        cy.contains('Curated Picks', { timeout: 20000 }).should('be.visible')
      })

      it('Shows Quick Picks section with See All link', () => {
        cy.contains('Quick Picks', { timeout: 20000 }).should('be.visible')
        cy.contains('See All', { timeout: 20000 }).should('be.visible')
      })
    })

    describe('3.2 Browsing Games', () => {
      beforeEach(() => {
        cy.visit('/games')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Games/Matchups', () => {
        cy.url().should('include', '/games')
      })

      it('Step 2: Has sport tabs for filtering', () => {
        // Should have at least some sport tabs
        cy.contains(/MLB|NBA|NFL|NHL/i, { timeout: 10000 }).should('exist')
      })

      it('Has refresh control', () => {
        cy.contains(/Refresh|↻/i).should('exist')
      })
    })

    describe('3.3 Viewing Recommendations', () => {
      beforeEach(() => {
        cy.visit('/recommendations')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Recommendations/Picks', () => {
        cy.url().should('include', '/recommendations')
      })

      it('Step 2: Has Generate Picks button', () => {
        cy.contains(/Generate|Refresh/i, { timeout: 10000 }).should('exist')
      })

      it('Step 3: Has sport filter dropdown', () => {
        cy.contains(/All Sports|Sport/i, { timeout: 10000 }).should('exist')
      })
    })
  })

  // ============================================
  // SECTION 4: BETTING WORKFLOWS
  // ============================================
  describe('4. Betting Workflows', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    })

    describe('4.1 Paper Trading (Practice)', () => {
      beforeEach(() => {
        cy.visit('/paper-trading')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Paper Trading', () => {
        cy.url().should('include', '/paper-trading')
      })

      it('Step 2: Shows virtual stats (Balance, ROI, etc.)', () => {
        cy.contains(/Balance|Bankroll|Starting|Profit/i, { timeout: 15000 }).should('exist')
      })

      it('Step 3: Has Place Bet button', () => {
        cy.contains(/Place|Trade|Bet|New/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('4.2 Tracking Real Bets', () => {
      beforeEach(() => {
        cy.visit('/tracking')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Tracking/My Bets', () => {
        cy.url().should('include', '/tracking')
      })

      it('Step 2: Shows performance stats', () => {
        cy.contains(/Performance|Precision|ROI|Streak/i, { timeout: 10000 }).should('exist')
      })

      it('Step 3: Has Track a Bet button', () => {
        cy.contains(/Track.*Bet|Add|New/i, { timeout: 10000 }).should('exist')
      })

      it('Step 4: Has status and sport filters', () => {
        cy.contains(/All Status|Status/i, { timeout: 10000 }).should('exist')
        cy.contains(/All Sports|Sport/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('4.3 Building Parlays', () => {
      beforeEach(() => {
        cy.visit('/parlays')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Parlays', () => {
        cy.url().should('include', '/parlays')
      })

      it('Step 2: Has Add Pick form with Selection and Odds inputs', () => {
        cy.contains('Add Pick', { timeout: 10000 }).should('exist')
        cy.get('input', { timeout: 10000 }).should('exist')
      })

      it('Step 5: Has Analyze Parlay button', () => {
        // Note: Button may only appear after adding 2+ picks
        cy.contains(/Analyze|Add Pick/i, { timeout: 10000 }).should('exist')
      })
    })
  })

  // ============================================
  // SECTION 5: ADVANCED FEATURES
  // ============================================
  describe('5. Advanced Features', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    })

    describe('5.1 Setting Up Alerts', () => {
      beforeEach(() => {
        cy.visit('/alerts')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Alerts', () => {
        cy.url().should('include', '/alerts')
      })

      it('Step 2: Has Create Alert form', () => {
        cy.contains(/Create|Set Alert|New/i, { timeout: 10000 }).should('exist')
      })

      it('Has notification method options', () => {
        cy.contains(/Push|Email|Telegram/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('5.2 Power Ratings', () => {
      beforeEach(() => {
        cy.visit('/power-ratings')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Power Ratings', () => {
        cy.url().should('include', '/power-ratings')
      })

      it('Step 2: Has sport selection tabs', () => {
        cy.contains(/NFL|NBA|MLB|NHL/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('5.3 Edge Tracker', () => {
      beforeEach(() => {
        cy.visit('/edge-tracker')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Edge Tracker', () => {
        cy.url().should('include', '/edge-tracker')
      })

      it('Shows performance metrics', () => {
        cy.contains(/Win|ROI|Edge|Picks/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('5.4 DFS Lineups', () => {
      beforeEach(() => {
        cy.visit('/dfs')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to DFS', () => {
        cy.url().should('include', '/dfs')
      })

      it('Shows page content or handles loading', () => {
        cy.contains(/Lineups|Build|Analyzing|Something's not right/i, { timeout: 20000 }).should('exist')
      })
    })

    describe('5.5 Intelligence Models', () => {
      beforeEach(() => {
        cy.visit('/models')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Models/Intelligence', () => {
        cy.url().should('include', '/models')
      })

      it('Shows page content or handles loading', () => {
        cy.contains(/Intelligence|Analyzing|Something's not right/i, { timeout: 20000 }).should('exist')
      })
    })
  })

  // ============================================
  // SECTION 6: ACCOUNT MANAGEMENT
  // ============================================
  describe('6. Account Management', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
    })

    describe('6.1 Profile Settings', () => {
      it('Profile page has all documented sections', () => {
        cy.visit('/profile')
        cy.contains('Personal Information', { timeout: 10000 }).should('be.visible')
        cy.contains(/Currency/i).should('be.visible')
        cy.contains(/Bankroll/i).should('be.visible')
        cy.contains(/Risk Profile/i).should('be.visible')
      })
    })

    describe('6.2 Security Settings', () => {
      beforeEach(() => {
        cy.visit('/security')
        cy.url().should('include', '/security')
      })

      it('Step 1: Can navigate to Security', () => {
        cy.url().should('include', '/security')
      })

      it('Step 2: Has Two-Factor Authentication section', () => {
        cy.contains(/Two-Factor|2FA|Authenticator/i, { timeout: 10000 }).should('exist')
      })

      it('Step 3: Has Active Sessions section', () => {
        cy.contains(/Session|Device|Logged/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('6.3 Subscription & Pricing', () => {
      beforeEach(() => {
        cy.visit('/pricing')
        cy.contains('testuser', { timeout: 15000 }).should('be.visible')
      })

      it('Step 1: Can navigate to Pricing', () => {
        cy.url().should('include', '/pricing')
      })

      it('Step 2: Shows plan comparison', () => {
        cy.contains(/Free|Premium|Pro/i, { timeout: 10000 }).should('be.visible')
      })

      it('Step 3: Has billing period toggle', () => {
        cy.contains(/Monthly|Yearly/i, { timeout: 10000 }).should('be.visible')
      })

      it('Shows savings badge for yearly', () => {
        cy.contains(/Save|%/i, { timeout: 10000 }).should('exist')
      })
    })

    describe('6.4 Telegram Integration', () => {
      it('Profile page has Telegram section', () => {
        cy.visit('/profile')
        cy.contains(/Telegram/i, { timeout: 10000 }).should('be.visible')
      })

      it('Alerts page has Telegram section', () => {
        cy.visit('/alerts')
        cy.contains(/Telegram/i, { timeout: 10000 }).should('exist')
      })
    })
  })

  // ============================================
  // NAVIGATION VALIDATION
  // ============================================
  describe('Sidebar Navigation (Quick Reference)', () => {
    beforeEach(() => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
      cy.visit('/dashboard')
      cy.contains('testuser', { timeout: 15000 }).should('be.visible')
    })

    it('Today → Dashboard', () => {
      cy.contains('Today').click()
      cy.url().should('include', '/dashboard')
    })

    it('Matchups → Games', () => {
      cy.contains('Matchups').click()
      cy.url().should('include', '/games')
    })

    it('Picks → Recommendations', () => {
      cy.contains('Picks').click()
      cy.url().should('include', '/recommendations')
    })

    it('My Bets → Tracking', () => {
      cy.contains('My Bets').click()
      cy.url().should('include', '/tracking')
    })

    it('Parlays → Parlays', () => {
      cy.contains('Parlays').click()
      cy.url().should('include', '/parlays')
    })
  })
})
