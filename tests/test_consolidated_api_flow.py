#!/usr/bin/env python3
"""
Birth Time Rectifier API Test Script

This script tests the complete flow of the Birth Time Rectifier API,
from session initialization to chart export.
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

import requests

# Import the chart visualization functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from birth_time_rectifier.chart_visualizer import (
    generate_multiple_charts,
    modify_chart_for_harmonic,
    modify_chart_for_moon_ascendant,
    compare_charts,
    export_charts
)

# Try to import matplotlib for visualization
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Terminal colors for better UX
class TermColors:
    """Terminal color codes for prettier output"""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def colorize(text, color):
        """Add color to terminal text"""
        return f"{color}{text}{TermColors.RESET}"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("api_flow_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# API endpoints
# BASE_URL = "https://api.birthtimerectifier.com/v1"
BASE_URL = "http://localhost:8000/api/v1"
SESSION_ENDPOINT = f"{BASE_URL}/session/init"
BIRTH_DETAILS_ENDPOINT = f"{BASE_URL}/chart/validate"
CHART_ENDPOINT = f"{BASE_URL}/chart"
QUESTIONNAIRE_ENDPOINT = f"{BASE_URL}/questionnaire"
RECTIFICATION_ENDPOINT = f"{BASE_URL}/chart/rectify"
EXPORT_ENDPOINT = f"{BASE_URL}/chart/export"
LOCATION_SEARCH_ENDPOINT = f"{BASE_URL}/geocode"

def validate_vedic_planetary_data(planets_data) -> List[str]:
    """Validate that the planetary data follows Vedic astrology standards."""
    issues = []

    # Check for required planets in Vedic astrology
    required_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
    found_planets = [p.get("name") for p in planets_data]

    for planet in required_planets:
        if planet not in found_planets:
            issues.append(f"Missing required planet: {planet}")

    # Should have house cusps data for proper Vedic charts
    if len(planets_data) < 9:  # At minimum, the 7 classical planets + Rahu/Ketu are expected
        issues.append(f"Not enough planets for a complete Vedic chart. Found {len(planets_data)}, expected 9+")

    return issues

def initialize_session() -> str:
    """Initialize a session and return the session ID."""
    logger.info("STEP 1: SESSION INITIALIZATION")
    logger.info("Step 1: Testing session initialization")

    try:
        response = requests.get(SESSION_ENDPOINT)
        session_id = response.json().get("session_id")

        if not session_id:
            raise ValueError("No session ID returned from API")

        logger.info(f"Session initialized with ID: {session_id}")
        print(TermColors.colorize("✓ Session initialized successfully", TermColors.GREEN))
        return session_id
    except Exception as e:
        logger.error(f"Session initialization failed: {str(e)}")
        print(TermColors.colorize(f"✗ Session initialization failed: {str(e)}", TermColors.RED))
        raise

def validate_birth_details(birth_data: Dict[str, Any], session_id: str) -> bool:
    """Validate the provided birth details against the API."""
    logger.info("STEP 3: BIRTH DETAILS VALIDATION")
    logger.info("Validating birth details")
    print(f"  Validating birth details...")

    # Prepare validation request data
    validation_data = {
        "date": birth_data.get("birth_date"),
        "time": birth_data.get("birth_time"),
        "location": birth_data.get("location", f"{birth_data.get('city', '')}, {birth_data.get('country', '')}"),
        "latitude": birth_data.get("latitude"),
        "longitude": birth_data.get("longitude"),
        "tz": birth_data.get("timezone"),
    }

    try:
        # Make validation request
        response = requests.post(BIRTH_DETAILS_ENDPOINT, json=validation_data, headers={"X-Session-ID": session_id})

        if response.status_code >= 200 and response.status_code < 300:
            print(TermColors.colorize(f"✓ Birth details are valid", TermColors.GREEN))
            logger.info("Birth details validation successful")
            return True
        else:
            error_message = response.text
            print(TermColors.colorize(f"✗ Birth details validation failed: {error_message}", TermColors.RED))
            logger.error(f"Birth details validation failed: {error_message}")
            return False
    except Exception as e:
        print(TermColors.colorize(f"✗ Birth details validation failed: {str(e)}", TermColors.RED))
        logger.error(f"Birth details validation failed: {str(e)}")
        return False

def get_birth_data_from_user() -> Dict[str, Any]:
    """
    Collect birth data from user input and automatically get coordinates via geocoding.

    Returns:
        Dictionary with birth details including coordinates from geocoding API
    """
    print("\nPlease enter birth details:")

    name = input("Name: ")

    # Collect and validate birth date
    while True:
        birth_date = input("Birth date (YYYY-MM-DD): ")
        try:
            year, month, day = birth_date.split("-")
            # Use datetime.datetime directly
            datetime(int(year), int(month), int(day))
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    # Collect and validate birth time
    while True:
        birth_time = input("Birth time (HH:MM): ")
        try:
            hour, minute = birth_time.split(":")
            birth_time = f"{int(hour):02d}:{int(minute):02d}:00"
            break
        except ValueError:
            print("Invalid time format. Please use HH:MM.")

    # Collect location information
    city = input("City of birth: ")
    country = input("Country of birth: ")
    location = f"{city}, {country}"

    # Use geocoding API to get coordinates and timezone
    try:
        # Prepare the geocoding request
        geocode_data = {"query": location}
        geocode_result = requests.post(LOCATION_SEARCH_ENDPOINT, json=geocode_data)

        if not geocode_result:
            raise ValueError("Empty response from geocoding service")

        # Extract locations from results array
        locations = geocode_result.json().get("results", [])

        if not locations:
            raise ValueError(f"No geocoding results found for '{location}'")

        # Use the first location result
        location_data = locations[0]

        # Extract coordinates and timezone from geocoding result
        latitude = location_data.get("latitude")
        longitude = location_data.get("longitude")
        timezone = location_data.get("timezone")

        if not all([latitude, longitude, timezone]):
            raise ValueError("Incomplete geocoding data received")

        print(f"✅ Location geocoded successfully: {latitude}, {longitude} ({timezone})")
    except Exception as e:
        print(f"❗ Geocoding failed: {str(e)}")
        print("Please enter coordinates manually:")

        # Fallback for geocoding failure
        while True:
            try:
                latitude = float(input("Latitude (decimal degrees): "))
                longitude = float(input("Longitude (decimal degrees): "))
                timezone = input("Timezone (e.g., 'America/New_York', 'Europe/London'): ")
                break
            except ValueError:
                print("Invalid coordinates. Please enter decimal numbers.")

    birth_data = {
        "name": name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "city": city,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "location": location
    }

    logger.info(f"Collected birth data from user: {birth_data}")
    display_birth_data(birth_data)

    return birth_data

def generate_birth_data() -> Dict[str, Any]:
    """
    Generate random birth data for testing.

    Returns:
        Dictionary with random birth details
    """
    # Generate random date between 1950 and 2000
    year = random.randint(1950, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Avoid edge cases with month lengths

    # Generate random time
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)

    # Format date and time strings
    birth_date = f"{year:04d}-{month:02d}-{day:02d}"
    birth_time = f"{hour:02d}:{minute:02d}:00"

    # Select random location from common cities
    cities = [
        {"city": "New York", "country": "United States", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
        {"city": "London", "country": "United Kingdom", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
        {"city": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
        {"city": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"},
        {"city": "Moscow", "country": "Russia", "latitude": 55.7558, "longitude": 37.6173, "timezone": "Europe/Moscow"},
        {"city": "Cairo", "country": "Egypt", "latitude": 30.0444, "longitude": 31.2357, "timezone": "Africa/Cairo"},
        {"city": "Rio de Janeiro", "country": "Brazil", "latitude": -22.9068, "longitude": -43.1729, "timezone": "America/Sao_Paulo"},
        {"city": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
    ]

    location = random.choice(cities)
    city = location["city"]
    country = location["country"]
    location_str = f"{city}, {country}"

    # Try to use geocoding API to get coordinates and timezone
    try:
        # Prepare the geocoding request
        geocode_data = {"query": location_str}
        logger.info(f"Attempting to geocode: {location_str}")
        geocode_result = requests.post(LOCATION_SEARCH_ENDPOINT, json=geocode_data)

        if geocode_result:
            # Use the first location result
            location_data = geocode_result.json().get("results", [{}])[0]

            # Extract coordinates and timezone from geocoding result
            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")
            timezone = location_data.get("timezone")

            if all([latitude, longitude, timezone]):
                logger.info(f"Successfully geocoded {location_str} via API")
            else:
                # Fallback to our predefined coordinates
                logger.info(f"Incomplete geocoding results, using predefined coordinates")
                latitude = location["latitude"]
                longitude = location["longitude"]
                timezone = location["timezone"]
        else:
            # Fallback to our predefined coordinates
            logger.info(f"No geocoding results, using predefined coordinates")
            latitude = location["latitude"]
            longitude = location["longitude"]
            timezone = location["timezone"]
    except Exception as e:
        # Fallback to our predefined coordinates
        logger.info(f"Geocoding service error: {str(e)}, using predefined coordinates")
        latitude = location["latitude"]
        longitude = location["longitude"]
        timezone = location["timezone"]

    # Create birth data dictionary
    birth_data = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "city": city,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "location": location_str,
        "name": f"Test Person {uuid.uuid4().hex[:6]}"
    }

    logger.info(f"Generated random birth data: {birth_data}")
    display_birth_data(birth_data)

    return birth_data

def generate_birth_chart(birth_data: Dict[str, Any], session_id: str) -> str:
    """
    Generate a birth chart for the provided birth data.

    Args:
        birth_data: Dictionary containing birth details
        session_id: Session ID for API authentication

    Returns:
        String containing the chart ID of the generated chart
    """
    logger.info("STEP 4: CHART GENERATION")
    print("\nGenerating birth chart with OpenAI verification...")

    # Prepare chart generation request data
    chart_data = {
        "birth_details": birth_data,
        "options": {
            "house_system": "W",  # Changed from "placidus" to "W" for more reliable house calculations
            "zodiac_type": "sidereal",   # Vedic astrology uses sidereal zodiac
            "ayanamsa": "lahiri",        # Lahiri is the standard ayanamsa for Vedic charts
            "calculation_type": "precise",
            "include_openai_verification": True,  # Explicitly request OpenAI verification
            "verify_with_ai": True,      # Alternative flag to ensure AI verification
            "node_type": "true",         # For accurate Rahu/Ketu positions
            "force_openai_validation": True,  # Force OpenAI validation
            "openai_verification": True,  # Add additional flag for compatibility
            "prashna_kundali_analysis": True  # Enable Prashna Kundali analysis as specified in requirements
        }
    }

    try:
        # Make API request
        response = requests.post(f"{CHART_ENDPOINT}/generate", json=chart_data, headers={"X-Session-ID": session_id})
        response.raise_for_status()  # Raise exception for HTTP errors

        # Extract chart ID
        chart_id = response.json().get("chart_id")

        if chart_id:
            print(f"Birth chart generated successfully. Chart ID: {chart_id}")
            logger.info(f"Birth chart generated with ID: {chart_id}")
            return chart_id
        else:
            error_msg = "Failed to get chart ID from chart generation API response"
            logger.error(error_msg)
            print(TermColors.colorize(f"✗ {error_msg}", TermColors.RED))
            raise ValueError(error_msg)

    except Exception as e:
        logger.error(f"Chart generation failed: {str(e)}")
        print(TermColors.colorize(f"✗ Chart generation failed: {str(e)}", TermColors.RED))
        raise

def get_chart(chart_id: str, session_id: str) -> Dict[str, Any]:
    """
    Retrieve chart data by ID.

    Args:
        chart_id: ID of the chart to retrieve
        session_id: Session ID for API authentication

    Returns:
        Dictionary containing chart data
    """
    logger.info("STEP 5: CHART RETRIEVAL")
    print(f"\nRetrieving chart data for ID: {chart_id}...")

    try:
        # Make API request
        response = requests.get(f"{CHART_ENDPOINT}/{chart_id}", headers={"X-Session-ID": session_id})

        # Validate chart data
        planets = response.json().get("planets", [])
        houses = response.json().get("houses", [])

        print(f"Chart retrieved successfully. Contains {len(planets)} planets and {len(houses)} houses.")
        logger.info(f"Chart retrieved with {len(planets)} planets and {len(houses)} houses")

        return response.json()
    except Exception as e:
        logger.error(f"Chart retrieval failed: {str(e)}")
        print(TermColors.colorize(f"✗ Chart retrieval failed: {str(e)}", TermColors.RED))
        raise

def display_confidence_progress_bar(current: float, threshold: int = 80, bar_width: int = 50) -> None:
    """
    Display a progress bar for confidence level.

    Args:
        current: Current confidence level (0-100)
        threshold: Target confidence threshold (0-100)
        bar_width: Width of the progress bar in characters
    """
    # Ensure confidence is in the range 0-100
    current = max(0, min(100, current))

    # Calculate filled width
    filled_width = int(bar_width * current / 100)

    # Create progress bar
    bar = '█' * filled_width + '░' * (bar_width - filled_width)

    # Determine color based on threshold
    if current >= threshold:
        color = TermColors.GREEN
    elif current >= threshold * 0.7:
        color = TermColors.YELLOW
    else:
        color = TermColors.RED

    # Print progress bar
    print(f"[{TermColors.colorize(bar, color)}] {current:.1f}% / {threshold}%")

def prompt_for_questionnaire_answer(question: Dict[str, Any]) -> str:
    """
    Prompt the user for an answer to a questionnaire question.

    Args:
        question: Dictionary containing question details

    Returns:
        String containing the user's answer
    """
    question_type = question.get("type", "text")

    if question_type == "boolean":
        while True:
            answer = input("Your answer (yes/no): ").lower()
            if answer in ["yes", "no", "y", "n"]:
                return "Yes" if answer in ["yes", "y"] else "No"
            print("Please answer with 'yes' or 'no'.")
    elif question_type == "multiple_choice":
        options = question.get("options", [])
        if options:
            print("Options:")
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")

            while True:
                try:
                    choice = int(input("Enter option number: "))
                    if 1 <= choice <= len(options):
                        return options[choice-1]
                    print(f"Please enter a number between 1 and {len(options)}.")
                except ValueError:
                    print("Please enter a valid number.")

    # Default to text input for all other question types
    return input("Your answer: ")

def process_questionnaire(
    chart_id: str,
    birth_data: Dict[str, Any],
    session_id: str,
    target_confidence: float,
    non_interactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Process the dynamic questionnaire until confidence threshold reached.

    Args:
        chart_id: ID of the chart to process questions for
        birth_data: Dictionary containing birth details
        session_id: Session ID for API authentication
        target_confidence: Target confidence threshold (0-100)
        non_interactive: Whether to run in non-interactive mode (DEPRECATED - always interactive now)

    Returns:
        List of dictionaries containing confidence history
    """
    logger.info("STEP 6: DYNAMIC QUESTIONNAIRE")

    # Convert target confidence to integer (0-100 scale)
    target_confidence_int = int(target_confidence * 100)
    print(f"\nStarting questionnaire (target confidence: {target_confidence_int}%)")
    logger.info(f"Starting dynamic questionnaire flow (threshold: {target_confidence_int}%)")

    # Always use interactive mode now
    print(TermColors.colorize("\nINTERACTIVE QUESTIONNAIRE MODE", TermColors.BOLD + TermColors.GREEN))
    print("You will be prompted to answer each question to help refine the birth time.")

    # Initialize variables for tracking
    question_num = 0
    confidence = 0.0
    confidence_history = []
    question_answers = []  # Track all questions and answers for rectification step
    retry_count = 0
    max_retries = 3

    try:
        # Make initial questionnaire API request to get first question
        request_data = {
            "chart_id": chart_id,
            "max_questions": 20,  # Increased to allow for more questions if needed
            "target_confidence": target_confidence_int,
            "use_openai_validation": True,  # Explicitly request OpenAI validation
            "force_generate": True,  # Force OpenAI to generate questions
            "prashna_kundali_analysis": True  # Use Prashna Kundali analysis for question generation
        }

        while retry_count < max_retries:
            logger.info(f"Requesting questionnaire (attempt {retry_count + 1}/{max_retries})")
            response = requests.post(QUESTIONNAIRE_ENDPOINT, json=request_data, headers={"X-Session-ID": session_id})

            if response.status_code != 200:
                logger.warning(f"Questionnaire API returned status code {response.status_code}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying questionnaire request ({retry_count}/{max_retries})")
                    time.sleep(1)  # Brief delay before retry
                    continue
                else:
                    logger.error(f"Failed to get questions after {max_retries} attempts")
                    break

            # Get questions from API response
            response_data = response.json()
            questions = response_data.get("questions", [])
            confidence = float(response_data.get("confidence", 0))

            # Check if API returned questions
            if not questions:
                # No questions received, try with more forceful parameters
                logger.warning("No questions returned from API, trying with enhanced parameters")
                request_data.update({
                    "force_generate": True,
                    "openai_force": True,
                    "debug_mode": True,
                    "skip_cache": True,
                    "retry_generation": True
                })
                retry_count += 1
                if retry_count < max_retries:
                    continue
                else:
                    logger.error("Failed to generate questions even with enhanced parameters")
                    print(TermColors.colorize("✗ Unable to generate questions for this chart. Proceeding with direct rectification.", TermColors.RED))
                    return []
            else:
                # Success! We have questions
                break

        # Check if we have questions after all retries
        if not questions:
            logger.error("No questions available after all retries")
            print(TermColors.colorize("✗ Failed to retrieve questions from API. Using direct rectification.", TermColors.RED))
            return []

        # Get confidence value
        print(f"Initial confidence: {confidence:.1f}%")
        logger.info(f"Initial confidence: {confidence:.1f}%")
        display_confidence_progress_bar(confidence, target_confidence_int)

        # Continue until confidence threshold reached or questionnaire completed
        question_idx = 0
        while question_idx < len(questions) and confidence < target_confidence:
            question = questions[question_idx]
            question_idx += 1
            question_num += 1

            # Format and display question
            print(f"\nQuestion {question_num}: {question.get('text', 'No question text available')}")

            # Always use interactive mode - prompt for answer
            answer = prompt_for_questionnaire_answer(question)

            # Record question and answer
            qa_entry = {
                "question_num": question_num,
                "question_id": question.get("id", f"q_{question_num}"),
                "question_text": question.get("text", ""),
                "answer": answer,
                "confidence": confidence
            }
            question_answers.append(qa_entry)

            # Send answer to API
            answer_data = {
                "chart_id": chart_id,
                "question_id": question.get("id", f"q_{question_num}"),
                "answer": answer,
                "use_openai_validation": True  # Request OpenAI validation for this answer
            }

            logger.info(f"Sending answer for question {question_num}: {answer}")
            answer_response = requests.post(
                f"{QUESTIONNAIRE_ENDPOINT}/{question.get('id', 'unknown')}/answer",
                json=answer_data,
                headers={"X-Session-ID": session_id}
            )

            # Check if the answer was accepted
            if answer_response.status_code != 200:
                logger.warning(f"Answer API returned status code {answer_response.status_code}")
                print(TermColors.colorize(f"✗ Error submitting answer: {answer_response.text}", TermColors.RED))
                continue

            # Extract updated confidence from response
            try:
                response_data = answer_response.json()

                # Get next question if available
                next_question = response_data.get("next_question", {})
                if next_question and isinstance(next_question, dict) and "text" in next_question:
                    questions.append(next_question)

                # Update confidence
                new_confidence = float(response_data.get("confidence", confidence))

                # Only update if confidence increased (sanity check)
                if new_confidence > confidence:
                    confidence = new_confidence
                    qa_entry["confidence"] = confidence

                # Display updated confidence
                print(f"Confidence after Q{question_num}: {confidence:.1f}%")
                display_confidence_progress_bar(confidence, target_confidence_int)

                # Check if confidence threshold reached
                if confidence >= target_confidence:
                    logger.info(f"Confidence threshold reached: {confidence:.1f}%")
                    print(TermColors.colorize(f"✓ Confidence threshold reached: {confidence:.1f}%", TermColors.GREEN))
                    break

                # Check if we need more questions
                if question_idx >= len(questions) and confidence < target_confidence:
                    # Request more questions
                    logger.info("Requesting additional questions")
                    request_data["current_confidence"] = confidence
                    more_questions_response = requests.post(QUESTIONNAIRE_ENDPOINT, json=request_data, headers={"X-Session-ID": session_id})

                    if more_questions_response.status_code == 200:
                        more_data = more_questions_response.json()
                        more_questions = more_data.get("questions", [])
                        if more_questions:
                            questions.extend(more_questions)
                            logger.info(f"Received {len(more_questions)} additional questions")

            except Exception as e:
                logger.error(f"Error processing question response: {str(e)}")
                print(TermColors.colorize(f"✗ Error processing response: {str(e)}", TermColors.RED))

        logger.info(f"Questionnaire completed with {question_num} questions and final confidence {confidence:.1f}%")

        # Add final confidence to history
        confidence_history.append({
            "question_num": question_num,
            "confidence": confidence
        })

        return confidence_history

    except Exception as e:
        # Handle exceptions
        import traceback
        tb_info = traceback.format_exc()
        logger.error(f"Error in questionnaire flow: {str(e)}\n{tb_info}")
        print(TermColors.colorize(f"✗ Error in questionnaire: {str(e)}", TermColors.RED))
        return []

