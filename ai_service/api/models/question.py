"""
Question model for questionnaire API.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class Question:
    """Represents a questionnaire question."""

    def __init__(
        self,
        question_id: Optional[str] = None,
        text: Optional[str] = None,
        question_type: str = "text",
        category: str = "general",
        options: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize a new Question.

        Args:
            question_id: Optional question ID (generated if not provided)
            text: Question text
            question_type: Question type (text, multiple_choice, etc.)
            category: Question category
            options: Optional list of options for multiple choice questions
        """
        self.id = question_id or str(uuid.uuid4())
        self.text = text or ""
        self.type = question_type
        self.category = category
        self.options = options or []
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert question to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "category": self.category,
            "options": self.options,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create a question from dictionary data."""
        question = cls(
            question_id=data.get("id"),
            text=data.get("text"),
            question_type=data.get("type", "text"),
            category=data.get("category", "general"),
            options=data.get("options", [])
        )

        # Parse dates if they exist
        if "created_at" in data:
            try:
                question.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                question.created_at = datetime.now()

        return question
