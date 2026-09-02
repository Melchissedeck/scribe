from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True)

    recording_id = Column(
        Integer,
        ForeignKey("recordings.id"),
        nullable=False,
        index=True,
    )

    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)

    text = Column(Text, nullable=False)

    speaker = Column(String(100), nullable=False)

    tone = Column(String(50), nullable=True)
    theme = Column(String(100), nullable=True)
    urgency = Column(String(20), nullable=True)

    recording = relationship(
        "Recording",
        back_populates="segments",
    )