def rectify_birth_time(
    chart_id: str,
    birth_data: Dict[str, Any],
    confidence_history: List[Dict[str, Any]],
    session_id: str
) -> Dict[str, Any]:
    """
    Request birth time rectification based on questionnaire answers.

    Args:
        chart_id: ID of the chart to rectify
        birth_data: Dictionary containing birth details
        confidence_history: List of confidence data from questionnaire
        session_id: Session ID for API authentication

    Returns:
        Dictionary containing rectification results
    """
    logger.info("STEP 7: BIRTH TIME RECTIFICATION")
    print("\nRequesting birth time rectification...")

    # Extract answers from confidence history
    answers = []
    for entry in confidence_history:
        if all(k in entry for k in ["question_id", "question", "answer"]):
            answers.append({
                "question_id": entry.get("question_id"),
                "answer": entry.get("answer")
            })

    # If no answers are available from the questionnaire, we can't do rectification
    if not answers:
        print(TermColors.colorize("✗ No questionnaire answers available. Cannot perform birth time rectification.", TermColors.RED))
        logger.error("No questionnaire answers available for rectification")
        raise ValueError("Cannot perform birth time rectification without questionnaire answers")

    # Prepare rectification request data based on API expectations
    rectification_data = {
        "chart_id": chart_id,
        "answers": answers
    }

    # Add birth time range (required by the API)
    hours, minutes = map(int, birth_data.get("birth_time", "00:00:00").split(":")[:2])
    rectification_data["birth_time_range"] = {
        "min_hours": max(0, hours - 1),
        "min_minutes": 0,
        "max_hours": min(23, hours + 1),
        "max_minutes": 0
    }

    try:
        # Make API request
        response = requests.post(RECTIFICATION_ENDPOINT, json=rectification_data, headers={"X-Session-ID": session_id})
        response.raise_for_status()  # Raise exception for HTTP errors

        rectification_result = response.json()

        # Extract key information
        original_time = rectification_result.get("original_time")
        rectified_time = rectification_result.get("rectified_time")
        confidence = rectification_result.get("confidence_score")
        rectified_chart_id = rectification_result.get("rectified_chart_id")
        explanation = rectification_result.get("explanation")

        # Display results
        print("\nRectification results:")
        print(f"  Original time: {original_time}")
        print(f"  Rectified time: {rectified_time}")
        print(f"  Confidence: {confidence}%")
        print(f"  Rectified chart ID: {rectified_chart_id}")
        print(f"\nExplanation:\n  {explanation}")

        logger.info(f"Birth time rectified from {original_time} to {rectified_time} with {confidence}% confidence")
        logger.info(f"Rectified chart ID: {rectified_chart_id}")

        return rectification_result
    except Exception as e:
        logger.error(f"Birth time rectification failed: {str(e)}")
        print(TermColors.colorize(f"✗ Birth time rectification failed: {str(e)}", TermColors.RED))

        # We don't want to silently continue with fake data in a real test
        # Instead, raise the error to stop the test
        raise ValueError(f"Birth time rectification API call failed: {str(e)}")

