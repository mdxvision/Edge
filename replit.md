# EdgeBet - Multi-Sport Betting & DFS Recommendation Platform

## Overview
A comprehensive global sports analytics and betting recommendation system covering 15 sports worldwide. The platform uses machine learning models to identify value bets and provides personalized recommendations based on client risk profiles with full transparency on every pick.

**Current State**: All Phases Complete - Production Ready with Full Feature Set

## Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Foundation & Frontend | Complete | 100% |
| Phase 2: Advanced ML & Historical Data | Complete | 100% |
| Phase 3: DFS Integration | Complete | 100% |
| Phase 4: Production Readiness | Complete | 100% |
| Phase 5: Advanced Features | Complete | 100% |

## Recent Changes
- 2024-12-02: Authentication System Finalized
  - Fixed Login.tsx with proper tabbed UI (Create Account / Sign In)
  - Added refresh token handling and session renewal in AuthContext
  - Created dedicated ResetPassword page with email-based flow
  - Added "Forgot password?" link to login form
  - Session and refresh tokens properly stored and rotated
  - 21+ age verification checkbox required on registration

- 2024-12-02: Phase 5 Complete - Advanced Features
  - Parlay Builder with correlation detection and EV analysis
  - Leaderboard system with display names and rankings
  - Multi-currency support (USD, EUR, GBP, CAD, AUD, BTC, ETH)
  - Custom alerts system with email/push/telegram notifications
  - Webhook infrastructure for external integrations
  - Telegram bot integration with linking workflow
  - Terms of Service page with 21+ age verification
  - Display name support for user profiles
  - Account recovery with password reset flow
  - Email infrastructure ready for SendGrid/Mailgun
  - Real-time odds infrastructure ready for The Odds API
  - Profile page enhancements (currency, telegram, age verification)

- 2024-12-02: Phase 4 Complete - Production Infrastructure
  - PostgreSQL database migration (from SQLite)
  - User authentication system with secure session tokens
  - Password hashing with PBKDF2 (100,000 iterations)
  - HMAC token storage (tokens hashed before database storage)
  - Refresh token rotation on each use
  - Session invalidation on password change
  - Rate limiting middleware (100 req/min, 2000 req/hour)
  - Auth-specific rate limits (5 login attempts/min, 10 registrations/hour)
  - Security headers (CSP, HSTS, X-Frame-Options, etc.)
  - Structured logging with request tracking
  - In-memory caching layer with TTL
  - Enhanced API documentation with OpenAPI tags

## Project Architecture

### Directory Structure
```
app/                 # FastAPI Backend
├── main.py          # FastAPI entry point
├── config.py        # Configuration constants
├── db.py            # SQLAlchemy models
├── models/          # ML models (15 sport-specific)
├── schemas/         # Pydantic validation schemas
├── services/        # Business logic
│   ├── data_ingestion.py
│   ├── edge_engine.py
│   ├── bankroll.py
│   ├── auth.py          # Authentication service
│   ├── totp.py          # 2FA TOTP service
│   ├── audit.py         # Audit logging
│   ├── alerts.py        # Custom alerts
│   ├── webhooks.py      # Webhook delivery
│   ├── currency.py      # Multi-currency
│   ├── email.py         # Email service
│   ├── telegram_bot.py  # Telegram integration
│   ├── bet_tracking.py  # Bet tracking
│   ├── parlay.py        # Parlay analysis
│   ├── odds_api.py      # Real-time odds
│   ├── dfs_projections.py
│   └── lineup_optimizer.py
├── routers/         # API endpoints
│   ├── auth.py          # Authentication routes
│   ├── security.py      # 2FA and session management
│   ├── account.py       # Profile and age verification
│   ├── tracking.py      # Bet tracking
│   ├── alerts.py        # Alert management
│   ├── webhooks.py      # Webhook management
│   ├── parlays.py       # Parlay analysis
│   ├── currency.py      # Currency conversion
│   ├── telegram.py      # Telegram integration
│   ├── odds.py          # Real-time odds
│   ├── dfs.py           # DFS routes
│   ├── historical.py    # ML/Historical routes
│   └── ...
├── middleware/      # Custom middleware
│   ├── rate_limit.py    # Rate limiting
│   └── security.py      # Security headers
└── utils/           # Utilities
    ├── logging.py       # Structured logging
    ├── cache.py         # Caching layer
    └── odds.py          # Odds calculations
client/              # React TypeScript Frontend
├── src/
│   ├── pages/       # All UI pages
│   │   ├── Dashboard.tsx
│   │   ├── Games.tsx
│   │   ├── Recommendations.tsx
│   │   ├── Tracking.tsx
│   │   ├── Parlays.tsx
│   │   ├── Leaderboard.tsx
│   │   ├── DFS.tsx
│   │   ├── Models.tsx
│   │   ├── Alerts.tsx
│   │   ├── Security.tsx
│   │   ├── Profile.tsx
│   │   └── Terms.tsx
│   ├── components/  # Reusable UI components
│   ├── context/     # Auth context provider
│   └── lib/         # API client
├── cypress/         # E2E tests
│   └── e2e/         # Test specs
└── vite.config.ts   # Vite + TailwindCSS v4 config
tests/               # Pytest API tests
docs/                # Documentation
.github/workflows/   # CI configuration
```

