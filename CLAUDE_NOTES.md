# Claude Notes - Edge Betting Platform

## Last Updated: December 29, 2025

---

## Project Overview
Multi-sport betting recommendation engine with FastAPI backend and React frontend.

**Running Services:**
- Backend API: `http://localhost:8080`
- Frontend: `http://localhost:5001`
- Login: `test@edgebet.com` / `TestPass123!`

---

## Current Record

```
Overall:  14-25-0 (35.9%)  -16.07u
NBA:      6-15 (29%)       -10.62u  ← Problem area
NFL:      5-10 (33%)       -5.45u
Soccer:   3-0 (100%)       +0.00u
```

---

## Strategy Change (Dec 28, 2025)

### Problem Identified
- Heavy favorites kept losing outright (Celtics -250, Grizzlies -200)
- Large spreads never covered (0-3 on spreads > 7)
- Favorites: 5-14 (26%) → -10.62u

### New Strategy Rules (`/app/betting_strategy.py`)

| Rule | Old | New |
|------|-----|-----|
| Max Spread | No limit | 6 points |
| ML Favorites | Any odds | -150 max |
| Underdog Range | Rarely bet | +100 to +200 |
| Favorite Units | 1.5-1.7u | 0.75u max |
| Underdog Units | 1.0u | 1.5u |
| Min Edge (Favorites) | 3% | 6% |

### Key Principles
1. NO spreads larger than 6 points
2. NO heavy chalk (juicier than -150)
3. PREFER plus-money underdogs
4. Higher edge requirement for favorites (6% vs 3%)
5. More units on dogs, fewer on favorites

---

## Pending Picks (Dec 29, 2025)

```
Cleveland Cavaliers ML @ +150 (1.7u) - 8:00 PM ET
Dallas Mavericks ML @ +100 (1.6u) - 10:30 PM ET

Total exposure: 3.3u
Both UNDERDOGS (new strategy)
```

---

## Important Files

| File | Purpose |
|------|---------|
| `/app/betting_strategy.py` | New strategy filters and rules |
| `/app/services/edge_engine.py` | Value bet detection |
| `/app/services/auto_settler.py` | Auto-settlement service |
| `/scripts/settle_dec29.py` | Settlement script for Dec 29 picks |
| `/scripts/seed_test_user.py` | Create test user |

---

## Commands

**Start Backend:**
```bash
cd /Users/rafaelrodriguez/GitHub/Edge
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Start Frontend:**
```bash
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev
```

**Show Record:**
```python
# Query tracked_picks table for status in ('won', 'lost', 'push')
```

**Settle Picks:**
```bash
python scripts/settle_dec29.py
```

---

## Session Context

- User is tracking betting performance
- Recently analyzed losses and adjusted strategy
- Cancelled 3 bad pending picks that violated new rules
- Generated 2 new underdog picks using new strategy
- Waiting for Dec 29 games to settle

---

## Next Steps

1. Monitor Dec 29 games (Cavs @ Spurs, Mavs @ Blazers)
2. Settle picks when games finish
3. Continue applying new strategy filters
4. Track performance of new underdog-focused approach