def export_chart(chart_id: str, session_id: str) -> Dict[str, Any]:
    """
    Export a chart to PDF format.

    Args:
        chart_id: ID of the chart to export
        session_id: Session ID for authorization

    Returns:
        Dictionary with export details
    """
    logger.info("STEP 9: CHART EXPORT")
    print("\nExporting chart...")

    # Prepare export request data
    export_data = {
        "chart_id": chart_id,
        "format": "pdf",
        "options": {
            "include_interpretation": True,
            "include_aspects": True
        }
    }

    try:
        # Make export request
        response = requests.post(EXPORT_ENDPOINT, json=export_data, headers={"X-Session-ID": session_id})

        # Extract download URL
        download_url = response.json().get("download_url", "")

        # Display export results
        if download_url:
            print(f"Chart exported successfully.")
            print(f"Download URL: {download_url}")
            logger.info(f"Chart exported successfully with download URL: {download_url}")
        else:
            print(TermColors.colorize("Export successful but no download URL provided", TermColors.YELLOW))
            logger.warning("Export response missing download_url")

        return response.json()
    except Exception as e:
        logger.error(f"Chart export failed: {str(e)}")
        print(TermColors.colorize(f"✗ Chart export failed: {str(e)}", TermColors.RED))

        # Return simulated data as a fallback
        print(TermColors.colorize("Using simulated export data as fallback", TermColors.YELLOW))
        logger.info("Using simulated export data as fallback due to API error")

        # Create a simulated download URL
        export_id = uuid.uuid4().hex[:8]
        download_url = f"/api/chart/export/{export_id}/download"

        return {
            "chart_id": chart_id,
            "download_url": download_url,
            "format": "pdf",
            "status": "completed",
            "simulated": True
        }

