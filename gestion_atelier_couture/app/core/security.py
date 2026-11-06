"""Sécurité : hachage Argon2 des mots de passe (RG21) et jetons JWT (RG22)."""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# PasswordHash.recommended() = Argon2 (algorithme recommandé par l'OWASP)
_hasher = PasswordHash.recommended()


def hash_password(mot_de_passe: str) -> str:
    """Renvoie l'empreinte Argon2 du mot de passe (« $argon2id$v=19$... »)."""
    return _hasher.hash(mot_de_passe)


def verify_password(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    """Compare un mot de passe tapé avec l'empreinte stockée."""
    try:
        return _hasher.verify(mot_de_passe, mot_de_passe_hash)
    except Exception:  # hash corrompu / format inconnu -> refus
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    """Crée un JWT signé : {"sub": "<id>", "exp": <timestamp>}."""
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    maintenant = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # la norme JWT veut une chaîne
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Vérifie la signature ET l'expiration. Lève jwt.InvalidTokenError sinon."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
