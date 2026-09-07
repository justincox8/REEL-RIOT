import pandas as pd
import sqlite3

conn = sqlite3.connect("media.db")
df = pd.read_csv("songs.csv")

for _, row in df.iterrows():
    conn.execute("""
        INSERT OR IGNORE INTO songs (title, artist, genre, theme)
        VALUES (?, ?, ?, ?)
    """, (row["title"], row["artist"], row["genre"], row["theme"]))

conn.commit()
conn.close()

