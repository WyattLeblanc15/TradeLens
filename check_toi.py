import sqlite3
import requests
import time

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

cursor.execute('SELECT player_id, first_name, last_name, team FROM players')
players = cursor.fetchall()
print(f"Fixing TOI for {len(players)} players...")

updated = 0

for player_id, first, last, team in players:
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    response = requests.get(url)

    if response.status_code != 200:
        continue

    data = response.json()
    season_totals = data.get('seasonTotals', [])

    for season in season_totals:
        if (season.get('season') == 20252026 and
            season.get('gameTypeId') == 2 and
            season.get('leagueAbbrev') == 'NHL'):
            avg_toi = season.get('avgToi', 'N/A')
            cursor.execute('''
                UPDATE players SET toi_per_game = ?
                WHERE player_id = ?
            ''', (avg_toi, player_id))
            updated += 1
            print(f"  {first} {last} ({team}) — TOI: {avg_toi}")
            break

    time.sleep(0.08)

conn.commit()
conn.close()
print(f"\nDone! Updated {updated} players with avg TOI per game")