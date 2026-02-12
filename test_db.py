import sys
import os
from sqlalchemy import create_engine, text

# Ajouter le chemin du projet pour importer config
sys.path.append(os.getcwd())
from app.core.config import settings

def test_conn():
    url = settings.DATABASE_URL
    print(f"Testing connection to: {url.split('@')[1] if '@' in url else url}")
    
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connection successful!")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_conn()