### Key Components
- **Backend**: FastAPI with PostgreSQL via SQLAlchemy
- **Frontend**: React 19 + TypeScript + TailwindCSS v4 + React Query
- **Database Models**: Teams, Competitors, Games, Markets, Lines, Clients, Users, UserSessions, Alerts, Webhooks, TrackedBets, Parlays
- **Authentication**: Session-based auth with PBKDF2 password hashing and HMAC token storage
- **ML Models**: ELO-based rating systems customized per sport
- **DFS Engine**: PuLP-based lineup optimizer with salary constraints
- **API Docs**: OpenAPI documentation at /docs and /redoc

### Supported Sports
NFL, NBA, MLB, NHL, NCAA_FOOTBALL, NCAA_BASKETBALL, SOCCER, CRICKET, RUGBY, TENNIS, GOLF, MMA, BOXING, MOTORSPORTS, ESPORTS

### Supported Currencies
USD ($), EUR (€), GBP (£), CAD (C$), AUD (A$), BTC (₿), ETH (Ξ)

## User Preferences
- Clean professional design (NOT sports-themed)
- Transparency-first approach - show confidence, edge, and explanation for every pick
- Dark/Light mode toggle
- Mobile-responsive design

## Running the Project

### Development (both servers)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd client && npm run dev
```

### Running Tests
```bash
# Backend API tests (51 tests)
python -m pytest tests/ -v

