import requests

# Hit the NHL API and pull today's schedule
url = "https://api-web.nhle.com/v1/schedule/now"
response = requests.get(url)
data = response.json()

print("NHL API is working!")
print(f"Status code: {response.status_code}")

# Print the first game we find
games = data.get('gameWeek', [{}])[0].get('games', [])
print(f"Games found: {len(games)}")
if games:
    g = games[0]
    print(f"First game: {g['awayTeam']['placeName']['default']} vs {g['homeTeam']['placeName']['default']}")