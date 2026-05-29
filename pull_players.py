import requests
import json

# Step 1: Get all NHL teams
print("Pulling NHL teams...")
teams_url = "https://api.nhle.com/stats/rest/en/team"
teams_data = requests.get(teams_url).json()

teams = teams_data['data']
print(f"Found {len(teams)} teams")

# Step 2: Pull roster for one team to test (LA Kings = LAK)
print("\nPulling LA Kings roster...")
roster_url = "https://api-web.nhle.com/v1/roster/LAK/20252026"
roster_data = requests.get(roster_url).json()

forwards = roster_data.get('forwards', [])
print(f"Found {len(forwards)} forwards")

# Step 3: Print each forward's name
print("\nLA Kings Forwards:")
for player in forwards:
    name = f"{player['firstName']['default']} {player['lastName']['default']}"
    number = player.get('sweaterNumber', '?')
    print(f"  #{number} {name}")

# Step 4: Pull Byfield's stats specifically
print("\nPulling Quinton Byfield stats...")
byfield_id = 8482124
player_url = f"https://api-web.nhle.com/v1/player/{byfield_id}/landing"
player_data = requests.get(player_url).json()

season_stats = player_data.get('featuredStats', {}).get('regularSeason', {}).get('subSeason', {})
print(f"Goals: {season_stats.get('goals', 'N/A')}")
print(f"Assists: {season_stats.get('assists', 'N/A')}")
print(f"Points: {season_stats.get('points', 'N/A')}")
print(f"Games Played: {season_stats.get('gamesPlayed', 'N/A')}")