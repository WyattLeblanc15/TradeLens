import sqlite3
import requests
import time
import math

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE players ADD COLUMN xGF REAL DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN xGA REAL DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN xGF_pct REAL DEFAULT 0')
    cursor.execute('ALTER TABLE players ADD COLUMN shots_taken INTEGER DEFAULT 0')
    conn.commit()
    print("Added xG columns to database")
except:
    print("xG columns already exist, continuing")

def calculate_xg(x, y, shot_type):
    distance = math.sqrt((89 - abs(x))**2 + y**2)
    
    if abs(89 - abs(x)) > 0:
        angle = math.degrees(math.atan(abs(y) / abs(89 - abs(x))))
    else:
        angle = 90
    
    if distance < 15:
        xg = 0.35
    elif distance < 25:
        xg = 0.18
    elif distance < 40:
        xg = 0.08
    elif distance < 55:
        xg = 0.04
    else:
        xg = 0.02
    
    if angle < 20:
        xg *= 1.3
    elif angle > 45:
        xg *= 0.7
    
    shot_type = shot_type.lower() if shot_type else ''
    if 'deflect' in shot_type:
        xg *= 1.4
    elif 'tip' in shot_type:
        xg *= 1.5
    elif 'back' in shot_type:
        xg *= 0.9
    elif 'slap' in shot_type:
        xg *= 0.8
    elif 'snap' in shot_type:
        xg *= 1.05
    
    return round(xg, 4)

# Get real game IDs
print("Getting real game IDs from 2025-26 season...")
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

# Track xG per player
player_xg = {}
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
    
    # Build team rosters from rosterSpots
    # Maps team_id to list of player_ids on that team
    team_rosters = {}
    for player in roster_spots:
        team_id = player.get('teamId')
        player_id = player.get('playerId')
        position = player.get('positionCode', '')
        
        if not team_id or not player_id:
            continue
        
        # Skip goalies for skater xG calculation
        if position == 'G':
            continue
            
        if team_id not in team_rosters:
            team_rosters[team_id] = []
        team_rosters[team_id].append(player_id)
    
    games_processed += 1
    shot_count = 0
    
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
        x = details.get('xCoord', 0)
        y = details.get('yCoord', 0)
        shot_type = details.get('shotType', 'wrist')
        shooting_team_id = details.get('eventOwnerTeamId')
        
        if not shooting_team_id:
            continue
        
        xg_value = calculate_xg(x, y, shot_type)
        
        # Get all team IDs in this game
        all_team_ids = list(team_rosters.keys())
        if len(all_team_ids) < 2:
            continue
        
        # Defending team is whoever is not shooting
        defending_team_ids = [t for t in all_team_ids if t != shooting_team_id]
        if not defending_team_ids:
            continue
        defending_team_id = defending_team_ids[0]
        
        # Credit xGF to shooting team players
        for pid in team_rosters.get(shooting_team_id, []):
            if pid not in player_xg:
                player_xg[pid] = {'xGF': 0, 'xGA': 0, 'shots': 0}
            player_xg[pid]['xGF'] += xg_value
        
        # Credit xGA to defending team players
        for pid in team_rosters.get(defending_team_id, []):
            if pid not in player_xg:
                player_xg[pid] = {'xGF': 0, 'xGA': 0, 'shots': 0}
            player_xg[pid]['xGA'] += xg_value
        
        shot_count += 1
    
    print(f"  Game {game_id} — {shot_count} shots | {len(team_rosters)} teams tracked")
    time.sleep(0.15)

print(f"\nProcessed {games_processed} games")
print(f"Found xG data for {len(player_xg)} players")

# Save to database
print("Saving to database...")
updated = 0

for player_id, xg_data in player_xg.items():
    xgf = round(xg_data['xGF'], 3)
    xga = round(xg_data['xGA'], 3)
    shots = xg_data['shots']
    
    if xgf + xga > 0:
        xgf_pct = round(xgf / (xgf + xga) * 100, 1)
    else:
        xgf_pct = 0
    
    cursor.execute('''
        UPDATE players
        SET xGF = ?, xGA = ?, xGF_pct = ?, shots_taken = ?
        WHERE player_id = ?
    ''', (xgf, xga, xgf_pct, shots, player_id))
    
    if cursor.rowcount > 0:
        updated += 1

conn.commit()
conn.close()

print(f"Updated {updated} players with xG stats")
print("Done!")