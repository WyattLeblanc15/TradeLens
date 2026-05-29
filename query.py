import sqlite3

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

# Test 1: How many players total
cursor.execute('SELECT COUNT(*) FROM players')
print(f"Total players in database: {cursor.fetchone()[0]}")

# Test 2: Top 10 scorers in the league
print("\nTop 10 NHL Scorers 2025-26:")
cursor.execute('''
    SELECT first_name, last_name, team, goals, assists, points, games_played
    FROM players
    ORDER BY points DESC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]} ({row[2]}) — {row[3]}G {row[4]}A {row[5]}PTS in {row[6]}GP")

# Test 3: Pull a specific team
print("\nPittsburgh Penguins roster:")
cursor.execute('''
    SELECT first_name, last_name, position, goals, assists, points
    FROM players
    WHERE team = 'PIT'
    ORDER BY points DESC
''')
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]} ({row[2]}) — {row[3]}G {row[4]}A {row[5]}PTS")

conn.close()