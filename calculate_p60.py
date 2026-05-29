import sqlite3

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE players ADD COLUMN P60 REAL DEFAULT 0')
    conn.commit()
    print("Added P60 column to database")
except:
    print("P60 column already exists, continuing")

# Pull all players with points and TOI
cursor.execute('''
    SELECT player_id, first_name, last_name, team,
           points, games_played, toi_per_game
    FROM players
    WHERE points > 0 AND toi_per_game != 'N/A' AND toi_per_game != '0:00'
''')
players = cursor.fetchall()
print(f"Calculating P/60 for {len(players)} players...")

def toi_to_seconds(toi):
    try:
        parts = toi.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0

updated = 0

for row in players:
    player_id, first, last, team, points, gp, toi = row

    if not gp or gp == 0:
        continue

    toi_seconds = toi_to_seconds(toi)
    if toi_seconds == 0:
        continue

    # Total ice time in hours
    total_toi_seconds = toi_seconds * gp
    total_toi_hours   = total_toi_seconds / 3600

    # P/60 = points per 60 minutes of ice time
    p60 = round(points / total_toi_hours, 2)

    cursor.execute('''
        UPDATE players SET P60 = ? WHERE player_id = ?
    ''', (p60, player_id))

    if cursor.rowcount > 0:
        updated += 1
        print(f"  {first} {last} ({team}) — {points}pts in {gp}GP — P/60: {p60}")

conn.commit()
conn.close()

print(f"\nUpdated {updated} players with P/60")
print("Done!")