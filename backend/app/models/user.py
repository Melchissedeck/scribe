from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    # Table utilisateur : represente une personne inscrite sur Scribe

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Horodatage du consentement RGPD (écran de consentement avant toute
    # captation). NULL = jamais donné. Vérifié côté serveur par la
    # dépendance require_consent, pas seulement côté client.
    consent_given_at = Column(DateTime, nullable=True)

    recordings = relationship('Recording', back_populates='user')