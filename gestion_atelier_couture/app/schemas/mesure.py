from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constantes import CHAMPS_MESURES

# RG2 : chaque mesure est facultative mais, si elle est donnée, 0 < x <= 300 (cm)
CM = Field(default=None, gt=0, le=300, description="en cm, > 0 et ≤ 300")


class _ChampsMesures(BaseModel):
    """Les 18 mesures (toutes facultatives). Classe mère partagée par Create / Update."""

    taille_cm: float | None = CM
    tour_cou: float | None = CM
    carrure_dos: float | None = CM
    longueur_epaule: float | None = CM
    tour_poitrine: float | None = CM
    tour_taille: float | None = CM
    tour_bassin: float | None = CM
    longueur_manche: float | None = CM
    tour_bras: float | None = CM
    tour_poignet: float | None = CM
    longueur_dos: float | None = CM
    longueur_haut: float | None = CM
    longueur_pantalon: float | None = CM
    tour_cuisse: float | None = CM
    tour_genou: float | None = CM
    bas_pantalon: float | None = CM
    entrejambe: float | None = CM
    longueur_robe: float | None = CM


class MesureCreate(_ChampsMesures):
    date_prise: date | None = None  # défaut : aujourd'hui (fixé par le service)
    notes: str | None = None

    @model_validator(mode="after")
    def au_moins_une_mesure(self):
        """RG2 : règle sur PLUSIEURS champs -> model_validator."""
        if all(getattr(self, c) is None for c in CHAMPS_MESURES):
            raise ValueError("Au moins une mesure doit être renseignée")
        if self.date_prise and self.date_prise > date.today():
            raise ValueError("La date de prise ne peut pas être dans le futur")
        return self


class MesureUpdate(_ChampsMesures):
    """PATCH : on peut aussi mettre une mesure à null pour l'effacer.

    La vérification « il reste au moins une mesure » est faite par le service
    APRÈS fusion avec les valeurs existantes.
    """

    date_prise: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _date(self):
        if "date_prise" in self.model_fields_set:
            if self.date_prise is None:
                raise ValueError("Le champ date_prise ne peut pas être vidé")
            if self.date_prise > date.today():
                raise ValueError("La date de prise ne peut pas être dans le futur")
        return self


class MesureRead(_ChampsMesures):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int | None
    notes: str | None
    created_at: datetime
