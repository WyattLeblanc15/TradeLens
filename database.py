import sqlite3
import requests
import time

# ── Connect to (or create) the database ──────────────────────────
conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

# ── Create the players table ──────────────────────────────────────
cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id     INTEGER PRIMARY KEY,
        first_name    TEXT,
        last_name     TEXT,
        team          TEXT,
        position      TEXT,
        sweater_number INTEGER,
        goals         INTEGER,
        assists       INTEGER,
        points        INTEGER,
        games_played  INTEGER,
        plus_minus    INTEGER,
        toi_per_game  TEXT
    )
''')

conn.commit()
print("Database created successfully!")

# ── All 32 NHL team codes ─────────────────────────────────────────
TEAMS = [
    'ANA','BOS','BUF','CAR','CBJ','CGY','CHI','COL',
    'DAL','DET','EDM','FLA','LAK','MIN','MTL','NJD',
    'NSH','NYI','NYR','OTT','PHI','PIT','SEA','SJS',
    'STL','TBL','TOR','UTA','VAN','VGK','WSH','WPG'
]

# ── Pull every team's roster and save every player ────────────────
total_players = 0

for team_code in TEAMS:
    print(f"Pulling {team_code} roster...")
    
    url = f"https://api-web.nhle.com/v1/roster/{team_code}/20252026"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"  Skipping {team_code} — API error")
        continue
    
    roster = response.json()
    
    # Forwards, defensemen, and goalies
    all_players = (
        roster.get('forwards', []) +
        roster.get('defensemen', []) +
        roster.get('goalies', [])
    )
    
    for player in all_players:
        player_id = player['id']
        first     = player['firstName']['default']
        last      = player['lastName']['default']
        position  = player.get('positionCode', 'N/A')
        number    = player.get('sweaterNumber', 0)
        
        # Pull individual player stats
        stats_url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
        stats_res = requests.get(stats_url)
        
        goals = assists = points = gp = plus_minus = 0
        toi = 'N/A'
        
        if stats_res.status_code == 200:
            stats_data = stats_res.json()
            s = stats_data.get('featuredStats', {}).get('regularSeason', {}).get('subSeason', {})
            goals      = s.get('goals', 0)
            assists    = s.get('assists', 0)
            points     = s.get('points', 0)
            gp         = s.get('gamesPlayed', 0)
            plus_minus = s.get('plusMinus', 0)
            toi        = s.get('avgToi', 'N/A')
        
        # Save to database
        cursor.execute('''
            INSERT OR REPLACE INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (player_id, first, last, team_code, position, number,
              goals, assists, points, gp, plus_minus, toi))
        
        total_players += 1
        print(f"  Saved: {first} {last} — {points}pts in {gp}GP")
    
    conn.commit()
    time.sleep(0.5)  # be polite to the API

print(f"\nDone! {total_players} players saved to tradelens.db")
conn.close()