"""
AI-powered questionnaire generation engine for birth time rectification.

This module provides functionality to dynamically generate questions
based on birth chart analysis and user responses to improve birth time accuracy.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import math
import numpy as np
from collections import Counter

import logging
logger = logging.getLogger(__name__)

# Question types
YES_NO = "yes_no"
MULTIPLE_CHOICE = "multiple_choice"
DATE_PICKER = "date_picker"
TIME_PICKER = "time_picker"
TEXT_INPUT = "text_input"

# Relevance levels
HIGH = "high"
MEDIUM = "medium"
LOW = "low"

# Question categories
GENERAL = "general"
PERSONALITY = "personality"
LIFE_EVENTS = "life_events"
PLANETARY = "planetary"
HOUSE = "house"
TIMING = "timing"
RELATIONAL = "relational"

class QuestionnaireEngine:
    """
    Engine for generating dynamic questionnaires for birth time rectification.

    This class handles the generation of questions based on the user's birth chart
    and previous answers, with the goal of narrowing down the possible birth time.
    """

    def __init__(self, chart_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the questionnaire engine.

        Args:
            chart_data: Initial chart data to base questions on
        """
        self.chart_data = chart_data if chart_data is not None else {}
        self.question_history = []
        self.answers = {}
        self.confidence_levels = {
            "ascendant": 0.0,
            "houses": 0.0,
            "planets": 0.0,
            "overall": 0.0
        }

        # Dynamic category weights based on confidence levels
        self.category_weights = {
            GENERAL: 1.0,
            PERSONALITY: 1.0,
            LIFE_EVENTS: 1.0,
            PLANETARY: 1.0,
            HOUSE: 1.0,
            TIMING: 1.0,
            RELATIONAL: 1.0
        }

        # Initialize question bank
        self._initialize_question_bank()

    def _initialize_question_bank(self):
        """Initialize the bank of potential questions."""
        self.question_bank = {
            GENERAL: self._generate_general_questions(),
            PERSONALITY: self._generate_personality_questions(),
            LIFE_EVENTS: self._generate_life_event_questions(),
            PLANETARY: self._generate_planetary_questions(),
            HOUSE: self._generate_house_questions(),
            TIMING: [],  # Will be generated dynamically
            RELATIONAL: self._generate_relational_questions()
        }

    def generate_next_question(self) -> Dict[str, Any]:
        """
        Generate the next most relevant question based on chart data and previous answers.

        Returns:
            Dict containing the next question
        """
        # Reset question history if it's too long to avoid repetitive questions
        if len(self.question_history) > 20:
            self.question_history = self.question_history[-10:]

        # Adjust category weights based on confidence levels
        self._adjust_category_weights()

        # Generate timing and aspect questions dynamically based on current knowledge
        self.question_bank[TIMING] = self._generate_timing_questions()

        # Generate candidate questions from various categories
        candidate_questions = []
        for category, weight in self.category_weights.items():
            # Skip categories with no questions
            if not self.question_bank[category]:
                continue

            # Get questions from this category
            category_questions = self.question_bank[category]

            # Score questions based on relevance
            scored_questions = self._score_questions(category_questions, weight)

            # Add top questions to candidates
            candidate_questions.extend(scored_questions[:3])

        # Sort candidates by score
        candidate_questions.sort(key=lambda q: q["score"], reverse=True)

        # Select the highest scoring question
        if candidate_questions:
            next_question = candidate_questions[0]
            # Remove score before returning
            score = next_question.pop("score", 0)
            # Add to question history
            self.question_history.append(next_question["id"])
            return next_question

        # Fallback to a general question if no candidates
        fallback_question = {
            "id": f"fallback_{len(self.question_history)}",
            "text": "Is there any significant life event you can recall that might help determine your birth time?",
            "type": TEXT_INPUT,
            "category": GENERAL
        }
        self.question_history.append(fallback_question["id"])
        return fallback_question

    def _adjust_category_weights(self):
        """Adjust category weights based on confidence levels and previous answers."""
        # If we have low confidence in ascendant, prioritize house and personality questions
        if self.confidence_levels["ascendant"] < 0.3:
            self.category_weights[HOUSE] = 1.5
            self.category_weights[PERSONALITY] = 1.3

        # If we have high confidence in ascendant but low in planets, focus on planetary
        elif self.confidence_levels["ascendant"] > 0.7 and self.confidence_levels["planets"] < 0.5:
            self.category_weights[PLANETARY] = 1.5
            self.category_weights[TIMING] = 1.3

        # If we have good confidence overall, focus on timing for refinement
        elif self.confidence_levels["overall"] > 0.6:
            self.category_weights[TIMING] = 1.8
            self.category_weights[LIFE_EVENTS] = 1.5

        # Analyze answer patterns to adjust weights
        if len(self.answers) > 5:
            # Count categories of answered questions
            category_counts = Counter([q.get("category", GENERAL) for q in self.answers.values()])

            # Boost underrepresented categories
            for category in self.category_weights:
                if category_counts.get(category, 0) < 2:
                    self.category_weights[category] *= 1.2

    def _score_questions(self, questions: List[Dict[str, Any]], category_weight: float) -> List[Dict[str, Any]]:
        """
        Score questions based on relevance, variety, and information gain.

        Args:
            questions: List of question dictionaries
            category_weight: Weight of the category

        Returns:
            List of questions with added score field, sorted by score
        """
        scored_questions = []

        for question in questions:
            # Skip questions already asked
            if question["id"] in self.question_history:
                continue

            # Base score is the question's relevance * category weight
            relevance = question.get("relevance", MEDIUM)
            relevance_score = 1.0
            if relevance == HIGH:
                relevance_score = 1.5
            elif relevance == LOW:
                relevance_score = 0.7

            base_score = relevance_score * category_weight

            # Adjust for variety (avoid similar questions)
            variety_penalty = 0
            for asked_id in self.question_history[-5:]:  # Look at last 5 questions
                # Check if this question is similar to recently asked ones
                if self._is_similar_question(question, asked_id):
                    variety_penalty += 0.2  # Penalize similar questions

            # Adjust for potential information gain
            info_gain = 1.0
            if question.get("type") == MULTIPLE_CHOICE and len(question.get("options", [])) > 3:
                info_gain = 1.2  # More options = more information
            elif question.get("type") == DATE_PICKER or question.get("type") == TIME_PICKER:
                info_gain = 1.3  # Precise date/time data is valuable

            # Calculate final score
            final_score = base_score * (1 - variety_penalty) * info_gain

            # Add score to question
            scored_question = question.copy()
            scored_question["score"] = final_score
            scored_questions.append(scored_question)

        # Sort by score
        scored_questions.sort(key=lambda q: q["score"], reverse=True)
        return scored_questions

    def _is_similar_question(self, question: Dict[str, Any], asked_id: str) -> bool:
        """
        Check if a question is semantically similar to an already asked question.

        Args:
            question: The question to check
            asked_id: ID of a previously asked question

        Returns:
            True if questions are similar, False otherwise
        """
        # Get the asked question from history
        asked_question = None
        for q in self.question_bank.get(question.get("category", GENERAL), []):
            if q.get("id") == asked_id:
                asked_question = q
                break

        if not asked_question:
            return False

        # Check if they're in the same subcategory
        if question.get("subcategory") and asked_question.get("subcategory"):
            if question["subcategory"] == asked_question["subcategory"]:
                return True

        # Check for keyword overlap in the question text
        q1_words = set(question["text"].lower().split())
        q2_words = set(asked_question["text"].lower().split())
        overlap = len(q1_words.intersection(q2_words)) / len(q1_words.union(q2_words))

        return overlap > 0.5  # If more than 50% of words overlap

    def _generate_timing_questions(self) -> List[Dict[str, Any]]:
        """Generate questions about timing and daily patterns."""
        timing_questions = [
            {
                "id": f"timing_daily_energy_{len(self.question_history)}",
                "text": "What time of day do you typically feel most energetic?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "morning", "text": "Morning (6am-12pm)"},
                    {"id": "afternoon", "text": "Afternoon (12pm-6pm)"},
                    {"id": "evening", "text": "Evening (6pm-12am)"},
                    {"id": "night", "text": "Night (12am-6am)"}
                ],
                "category": TIMING,
                "subcategory": "daily_energy",
                "relevance": HIGH
            }
        ]

        # Add Jupiter timing question
        timing_questions.append({
            "id": f"timing_jupiter_{len(self.question_history)}",
            "text": "Can you recall a year when you experienced significant growth, expansion, or good fortune?",
            "type": DATE_PICKER,
            "category": TIMING,
            "subcategory": "jupiter_transit",
            "relevance": MEDIUM
        })

        # Add more dynamic timing questions based on chart data
        if "planets" in self.chart_data:
            # Check for Mars position for questions about energy/action timing
            mars_position = next((p for p in self.chart_data["planets"] if p["name"] == "Mars"), None)
            if mars_position:
                timing_questions.append({
                    "id": f"timing_mars_{len(self.question_history)}",
                    "text": "Do you tend to feel most energetic in the morning, afternoon, evening, or night?",
                    "type": MULTIPLE_CHOICE,
                    "options": [
                        {"id": "morning", "text": "Morning (6am-12pm)"},
                        {"id": "afternoon", "text": "Afternoon (12pm-6pm)"},
                        {"id": "evening", "text": "Evening (6pm-12am)"},
                        {"id": "night", "text": "Night (12am-6am)"}
                    ],
                    "category": TIMING,
                    "subcategory": "mars_energy",
                    "relevance": MEDIUM
                })

        return timing_questions

    def _generate_aspect_questions(self) -> List[Dict[str, Any]]:
        """
        Generate questions about planetary aspects based on current chart data.

        Returns:
            List of aspect-related questions
        """
        aspect_questions = []

        # Generate questions based on Sun-Moon aspect
        aspect_questions.append({
            "id": f"aspect_sun_moon_{len(self.question_history)}",
            "text": "Do you feel your emotional needs (Moon) align with your conscious goals (Sun)?",
            "type": MULTIPLE_CHOICE,
            "options": [
                {"id": "strongly_agree", "text": "Strongly agree"},
                {"id": "agree", "text": "Agree"},
                {"id": "neutral", "text": "Neutral"},
                {"id": "disagree", "text": "Disagree"},
                {"id": "strongly_disagree", "text": "Strongly disagree"}
            ],
            "category": PLANETARY,
            "subcategory": "sun_moon_aspect",
            "relevance": HIGH
        })

        # Add more aspect questions based on chart data
        if "aspects" in self.chart_data:
            # Check for Venus-Mars aspect for questions about relationship dynamics
            venus_mars_aspect = next((a for a in self.chart_data["aspects"]
                                    if (a["planet1"] == "Venus" and a["planet2"] == "Mars") or
                                       (a["planet1"] == "Mars" and a["planet2"] == "Venus")), None)
            if venus_mars_aspect:
                aspect_questions.append({
                    "id": f"aspect_venus_mars_{len(self.question_history)}",
                    "text": "How would you describe the balance of giving and receiving in your relationships?",
                    "type": MULTIPLE_CHOICE,
                    "options": [
                        {"id": "mostly_give", "text": "I tend to give more than I receive"},
                        {"id": "balanced", "text": "My relationships are generally balanced"},
                        {"id": "mostly_receive", "text": "I tend to receive more than I give"},
                        {"id": "varies", "text": "It varies significantly between relationships"}
                    ],
                    "category": PLANETARY,
                    "subcategory": "venus_mars_aspect",
                    "relevance": MEDIUM
                })

        return aspect_questions

    def _generate_general_questions(self) -> List[Dict[str, Any]]:
        """Generate general questions about birth time knowledge."""
        return [
            {
                "id": "general_birth_time_knowledge",
                "text": "Do you have any information about what time of day you were born?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "morning", "text": "Morning (6am-12pm)"},
                    {"id": "afternoon", "text": "Afternoon (12pm-6pm)"},
                    {"id": "evening", "text": "Evening (6pm-12am)"},
                    {"id": "night", "text": "Night (12am-6am)"},
                    {"id": "no_idea", "text": "I have no idea"}
                ],
                "category": GENERAL,
                "relevance": HIGH
            },
            {
                "id": "general_birth_certificate",
                "text": "Is there a birth time recorded on your birth certificate?",
                "type": YES_NO,
                "category": GENERAL,
                "relevance": HIGH
            },
            {
                "id": "general_family_recollection",
                "text": "Has anyone in your family mentioned anything about the time you were born?",
                "type": TEXT_INPUT,
                "category": GENERAL,
                "relevance": MEDIUM
            }
        ]

    def _generate_personality_questions(self) -> List[Dict[str, Any]]:
        """Generate questions about personality traits related to ascendant signs."""
        return [
            {
                "id": "personality_first_impression",
                "text": "How do people typically describe you when they first meet you?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "confident", "text": "Confident and assertive"},
                    {"id": "calm", "text": "Calm and grounded"},
                    {"id": "talkative", "text": "Talkative and curious"},
                    {"id": "nurturing", "text": "Nurturing and supportive"},
                    {"id": "charismatic", "text": "Charismatic and dramatic"},
                    {"id": "analytical", "text": "Analytical and detail-oriented"},
                    {"id": "diplomatic", "text": "Diplomatic and harmonious"},
                    {"id": "intense", "text": "Intense and mysterious"},
                    {"id": "adventurous", "text": "Adventurous and philosophical"},
                    {"id": "ambitious", "text": "Ambitious and disciplined"},
                    {"id": "unique", "text": "Unique and unconventional"},
                    {"id": "compassionate", "text": "Compassionate and dreamy"}
                ],
                "category": PERSONALITY,
                "subcategory": "ascendant",
                "relevance": HIGH
            },
            {
                "id": "personality_physical_appearance",
                "text": "Which of these best describes your physical appearance?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "athletic", "text": "Athletic build, strong features"},
                    {"id": "solid", "text": "Solid build, strong neck/shoulders"},
                    {"id": "slim", "text": "Slim build, expressive hands/face"},
                    {"id": "soft", "text": "Soft features, nurturing presence"},
                    {"id": "regal", "text": "Regal posture, noticeable hair/eyes"},
                    {"id": "proportioned", "text": "Well-proportioned, neat appearance"},
                    {"id": "balanced", "text": "Balanced features, graceful movement"},
                    {"id": "magnetic", "text": "Magnetic eyes, strong presence"},
                    {"id": "tall", "text": "Tall or long limbs, open expression"},
                    {"id": "structured", "text": "Structured features, mature appearance"},
                    {"id": "unusual", "text": "Unusual features, distinctive look"},
                    {"id": "ethereal", "text": "Ethereal quality, gentle eyes"}
                ],
                "category": PERSONALITY,
                "subcategory": "ascendant_physical",
                "relevance": MEDIUM
            }
        ]

    def _generate_life_event_questions(self) -> List[Dict[str, Any]]:
        """Generate questions about significant life events."""
        return [
            {
                "id": "life_events_career_change",
                "text": "When did you experience a significant career change or achievement?",
                "type": DATE_PICKER,
                "category": LIFE_EVENTS,
                "subcategory": "career",
                "relevance": HIGH
            },
            {
                "id": "life_events_relationship",
                "text": "When did you meet a significant partner or experience an important relationship milestone?",
                "type": DATE_PICKER,
                "category": LIFE_EVENTS,
                "subcategory": "relationship",
                "relevance": HIGH
            },
            {
                "id": "life_events_relocation",
                "text": "When did you relocate to a different city or country?",
                "type": DATE_PICKER,
                "category": LIFE_EVENTS,
                "subcategory": "relocation",
                "relevance": MEDIUM
            },
            {
                "id": "life_events_health",
                "text": "Have you experienced any significant health events? If so, when?",
                "type": DATE_PICKER,
                "category": LIFE_EVENTS,
                "subcategory": "health",
                "relevance": MEDIUM
            }
        ]

    def _generate_planetary_questions(self) -> List[Dict[str, Any]]:
        """Generate questions related to planetary positions."""
        return [
            {
                "id": "planetary_moon_emotions",
                "text": "How would you describe your emotional nature?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "fiery", "text": "Passionate and expressive"},
                    {"id": "earthy", "text": "Stable and practical"},
                    {"id": "airy", "text": "Intellectual and communicative"},
                    {"id": "watery", "text": "Deep and intuitive"}
                ],
                "category": PLANETARY,
                "subcategory": "moon_sign",
                "relevance": HIGH
            },
            {
                "id": "planetary_mercury_communication",
                "text": "How would you describe your communication style?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "direct", "text": "Direct and to the point"},
                    {"id": "methodical", "text": "Methodical and thorough"},
                    {"id": "quick", "text": "Quick and adaptable"},
                    {"id": "empathetic", "text": "Empathetic and understanding"},
                    {"id": "dramatic", "text": "Dramatic and expressive"},
                    {"id": "analytical", "text": "Analytical and precise"},
                    {"id": "diplomatic", "text": "Diplomatic and balanced"},
                    {"id": "probing", "text": "Probing and investigative"},
                    {"id": "philosophical", "text": "Philosophical and expansive"},
                    {"id": "structured", "text": "Structured and serious"},
                    {"id": "innovative", "text": "Innovative and unconventional"},
                    {"id": "intuitive", "text": "Intuitive and compassionate"}
                ],
                "category": PLANETARY,
                "subcategory": "mercury_sign",
                "relevance": MEDIUM
            }
        ]

    def _generate_house_questions(self) -> List[Dict[str, Any]]:
        """Generate questions related to house placements."""
        return [
            {
                "id": "house_career_focus",
                "text": "Which area of your life do you feel most driven to succeed in?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "self_identity", "text": "Personal identity and self-expression"},
                    {"id": "finances", "text": "Financial security and resources"},
                    {"id": "communication", "text": "Communication and learning"},
                    {"id": "home_family", "text": "Home and family life"},
                    {"id": "creativity", "text": "Creative expression and romance"},
                    {"id": "daily_work", "text": "Daily work and health routines"},
                    {"id": "relationships", "text": "One-on-one relationships"},
                    {"id": "transformation", "text": "Transformation and shared resources"},
                    {"id": "philosophy", "text": "Philosophy and higher education"},
                    {"id": "career", "text": "Career and public reputation"},
                    {"id": "community", "text": "Community and social groups"},
                    {"id": "spirituality", "text": "Spirituality and inner world"}
                ],
                "category": HOUSE,
                "subcategory": "mc_focus",
                "relevance": HIGH
            },
            {
                "id": "house_challenge_area",
                "text": "Which area of life has presented the most challenges for you?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "self_identity", "text": "Personal identity and self-expression"},
                    {"id": "finances", "text": "Financial security and resources"},
                    {"id": "communication", "text": "Communication and learning"},
                    {"id": "home_family", "text": "Home and family life"},
                    {"id": "creativity", "text": "Creative expression and romance"},
                    {"id": "daily_work", "text": "Daily work and health routines"},
                    {"id": "relationships", "text": "One-on-one relationships"},
                    {"id": "transformation", "text": "Transformation and shared resources"},
                    {"id": "philosophy", "text": "Philosophy and higher education"},
                    {"id": "career", "text": "Career and public reputation"},
                    {"id": "community", "text": "Community and social groups"},
                    {"id": "spirituality", "text": "Spirituality and inner world"}
                ],
                "category": HOUSE,
                "subcategory": "saturn_house",
                "relevance": MEDIUM
            }
        ]

    def _generate_relational_questions(self) -> List[Dict[str, Any]]:
        """Generate questions about relationship patterns."""
        return [
            {
                "id": "relational_partner_type",
                "text": "What qualities do you tend to look for in a partner?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "independence", "text": "Independence and strength"},
                    {"id": "stability", "text": "Stability and reliability"},
                    {"id": "intellect", "text": "Intellect and communication skills"},
                    {"id": "nurturing", "text": "Nurturing and emotional support"},
                    {"id": "passion", "text": "Passion and creativity"},
                    {"id": "practicality", "text": "Practicality and attention to detail"},
                    {"id": "harmony", "text": "Harmony and fairness"},
                    {"id": "intensity", "text": "Intensity and depth"},
                    {"id": "adventure", "text": "Adventure and optimism"},
                    {"id": "ambition", "text": "Ambition and responsibility"},
                    {"id": "uniqueness", "text": "Uniqueness and innovation"},
                    {"id": "compassion", "text": "Compassion and spiritual connection"}
                ],
                "category": RELATIONAL,
                "subcategory": "venus_sign",
                "relevance": MEDIUM
            },
            {
                "id": "relational_friendship_pattern",
                "text": "How would you describe your approach to friendships?",
                "type": MULTIPLE_CHOICE,
                "options": [
                    {"id": "few_close", "text": "A few very close friends"},
                    {"id": "large_network", "text": "A large network of connections"},
                    {"id": "selective", "text": "Selective but loyal"},
                    {"id": "community", "text": "Community-oriented"}
                ],
                "category": RELATIONAL,
                "subcategory": "moon_venus",
                "relevance": LOW
            }
        ]

    def process_answer(self, question_id: str, answer: Any) -> None:
        """
        Process a user's answer to update confidence levels and store the answer.

        Args:
            question_id: ID of the answered question
            answer: User's answer
        """
        # Find the question
        question = None
        for category in self.question_bank:
            for q in self.question_bank[category]:
                if q.get("id") == question_id:
                    question = q
                    break
            if question:
                break

        if not question:
            logger.warning(f"Question with ID {question_id} not found")
            return

        # Store the answer
        self.answers[question_id] = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }

        # Update confidence levels based on the answer
        self._update_confidence_levels(question, answer)

    def _update_confidence_levels(self, question: Dict[str, Any], answer: Any) -> None:
        """
        Update confidence levels based on the answer.

        Args:
            question: The question that was answered
            answer: The user's answer
        """
        category = question.get("category", GENERAL)
        subcategory = question.get("subcategory", "")

        # Update specific confidence areas based on question category
        if category == PERSONALITY and subcategory == "ascendant":
            self.confidence_levels["ascendant"] += 0.1
        elif category == HOUSE:
            self.confidence_levels["houses"] += 0.1
        elif category == PLANETARY:
            self.confidence_levels["planets"] += 0.1

        # Cap confidence levels at 1.0
        for key in self.confidence_levels:
            self.confidence_levels[key] = min(self.confidence_levels[key], 1.0)

        # Update overall confidence as weighted average
        self.confidence_levels["overall"] = (
            self.confidence_levels["ascendant"] * 0.4 +
            self.confidence_levels["houses"] * 0.3 +
            self.confidence_levels["planets"] * 0.3
        )

    def get_confidence_levels(self) -> Dict[str, float]:
        """
        Get the current confidence levels.

        Returns:
            Dictionary of confidence levels
        """
        return self.confidence_levels.copy()

    def get_answer_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the history of answers.

        Returns:
            Dictionary of answers by question ID
        """
        return self.answers.copy()
