# Edge Betting Platform - Build Checklist

## Last Updated: December 31, 2025 (11 PM ET)

---

## Current Status

| Metric | Value |
|--------|-------|
| Overall Record | 17-27 (38.6%) |
| Overall Units | -11.55u |
| Strategy | Underdog ML (+100 to +200) |
| New Strategy Record | **3-2, +3.02u** |
| Pending Exposure | 1.5u (1 pick) |

---

## Phase 7: Real Data Integration - PROGRESS

### Completed Today (Dec 31)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | Wire NBA rest days to factor generator | ✅ DONE | nba_api library |
| 7.2 | Wire NFL rest days to factor generator | ✅ DONE | ESPN API |
| 7.3 | Replace random line movement with neutral | ✅ DONE | Awaits Odds API |
| 7.4 | Replace random public betting with neutral | ✅ DONE | Manual input added |
| 7.5 | Configure The Odds API key | ✅ DONE | In .env, resets Jan 1 |
| 7.6 | Test factor generator with real data | ✅ DONE | Hawks/Steelers tested |
| 7.7 | Add real NFL coach ATS data | ✅ DONE | 32 coaches from Sharp Football |
| 7.8 | Add real NBA coach ATS data | ✅ DONE | 30 teams from Covers |
| 7.9 | Add NBA referee tendency data | ✅ DONE | 10 refs from Covers |
| 7.10 | Add public betting manual input | ✅ DONE | From Action Network |

### Pending

| # | Task | Status | Blocker |
|---|------|--------|---------|
| 7.11 | Add MySportsFeeds injury endpoint | ⏸️ BLOCKED | Need $5 DETAILED bundle |
| 7.12 | Wire Odds API line movement | 🔜 JAN 1 | API resets tomorrow |
| 7.13 | Build situational database | 🔄 ONGOING | Need 50+ settled picks |

---

## Factor Generator Status

| Factor | Data Source | Status | Notes |
|--------|-------------|--------|-------|
| REST | NBA API / ESPN | ✅ **REAL** | Tested, working |
| COACH_DNA | Sharp Football / Covers | ✅ **REAL** | 62 coaches loaded |
| REFEREE | Covers.com | ✅ **REAL** | 10 NBA refs loaded |
| WEATHER | Weather API | ✅ **REAL** | Indoor = N/A |
| TRAVEL | Static distances | ✅ **REAL** | Working |
| PUBLIC_BETTING | Action Network | ✅ **REAL** | Manual input |
| LINE_MOVEMENT | The Odds API | ⏸️ PENDING | Resets Jan 1 |
| SITUATIONAL | Own database | 🔄 BUILDING | Need more picks |

**Real Data: 6/8 factors**
**Pending: 1/8 (Line Movement - tomorrow)**
**Building: 1/8 (Situational - ongoing)**

---

## API Status

| API | Status | Cost | Data |
|-----|--------|------|------|
| The Odds API | ✅ Key configured | Free (500/mo) | Line movement, odds |
| MySportsFeeds | ✅ NBA + NFL | ~$10/mo | Scores, schedules |
| MySportsFeeds Injuries | ❌ Not added | +$5/mo | Injury reports |
| NBA API (nba_api) | ✅ Working | Free | Rest days, stats |
| ESPN API | ✅ Working | Free | NFL schedules |
| Weather API | ✅ Configured | Free | Game weather |
| Action Network | ❌ No API | Free website | Public betting % |

---

## Data Sources

### Coach ATS Data (REAL)
- **NFL**: Sharp Football Analysis - career ATS records for all 32 coaches
- **NBA**: Covers.com estimates - current season performance

### Referee Data (REAL)
- **NBA**: Covers.com - O/U tendencies, home team ATS
- **NFL**: Not yet added

### Public Betting (MANUAL)
- Check: https://www.actionnetwork.com/nba/public-betting
- Check: https://www.actionnetwork.com/nfl/public-betting
- Pass % to factor generator when creating picks

---

## Settled Picks (New Strategy)

| Date | Game | Pick | Odds | Result | Units |
|------|------|------|------|--------|-------|
| Dec 29 | Spurs @ Cavaliers | Cavaliers ML | +150 | ✅ WIN | +2.55u |
| Dec 29 | Blazers @ Mavericks | Mavericks ML | +100 | ❌ LOSS | -1.6u |
| Dec 30 | Pistons @ Lakers | Lakers ML | +113 | ❌ LOSS | -1.5u |
| Dec 31 | Hawks vs Wolves | Hawks ML | +136 | ✅ WIN | +2.04u |
| Dec 31 | Bulls @ Pelicans | Bulls ML | +102 | ✅ WIN | +1.53u |

**New Strategy: 3-2, +3.02u**

## Pending Picks

| Date | Game | Pick | Odds | Units | Status |
|------|------|------|------|-------|--------|
| Jan 4 | Ravens @ Steelers | Steelers ML | +144 | 1.5u | Pending |

**Total Exposure:** 1.5u

---

## Gap Analysis Summary

### What's Fixed (Dec 31)
- ✅ REST factor uses real NBA API / ESPN data
- ✅ COACH_DNA uses real ATS records (not random)
- ✅ REFEREE uses real tendency data (not random)
- ✅ PUBLIC_BETTING accepts manual input from Action Network
- ✅ LINE_MOVEMENT returns neutral (not random) when no data
- ✅ All random.randint() calls removed from core factors
- ✅ The Odds API key configured

### What's Still Needed
- ⏸️ LINE_MOVEMENT - Odds API resets Jan 1 (tomorrow)
- ⏸️ Injuries - MySportsFeeds $5 DETAILED bundle
- 🔄 SITUATIONAL - Building from our own pick history
- ⬜ NFL referee data - Need source

### Root Cause (RESOLVED)
~~**Integration gap** - APIs configured but not wired up.~~
**Fixed**: Factor generator now uses real data from all configured APIs.

---

## How to Generate a Pick with Real Data

```python
# Example: Hawks ML +136 with 40% public betting
factors = await factor_generator.generate_factors(
    sport='NBA',
    home_team='Atlanta Hawks',
    away_team='Minnesota Timberwolves',
    pick_team='Atlanta Hawks',
    pick_type='moneyline',
    line_value=136,
    game_time=datetime(2025, 12, 31, 15, 0),
    public_betting_pct=40  # From Action Network
)
```

---

## Commands

**Start Backend:**
```bash
cd /Users/rafaelrodriguez/GitHub/Edge
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Test Factor Generator:**
```bash
source venv/bin/activate && python3 -c "
import asyncio
from datetime import datetime
from app.services.factor_generator import FactorGenerator

async def test():
    fg = FactorGenerator()
    factors = await fg.generate_factors(
        sport='NBA',
        home_team='Atlanta Hawks',
        away_team='Minnesota Timberwolves',
        pick_team='Atlanta Hawks',
        pick_type='moneyline',
        line_value=136,
        game_time=datetime.now(),
        public_betting_pct=40
    )
    for name, f in factors.items():
        print(f'{name}: {f[\"score\"]} - {f.get(\"detail\", \"\")}')

asyncio.run(test())
"
```

**Check Public Betting:**
- NBA: https://www.actionnetwork.com/nba/public-betting
- NFL: https://www.actionnetwork.com/nfl/public-betting
