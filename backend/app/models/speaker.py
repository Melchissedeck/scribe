from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Speaker(Base):
    __tablename__ = 'speakers'

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey('recordings.id'), nullable=False, index=True)
    provisional_name = Column(String(100), nullable=False)
    real_name = Column(String(100), nullable=True)

    recording = relationship('Recording', back_populates='speakers')
    actions = relationship('Action', back_populates='speaker')
