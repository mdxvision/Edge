# Claude Notes - Edge Betting Platform

## Last Updated: January 3, 2026 (Evening)

---

## Project Overview
Multi-sport betting recommendation engine with FastAPI backend and React frontend.
Now with **live RLM (Reverse Line Movement) detection** and real-time odds from The Odds API.

**Running Services:**
- Backend API: `http://localhost:8080`
- Frontend: `http://localhost:5001`
- Login: See `TEST_CREDENTIALS.md` for credentials

**UI Features:**
- Accordion sidebar with 4 categories (Betting, Analysis, Practice, Account)
- Dark mode toggle (sun/moon icon)
- 8-Factor Edge Tracker with expandable pick details

---

## Current Status

### Odds API
- **Plan:** Starter ($20/mo) - 20,000 requests/month
- **Key:** `b7dda300f2b103e4153b50793de01144`
- **Refresh:** Every 30 minutes (saves API quota)

### Line Movement Analysis
- RLM detection working
- Steam move detection working
- 24 signals detected on Jan 3, 2026

---

## Active Bets (Jan 4-5, 2026)

### 10 STRONG BETS (RLM + Steam Confirmed)

| Sport | Game | Pick | Spread | Date |
|-------|------|------|--------|------|
| NFL | Saints @ Falcons | Saints | +3.5 | Jan 5 |
| NFL | Browns @ Bengals | Browns | +7.5 | Jan 5 |
| NFL | Packers @ Vikings | Vikings | -10.0 | Jan 5 |
| NFL | Cowboys @ Giants | Cowboys | +3.5 | Jan 5 |
| NFL | Titans @ Jaguars | Titans | +13.5 | Jan 5 |
| CBB | GA Southern @ Coastal Carolina | Coastal Carolina | +2.5 | Jan 4 |
| CBB | Green Bay @ Fort Wayne | Green Bay | -9.0 | Jan 4 |
| CBB | Jacksonville @ Lipscomb | Lipscomb | +10.5 | Jan 4 |
| Soccer | Leeds @ Liverpool | Leeds | +0.2 | Jan 4 |
| Soccer | Man City @ Sunderland | Man City | -0.8 | Jan 4 |

**Total:** 10 bets @ 2 units = 20 units risked
**Status:** All PENDING

### Automated Results Checker
Script: `scripts/check_bet_results.py`
- Checks NFL/CBB scores from ESPN
- Sends results via Telegram when games complete
- Run manually: `./venv/bin/python scripts/check_bet_results.py`

---

## Recent Fixes (Jan 3, 2026)

1. **Edge Dilution Fix** - Weight normalization so RLM signals produce real edges
2. **Market Type Fix** - Changed 'spread' to 'spreads' to match Odds API format
3. **API Optimization** - 30-min refresh to fit within Starter plan quota
4. **Game Sync** - Syncs real games from ESPN APIs
5. **Odds Fetch** - Pulls live odds from The Odds API

---

## Key Files

| File | Purpose |
|------|---------|
| `/app/services/edge_aggregator.py` | Weight normalization fix for edge calculation |
| `/app/services/line_movement_analyzer.py` | RLM and steam move detection |
| `/app/services/odds_scheduler.py` | Auto-refresh odds every 30 min |
| `/app/routers/tracker.py` | Edge Tracker endpoints (8-factor) |
| `/client/src/components/layout/Sidebar.tsx` | Accordion navigation sidebar |
| `/client/src/pages/EdgeTracker.tsx` | 8-Factor edge validation page |
| `/scripts/check_bet_results.py` | Automated bet results checker |
| `/TEST_CREDENTIALS.md` | Login credentials for app |
| `/.env` | API keys (Odds API, Telegram, etc.) |

---

## 8-Factor Edge System

| Factor | Weight | Description |
|--------|--------|-------------|
| Line Movement | 20% | RLM, steam moves, sharp action |
| Coach DNA | 18% | Situational coaching records |
| Situational | 17% | Rest, travel, motivation |
| Weather | 12% | Wind, temp, precipitation |
| Officials | 10% | Referee tendencies |
| Public Fade | 10% | Contrarian signals |
| ELO | 8% | Power ratings |
| Social | 5% | Sentiment analysis |

---

## Commands

**Start Backend:**
```bash
cd /Users/rafaelrodriguez/GitHub/Edge
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Start Frontend:**
```bash
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev
```

**Manual Odds Refresh:**
```bash
curl -X POST http://localhost:8080/analytics/scheduler/refresh-now
```

**Check Predictions:**
```python
from app.services.edge_aggregator import get_ranked_picks
picks = await get_ranked_picks(db, limit=20)
```

---

## Telegram Alerts
- Bot: @EdgeBetalertsbot
- Token in .env: `TELEGRAM_BOT_TOKEN`
- User chat ID: `769278691`
- Alerts trigger when edges exceed thresholds

---

## Session Context

- Live odds flowing from The Odds API (Starter plan)
- RLM detection working with real data
- 10 strong bets placed for Jan 4-5, 2026 (all pending)
- System auto-refreshes every 30 minutes
- Telegram alerts configured
- Accordion sidebar with 4 categories
- 8-Factor Edge Tracker showing data for NBA, NFL, SOCCER
- 47 tracked picks in database (17W-27L)

---

## Edge Tracker Stats

| Sport | Picks | With Factors |
|-------|-------|--------------|
| NBA | 29 | 20 |
| NFL | 16 | 15 |
| SOCCER | 3 | 3 |

---

## Next Steps

1. Monitor Jan 4-5 bets for results (CBB/Soccer Sat, NFL Sun)
2. Track RLM prediction accuracy
3. Fine-tune edge weights based on performance
4. Improve factor generation for new picks
