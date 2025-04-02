"""
Answer model for questionnaire API.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class Answer:
    """Represents an answer to a questionnaire question."""

    def __init__(
        self,
        answer_id: Optional[str] = None,
        question_id: Optional[str] = None,
        session_id: Optional[str] = None,
        answer_data: Optional[Any] = None
    ):
        """
        Initialize a new Answer.

        Args:
            answer_id: Optional answer ID (generated if not provided)
            question_id: Optional question ID this answer is for
            session_id: Optional session ID this answer belongs to
            answer_data: The actual answer data
        """
        self.id = answer_id or str(uuid.uuid4())
        self.question_id = question_id or ""
        self.session_id = session_id or ""
        self.answer_data = answer_data
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert answer to dictionary."""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "session_id": self.session_id,
            "answer": self.answer_data,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Answer':
        """Create an answer from dictionary data."""
        answer = cls(
            answer_id=data.get("id"),
            question_id=data.get("question_id"),
            session_id=data.get("session_id"),
            answer_data=data.get("answer")
        )

        # Parse dates if they exist
        if "created_at" in data:
            try:
                answer.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                answer.created_at = datetime.now()

        return answer
