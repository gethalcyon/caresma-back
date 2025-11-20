"""
Service for analyzing conversation transcripts and generating cognitive assessments
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
import uuid
import json
from openai import AsyncOpenAI

from app.models.assessment import Assessment
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AssessmentService:
    """Service for cognitive assessment analysis"""

    # Assessment prompt for OpenAI
    ASSESSMENT_PROMPT = """You are a clinical neuropsychologist specializing in cognitive assessment and dementia screening. Analyze the following conversation transcript and provide a detailed cognitive assessment based on these four criteria:

1. **Memory** (0-10 scale):
   - Short-term and long-term recall
   - Repetition patterns or perseveration
   - Ability to remember previous topics in the conversation
   - Recognition vs. recall abilities

2. **Language** (0-10 scale):
   - Vocabulary richness and word choice
   - Sentence structure and complexity
   - Word-finding difficulties (anomia)
   - Coherence and relevance of responses
   - Use of empty phrases or filler words

3. **Executive Function** (0-10 scale):
   - Conversation flow and logical sequencing
   - Ability to stay on topic
   - Abstract thinking and reasoning
   - Problem-solving abilities
   - Mental flexibility

4. **Orientation** (0-10 scale):
   - Awareness of time, place, and context
   - Appropriate responses to situational cues
   - Reality testing and judgment

**Scoring Guidelines:**
- 8-10: Normal cognitive function for domain
- 5-7: Mild impairment, warrants monitoring
- 3-4: Moderate impairment, clinical evaluation recommended
- 0-2: Severe impairment, urgent evaluation needed

**Output Format (JSON):**
```json
{{
  "memory": {{
    "score": 7.5,
    "feedback": "Detailed analysis of memory performance..."
  }},
  "language": {{
    "score": 8.0,
    "feedback": "Detailed analysis of language abilities..."
  }},
  "executive_function": {{
    "score": 6.5,
    "feedback": "Detailed analysis of executive function..."
  }},
  "orientation": {{
    "score": 9.0,
    "feedback": "Detailed analysis of orientation..."
  }},
  "overall": {{
    "score": 7.75,
    "feedback": "Overall cognitive assessment summary...",
    "risk_level": "low|moderate|high"
  }}
}}
```

**Risk Level Classification:**
- **low**: Average overall score ≥ 7.0
- **moderate**: Average overall score 4.0-6.9
- **high**: Average overall score < 4.0

Be specific, cite examples from the transcript, and provide actionable insights. Focus on patterns rather than isolated instances.

**TRANSCRIPT TO ANALYZE:**
{transcript}

Provide your assessment in the JSON format specified above."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_transcript(
        self,
        session_id: uuid.UUID,
        transcript: str
    ) -> Assessment:
        """
        Analyze a conversation transcript and generate cognitive assessment.

        Args:
            session_id: UUID of the session
            transcript: Conversation transcript text

        Returns:
            Assessment object with scores and feedback

        Raises:
            Exception: If OpenAI API call fails
        """
        logger.info(f"Starting cognitive assessment for session {session_id}")

        # Call OpenAI to analyze transcript
        try:
            analysis = await self._call_openai_analysis(transcript)
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise

        # Create assessment record
        assessment = Assessment(
            session_id=session_id,
            transcript=transcript,
            memory_score=analysis["memory"]["score"],
            memory_feedback=analysis["memory"]["feedback"],
            language_score=analysis["language"]["score"],
            language_feedback=analysis["language"]["feedback"],
            executive_function_score=analysis["executive_function"]["score"],
            executive_function_feedback=analysis["executive_function"]["feedback"],
            orientation_score=analysis["orientation"]["score"],
            orientation_feedback=analysis["orientation"]["feedback"],
            overall_score=analysis["overall"]["score"],
            overall_feedback=analysis["overall"]["feedback"],
            risk_level=analysis["overall"]["risk_level"],
            assessment_metadata={"raw_analysis": analysis}
        )

        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)

        logger.info(
            f"Assessment completed for session {session_id}: "
            f"overall_score={assessment.overall_score}, risk_level={assessment.risk_level}"
        )

        return assessment

    async def _call_openai_analysis(self, transcript: str) -> Dict[str, Any]:
        """
        Call OpenAI Chat Completion API to analyze transcript.

        Args:
            transcript: Conversation transcript

        Returns:
            Dictionary with cognitive scores and feedback

        Raises:
            Exception: If API call fails or response parsing fails
        """

        prompt = self.ASSESSMENT_PROMPT.format(transcript=transcript)

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 for better analysis
                messages=[
                    {
                        "role": "system",
                        "content": "You are a clinical neuropsychologist. Provide cognitive assessments in valid JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},  # Force JSON response
                temperature=0.3,  # Lower temperature for consistent analysis
                max_tokens=2000
            )

            # Parse JSON response
            content = response.choices[0].message.content
            logger.info(f"Raw OpenAI response: {content[:500]}...")  # Log first 500 chars

            analysis = json.loads(content)
            logger.info(f"Parsed JSON keys: {analysis.keys()}")

            # Validate structure
            required_keys = ["memory", "language", "executive_function", "orientation", "overall"]
            for key in required_keys:
                if key not in analysis:
                    raise ValueError(f"Missing required key in OpenAI response: {key}")

            logger.debug(f"OpenAI analysis completed successfully")
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Raw content received: {content}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            if hasattr(e, 'response'):
                logger.error(f"Response content: {e.response}")
            raise

    async def get_assessment(self, assessment_id: uuid.UUID) -> Optional[Assessment]:
        """Get an assessment by ID"""
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        return result.scalar_one_or_none()

    async def get_session_assessments(
        self,
        session_id: uuid.UUID,
        limit: int = 10
    ) -> List[Assessment]:
        """Get all assessments for a session"""
        result = await self.db.execute(
            select(Assessment)
            .where(Assessment.session_id == session_id)
            .order_by(Assessment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_assessment(self, assessment_id: uuid.UUID) -> bool:
        """Delete an assessment"""
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment:
            await self.db.delete(assessment)
            await self.db.commit()
            return True
        return False