def get_birth_details(use_random: bool = False) -> Dict[str, Any]:
    """
    Get birth details either from user input or generate randomly.

    Args:
        use_random: Whether to use random birth details

    Returns:
        Dictionary with birth details
    """
    if use_random:
        print(TermColors.colorize("Generating random birth details...", TermColors.CYAN))
        return generate_birth_data()
    else:
        print(TermColors.colorize("Please enter birth details:", TermColors.CYAN))
        return get_birth_data_from_user()

def display_birth_data(birth_data: Dict[str, Any]) -> None:
    """Display formatted birth data."""
    print("\nBirth Details:")
    print(f"  Date: {birth_data.get('birth_date')}")
    print(f"  Time: {birth_data.get('birth_time')}")
    location_str = f"{birth_data.get('city')}, {birth_data.get('country')}" if birth_data.get('city') and birth_data.get('country') else None
    print(f"  Location: {location_str}")
    print(f"  Coordinates: {birth_data.get('latitude')} {birth_data.get('longitude')}")
    print(f"  Timezone: {birth_data.get('timezone')}")
    print("")

def display_menu() -> str:
    """Display the menu and return the selected option."""
    # Clear screen (works on Windows, macOS, and Linux)
    os.system('cls' if os.name == 'nt' else 'clear')

    # ASCII art header
    header = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ██╗██████╗ ████████╗██╗  ██╗    ████████╗██╗███╗   ███╗███████╗  ║
    ║   ██╔══██╗██║██╔══██╗╚══██╔══╝██║  ██║    ╚══██╔══╝██║████╗ ████║██╔════╝  ║
    ║   ██████╔╝██║██████╔╝   ██║   ███████║       ██║   ██║██╔████╔██║█████╗    ║
    ║   ██╔══██╗██║██╔══██╗   ██║   ██╔══██║       ██║   ██║██║╚██╔╝██║██╔══╝    ║
    ║   ██████╔╝██║██║  ██║   ██║   ██║  ██║       ██║   ██║██║ ╚═╝ ██║███████╗  ║
    ║   ╚═════╝ ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝       ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝  ║
    ║                                                               ║
    ║           ██████╗ ███████╗ ██████╗████████╗██╗███████╗██╗███████╗██████╗    ║
    ║           ██╔══██╗██╔════╝██╔════╝╚══██╔══╝██║██╔════╝██║██╔════╝██╔══██╗   ║
    ║           ██████╔╝█████╗  ██║        ██║   ██║█████╗  ██║█████╗  ██████╔╝   ║
    ║           ██╔══██╗██╔══╝  ██║        ██║   ██║██╔══╝  ██║██╔══╝  ██╔══██╗   ║
    ║           ██║  ██║███████╗╚██████╗   ██║   ██║██║     ██║███████╗██║  ██║   ║
    ║           ╚═╝  ╚═╝╚══════╝ ╚═════╝   ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝   ║
    ║                                                               ║
    ║                  END-TO-END TEST SUITE                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(TermColors.colorize(header, TermColors.CYAN))

    # Display options
    print(TermColors.colorize("Please select an option:", TermColors.BOLD))
    print("  " + TermColors.colorize("[1]", TermColors.GREEN) + " Run test with randomly generated birth details")
    print("  " + TermColors.colorize("[2]", TermColors.YELLOW) + " Run test with manually entered birth details")
    print("  " + TermColors.colorize("[q]", TermColors.RED) + " Quit")
    print()

    # Get user choice
    while True:
        choice = input(TermColors.colorize("Enter your choice (1, 2, or q): ", TermColors.BOLD))
        if choice in ["1", "2", "q"]:
            return choice
        print(TermColors.colorize("Invalid choice. Please try again.", TermColors.RED))

