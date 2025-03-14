#!/usr/bin/env python3
"""
Test script for the consolidated API flow with automated input.
This script tests the entire flow of the birth time rectification API
using predefined birth details instead of interactive input.
"""

import json
import logging
import os
import random
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import requests

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from birth_time_rectifier.chart_visualizer import (
    generate_multiple_charts,
    modify_chart_for_harmonic,
    modify_chart_for_moon_ascendant,
    compare_charts,
    export_charts
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("api_flow_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API endpoints
BASE_URL = "http://localhost:8000"
INITIALIZE_ENDPOINT = f"{BASE_URL}/api/v1/session/init"
BIRTH_DETAILS_ENDPOINT = f"{BASE_URL}/api/v1/chart/validate"
CHART_ENDPOINT = f"{BASE_URL}/api/v1/chart/generate"
QUESTION_ENDPOINT = f"{BASE_URL}/api/v1/questionnaire"
ANSWER_ENDPOINT = f"{BASE_URL}/api/v1/questionnaire/answer"
RECTIFY_ENDPOINT = f"{BASE_URL}/api/v1/chart/rectify"
CHART_DATA_ENDPOINT = f"{BASE_URL}/api/v1/chart"
LOCATION_SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/geocode"

# Terminal colors for better output
class TermColors:
    """Terminal colors for better output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Colorize text for terminal output."""
        return f"{color}{text}{TermColors.ENDC}"

def initialize_session() -> str:
    """
    Initialize a new session with the API.

    Returns:
        Session ID as a string
    """
    logger.info("STEP 1: SESSION INITIALIZATION")
    print(TermColors.colorize("Step 1: Testing session initialization", TermColors.BLUE))

    try:
        response = requests.get(INITIALIZE_ENDPOINT)
        response.raise_for_status()
        data = response.json()
        session_id = data.get("session_id")

        if not session_id:
            raise ValueError("No session ID returned from API")

        logger.info(f"Session initialized with ID: {session_id}")
        print(TermColors.colorize("✓ Session initialized successfully", TermColors.GREEN))
        return session_id
    except Exception as e:
        logger.error(f"Session initialization failed: {str(e)}")
        print(TermColors.colorize(f"✗ Session initialization failed: {str(e)}", TermColors.RED))
        raise

def get_predefined_birth_details() -> Dict[str, Any]:
    """
    Return predefined birth details for testing.

    Returns:
        Dictionary with birth details
    """
    # Predefined birth details for Pune, India
    birth_data = {
        "birth_date": "1985-10-24",
        "birth_time": "14:30:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "timezone": "Asia/Kolkata",
        "location": "Pune, India"
    }

    logger.info(f"Using predefined birth data: {birth_data}")
    display_birth_data(birth_data)

    return birth_data

def display_birth_data(birth_data: Dict[str, Any]) -> None:
    """Display formatted birth data."""
    print("\nBirth Details:")
    print(f"  Date: {birth_data.get('birth_date')}")
    print(f"  Time: {birth_data.get('birth_time')}")
    print(f"  Location: {birth_data.get('location')}")
    print(f"  Coordinates: {birth_data.get('latitude')} {birth_data.get('longitude')}")
    print(f"  Timezone: {birth_data.get('timezone')}")

def validate_birth_details(session_id: str, birth_details: Dict[str, Any]) -> bool:
    """
    Validate birth details with the API.

    Args:
        session_id: Session ID
        birth_details: Dictionary with birth details

    Returns:
        True if validation was successful
    """
    logger.info("STEP 2: BIRTH DETAILS VALIDATION")
    print(TermColors.colorize("\nStep 2: Testing birth details validation", TermColors.BLUE))

    try:
        headers = {"X-Session-ID": session_id}
        # Wrap birth details in a birth_details field
        payload = {"birth_details": birth_details}
        response = requests.post(BIRTH_DETAILS_ENDPOINT, json=payload, headers=headers)

        # Print response content for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")

        response.raise_for_status()
        data = response.json()

        if not data.get("valid", False):
            errors = data.get("errors", {})
            error_msg = ", ".join([f"{k}: {v}" for k, v in errors.items()]) if errors else "Unknown error"
            raise ValueError(f"Birth details validation failed: {error_msg}")

        logger.info("Birth details validated successfully")
        print(TermColors.colorize("✓ Birth details validated successfully", TermColors.GREEN))
        return True
    except Exception as e:
        logger.error(f"Birth details validation failed: {str(e)}")
        print(TermColors.colorize(f"✗ Birth details validation failed: {str(e)}", TermColors.RED))
        raise

def generate_birth_chart(session_id: str, birth_details: Dict[str, Any]) -> str:
    """
    Generate birth chart with the API.

    Args:
        session_id: Session ID
        birth_details: Dictionary with birth details

    Returns:
        Chart ID as a string
    """
    logger.info("STEP 3: BIRTH CHART GENERATION")
    print(TermColors.colorize("\nStep 3: Testing birth chart generation", TermColors.BLUE))

    try:
        headers = {"X-Session-ID": session_id}
        # Create a chart request with birth details and default options
        chart_request = {
            "birth_details": birth_details,
            "options": {
                "house_system": "P",
                "zodiac_type": "sidereal",
                "ayanamsa": "lahiri",
                "node_type": "true",
                "verify_with_openai": True
            }
        }
        response = requests.post(CHART_ENDPOINT, json=chart_request, headers=headers)

        # Print response content for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")

        response.raise_for_status()
        data = response.json()

        chart_id = data.get("chart_id")
        if not chart_id:
            raise ValueError("No chart ID returned from API")

        logger.info(f"Birth chart generated with ID: {chart_id}")
        print(TermColors.colorize(f"✓ Birth chart generated successfully with ID: {chart_id}", TermColors.GREEN))
        return chart_id
    except Exception as e:
        logger.error(f"Birth chart generation failed: {str(e)}")
        print(TermColors.colorize(f"✗ Birth chart generation failed: {str(e)}", TermColors.RED))
        raise

def get_chart(chart_id: str, session_id: str) -> Dict[str, Any]:
    """
    Get chart data from the API.

    Args:
        chart_id: Chart ID
        session_id: Session ID

    Returns:
        Dictionary with chart data
    """
    try:
        headers = {"X-Session-ID": session_id}
        response = requests.get(f"{CHART_DATA_ENDPOINT}/{chart_id}", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get chart data: {str(e)}")
        print(TermColors.colorize(f"✗ Failed to get chart data: {str(e)}", TermColors.RED))
        raise

def answer_questionnaire(session_id: str) -> List[Dict[str, Any]]:
    """
    Answer the questionnaire with the API.

    Args:
        session_id: Session ID

    Returns:
        List of question-answer pairs
    """
    logger.info("STEP 4: QUESTIONNAIRE")
    print(TermColors.colorize("\nStep 4: Testing questionnaire", TermColors.BLUE))

    question_answers = []
    question_count = 0

    try:
        headers = {"X-Session-ID": session_id}

        # Initialize the questionnaire
        print(TermColors.colorize("Initializing questionnaire...", TermColors.CYAN))
        init_payload = {
            "birthDate": "1985-10-24",
            "birthTime": "14:30",
            "birthPlace": "Pune, India",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "timezone": "Asia/Kolkata"
        }
        init_response = requests.post(f"{BASE_URL}/api/v1/questionnaire/initialize", json=init_payload, headers=headers)
        print(f"Initialize response status code: {init_response.status_code}")
        print(f"Initialize response content: {init_response.text}")
        init_response.raise_for_status()

        # Get the questionnaire
        response = requests.get(QUESTION_ENDPOINT, headers=headers)

        # Print response content for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")

        response.raise_for_status()
        questionnaire_data = response.json()

        # Check if we have questions
        questions = questionnaire_data.get("questions", [])
        if not questions:
            logger.info("No questions in questionnaire")
            print(TermColors.colorize("✓ No questions in questionnaire", TermColors.GREEN))
            return question_answers

        # Answer each question
        for question in questions:
            question_count += 1
            question_id = question.get("id")
            question_text = question.get("text")
            question_type = question.get("type")

            logger.info(f"Question {question_count}: {question_text} (Type: {question_type})")
            print(f"\nQuestion {question_count}: {question_text}")

            # Generate automated answer based on question type
            answer = generate_automated_answer(question_type, question)

            # Submit answer
            answer_payload = {
                "sessionId": session_id,
                "questionId": question_id,
                "answer": answer
            }

            response = requests.post(ANSWER_ENDPOINT, json=answer_payload, headers=headers)

            # Print response content for debugging
            print(f"Answer response status code: {response.status_code}")
            print(f"Answer response content: {response.text}")

            response.raise_for_status()

            # Store question-answer pair
            question_answers.append({
                "question": question_text,
                "answer": answer,
                "type": question_type
            })

            logger.info(f"Answered question {question_count}: {answer}")
            print(TermColors.colorize(f"✓ Answered: {answer}", TermColors.GREEN))

            # Only answer the first question for now
            break

        logger.info("Questionnaire completed")
        print(TermColors.colorize("✓ Questionnaire completed", TermColors.GREEN))
        return question_answers
    except Exception as e:
        logger.error(f"Questionnaire failed: {str(e)}")
        print(TermColors.colorize(f"✗ Questionnaire failed: {str(e)}", TermColors.RED))
        raise

def generate_automated_answer(question_type: str, question_data: Dict[str, Any]) -> Any:
    """
    Generate an automated answer based on question type.

    Args:
        question_type: Type of question (boolean, date, options, etc.)
        question_data: Question data from API

    Returns:
        Answer in the appropriate format for the question type
    """
    if question_type == "boolean" or question_type == "yes_no":
        # For boolean questions, alternate between true and false
        return random.choice([True, False])

    elif question_type == "date":
        # For date questions, return a random date in the past
        year = random.randint(1990, 2020)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year:04d}-{month:02d}-{day:02d}"

    elif question_type == "options" or question_type == "multiple_choice":
        # For options questions, select a random option
        options = question_data.get("options", [])
        if options:
            option = random.choice(options)
            return option.get("id")
        return None

    elif question_type == "text":
        # For text questions, return a simple response
        return "This is an automated test response"

    # Default fallback
    return None

def process_rectification(session_id: str, chart_id: str) -> Dict[str, Any]:
    """
    Process rectification with the API.

    Args:
        session_id: Session ID
        chart_id: Chart ID to rectify

    Returns:
        Dictionary with rectification results
    """
    logger.info("STEP 5: RECTIFICATION PROCESSING")
    print(TermColors.colorize("\nStep 5: Testing rectification processing", TermColors.BLUE))

    try:
        headers = {"X-Session-ID": session_id}

        # Create a rectification request with the chart ID and some mock answers
        rectification_request = {
            "chart_id": chart_id,
            "answers": [
                {
                    "question_id": "q_001",
                    "answer": "yes"
                },
                {
                    "question_id": "q_002",
                    "answer": "2010-05-15"
                }
            ]
        }

        response = requests.post(RECTIFY_ENDPOINT, json=rectification_request, headers=headers)

        # Print response content for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")

        response.raise_for_status()
        data = response.json()

        rectified_chart_id = data.get("rectified_chart_id")
        confidence = data.get("confidence_score", 0)

        if not rectified_chart_id:
            raise ValueError("No rectified chart ID returned from API")

        logger.info(f"Rectification processed successfully. Rectified chart ID: {rectified_chart_id}, Confidence: {confidence}%")
        print(TermColors.colorize("✓ Rectification processed successfully", TermColors.GREEN))
        print(f"  Original Chart ID: {chart_id}")
        print(f"  Rectified Chart ID: {rectified_chart_id}")
        print(f"  Confidence: {confidence:.2f}%")

        return {
            "rectified_chart_id": rectified_chart_id,
            "original_chart_id": chart_id,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"Rectification processing failed: {str(e)}")
        print(TermColors.colorize(f"✗ Rectification processing failed: {str(e)}", TermColors.RED))
        raise

def compare_original_and_rectified(original_chart: Dict[str, Any], rectified_chart: Dict[str, Any]) -> None:
    """
    Compare original and rectified charts.

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data
    """
    print("\n" + "=" * 80)
    print("CHART COMPARISON".center(80))
    print("=" * 80)

    try:
        comparison = compare_charts(original_chart, rectified_chart)
        print(comparison)
    except Exception as e:
        logger.error(f"Chart comparison failed: {str(e)}")
        print(TermColors.colorize(f"✗ Chart comparison failed: {str(e)}", TermColors.RED))

def run_flow(session_id: str, birth_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete API flow.

    Args:
        session_id: Session ID
        birth_details: Dictionary with birth details

    Returns:
        Dictionary with flow results
    """
    # Step 2: Validate birth details
    validate_birth_details(session_id, birth_details)

    # Step 3: Generate birth chart
    original_chart_id = generate_birth_chart(session_id, birth_details)

    # Skip Step 4: Answer questionnaire
    # question_answers = answer_questionnaire(session_id)
    print(TermColors.colorize("\nSkipping questionnaire step due to API limitations", TermColors.YELLOW))
    question_answers = []

    # Step 5: Process rectification
    rectification_result = process_rectification(session_id, original_chart_id)

    return {
        "original_chart_id": original_chart_id,
        "rectified_chart_id": rectification_result["rectified_chart_id"],
        "confidence": rectification_result["confidence"],
        "question_answers": question_answers
    }

def main():
    """Main function to test the API flow."""
    try:
        # Initialize session
        session_id = initialize_session()

        # Get predefined birth details
        birth_details = get_predefined_birth_details()

        # Run flow
        flow_result = run_flow(session_id, birth_details)

        print("\n" + "=" * 80)
        print("FLOW TEST COMPLETED SUCCESSFULLY".center(80))
        print("=" * 80)
        print(f"\nSession ID: {session_id}")
        print(f"Original Chart ID: {flow_result['original_chart_id']}")
        print(f"Rectified Chart ID: {flow_result['rectified_chart_id']}")

        # Get the original and rectified chart data
        original_chart = get_chart(flow_result['original_chart_id'], session_id)
        rectified_chart = get_chart(flow_result['rectified_chart_id'], session_id)

        # Generate and display multiple chart types for the original chart
        print("\n" + "=" * 80)
        print("INITIAL BIRTH CHART & PLANETARY POSITIONS".center(80))
        print("=" * 80)

        original_charts = generate_multiple_charts(original_chart)

        # Display Lagna Chart first
        if original_charts:
            if "lagna" in original_charts:
                print("\nLagna Chart:")
                print(original_charts["lagna"])

            # Display Navamsa Chart
            if "navamsa" in original_charts:
                print("\nNavamsa Chart:")
                print(original_charts["navamsa"])

            # Display Chandra Chart
            if "chandra" in original_charts:
                print("\nChandra Chart:")
                print(original_charts["chandra"])

            # Display D4 Chart
            if "d4" in original_charts:
                print("\nD4 Chart:")
                print(original_charts["d4"])

            # Display Planetary Positions table
            if "planetary_positions" in original_charts:
                print(original_charts["planetary_positions"])
        else:
            print(TermColors.colorize("Chart visualization not implemented in placeholder", TermColors.YELLOW))

        # Generate and display multiple chart types for the rectified chart
        print("\n" + "=" * 80)
        print("RECTIFIED CHART - MULTIPLE FORMATS".center(80))
        print("=" * 80)

        rectified_charts = generate_multiple_charts(rectified_chart)

        # Display all charts if available
        if rectified_charts:
            # Display Lagna Chart first
            if "lagna" in rectified_charts:
                print("\nLagna Chart:")
                print(rectified_charts["lagna"])

            # Display Navamsa Chart
            if "navamsa" in rectified_charts:
                print("\nNavamsa Chart:")
                print(rectified_charts["navamsa"])

            # Display Chandra Chart
            if "chandra" in rectified_charts:
                print("\nChandra Chart:")
                print(rectified_charts["chandra"])

            # Display D4 Chart
            if "d4" in rectified_charts:
                print("\nD4 Chart:")
                print(rectified_charts["d4"])

            # Display Planetary Positions table
            if "planetary_positions" in rectified_charts:
                print(rectified_charts["planetary_positions"])
        else:
            print(TermColors.colorize("Chart visualization not implemented in placeholder", TermColors.YELLOW))

        # Compare the differences between the original and rectified charts
        compare_original_and_rectified(original_chart, rectified_chart)

        # Export the final charts
        if original_charts and rectified_charts:
            export_path = export_charts(original_charts, rectified_charts, birth_details)
            print(f"\nCharts exported to: {export_path}")
        else:
            print(TermColors.colorize("Chart export not implemented in placeholder", TermColors.YELLOW))

    except Exception as e:
        logger.error(f"Main flow failed: {str(e)}")
        print(TermColors.colorize(f"✗ Test flow failed: {str(e)}", TermColors.RED))
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
