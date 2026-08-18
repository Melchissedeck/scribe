from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE recordings ADD COLUMN IF NOT EXISTS theme VARCHAR(255)'))
    conn.commit()
    print('OK - colonne theme ajoutee')
