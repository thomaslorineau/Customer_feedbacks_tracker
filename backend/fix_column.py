import os
import psycopg2

os.environ['DATABASE_URL'] = 'postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker'

conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute('ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_false_positive BOOLEAN DEFAULT FALSE')
    print('Column is_false_positive added or already exists')
except Exception as e:
    print(f'Error adding column: {e}')

try:
    cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_is_false_positive ON posts(is_false_positive)')
    print('Index created or already exists')
except Exception as e:
    print(f'Error creating index: {e}')

try:
    cur.execute('UPDATE posts SET is_false_positive = FALSE WHERE is_false_positive IS NULL')
    print('Updated NULL values')
except Exception as e:
    print(f'Error updating: {e}')

# Verify
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'is_false_positive'")
result = cur.fetchone()
if result:
    print(f'Verification: Column exists - {result[0]}')
else:
    print('Verification: Column NOT found!')

cur.close()
conn.close()
print('Done!')

