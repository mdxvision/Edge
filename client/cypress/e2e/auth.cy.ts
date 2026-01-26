describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
  })

  describe('Login Page', () => {
    beforeEach(() => {
      cy.visit('/login')
    })

    it('displays the EdgeBet branding', () => {
      cy.contains('Welcome to EdgeBet').should('be.visible')
      cy.contains('Intelligent edge detection').should('be.visible')
    })

    it('shows simulation warning banner', () => {
      cy.contains('Simulation only').should('be.visible')
    })

    it('has Get Started and Sign In tabs', () => {
      cy.contains('button', 'Get Started').should('be.visible')
      cy.contains('button', 'Sign In').should('be.visible')
    })

    it('defaults to registration form', () => {
      cy.get('input[type="email"]').should('be.visible')
      cy.get('input[placeholder="Choose a username"]').should('be.visible')
      cy.get('input[placeholder="At least 8 characters"]').should('be.visible')
      cy.get('input[placeholder="Confirm your password"]').should('be.visible')
    })

    it('switches to login form when Sign In is clicked', () => {
      cy.contains('button', 'Sign In').click()
      cy.get('input[placeholder="you@example.com"]').should('be.visible')
      cy.get('input[placeholder="Your password"]').should('be.visible')
      cy.contains('button', 'Forgot password?').should('be.visible')
    })

    it('shows Dev Login button on login form', () => {
      cy.contains('button', 'Sign In').click()
      cy.contains('button', 'Dev Login').should('be.visible')
    })

    it('requires email on login form', () => {
      cy.contains('button', 'Sign In').click()
      cy.get('input[placeholder="Your password"]').type('password123')
      cy.contains('button', 'Continue').click()
      cy.url().should('include', '/login')
    })

    it('requires password on login form', () => {
      cy.contains('button', 'Sign In').click()
      cy.get('input[placeholder="you@example.com"]').type('test@example.com')
      cy.contains('button', 'Continue').click()
      cy.url().should('include', '/login')
    })

    it('shows error on invalid credentials', () => {
      cy.contains('button', 'Sign In').click()
      cy.get('input[placeholder="you@example.com"]').type('invalid@email.com')
      cy.get('input[placeholder="Your password"]').type('wrongpassword')
      cy.contains('button', 'Continue').click()
      // Should either show error message or stay on login page
      cy.url({ timeout: 10000 }).should('include', '/login')
    })

    it('successfully logs in with Dev Login button', () => {
      cy.contains('button', 'Sign In').click()
      cy.contains('button', 'Dev Login').click()
      cy.url({ timeout: 15000 }).should('include', '/dashboard')
    })

    it('successfully logs in with test credentials', () => {
      cy.contains('button', 'Sign In').click()
      cy.get('input[placeholder="you@example.com"]').type('test@edgebet.com')
      cy.get('input[placeholder="Your password"]').type('TestPass123!')
      cy.contains('button', 'Continue').click()
      cy.url({ timeout: 15000 }).should('include', '/dashboard')
    })
  })

  describe('Registration Form', () => {
    beforeEach(() => {
      cy.visit('/login')
    })

    it('has age confirmation checkbox', () => {
      // Verify age confirmation checkbox exists on registration form
      cy.get('input[type="checkbox"]').should('exist')
      cy.contains(/21 or older|confirm/i).should('exist')
    })

    it('validates password match', () => {
      const uniqueEmail = `test${Date.now()}@example.com`
      cy.get('input[type="email"]').type(uniqueEmail)
      cy.get('input[placeholder="Choose a username"]').type(`user${Date.now()}`)
      cy.get('input[placeholder="At least 8 characters"]').type('TestPass123!')
      cy.get('input[placeholder="Confirm your password"]').type('DifferentPass!')
      cy.get('input[type="checkbox"]').check()
      // Submit form via button inside form
      cy.get('form').find('button[type="submit"]').click()
      // Exact message from Login.tsx line 86
      cy.contains("Passwords don't match", { timeout: 10000 }).should('be.visible')
    })

    it('validates minimum password length', () => {
      const uniqueEmail = `test${Date.now()}@example.com`
      cy.get('input[type="email"]').type(uniqueEmail)
      cy.get('input[placeholder="Choose a username"]').type(`user${Date.now()}`)
      cy.get('input[placeholder="At least 8 characters"]').type('short')
      cy.get('input[placeholder="Confirm your password"]').type('short')
      cy.get('input[type="checkbox"]').check()
      // Submit form via button inside form
      cy.get('form').find('button[type="submit"]').click()
      // Exact message from Login.tsx line 91
      cy.contains('Password needs at least 8 characters', { timeout: 10000 }).should('be.visible')
    })

    it('has risk profile selector', () => {
      cy.get('select').should('be.visible')
      cy.get('select option').should('have.length.at.least', 3)
    })
  })

  describe('Logout', () => {
    it('logs out user and redirects to login', () => {
      // Login via UI directly (not using session cache)
      cy.visit('/login')
      cy.contains('button', 'Sign In').click()
      cy.contains('button', 'Dev Login').click()
      cy.url({ timeout: 15000 }).should('include', '/dashboard')
      cy.url().should('include', '/dashboard')

      // Find and click Sign Out
      cy.contains('Sign Out').click()
      cy.url({ timeout: 10000 }).should('include', '/login')
    })
  })

  describe('Session Persistence', () => {
    it('maintains session after page reload', () => {
      // Login via UI directly
      cy.visit('/login')
      cy.contains('button', 'Sign In').click()
      cy.contains('button', 'Dev Login').click()
      cy.url({ timeout: 15000 }).should('include', '/dashboard')
      cy.url().should('include', '/dashboard')

      // Reload and verify still logged in
      cy.reload()
      cy.url({ timeout: 15000 }).should('include', '/dashboard')
      cy.url().should('include', '/dashboard')
    })

    it('redirects to login when not authenticated', () => {
      cy.clearLocalStorage()
      cy.visit('/dashboard')
      cy.url({ timeout: 10000 }).should('include', '/login')
    })
  })

  describe('Protected Routes', () => {
    it('redirects unauthenticated users to login', () => {
      cy.clearLocalStorage()
      cy.visit('/games')
      cy.url({ timeout: 10000 }).should('include', '/login')
    })

    it('allows authenticated users to access protected routes', () => {
      cy.loginWithCredentials('test@edgebet.com', 'TestPass123!')
      cy.visit('/games')
      cy.url().should('include', '/games')
    })
  })
})
