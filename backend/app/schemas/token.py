from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    # Reponse renvoyee a la connexion, contenant le token d'acces
    access_token: str
    token_type: str = 'bearer'


class TokenData(BaseModel):
    # Donnees extraites du token une fois decode
    user_id: Optional[int] = None
