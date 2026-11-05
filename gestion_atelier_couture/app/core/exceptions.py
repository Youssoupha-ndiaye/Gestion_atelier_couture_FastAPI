"""Exceptions métier + handlers qui les transforment en réponses HTTP.

Les services lèvent ces exceptions SANS connaître HTTP ; main.py enregistre les
handlers ci-dessous qui les traduisent en {"detail": "..."} avec le bon code.
"""
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErreurMetier(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(ErreurMetier):
    """Ressource introuvable -> 404."""
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(ErreurMetier):
    """Conflit avec l'état actuel (doublon, transition interdite...) -> 409."""
    status_code = status.HTTP_409_CONFLICT


class RegleMetierError(ErreurMetier):
    """Données valides en forme mais contraires à une règle de gestion -> 422."""
    status_code = 422


class ForbiddenError(ErreurMetier):
    """Rôle insuffisant pour cette action précise (ex. tailleur qui annule) -> 403."""
    status_code = status.HTTP_403_FORBIDDEN


class UnauthorizedError(ErreurMetier):
    """Identifiants invalides -> 401."""
    status_code = status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Traduction en français des erreurs de validation Pydantic (422)
# ---------------------------------------------------------------------------
_MESSAGES_FR = {
    "missing": "Champ obligatoire",
    "string_too_short": "Doit contenir au moins {min_length} caractère(s)",
    "string_too_long": "Doit contenir au plus {max_length} caractère(s)",
    "greater_than": "Doit être strictement supérieur à {gt}",
    "greater_than_equal": "Doit être supérieur ou égal à {ge}",
    "less_than": "Doit être strictement inférieur à {lt}",
    "less_than_equal": "Doit être inférieur ou égal à {le}",
    "int_parsing": "Doit être un nombre entier",
    "int_type": "Doit être un nombre entier",
    "int_from_float": "Doit être un nombre entier",
    "float_parsing": "Doit être un nombre",
    "float_type": "Doit être un nombre",
    "bool_parsing": "Doit être true ou false",
    "date_parsing": "Date invalide (format attendu : AAAA-MM-JJ)",
    "date_from_datetime_parsing": "Date invalide (format attendu : AAAA-MM-JJ)",
    "string_type": "Doit être une chaîne de caractères",
    "literal_error": "Valeur non autorisée. Valeurs possibles : {expected}",
    "enum": "Valeur non autorisée. Valeurs possibles : {expected}",
    "too_short": "Doit contenir au moins {min_length} élément(s)",
    "list_type": "Doit être une liste",
    "extra_forbidden": "Champ non autorisé",
    "json_invalid": "JSON invalide",
    "model_attributes_type": "Objet attendu",
    "dict_type": "Objet attendu",
}


def _traduire(err: dict) -> dict:
    type_ = err.get("type", "")
    ctx = err.get("ctx") or {}
    if type_ == "value_error":
        # Message écrit par nos validateurs : "Value error, <message>" -> "<message>"
        message = str(err.get("msg", "")).removeprefix("Value error, ")
        if "email address" in message.lower():
            message = "Adresse email invalide"
    elif type_ in _MESSAGES_FR:
        try:
            message = _MESSAGES_FR[type_].format(**ctx)
        except (KeyError, IndexError):
            message = _MESSAGES_FR[type_]
    else:
        message = err.get("msg", "Valeur invalide")
    loc = [str(x) for x in err.get("loc", ()) if x != "body"]
    return {"champ": ".".join(loc) or None, "message": message, "type": type_}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErreurMetier)
    async def _erreur_metier(_: Request, exc: ErreurMetier):
        headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, UnauthorizedError) else None
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        erreurs = [_traduire(e) for e in exc.errors()]
        return JSONResponse(status_code=422, content=jsonable_encoder({"detail": erreurs}))
