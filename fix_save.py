import sqlite3

conn = sqlite3.connect('tradelens.db')
cursor = conn.cursor()

# Add the missing column
try:
    cursor.execute('ALTER TABLE players ADD COLUMN shots_taken INTEGER DEFAULT 0')
    conn.commit()
    print("Added shots_taken column")
except:
    print("Column already exists")

conn.close()
print("Done — now run calculate_xg.py again")