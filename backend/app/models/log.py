from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Log(Base):
    # Journal d'audit : connexions et suppressions de donnees (RGPD).
    # user_id passe a NULL si le compte est ensuite supprime (ON DELETE
    # SET NULL), pour que le log de suppression survive a la suppression
    # elle-meme sans rester rattache a un utilisateur inexistant.
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    detail = Column(Text, nullable=True)
