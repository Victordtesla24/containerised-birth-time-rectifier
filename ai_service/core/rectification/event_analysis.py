"""
Life event analysis functionality for birth time rectification.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def extract_life_events_from_answers(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract relevant life events from questionnaire answers.

    Args:
        answers: List of questionnaire answers in various formats

    Returns:
        List of life events with date, description, and event type
    """
    if not answers:
        return []

    events = []

    for answer in answers:
        try:
            # Handle different answer formats
            question = ""
            response = ""

            # Format 1: {question, user_response}
            if "question" in answer and ("answer" in answer or "user_response" in answer):
                question = answer.get("question", "")
                response = answer.get("answer", answer.get("user_response", ""))

            # Format 2: {question_text, response_text}
            elif "question_text" in answer and "response_text" in answer:
                question = answer.get("question_text", "")
                response = answer.get("response_text", "")

            # Format 3: {text, response}
            elif "text" in answer and "response" in answer:
                question = answer.get("text", "")
                response = answer.get("response", "")

            # Format 4: Direct string answer with a question key
            elif isinstance(answer.get("question"), str) and isinstance(answer.get("answer"), str):
                question = answer.get("question", "")
                response = answer.get("answer", "")

            # Skip if we couldn't extract a question and response
            if not question or not response:
                continue

            # Convert response to string if it's not already
            if not isinstance(response, str):
                response = str(response)

            # Look for date patterns in the answer
            import re
            from datetime import datetime, date

            # Various date formats to check
            date_patterns = [
                # YYYY-MM-DD
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                # MM/DD/YYYY
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                # Month DD, YYYY
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                # DD Month YYYY
                r'(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                # Age-based reference (when I was X years old)
                r'(when I was|at age|aged)\s+(\d{1,2})',
                # Year only
                r'(in|during|around)\s+(\d{4})'
            ]

            event_date = None
            date_found = False
            event_description = response.strip()

            # Check if the question is about a specific life event
            event_terms = ["birth", "marriage", "wedding", "divorce", "graduation", "job", "move",
                        "accident", "injury", "illness", "death", "loss", "promotion", "child",
                        "relationship", "surgery", "major", "significant", "event"]

            # Define event types based on keywords
            event_type_mapping = {
                "birth": "birth",
                "born": "birth",
                "child": "child_birth",
                "baby": "child_birth",
                "wedding": "marriage",
                "marriage": "marriage",
                "spouse": "marriage",
                "divorce": "divorce",
                "separation": "divorce",
                "graduate": "education",
                "graduation": "education",
                "degree": "education",
                "diploma": "education",
                "job": "career",
                "career": "career",
                "work": "career",
                "promotion": "career",
                "move": "relocation",
                "moving": "relocation",
                "relocate": "relocation",
                "accident": "health",
                "injury": "health",
                "hospital": "health",
                "illness": "health",
                "disease": "health",
                "health": "health",
                "surgery": "health",
                "operation": "health",
                "death": "death",
                "died": "death",
                "loss": "loss",
                "relationship": "relationship",
                "partner": "relationship",
                "travel": "travel",
                "trip": "travel",
                "journey": "travel",
                "moved": "relocation",
                "achievement": "achievement",
                "accomplishment": "achievement",
                "award": "achievement",
                "success": "achievement"
            }

            # Extract event type from question or answer
            event_type = "general_event"  # Default
            for key, value in event_type_mapping.items():
                if key in question.lower() or key in response.lower():
                    event_type = value
                    break

            # Try to find a date in the response
            for pattern in date_patterns:
                match = re.search(pattern, response)
                if match:
                    date_str = match.group(0)

                    # Try different date parsing approaches
                    try:
                        # Try parsing with different formats
                        formats = [
                            "%Y-%m-%d", "%Y/%m/%d",
                            "%m/%d/%Y", "%m-%d-%Y",
                            "%B %d, %Y", "%B %d %Y",
                            "%d %B %Y"
                        ]

                        for fmt in formats:
                            try:
                                event_date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                                date_found = True
                                break
                            except ValueError:
                                continue

                        # Handle age-based references
                        if not date_found and "age" in date_str or "aged" in date_str:
                            age_match = re.search(r'(\d{1,2})', date_str)
                            if age_match:
                                age = int(age_match.group(1))
                                # Approximate the date based on typical birth year (calculate from questionnaire date)
                                # This is a rough estimate and would need the person's birth year to be accurate
                                event_date = f"approximate:{age}"
                                date_found = True

                        # Handle year-only references
                        if not date_found and re.search(r'\d{4}', date_str):
                            year_match = re.search(r'(\d{4})', date_str)
                            if year_match:
                                year = year_match.group(1)
                                event_date = f"{year}-01-01"  # Default to January 1st
                                date_found = True

                    except Exception as e:
                        logger.debug(f"Error parsing date '{date_str}': {e}")
                        continue

                    # If we found a valid date, create an event
                    if date_found:
                        break

            # If we have a potential life event and either a date or event type
            if (any(term in question.lower() for term in event_terms) or
                any(term in response.lower() for term in event_terms) or
                event_type != "general_event") and (date_found or event_type != "general_event"):

                # Create the event entry
                event = {
                    "event_type": event_type,
                    "description": event_description,
                    "relevance": "high" if date_found else "medium",
                    "source_question": question
                }

                # Add date if found
                if date_found:
                    event["date"] = event_date

                events.append(event)

        except Exception as e:
            logger.warning(f"Error extracting life event from answer: {e}")
            continue

    return events
