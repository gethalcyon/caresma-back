from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)

    # Transcript data
    transcript = Column(Text, nullable=False)

    # Cognitive assessment scores (0-10 scale)
    memory_score = Column(Float, nullable=True)
    language_score = Column(Float, nullable=True)
    executive_function_score = Column(Float, nullable=True)
    orientation_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    # Detailed feedback per criterion
    memory_feedback = Column(Text, nullable=True)
    language_feedback = Column(Text, nullable=True)
    executive_function_feedback = Column(Text, nullable=True)
    orientation_feedback = Column(Text, nullable=True)

    # Overall assessment
    overall_feedback = Column(Text, nullable=True)
    risk_level = Column(String, nullable=True)  # low, moderate, high

    # Metadata
    assessment_metadata = Column(JSONB, nullable=True)  # Additional analysis data

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    session = relationship("Session", backref="assessments")
