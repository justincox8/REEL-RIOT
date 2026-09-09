import sqlite3

conn = sqlite3.connect("media.db")
cur = conn.cursor()

cur.execute("ALTER TABLE ratings RENAME COLUMN song_id TO source_id")
cur.execute("ALTER TABLE ratings ADD COLUMN source_media_type TEXT")

# Since all 119 existing rows had a song as the source, backfill that explicitly
cur.execute("UPDATE ratings SET source_media_type = 'song' WHERE source_media_type IS NULL")

conn.commit()
conn.close()
print("Migration done.")