def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    line = "═" * (len(title) + 10)
    print("\n" + TermColors.colorize(line, TermColors.BLUE))
    print(TermColors.colorize(f"    {title}    ", TermColors.BLUE + TermColors.BOLD))
    print(TermColors.colorize(line, TermColors.BLUE))

def print_step(step_num: int, step_name: str) -> None:
    """Print a formatted step header."""
    print("\n" + TermColors.colorize(f"STEP {step_num}: {step_name}", TermColors.YELLOW + TermColors.BOLD))
    print(TermColors.colorize("─" * (len(step_name) + 10), TermColors.YELLOW))

def print_test_summary(success: bool, start_time: float) -> None:
    """Print a summary of the test results."""
    duration = time.time() - start_time

    if success:
        result = "SUCCESS"
        color = TermColors.GREEN
    else:
        result = "FAILURE"
        color = TermColors.RED

    footer = f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   TEST RESULT: {result.ljust(40)}                  ║
    ║   DURATION: {f"{duration:.2f} seconds".ljust(42)}                  ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(TermColors.colorize(footer, color))

def format_data_display(data_dict: Dict[str, Any]) -> str:
    """Format a dictionary for pretty console display."""
    output = ""
    for key, value in data_dict.items():
        # Format key with title case and replace underscores with spaces
        formatted_key = key.replace('_', ' ').title()
        # Apply different colors based on data type
        if isinstance(value, (int, float)):
            value_str = TermColors.colorize(str(value), TermColors.YELLOW)
        elif isinstance(value, dict):
            value_str = "{\n" + "".join([f"    {k}: {v}\n" for k, v in value.items()]) + "  }"
            value_str = TermColors.colorize(value_str, TermColors.CYAN)
        else:
            value_str = TermColors.colorize(str(value), TermColors.GREEN)

        output += f"  {TermColors.colorize(formatted_key, TermColors.BOLD)}: {value_str}\n"

    return output

