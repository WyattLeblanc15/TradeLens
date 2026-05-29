import requests
import json

# Check shifts endpoint
url = "https://api-web.nhle.com/v1/gamecenter/2025020034/play-by-play"
response = requests.get(url)
data = response.json()

# Get roster spots
roster = data.get('rosterSpots', [])
print(f"Total players in game: {len(roster)}")

# Show all players and their teams
for player in roster:
    team_id = player.get('teamId')
    player_id = player.get('playerId')
    first = player.get('firstName', {}).get('default', '')
    last = player.get('lastName', {}).get('default', '')
    position = player.get('positionCode', '')
    print(f"  Team {team_id} | {first} {last} | {position} | ID: {player_id}")