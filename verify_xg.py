import sqlite3

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

print("Top 15 players by xGF%:")
cursor.execute('''
    SELECT first_name, last_name, team, xGF_pct, xGF, xGA
    FROM players
    WHERE xGF_pct > 0
    ORDER BY xGF_pct DESC
    LIMIT 15
''')
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]} ({row[2]}) — xGF%: {row[3]} | xGF: {row[4]} | xGA: {row[5]}")

print("\nBottom 10 players by xGF%:")
cursor.execute('''
    SELECT first_name, last_name, team, xGF_pct, xGF, xGA
    FROM players
    WHERE xGF_pct > 0
    ORDER BY xGF_pct ASC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]} ({row[2]}) — xGF%: {row[3]}")

conn.close()