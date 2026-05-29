import sqlite3
import requests
import time

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_goals_for INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_shots_for INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_goals_against INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_shots_against INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_sh_pct REAL DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN on_ice_sv_pct REAL DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN PDO REAL DEFAULT 0')
    conn.commit()
    print("Added PDO columns to database")
except:
    print("PDO columns already exist, continuing")

# Use hardcoded game IDs we already know work
# 2025-26 regular season games 1 through 1043
print("Building game ID list...")
game_ids = [2025020000 + i for i in range(1, 1044)]
print(f"Processing {len(game_ids)} games")

player_pdo = {}
games_processed = 0

for game_id in game_ids:
    try:
        url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            continue

        data = response.json()
        plays = data.get('plays', [])
        roster_spots = data.get('rosterSpots', [])

        if not plays or not roster_spots:
            continue

        team_rosters = {}
        for player in roster_spots:
            team_id   = player.get('teamId')
            player_id = player.get('playerId')
            position  = player.get('positionCode', '')
            if not team_id or not player_id or position == 'G':
                continue
            if team_id not in team_rosters:
                team_rosters[team_id] = []
            team_rosters[team_id].append(player_id)

        games_processed += 1

        for play in plays:
            event_type = play.get('typeDescKey', '')
            if event_type not in ['shot-on-goal', 'goal']:
                continue

            period = play.get('periodDescriptor', {}).get('number', 0)
            if period > 3:
                continue

            situation = play.get('situationCode', '0000')
            if situation not in ['1551', '1515']:
                continue

            details = play.get('details', {})
            shooting_team_id = details.get('eventOwnerTeamId')
            is_goal = event_type == 'goal'

            if not shooting_team_id:
                continue

            all_team_ids = list(team_rosters.keys())
            if len(all_team_ids) < 2:
                continue

            defending_team_ids = [t for t in all_team_ids if t != shooting_team_id]
            if not defending_team_ids:
                continue
            defending_team_id = defending_team_ids[0]

            for pid in team_rosters.get(shooting_team_id, []):
                if pid not in player_pdo:
                    player_pdo[pid] = {'goals_for':0,'shots_for':0,'goals_against':0,'shots_against':0}
                player_pdo[pid]['shots_for'] += 1
                if is_goal:
                    player_pdo[pid]['goals_for'] += 1

            for pid in team_rosters.get(defending_team_id, []):
                if pid not in player_pdo:
                    player_pdo[pid] = {'goals_for':0,'shots_for':0,'goals_against':0,'shots_against':0}
                player_pdo[pid]['shots_against'] += 1
                if is_goal:
                    player_pdo[pid]['goals_against'] += 1

        if games_processed % 50 == 0:
            print(f"  Processed {games_processed} games so far...")

        time.sleep(0.1)

    except Exception as e:
        print(f"  Skipping game {game_id} — {e}")
        continue

print(f"\nProcessed {games_processed} games")
print(f"Found PDO data for {len(player_pdo)} players")
print("Saving to database...")

updated = 0
for player_id, pdo_data in player_pdo.items():
    gf = pdo_data['goals_for']
    sf = pdo_data['shots_for']
    ga = pdo_data['goals_against']
    sa = pdo_data['shots_against']

    sh_pct = round(gf / sf * 100, 2) if sf > 0 else 0
    sv_pct = round((1 - ga / sa) * 100, 2) if sa > 0 else 0
    pdo    = round(sh_pct + sv_pct, 1)

    cursor.execute('''
        UPDATE players
        SET on_ice_goals_for = ?,
            on_ice_shots_for = ?,
            on_ice_goals_against = ?,
            on_ice_shots_against = ?,
            on_ice_sh_pct = ?,
            on_ice_sv_pct = ?,
            PDO = ?
        WHERE player_id = ?
    ''', (gf, sf, ga, sa, sh_pct, sv_pct, pdo, player_id))

    if cursor.rowcount > 0:
        updated += 1

conn.commit()
conn.close()

print(f"Updated {updated} players with PDO stats")
print("Done!")