def generate_random_answer(question: Dict[str, Any]) -> str:
    """
    Generate a random answer for a question in automated testing mode.

    Args:
        question: Dictionary containing question details

    Returns:
        String containing the generated answer
    """
    question_text = question.get("text", "").lower()
    question_type = question.get("type", "text")

    # For boolean/yes-no questions
    if question_type == "boolean" or "yes or no" in question_text:
        return random.choice(["Yes", "No", "Not sure"])

    # Check question content and provide more realistic answers
    if any(word in question_text for word in ["marriage", "relationship", "partner"]):
        return random.choice([
            "Had a significant relationship change at age 28",
            "Married at 32, very positive experience",
            "Long-term partnership started at 26"
        ])
    elif any(word in question_text for word in ["career", "job", "profession", "work"]):
        return random.choice([
            "Changed career path at age 30, became more fulfilled",
            "Major promotion at 29, felt very accomplished",
            "Started own business at 35"
        ])
    elif any(word in question_text for word in ["health", "medical", "illness"]):
        return random.choice([
            "Had minor health issues in mid-30s but nothing serious",
            "Very healthy overall, regular exercise routine",
            "Significant health improvement after lifestyle change at 31"
        ])
    elif any(word in question_text for word in ["move", "location", "relocate", "travel"]):
        return random.choice([
            "Relocated to a new city at age 27, very positive experience",
            "Frequent international travel for work between ages 30-35",
            "Moved to another country at 33"
        ])
    elif any(word in question_text for word in ["education", "study", "school", "degree"]):
        return random.choice([
            "Completed advanced degree at 32, felt very accomplished",
            "Self-taught in many subjects, no formal education after 25",
            "Changed academic focus at 29"
        ])
    elif any(word in question_text for word in ["appearance", "physical", "look"]):
        return random.choice([
            "Average height, athletic build, distinctive facial features",
            "Tall with an athletic body type",
            "Medium height, slim build, distinctive eyes"
        ])
    elif any(word in question_text for word in ["spiritual", "awakening", "beliefs"]):
        return random.choice([
            "Had spiritual awakening around age 34",
            "Regular meditation practice since age 30",
            "Significant shift in beliefs at 28"
        ])
    elif any(word in question_text for word in ["family", "parents", "siblings"]):
        return random.choice([
            "Close relationship with family, especially mother",
            "Distant from parents, closer to siblings",
            "Family very supportive of career choices"
        ])
    elif any(word in question_text for word in ["personality", "character", "trait"]):
        return random.choice([
            "Analytical, thoughtful, sometimes reserved",
            "Outgoing, social, enjoy group activities",
            "Creative, intuitive, good at problem-solving"
        ])
    else:
        # Default responses for other question types
        return random.choice([
            "Yes, this was significant in my life journey",
            "Moderately important but not life-changing",
            "No, this wasn't particularly relevant to me",
            "This occurred around age 30",
            "This happened multiple times throughout my twenties"
        ])

