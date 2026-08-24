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


class VexaConnectionError(Exception):
    # Levee quand l'API Vexa est inaccessible (timeout, coupure réseau, HTTP error)
    def __init__(self, message: str = 'Le service de réunion est temporairement indisponible. Veuillez réessayer dans quelques instants.'):
        self.message = message
        super().__init__(message)


class VexaInvalidMeetingError(Exception):
    # Levee quand Vexa rejette le lien de réunion (lien invalide ou inaccessible)
    def __init__(self, message: str = 'Le lien de réunion est invalide ou inaccessible.'):
        self.message = message
        super().__init__(message)
