import sqlite3

conn = sqlite3.connect('echosphere.db')
c = conn.cursor()

tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("All tables:", tables)

for t in tables:
    if any(k in t.lower() for k in ['announc', 'speaker', 'repeat', 'queue', 'audit', 'delivery']):
        count = c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        cols = [col[1] for col in c.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"Table '{t}': {count} rows (columns: {cols})")
        if count > 0 and 'title' in cols:
            samples = c.execute(f"SELECT id, title FROM {t} LIMIT 5").fetchall()
            print(f"  Samples: {samples}")

conn.close()