# Frontend E2E tests
cd client && npm run cypress:run
```

## Key Endpoints

### Core
- GET / - API information
- GET /health - Health check
- GET /docs - OpenAPI documentation
- GET /redoc - ReDoc documentation

### Authentication
- POST /auth/register - Register new user
- POST /auth/login - Login with email or username
- POST /auth/logout - Logout current session
- POST /auth/refresh - Refresh access token (rotates tokens)
- GET /auth/me - Get current user info
- POST /auth/change-password - Change password (invalidates all sessions)
- GET /auth/validate - Validate session token

### Security (2FA)
- GET /security/2fa/status - Get 2FA status
- POST /security/2fa/setup - Setup 2FA (get QR code)
- POST /security/2fa/enable - Enable 2FA with code
- POST /security/2fa/disable - Disable 2FA
- POST /security/2fa/backup-codes/regenerate - Regenerate backup codes
- GET /security/sessions - List active sessions
- DELETE /security/sessions/{id} - Revoke specific session
- DELETE /security/sessions - Revoke all sessions
- GET /security/audit-logs - Get audit logs
- GET /security/security-events - Get security events

### Account
- GET /account/profile - Get user profile
- PATCH /account/profile - Update profile (display name, currency)
- POST /account/verify-age - Verify age (21+ required)
- POST /account/forgot-password - Request password reset
- POST /account/reset-password - Reset password with token

### Clients
- POST /clients - Create client
- GET /clients/{id} - Get client details
- PATCH /clients/{id} - Update client
- DELETE /clients/{id} - Delete client

### Games
- GET /games - List games with filtering
- GET /games/sports - List supported sports
- GET /games/teams - List teams
- GET /games/competitors - List individual competitors

### Recommendations
- POST /clients/{id}/recommendations/run - Generate recommendations
- GET /clients/{id}/recommendations/latest - Get latest recommendations

### Bet Tracking
- POST /tracking/bets - Place a bet
- GET /tracking/bets - List bets
- POST /tracking/bets/{id}/settle - Settle a bet
- DELETE /tracking/bets/{id} - Delete a bet
- GET /tracking/stats - Get betting statistics
- GET /tracking/profit/daily - Daily profit chart
- GET /tracking/profit/by-sport - Profit by sport
- GET /tracking/leaderboard - Public leaderboard

### Parlays
- POST /parlays/analyze - Analyze a parlay
- POST /parlays - Create a parlay
- GET /parlays - List parlays

### Alerts
- GET /alerts/types - List alert types
- POST /alerts - Create alert
- GET /alerts - List alerts
- PATCH /alerts/{id} - Update alert
- POST /alerts/{id}/toggle - Toggle alert
- DELETE /alerts/{id} - Delete alert

### Webhooks
- GET /webhooks/events - List available events
- POST /webhooks - Create webhook
- GET /webhooks - List webhooks
- PATCH /webhooks/{id} - Update webhook
- POST /webhooks/{id}/regenerate-secret - Regenerate secret
- DELETE /webhooks/{id} - Delete webhook

### Currency
- GET /currency/list - List supported currencies
- POST /currency/convert - Convert amount
- GET /currency/rates - Get exchange rates
- POST /currency/preference - Set preferred currency
- GET /currency/preference - Get preferred currency

### Telegram
- GET /telegram/status - Get telegram status
- POST /telegram/link - Generate link code
- DELETE /telegram/unlink - Unlink telegram
- PATCH /telegram/notifications - Update notification preferences
- POST /telegram/webhook - Telegram webhook endpoint

### Historical/ML
- POST /historical/seed - Seed historical game data
- POST /historical/train-models - Train ELO models
- GET /historical/model-status - Get model training status
- GET /historical/ratings/{sport} - Get team power rankings
- POST /historical/backtest/{sport} - Run backtest
- GET /historical/backtest/results - Get backtest results

### DFS
- GET /dfs/projections - Get player projections
- POST /dfs/optimize - Generate optimal lineup
- GET /dfs/ownership - Get ownership projections

## API Keys Required (User to Provide)
- **SENDGRID_API_KEY**: For email notifications (SendGrid or Mailgun)
- **FROM_EMAIL**: Sender email address
- **THE_ODDS_API_KEY**: For real-time odds data (the-odds-api.com)
- **TELEGRAM_BOT_TOKEN**: For Telegram bot notifications
- **TELEGRAM_BOT_USERNAME**: Bot username for deep links

## Security Features

### Authentication
- Passwords hashed with PBKDF2-SHA256 (100,000 iterations)
- Session/refresh tokens stored as HMAC-SHA256 hashes
- Refresh tokens rotated on each use (old tokens invalidated)
- All sessions invalidated when password is changed
- Timing-safe token comparison to prevent timing attacks

### Two-Factor Authentication (2FA)
- TOTP-based 2FA with 6-digit codes
- QR code generation for authenticator apps
- Backup codes for account recovery
- Optional but recommended for all accounts

### Rate Limiting
- 100 requests per minute (general)
- 2000 requests per hour (general)
- 20 requests burst limit
- 5 login attempts per minute
- 10 registration attempts per hour

### Security Headers
- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy

### Age Verification
- Mandatory 21+ age verification
- Date of birth required
- Age calculated server-side

## Implementation Tracker
See `docs/IMPLEMENTATION_STATUS.md` for complete implementation details.
