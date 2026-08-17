from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Recording(Base):
    __tablename__ = 'recordings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    native_meeting_id = Column(String(255), nullable=False)
    bot_name = Column(String(100), nullable=False, default='Scribe')
    theme = Column(String(255), nullable=True)
    # pending | active | stopped | error
    status = Column(String(20), nullable=False, default='pending')
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    stopped_at = Column(DateTime, nullable=True)

    user = relationship('User', back_populates='recordings')
    speakers = relationship('Speaker', back_populates='recording')
