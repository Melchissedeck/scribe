from sqlalchemy import Column, ForeignKey, Integer, Text, Time
from sqlalchemy.orm import relationship

from app.database import Base


class TranscriptSegment(Base):
    __tablename__ = 'transcript_segments'

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey('recordings.id'), nullable=False, index=True)
    speaker_id = Column(Integer, ForeignKey('speakers.id'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    recording = relationship('Recording', back_populates='segments')
    speaker = relationship('Speaker', back_populates='segments')