def execute_test_flow(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Execute the end-to-end test flow for the API.

    Args:
        args: Command line arguments

    Returns:
        Dictionary with test results and metrics
    """
    start_time = time.time()

    try:
        print(f"\n{'=' * 80}")
        print(f"{' ' * 30}API FLOW TEST")
        print(f"{'=' * 80}\n")

        # Initialize session
        session_id = initialize_session()

        # Generate and validate birth details
        birth_data = get_birth_details(args.random_data)
        validate_birth_details(birth_data, session_id)

        # Generate birth chart
        chart_id = generate_birth_chart(birth_data, session_id)

        # Retrieve chart
        chart_data = get_chart(chart_id, session_id)

        # Generate multiple charts for the retrieved chart
        original_charts = generate_multiple_charts(chart_data)

        # Process questionnaire
        confidence_history = process_questionnaire(
            chart_id=chart_id,
            birth_data=birth_data,
            session_id=session_id,
            target_confidence=args.confidence_threshold,
            # Non-interactive mode is deprecated, always use interactive mode
            non_interactive=False
        )

        # Rectify birth time
        rectification = rectify_birth_time(
            chart_id,
            birth_data,
            confidence_history,
            session_id
        )

        rectified_time = rectification.get("rectified_time")
        rectified_chart_id = rectification.get("rectified_chart_id")

        # Ensure we have valid IDs before proceeding
        if not rectified_chart_id:
            raise ValueError("Failed to get rectified chart ID from rectification response")

        # Retrieve rectified chart
        rectified_chart = get_chart(rectified_chart_id, session_id)

        # Generate multiple charts for the rectified chart
        rectified_charts = generate_multiple_charts(rectified_chart)

        # Compare original and rectified charts using API endpoint
        print(f"\nComparing original chart {chart_id} with rectified chart {rectified_chart_id}...")
        try:
            # Use the chart comparison API endpoint
            compare_url = f"{CHART_ENDPOINT}/compare"
            compare_params = {
                "chart1_id": chart_id,
                "chart2_id": rectified_chart_id,
                "comparison_type": "differences",
                "include_significance": True
            }
            compare_response = requests.get(
                compare_url,
                params=compare_params,
                headers={"X-Session-ID": session_id}
            )
            compare_response.raise_for_status()
            differences = compare_response.json()
            print(TermColors.colorize("✓ Charts compared successfully", TermColors.GREEN))
            logger.info("Charts compared successfully")
        except Exception as e:
            logger.error(f"Chart comparison failed: {str(e)}")
            print(TermColors.colorize(f"✗ Chart comparison failed: {str(e)}", TermColors.RED))
            # Don't continue with dummy data, raise the error
            raise ValueError(f"Chart comparison API call failed: {str(e)}")

        # Export the charts
        export_path = export_charts(original_charts, rectified_charts, birth_data)

        # Create confidence progression visualization if matplotlib is available
        if confidence_history:
            try:
                # Extract confidence values and question numbers
                confidences = [entry.get("confidence", 0) for entry in confidence_history]
                questions = list(range(1, len(confidences) + 1))

                # Create timestamp for filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Set up the plot
                plt.figure(figsize=(10, 6))
                plt.plot(questions, confidences, marker='o', linestyle='-', color='blue', linewidth=2, markersize=8)
                plt.grid(True, linestyle='--', alpha=0.7)

                # Add horizontal line at target confidence
                target_confidence = int(args.confidence_threshold)
                plt.axhline(y=target_confidence, color='green', linestyle='--', alpha=0.7, label=f'Target ({target_confidence}%)')

                # Set labels and title
                plt.xlabel('Question Number', fontsize=12)
                plt.ylabel('Confidence (%)', fontsize=12)
                plt.title('Confidence Progression During Questionnaire', fontsize=14)

                # Set axis limits
                plt.ylim(0, 105)
                plt.xlim(0.5, len(confidences) + 0.5)

                # Add data labels
                for i, confidence in enumerate(confidences):
                    plt.annotate(f"{confidence:.1f}%",
                                xy=(i + 1, confidence),
                                xytext=(0, 10),
                                textcoords='offset points',
                                ha='center',
                                fontsize=9)

                # Add legend
                plt.legend(loc='lower right')

                # Add grid
                plt.grid(True, linestyle='--', alpha=0.7)

                # Ensure figures directory exists
                results_dir = os.path.join("tests", "results", "figures")
                os.makedirs(results_dir, exist_ok=True)

                # Save the figure
                filename = os.path.join(results_dir, f"confidence_progress_{timestamp}.png")
                plt.savefig(filename, dpi=100, bbox_inches='tight')
                plt.close()

                print(f"\nConfidence progression visualization saved to: {filename}")
                logger.info(f"Confidence visualization saved to {filename}")
            except ImportError:
                logger.warning("Matplotlib not available, skipping confidence visualization")
                print(TermColors.colorize("Note: Matplotlib not available, skipping confidence visualization", TermColors.YELLOW))

        duration = time.time() - start_time

        # Format results
        result = {
            "status": "success",
            "duration_seconds": duration,
            "original_chart_id": chart_id,
            "rectified_chart_id": rectified_chart_id,
            "original_time": birth_data.get("birth_time"),
            "rectified_time": rectified_time,
            "confidence_history": confidence_history,
            "differences": differences
        }

        print(f"\n{'=' * 80}")
        print(f"{' ' * 20}END-TO-END API TEST COMPLETED")
        print(f"{'=' * 80}")
        print(f"\nTest completed in {duration:.2f} seconds")
        print(f"Result: {TermColors.colorize('Success', TermColors.GREEN)}")

        logger.info(f"End-to-end API test completed successfully in {duration:.2f} seconds")

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Test failed after {duration:.2f} seconds: {str(e)}")

        # Include detailed traceback in the log
        tb_info = traceback.format_exc()
        logger.error(f"Traceback:\n{tb_info}")

        print(f"\n{'=' * 80}")
        print(f"{' ' * 20}END-TO-END API TEST FAILED")
        print(f"{'=' * 80}")
        print(f"\nTest failed after {duration:.2f} seconds")
        print(f"Error: {TermColors.colorize(str(e), TermColors.RED)}")

        # Raise the exception to stop execution
        raise

def main():
    """
    Main function to run the API test flow.
    """
    parser = argparse.ArgumentParser(description="Run the Birth Time Rectifier API test flow")
    parser.add_argument("--non-interactive", action="store_true", help="DEPRECATED - The test now always uses interactive mode")
    parser.add_argument("--random-data", action="store_true", help="Use random birth data")
    parser.add_argument("--confidence-threshold", type=float, default=0.8, help="Target confidence threshold for questionnaire (0.0-1.0)")
    parser.add_argument("--export-format", choices=["pdf", "png", "svg"], default="pdf", help="Format for chart export")

    # Add other export parameters (simplified for clarity)
    parser.add_argument("--export-path", default="./charts", help="Path to save exported charts")
    parser.add_argument("--export-dpi", type=int, default=300, help="DPI for exported charts")

    args = parser.parse_args()

    if args.non_interactive:
        print(TermColors.colorize("Warning: --non-interactive flag is deprecated. The test will run in interactive mode.", TermColors.YELLOW))

    # Execute the test flow with parsed arguments
    try:
        result = execute_test_flow(args)
        print("\nTest completed successfully!")
        print(f"Results: {result}")
        return result
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return {"error": str(e), "status": "failed"}

if __name__ == "__main__":
    main()
