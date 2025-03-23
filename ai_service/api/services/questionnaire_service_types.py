"""
Type definitions for the questionnaire service.

This module contains TypedDict definitions and constants used by the questionnaire service.
"""

from typing import Dict, List, Any, Optional, TypedDict

# Define question types
QUESTION_TYPES = [
    "yes_no",
    "multiple_choice",
    "open_text",
    "time_event",
    "date_event",
    "slider"
]

# Define types for questionnaire structures
class QuestionOption(TypedDict):
    id: str
    text: str

class Question(TypedDict, total=False):
    id: str
    type: str
    text: str
    category: str
    relevance: str
    options: Optional[List[QuestionOption]]
