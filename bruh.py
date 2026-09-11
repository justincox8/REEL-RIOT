import sqlite3

conn = sqlite3.connect("media.db")
cur = conn.cursor()

# Preview first
cur.execute("""
    SELECT id, title FROM books 
    WHERE title LIKE 'Beast Quest%' OR title LIKE 'Dinosaur Cove%' OR title LIKE '%Chronicles of Avantia%'
""")
rows = cur.fetchall()
print(f"About to delete {len(rows)} books:")
for r in rows:
    print(" ", r)

# Delete them
ids_to_delete = [r[0] for r in rows]
cur.execute(f"DELETE FROM books WHERE id IN ({','.join('?' * len(ids_to_delete))})", ids_to_delete)
conn.commit()
print(f"Deleted {cur.rowcount} rows")

# Clean up any ratings pointing at the now-deleted books
cur.execute("""
    DELETE FROM ratings 
    WHERE candidate_media_type = 'book' 
    AND candidate_id NOT IN (SELECT id FROM books)
""")
conn.commit()
print(f"Removed {cur.rowcount} orphaned ratings")

conn.close()