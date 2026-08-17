class TokenExpiredError(Exception):
    # Levee quand un token JWT est valide mais a expire
    def __init__(self, message: str = 'Votre session a expiré, veuillez vous reconnecter.'):
        self.message = message
        super().__init__(message)


class InvalidCredentialsError(Exception):
    # Levee quand les identifiants fournis (token ou login) sont invalides
    def __init__(self, message: str = 'Impossible de vérifier les identifiants.'):
        self.message = message
        super().__init__(message)
