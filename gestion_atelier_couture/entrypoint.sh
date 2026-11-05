#!/bin/sh
# Démarrage du conteneur API (appelé par le Dockerfile)
set -e

echo "⏳ Attente de PostgreSQL..."
python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for tentative in range(30):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✔ PostgreSQL est prêt")
        sys.exit(0)
    except Exception as exc:
        print(f"  base pas encore prête ({tentative + 1}/30) : {exc.__class__.__name__}")
        time.sleep(2)
print("✘ PostgreSQL injoignable"); sys.exit(1)
PY

echo "📦 Migrations : alembic upgrade head"
alembic upgrade head

echo "🌱 Données de départ : python -m app.seed"
python -m app.seed

echo "🚀 Lancement de l'API sur http://localhost:8000/docs"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
