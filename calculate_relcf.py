import sqlite3
import requests
import time

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE players ADD COLUMN CF_with INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN CA_with INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN CF_without INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN CA_without INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN rel_CF_pct REAL DEFAULT 0')
    conn.commit()
    print("Added relCF columns to database")
except:
    print("relCF columns already exist, continuing")

print("Building game ID list...")
game_ids = [2025020000 + i for i in range(1, 1044)]
print(f"Processing {len(game_ids)} games")

# Track CF with and without each player
# with = shot attempts while player is on ice
# without = shot attempts while player is off ice but still their team's game
player_rel = {}
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

        # Build team rosters
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

        # Initialize all players in this game
        for team_id, roster in team_rosters.items():
            for pid in roster:
                if pid not in player_rel:
                    player_rel[pid] = {
                        'CF_with': 0, 'CA_with': 0,
                        'CF_without': 0, 'CA_without': 0,
                        'team_id': team_id
                    }

        games_processed += 1

        for play in plays:
            event_type = play.get('typeDescKey', '')
            if event_type not in ['shot-on-goal', 'missed-shot', 'blocked-shot', 'goal']:
                continue

            period = play.get('periodDescriptor', {}).get('number', 0)
            if period > 3:
                continue

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

            shooting_roster = team_rosters.get(shooting_team_id, [])
            defending_roster = team_rosters.get(defending_team_id, [])

            # For shooting team — every player on that team
            # CF_with if they are one of the ~6 on ice (we use full roster as approximation)
            # This is simplified — true on-ice tracking needs shift data
            for pid in shooting_roster:
                if pid not in player_rel:
                    continue
                player_rel[pid]['CF_with'] += 1

            # Every other player on shooting team gets CF_without credit
            # (approximation — they were on bench for this shot)
            # We skip this for now and calculate from totals

            # For defending team
            for pid in defending_roster:
                if pid not in player_rel:
                    continue
                player_rel[pid]['CA_with'] += 1

        if games_processed % 50 == 0:
            print(f"  Processed {games_processed} games so far...")

        time.sleep(0.1)

    except Exception as e:
        print(f"  Skipping game {game_id} — {e}")
        continue

print(f"\nProcessed {games_processed} games")
print(f"Calculating relCF% for {len(player_rel)} players...")

# Calculate relCF%
# Since we are using team level data per game
# relCF% = player CF% - team CF% without them
# We approximate this using the difference between their CF%
# and the league average CF% for their team

# First get each player's CF% from database
cursor.execute('SELECT player_id, CF_pct FROM players WHERE CF_pct > 0')
player_cfpct = {row[0]: row[1] for row in cursor.fetchall()}

# Get team average CF% 
cursor.execute('''
    SELECT team, AVG(CF_pct)
    FROM players
    WHERE CF_pct > 0
    GROUP BY team
''')
team_avg_cf = {row[0]: row[1] for row in cursor.fetchall()}

# Get each player's team
cursor.execute('SELECT player_id, team FROM players')
player_team = {row[0]: row[1] for row in cursor.fetchall()}

print("Saving relCF% to database...")
updated = 0

for player_id in player_cfpct:
    player_cf_pct = player_cfpct.get(player_id, 0)
    team = player_team.get(player_id, '')
    team_cf = team_avg_cf.get(team, 50.0)

    # relCF% = player CF% minus team average CF%
    rel_cf = round(player_cf_pct - team_cf, 2)

    cursor.execute('''
        UPDATE players
        SET rel_CF_pct = ?
        WHERE player_id = ?
    ''', (rel_cf, player_id))

    if cursor.rowcount > 0:
        updated += 1

conn.commit()
conn.close()

print(f"Updated {updated} players with relCF% stats")
print("Done!")