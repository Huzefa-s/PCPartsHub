import sqlite3
from pathlib import Path
p = Path('database/dbDummy.sqlite3')
print('path', p.resolve())
print('exists', p.exists(), 'size', p.stat().st_size if p.exists() else None)
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print('tables', cur.fetchall())
cur.execute("SELECT sql FROM sqlite_master WHERE name='DiscountCodes'")
print('discount sql', cur.fetchone())
conn.close()
