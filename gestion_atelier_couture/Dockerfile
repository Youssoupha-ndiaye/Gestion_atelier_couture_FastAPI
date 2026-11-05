# ---- Image de l'API Atelier de couture ----
FROM python:3.12-slim

# Pas de fichiers .pyc, logs affichés immédiatement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# 1) Les dépendances d'abord : cette couche est mise en cache tant que
#    requirements.txt ne change pas (rebuild beaucoup plus rapide)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Puis le code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini pytest.ini entrypoint.sh ./
COPY tests/ ./tests/

# Corrige les fins de ligne Windows (CRLF) éventuelles et rend le script exécutable
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

# entrypoint.sh : attendre la base -> alembic upgrade head -> seed -> uvicorn
CMD ["./entrypoint.sh"]
