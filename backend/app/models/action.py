from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey('recordings.id'), nullable=False, index=True)
    speaker_id = Column(Integer, ForeignKey('speakers.id'), nullable=True, index=True)
    description = Column(Text, nullable=False)
    # todo | in_progress | done
    status = Column(String(20), nullable=False, default='todo')
    due_date = Column(Date, nullable=True)

    recording = relationship('Recording', back_populates='actions')
    speaker = relationship('Speaker', back_populates='actions')
