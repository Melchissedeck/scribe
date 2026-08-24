from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    # Donnees attendues en entree lors de la creation d'un compte
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    # Donnees attendues en entree lors de la mise a jour du profil, tout est optionnel
    name: str | None = None
    email: EmailStr | None = None


class UserLogin(BaseModel):
    # Donnees attendues en entree lors de la connexion
    email: EmailStr
    password: str


class UserRead(BaseModel):
    # Donnees renvoyees en sortie, sans jamais exposer le mot de passe
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True
