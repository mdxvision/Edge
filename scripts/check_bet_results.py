#!/usr/bin/env python3
"""
Check bet results and send Telegram notification.
Run this after games complete to get results.
"""

import asyncio
import aiohttp
import os
from datetime import datetime

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8080842197:AAEaJheVSM1PTXzLWAmDvlzE-vtE3ByTqbI')
TELEGRAM_CHAT_ID = '769278691'

# The 10 bets placed on Jan 3, 2026
BETS = [
    {"sport": "NFL", "pick": "Saints", "spread": 3.5, "opponent": "Falcons", "units": 2},
    {"sport": "NFL", "pick": "Browns", "spread": 7.5, "opponent": "Bengals", "units": 2},
    {"sport": "NFL", "pick": "Vikings", "spread": -10.0, "opponent": "Packers", "units": 2},
    {"sport": "NFL", "pick": "Cowboys", "spread": 3.5, "opponent": "Giants", "units": 2},
    {"sport": "NFL", "pick": "Titans", "spread": 13.5, "opponent": "Jaguars", "units": 2},
    {"sport": "CBB", "pick": "Coastal Carolina", "spread": 2.5, "opponent": "Georgia Southern", "units": 2},
    {"sport": "CBB", "pick": "Green Bay", "spread": -9.0, "opponent": "Fort Wayne", "units": 2},
    {"sport": "CBB", "pick": "Lipscomb", "spread": 10.5, "opponent": "Jacksonville", "units": 2},
    {"sport": "Soccer", "pick": "Leeds", "spread": 0.2, "opponent": "Liverpool", "units": 2},
    {"sport": "Soccer", "pick": "Man City", "spread": -0.8, "opponent": "Sunderland", "units": 2},
]


async def send_telegram(message: str):
    """Send message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return resp.status == 200


async def check_nfl_scores():
    """Check NFL scores from ESPN."""
    results = []
    async with aiohttp.ClientSession() as session:
        async with session.get('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard') as resp:
            data = await resp.json()

            for event in data.get('events', []):
                status_state = event.get('status', {}).get('type', {}).get('state', '')
                if status_state != 'post':
                    continue

                comps = event.get('competitions', [{}])[0]
                teams = comps.get('competitors', [])

                scores = {}
                for t in teams:
                    team_name = t.get('team', {}).get('displayName', '')
                    score = int(t.get('score', '0'))
                    scores[team_name] = score

                for bet in BETS:
                    if bet['sport'] != 'NFL':
                        continue

                    pick_score = None
                    opp_score = None

                    for team, score in scores.items():
                        if bet['pick'] in team:
                            pick_score = score
                        if bet['opponent'] in team:
                            opp_score = score

                    if pick_score is not None and opp_score is not None:
                        adjusted = pick_score + bet['spread']
                        if adjusted > opp_score:
                            result = "WIN"
                            profit = bet['units'] * 0.91  # -110 odds
                        elif adjusted < opp_score:
                            result = "LOSS"
                            profit = -bet['units']
                        else:
                            result = "PUSH"
                            profit = 0

                        results.append({
                            "pick": f"{bet['pick']} {bet['spread']:+.1f}",
                            "score": f"{pick_score}-{opp_score}",
                            "result": result,
                            "profit": profit
                        })
    return results


async def check_cbb_scores():
    """Check College Basketball scores from ESPN."""
    results = []
    async with aiohttp.ClientSession() as session:
        async with session.get('https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?limit=100') as resp:
            data = await resp.json()

            for event in data.get('events', []):
                status_state = event.get('status', {}).get('type', {}).get('state', '')
                if status_state != 'post':
                    continue

                name = event.get('name', '').lower()
                comps = event.get('competitions', [{}])[0]
                teams = comps.get('competitors', [])

                for bet in BETS:
                    if bet['sport'] != 'CBB':
                        continue

                    pick_words = bet['pick'].lower().split()
                    if not any(word in name for word in pick_words):
                        continue

                    scores = {}
                    for t in teams:
                        team_name = t.get('team', {}).get('displayName', '')
                        score = int(t.get('score', '0'))
                        scores[team_name] = score

                    pick_score = None
                    opp_score = None

                    for team, score in scores.items():
                        if any(word in team.lower() for word in pick_words):
                            pick_score = score
                        else:
                            opp_score = score

                    if pick_score is not None and opp_score is not None:
                        adjusted = pick_score + bet['spread']
                        if adjusted > opp_score:
                            result = "WIN"
                            profit = bet['units'] * 0.91
                        elif adjusted < opp_score:
                            result = "LOSS"
                            profit = -bet['units']
                        else:
                            result = "PUSH"
                            profit = 0

                        results.append({
                            "pick": f"{bet['pick']} {bet['spread']:+.1f}",
                            "score": f"{pick_score}-{opp_score}",
                            "result": result,
                            "profit": profit
                        })
    return results


async def main():
    print(f"\n{'='*50}")
    print(f"BET RESULTS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    all_results = []

    # Check NFL
    print("Checking NFL...")
    nfl_results = await check_nfl_scores()
    all_results.extend(nfl_results)
    for r in nfl_results:
        print(f"  {r['result']}: {r['pick']} ({r['score']}) -> {r['profit']:+.2f}u")

    # Check CBB
    print("\nChecking College Basketball...")
    cbb_results = await check_cbb_scores()
    all_results.extend(cbb_results)
    for r in cbb_results:
        print(f"  {r['result']}: {r['pick']} ({r['score']}) -> {r['profit']:+.2f}u")

    # Calculate totals
    if all_results:
        wins = sum(1 for r in all_results if r['result'] == 'WIN')
        losses = sum(1 for r in all_results if r['result'] == 'LOSS')
        pushes = sum(1 for r in all_results if r['result'] == 'PUSH')
        total_profit = sum(r['profit'] for r in all_results)

        print(f"\n{'='*50}")
        print(f"SUMMARY: {wins}-{losses}-{pushes} | {total_profit:+.2f} units")
        print(f"{'='*50}")

        # Send Telegram notification
        message = f"*EdgeBet Results*\n\n"
        message += f"Record: {wins}-{losses}-{pushes}\n"
        message += f"Profit: {total_profit:+.2f} units\n\n"

        for r in all_results:
            emoji = "✅" if r['result'] == 'WIN' else "❌" if r['result'] == 'LOSS' else "➖"
            message += f"{emoji} {r['pick']}: {r['score']}\n"

        print("\nSending Telegram notification...")
        success = await send_telegram(message)
        print(f"Telegram: {'Sent!' if success else 'Failed'}")
    else:
        print("\nNo completed games found yet.")
        print("NFL games start at 1:00 PM EST tomorrow.")


if __name__ == "__main__":
    asyncio.run(main())
