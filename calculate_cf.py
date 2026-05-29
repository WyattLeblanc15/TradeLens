import sqlite3
import requests
import time

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

# Add CF columns to database
try:
    cursor.execute('ALTER TABLE players ADD COLUMN CF INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN CA INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN CF_pct REAL DEFAULT 0')
    conn.commit()
    print("Added CF columns to database")
except:
    print("CF columns already exist, continuing")

# Pull real game IDs from schedule
print("Getting game IDs...")
game_ids = []

dates = [
    '2025-10-08', '2025-10-09', '2025-10-10', '2025-10-11',
    '2025-10-14', '2025-10-15', '2025-10-16', '2025-10-17',
    '2025-10-18', '2025-10-19', '2025-10-20', '2025-10-21',
    '2025-10-22', '2025-10-23', '2025-10-24', '2025-10-25',
    '2025-10-28', '2025-10-29', '2025-10-30', '2025-10-31',
]

for date in dates:
    url = f"https://api-web.nhle.com/v1/schedule/{date}"
    response = requests.get(url)
    if response.status_code != 200:
        continue
    data = response.json()
    for day in data.get('gameWeek', []):
        for game in day.get('games', []):
            gid = game.get('id')
            if gid:
                game_ids.append(gid)
    time.sleep(0.1)

print(f"Found {len(game_ids)} games to process")

# Track CF and CA per player
player_cf = {}
games_processed = 0

for game_id in game_ids:
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    response = requests.get(url)

    if response.status_code != 200:
        continue

    data = response.json()
    plays = data.get('plays', [])
    roster_spots = data.get('rosterSpots', [])

    if not plays or not roster_spots:
        continue

    # Build team rosters — skip goalies
    team_rosters = {}
    for player in roster_spots:
        team_id  = player.get('teamId')
        player_id = player.get('playerId')
        position = player.get('positionCode', '')
        if not team_id or not player_id or position == 'G':
            continue
        if team_id not in team_rosters:
            team_rosters[team_id] = []
        team_rosters[team_id].append(player_id)

    games_processed += 1
    shot_count = 0

    for play in plays:
        event_type = play.get('typeDescKey', '')

        # CF counts ALL shot attempts — on net, missed, and blocked
        if event_type not in ['shot-on-goal', 'missed-shot', 'blocked-shot', 'goal']:
            continue

        period = play.get('periodDescriptor', {}).get('number', 0)
        if period > 3:
            continue

        # 5v5 only
        situation = play.get('situationCode', '0000')
        if situation not in ['1551', '1515']:
            continue

        details = play.get('details', {})
        shooting_team_id = details.get('eventOwnerTeamId')

        if not shooting_team_id:
            continue

        all_team_ids = list(team_rosters.keys())
        if len(all_team_ids) < 2:
            continue

        defending_team_ids = [t for t in all_team_ids if t != shooting_team_id]
        if not defending_team_ids:
            continue
        defending_team_id = defending_team_ids[0]

        # Credit CF to shooting team players
        for pid in team_rosters.get(shooting_team_id, []):
            if pid not in player_cf:
                player_cf[pid] = {'CF': 0, 'CA': 0}
            player_cf[pid]['CF'] += 1

        # Credit CA to defending team players
        for pid in team_rosters.get(defending_team_id, []):
            if pid not in player_cf:
                player_cf[pid] = {'CF': 0, 'CA': 0}
            player_cf[pid]['CA'] += 1

        shot_count += 1

    print(f"  Game {game_id} — {shot_count} shot attempts processed")
    time.sleep(0.15)

print(f"\nProcessed {games_processed} games")
print(f"Found CF data for {len(player_cf)} players")

# Save to database
print("Saving to database...")
updated = 0

for player_id, cf_data in player_cf.items():
    cf  = cf_data['CF']
    ca  = cf_data['CA']

    if cf + ca > 0:
        cf_pct = round(cf / (cf + ca) * 100, 1)
    else:
        cf_pct = 0

    cursor.execute('''
        UPDATE players
        SET CF = ?, CA = ?, CF_pct = ?
        WHERE player_id = ?
    ''', (cf, ca, cf_pct, player_id))

    if cursor.rowcount > 0:
        updated += 1

conn.commit()
conn.close()

print(f"Updated {updated} players with CF% stats")
print("Done!")