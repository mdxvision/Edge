import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8080"

async def test_analysis(client, game_id, sport):
    print(f"\n--- Testing Analysis for {sport} Game ID: {game_id} ---")
    try:
        url = f"/predictions/game/{game_id}"
        print(f"URL: {url}")
        
        response = await client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            factors = data.get("factors", {})
            print("Factors Found:")
            for key, val in factors.items():
                print(f"  - {key}: {val.get('weighted_contribution', 'N/A')}")
            
            analysis = data.get("analysis", {})
            print(f"Alignment Score: {analysis.get('alignment_score')}")
            print("SUCCESS: Analysis returned.")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

async def get_valid_game_id(client, sport_endpoint):
    resp = await client.get(sport_endpoint, params={"include_finished": "true"})
    if resp.status_code == 200:
        games = resp.json().get("games", [])
        # Provide the LAST game (likely finished or late)
        if games:
            game = games[-1]
            return game.get("id") or game.get("game_id")
    return None

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        
        # Test specific simulated external ID
        test_id = 999999999
        print(f"Testing manual External ID: {test_id}")
        await test_analysis(client, test_id, "NBA (Manual ID)")

if __name__ == "__main__":
    asyncio.run(main())
