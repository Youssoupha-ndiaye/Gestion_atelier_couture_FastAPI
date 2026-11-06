from pydantic import BaseModel


class Token(BaseModel):
    """Réponse de POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # durée de validité en SECONDES
