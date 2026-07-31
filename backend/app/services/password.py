from passlib.context import CryptContext

# Contexte de hashage partage par toute l'application
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    # Transforme un mot de passe en clair en hash bcrypt avant stockage
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Compare un mot de passe en clair a un hash existant
    return pwd_context.verify(plain_password, hashed_password)