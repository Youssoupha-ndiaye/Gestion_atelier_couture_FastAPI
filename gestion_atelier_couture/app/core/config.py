"""Configuration de l'application (pydantic-settings).

Toutes les valeurs sensibles (mot de passe de la base, clé JWT...) sont lues
depuis les variables d'environnement ou le fichier .env : rien n'est écrit en dur
dans le code ni dans Git.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore" : les variables POSTGRES_* du .env (utilisées par Docker)
    # ne provoquent pas d'erreur même si l'API ne s'en sert pas.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "API Atelier de couture"

    DATABASE_URL: str = "postgresql+psycopg://atelier:changeme@localhost:5432/atelier"
    TEST_DATABASE_URL: str = "postgresql+psycopg://atelier:changeme@localhost:5432/atelier_test"

    SECRET_KEY: str = "cle_de_developpement_a_remplacer"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_EMAIL: str = "admin@atelier.sn"
    ADMIN_PASSWORD: str = "changeme123"
    ADMIN_NOM: str = "Mamadou Ndiaye"
    SEED_COMPTES_DEMO: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
