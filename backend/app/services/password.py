import bcrypt


def hash_password(password: str) -> str:
    """Transforme un mot de passe en clair en hash bcrypt avant stockage.

    Args:
        password: Mot de passe en clair à hasher.

    Returns:
        Le hash bcrypt du mot de passe, encodé en chaîne de caractères.
    """
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond à un hash existant.

    Args:
        plain_password: Mot de passe en clair saisi par l'utilisateur.
        hashed_password: Hash bcrypt stocké à comparer.

    Returns:
        True si le mot de passe correspond au hash, False sinon.
    """
    plain_password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
