# Conversation Log - Edge Betting Platform

This file tracks key decisions, fixes, and progress from Claude Code sessions.

---

## Session: January 3, 2026 (Evening)

### Summary
Fixed backend issues, verified 8-factor tracker works for all sports, added accordion sidebar.

### Key Accomplishments

1. **Fixed Backend**
   - Backend wasn't responding to API requests
   - Restarted on port 8080, now working correctly

2. **Verified 8-Factor Tracker**
   - Confirmed data exists for all sports (NBA, NFL, SOCCER)
   - 47 tracked picks: 17W-27L
   - Picks with factors: NBA (20), NFL (15), SOCCER (3)

3. **Accordion Sidebar**
   - 4 categories: Betting, Analysis, Practice, Account
   - Auto-expands category containing current route
   - Dark mode toggle preserved

4. **Test Credentials File**
   - Created `TEST_CREDENTIALS.md`
   - Login: `test@edgebet.com` / `TestPass123!`

5. **Bet Status Check**
   - All 10 bets still PENDING
   - CBB/Soccer games: Jan 4
   - NFL games: Jan 5

### Commits
- `2b77b50` - Add test credentials documentation

---

## Session: January 3, 2026 (Morning)

### Summary
Major breakthrough - got RLM detection working with real odds data.

### Key Accomplishments

1. **Upgraded Odds API**
   - New key: `b7dda300f2b103e4153b50793de01144`
   - Starter plan: 20,000 requests/month
   - Old key exhausted (500 free requests used in ~21 hours)

2. **Fixed Edge Dilution Bug**
   - Problem: 3.5% RLM edge was being diluted to 0.7%
   - Cause: Weight system assumed all 8 factors had data
   - Fix: Normalized weights based on factors with actual data
   - File: `app/services/edge_aggregator.py`

3. **Fixed Market Type Mismatch**
   - Problem: Analyzer looked for 'spread', API sends 'spreads'
   - Fix: Changed to match both `['spread', 'spreads']`
   - File: `app/services/line_movement_analyzer.py`

4. **Synced Real Games**
   - Pulled live games from ESPN APIs (NBA, NFL, CBB)
   - 40 games synced to database
   - 2,794 odds snapshots stored

5. **Optimized API Usage**
   - Changed refresh from 15 min to 30 min
   - Saves ~50% of API calls
   - Fits within Starter plan quota

### Bets Placed (10 STRONG BETS)

| Sport | Game | Pick | Spread |
|-------|------|------|--------|
| NFL | Saints @ Falcons | Saints | +3.5 |
| NFL | Browns @ Bengals | Browns | +7.5 |
| NFL | Packers @ Vikings | Vikings | -10.0 |
| NFL | Cowboys @ Giants | Cowboys | +3.5 |
| NFL | Titans @ Jaguars | Titans | +13.5 |
| CBB | GA Southern @ Coastal Carolina | Coastal Carolina | +2.5 |
| CBB | Green Bay @ Fort Wayne | Green Bay | -9.0 |
| CBB | Jacksonville @ Lipscomb | Lipscomb | +10.5 |
| Soccer | Leeds @ Liverpool | Leeds | +0.2 |
| Soccer | Man City @ Sunderland | Man City | -0.8 |

### Commits
- `722383f` - Fix edge dilution - RLM signals now produce actionable bets
- `60c4919` - Fix RLM detection and optimize API usage

---

## Session: January 2, 2026

### Summary
Wired Odds API, set up alerts, configured Telegram.

### Key Accomplishments

1. **Created line_movement_analyzer.py**
   - Detects RLM (Reverse Line Movement)
   - Detects steam moves
   - Identifies sharp book origination

2. **Wired analysis to odds scheduler**
   - Runs after each odds refresh
   - Creates LineMovementSummary records

3. **Set up Telegram alerts**
   - Bot: @EdgeBetalertsbot
   - Token configured in .env
   - Test alert sent successfully

4. **Fixed soccer scores display**
   - Was showing "-" for scores
   - Fixed in soccer_stats.py

5. **Fixed live status badges**
   - Changed from "LIVE - STATUS_IN_PROGRESS" to just "LIVE"

### Commits
- `be1f4d5` - Wire Odds API, add soccer scores, fix live status, setup alerts

---

## Session: December 31, 2025

### Summary
Strategy overhaul after losing streak.

### Key Decisions
- No spreads > 6 points
- No heavy favorites (> -150)
- Prefer plus-money underdogs
- Higher edge requirement for favorites (6% vs 3%)

---

## How to Continue

When resuming work, Claude should:

1. Read this file for context
2. Check CLAUDE_NOTES.md for current status
3. Run `git log --oneline -5` to see recent commits
4. Check pending bets and their results

---

## Important Context

- User is actively betting based on system recommendations
- RLM + Steam moves are the primary edge signals
- Odds API refreshes every 30 minutes
- Telegram alerts when edges exceed thresholds
