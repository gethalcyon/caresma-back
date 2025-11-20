"""
Schemas for cognitive assessment API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class CognitiveScore(BaseModel):
    """Individual cognitive domain score with feedback"""
    score: float = Field(..., ge=0, le=10, description="Score from 0-10")
    feedback: str = Field(..., description="Detailed feedback for this domain")


class AssessmentAnalyzeRequest(BaseModel):
    """Request to analyze a transcript"""
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID to link assessment to (auto-generated if not provided)")
    transcript: str = Field(..., min_length=50, description="Conversation transcript to analyze")


class AssessmentResponse(BaseModel):
    """Response with cognitive assessment results"""
    id: uuid.UUID
    session_id: Optional[uuid.UUID] = None

    # Cognitive scores
    memory_score: Optional[float] = Field(None, ge=0, le=10)
    language_score: Optional[float] = Field(None, ge=0, le=10)
    executive_function_score: Optional[float] = Field(None, ge=0, le=10)
    orientation_score: Optional[float] = Field(None, ge=0, le=10)
    overall_score: Optional[float] = Field(None, ge=0, le=10)

    # Feedback
    memory_feedback: Optional[str] = None
    language_feedback: Optional[str] = None
    executive_function_feedback: Optional[str] = None
    orientation_feedback: Optional[str] = None
    overall_feedback: Optional[str] = None

    # Risk assessment
    risk_level: Optional[str] = Field(None, description="Risk level: low, moderate, or high")

    # Metadata
    assessment_metadata: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssessmentSummary(BaseModel):
    """Summary view of assessment (without full transcript)"""
    id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    overall_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
