import sqlite3
import requests
import time

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

# Add TOI columns
try:
    cursor.execute('ALTER TABLE players ADD COLUMN toi_5v5 TEXT DEFAULT "0:00"')
    cursor.execute('ALTER TABLE players ADD COLUMN toi_pp TEXT DEFAULT "0:00"')
    cursor.execute('ALTER TABLE players ADD COLUMN toi_pk TEXT DEFAULT "0:00"')
    cursor.execute('ALTER TABLE players ADD COLUMN toi_5v5_seconds INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN toi_pp_seconds INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN toi_pk_seconds INTEGER DEFAULT 0')
    conn.commit()
    print("Added TOI columns to database")
except:
    print("TOI columns already exist, continuing")

# Pull all players from database
cursor.execute('SELECT player_id, first_name, last_name, team FROM players')
players = cursor.fetchall()
print(f"Updating TOI for {len(players)} players...")

def time_to_seconds(t):
    if not t or t == 'N/A':
        return 0
    try:
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0

updated = 0
errors  = 0

for player_id, first, last, team in players:
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    response = requests.get(url)

    if response.status_code != 200:
        errors += 1
        continue

    data = response.json()

    # Try to get current season splits
    career_stats = data.get('seasonTotals', [])

    toi_5v5 = '0:00'
    toi_pp  = '0:00'
    toi_pk  = '0:00'

    # Find 2025-26 regular season NHL stats
    for season in career_stats:
        if (season.get('season') == 20252026 and
            season.get('gameTypeId') == 2 and
            season.get('leagueAbbrev') == 'NHL'):

            toi_5v5 = season.get('evTimeOnIcePerGame', '0:00') or '0:00'
            toi_pp  = season.get('ppTimeOnIcePerGame', '0:00') or '0:00'
            toi_pk  = season.get('shTimeOnIcePerGame', '0:00') or '0:00'
            break

    toi_5v5_sec = time_to_seconds(toi_5v5)
    toi_pp_sec  = time_to_seconds(toi_pp)
    toi_pk_sec  = time_to_seconds(toi_pk)

    cursor.execute('''
        UPDATE players
        SET toi_5v5 = ?, toi_pp = ?, toi_pk = ?,
            toi_5v5_seconds = ?, toi_pp_seconds = ?, toi_pk_seconds = ?
        WHERE player_id = ?
    ''', (toi_5v5, toi_pp, toi_pk,
          toi_5v5_sec, toi_pp_sec, toi_pk_sec,
          player_id))

    if toi_5v5 != '0:00':
        updated += 1
        print(f"  {first} {last} ({team}) — 5v5: {toi_5v5} | PP: {toi_pp} | PK: {toi_pk}")

    time.sleep(0.1)

conn.commit()
conn.close()

print(f"\nDone! Updated {updated} players with TOI splits")
print(f"Errors: {errors}")