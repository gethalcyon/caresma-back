"""
API endpoints for cognitive assessments
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.schemas.assessment import (
    AssessmentAnalyzeRequest,
    AssessmentResponse,
    AssessmentSummary
)
from app.services.assessment_service import AssessmentService
from app.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("/analyze", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def analyze_transcript_text(
    request: AssessmentAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Analyze a conversation transcript and generate cognitive assessment.

    This endpoint accepts a text transcript and returns detailed cognitive scores
    across four domains: Memory, Language, Executive Function, and Orientation.
    If session_id is not provided, a new session will be created automatically.

    Args:
        request: Contains optional session_id and transcript text
        current_user: Authenticated user
        db: Database session

    Returns:
        Assessment with cognitive scores and detailed feedback
    """
    # Handle session_id: use provided or None
    session_uuid = request.session_id if request.session_id else None

    user_id = current_user.id if current_user else "anonymous"
    if request.session_id:
        logger.info(f"User {user_id} requested assessment for session {session_uuid}")
    else:
        logger.info(f"User {user_id} requested assessment without session")

    assessment_service = AssessmentService(db)

    try:
        assessment = await assessment_service.analyze_transcript(
            session_id=session_uuid,
            transcript=request.transcript
        )

        return AssessmentResponse.from_orm(assessment)

    except ValueError as e:
        logger.error(f"Invalid transcript or analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate assessment. Please try again."
        )


@router.post("/analyze-file", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def analyze_transcript_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Upload a transcript file and generate cognitive assessment.

    Accepts text files (.txt, .md) containing conversation transcripts.
    If session_id is not provided, a new session will be created automatically.

    Args:
        file: Uploaded transcript file
        session_id: Optional session ID to link assessment to (auto-generated if not provided)
        current_user: Authenticated user
        db: Database session

    Returns:
        Assessment with cognitive scores and detailed feedback
    """
    # Handle session_id: convert to UUID or use None
    user_id = current_user.id if current_user else "anonymous"
    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            logger.info(f"User {user_id} uploaded transcript file for session {session_uuid}")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session_id format: {session_id}"
            )
    else:
        # No session provided - assessment will be created without session link
        session_uuid = None
        logger.info(f"User {user_id} uploaded transcript file without session")

    # Validate file type
    allowed_extensions = [".txt", ".md", ".text"]
    file_ext = file.filename.split(".")[-1] if file.filename else ""
    if f".{file_ext.lower()}" not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Read file content
    try:
        content = await file.read()
        transcript = content.decode("utf-8")

        if len(transcript) < 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript too short. Minimum 50 characters required."
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding. Please upload UTF-8 encoded text file."
        )

    # Analyze transcript
    assessment_service = AssessmentService(db)

    try:
        assessment = await assessment_service.analyze_transcript(
            session_id=session_uuid,
            transcript=transcript
        )

        return AssessmentResponse.from_orm(assessment)

    except ValueError as e:
        logger.error(f"Invalid transcript or analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate assessment. Please try again."
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific assessment by ID.

    Args:
        assessment_id: UUID of the assessment
        current_user: Authenticated user
        db: Database session

    Returns:
        Assessment details
    """
    assessment_service = AssessmentService(db)
    assessment = await assessment_service.get_assessment(assessment_id)

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    return AssessmentResponse.from_orm(assessment)


@router.get("/session/{session_id}", response_model=List[AssessmentSummary])
async def get_session_assessments(
    session_id: uuid.UUID,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all assessments for a specific session.

    Args:
        session_id: UUID of the session
        limit: Maximum number of assessments to return
        current_user: Authenticated user
        db: Database session

    Returns:
        List of assessment summaries
    """
    assessment_service = AssessmentService(db)
    assessments = await assessment_service.get_session_assessments(
        session_id=session_id,
        limit=limit
    )

    return [AssessmentSummary.from_orm(a) for a in assessments]


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an assessment.

    Args:
        assessment_id: UUID of the assessment
        current_user: Authenticated user
        db: Database session
    """
    assessment_service = AssessmentService(db)
    deleted = await assessment_service.delete_assessment(assessment_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
