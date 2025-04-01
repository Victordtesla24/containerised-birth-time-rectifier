"""
AI-based verification for birth time rectification results.

This module provides functions to verify birth time rectification results
using AI models to ensure accurate and reliable output.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
import traceback
from datetime import datetime
import asyncio
import re

logger = logging.getLogger(__name__)

async def verify_with_openai(
    openai_service,
    prompt: str,
    max_retries: int = 3,
    retry_delay: int = 2,
    temperature: float = 0.2
) -> Tuple[bool, float, str]:
    """
    Verify chart or rectification result with OpenAI.

    Args:
        openai_service: OpenAI service instance
        prompt: Verification prompt
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries (seconds)
        temperature: OpenAI temperature parameter

    Returns:
        Tuple of (verified, confidence, message)

    Raises:
        ValueError: If OpenAI service is not available
        RuntimeError: If verification fails after max retries
    """
    if not openai_service:
        error_msg = "OpenAI service is required for verification"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Track retry attempts and last error
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Create proper message format for chat completion
            messages = [
                {"role": "system", "content": "You are an expert astrologer verifying birth time rectification."},
                {"role": "user", "content": prompt}
            ]

            # Call OpenAI with retry
            response = await openai_service.chat_completion(
                messages=messages,
                model="gpt-4",  # Use GPT-4 for best accuracy
                temperature=temperature,
                max_tokens=800
            )

            if not response:
                raise RuntimeError("Empty response from OpenAI")

            # Extract the content
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError("No content in OpenAI response")

            # Parse the verification result
            verification_result = await _parse_verification_response(content)
            return verification_result

        except Exception as e:
            # Log the error and retry
            retry_count += 1
            last_error = str(e)
            logger.warning(f"Verification attempt {retry_count} failed: {e}")

            if retry_count < max_retries:
                # Wait before retrying
                await asyncio.sleep(retry_delay)
            else:
                # Max retries reached
                logger.error(f"Verification failed after {max_retries} attempts: {last_error}")
                raise RuntimeError(f"OpenAI verification failed after {max_retries} attempts: {last_error}")

    # We should never reach here due to the exception in the else clause above
    raise RuntimeError(f"OpenAI verification failed: {last_error}")

async def _parse_verification_response(content: str) -> Tuple[bool, float, str]:
    """
    Parse verification response from OpenAI.

    Args:
        content: Response content from OpenAI

    Returns:
        Tuple of (verified, confidence, message)
    """
    # Default values
    verified = False
    confidence = 0.0
    message = ""

    try:
        # Try to parse as JSON first
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                verified = data.get("verified", False)

                # Safely convert confidence to float with proper error handling
                confidence_value = data.get("confidence", 0)
                if isinstance(confidence_value, (int, float)):
                    confidence = float(confidence_value)
                elif isinstance(confidence_value, str):
                    # Clean the string and handle various formats
                    clean_value = confidence_value.strip()
                    # Handle case where value is just a decimal point or empty
                    if not clean_value or clean_value == '.':
                        confidence = 70.0  # Default confidence
                    else:
                        try:
                            confidence = float(clean_value)
                        except ValueError:
                            # If decimal point is causing issues, try removing non-digits
                            digits_only = re.sub(r'[^\d.]', '', clean_value)
                            # Check again for just a decimal point
                            if not digits_only or digits_only == '.':
                                confidence = 70.0  # Default confidence
                            else:
                                try:
                                    confidence = float(digits_only)
                                except ValueError:
                                    confidence = 70.0  # Default confidence
                else:
                    confidence = 70.0  # Default for non-numeric types

                message = data.get("message", "")
                return verified, confidence, message
        except (json.JSONDecodeError, ValueError):
            pass

        # Look for verification indicators in text
        if "verified" in content.lower():
            verified = True
            confidence = 70.0  # Default confidence for text-based verification

        if "confidence" in content.lower():
            # Try to extract confidence value
            # Updated regex to better handle decimal points and various formats
            matches = re.findall(r"confidence[:\s]*(\d+(?:\.\d+)?)", content.lower())
            if matches:
                try:
                    # Clean the confidence value before conversion
                    cleaned_value = matches[0].strip()
                    # Handle case where value is just a decimal point or empty
                    if not cleaned_value or cleaned_value == '.':
                        confidence = 70.0  # Default value
                    else:
                        try:
                            confidence = float(cleaned_value)
                        except ValueError:
                            # If decimal point is causing issues, try with only digits
                            digits_only = re.sub(r'[^\d]', '', matches[0])
                            if digits_only:
                                try:
                                    confidence = float(digits_only)
                                    # If it's likely a percentage (>10), convert to 0-1 scale
                                    if confidence > 10:
                                        confidence = confidence / 100
                                except ValueError:
                                    confidence = 70.0  # Default if conversion fails
                            else:
                                confidence = 70.0  # Default if no digits found
                except Exception:
                    confidence = 70.0  # Default if any parsing error occurs

        # Extract message - use the whole content if nothing better found
        message = content

        return verified, confidence, message

    except Exception as e:
        logger.error(f"Error parsing verification response: {e}")
        raise RuntimeError(f"Failed to parse verification response: {e}")

def create_standardized_openai_prompt(
    birth_dt: datetime,
    rectified_dt: datetime,
    chart_data: Dict[str, Any],
    confidence: float,
    answers: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Create a standardized prompt for OpenAI verification.

    Args:
        birth_dt: Original birth datetime
        rectified_dt: Rectified birth datetime
        chart_data: Chart data for the rectified time
        confidence: Initial confidence score
        answers: Optional questionnaire answers
        events: Optional life events

    Returns:
        Formatted JSON prompt string
    """
    # Format answers and events for the prompt
    formatted_answers = []
    if answers:
        for answer in answers:
            question = answer.get("question", "")
            response = answer.get("answer", "")

            if not question and "text" in answer:
                question = answer.get("text", "")
            elif not question and "questionId" in answer:
                question = f"Question {answer.get('questionId', '')}"

            if not response and "response" in answer:
                response = answer.get("response", "")
            elif not response and "answer" in answer:
                response = answer.get("answer", "")

            if question and response:
                formatted_answers.append({
                    "question": question,
                    "response": response
                })

    formatted_events = []
    if events:
        for event in events:
            event_type = event.get("event_type", "general")
            date = event.get("date", "unknown")
            description = event.get("description", "")

            if date and description:
                formatted_events.append({
                    "type": event_type,
                    "date": date,
                    "description": description
                })

    # Create verification prompt data
    verification_data = {
        "task": "verify_birth_time_rectification",
        "original_birth_details": {
            "date": birth_dt.strftime("%Y-%m-%d"),
            "time": birth_dt.strftime("%H:%M:%S"),
        },
        "rectified_birth_details": {
            "date": rectified_dt.strftime("%Y-%m-%d"),
            "time": rectified_dt.strftime("%H:%M:%S"),
            "time_difference_minutes": (rectified_dt - birth_dt).total_seconds() / 60
        },
        "chart_data": {
            "ascendant": chart_data.get("angles", {}).get("Asc", {}).get("sign", "Unknown"),
            "midheaven": chart_data.get("angles", {}).get("MC", {}).get("sign", "Unknown"),
        },
        "initial_confidence": confidence,
        "answers_count": len(formatted_answers),
        "life_events_count": len(formatted_events),
        "instructions": [
            "Verify if the rectified birth time is astrologically reasonable",
            "Check if the time difference is justified by the chart data",
            "Assess if the confidence score is appropriate given the available information",
            "Provide feedback on the quality of the rectification",
            "Return a JSON object with verification results"
        ],
        "output_format": {
            "is_verified": "boolean indicating if the rectification passes verification",
            "confidence": "adjusted confidence score between 0-100",
            "notes": "explanation of verification result and any concerns"
        }
    }

    return json.dumps(verification_data)

async def verify_astrological_accuracy(chart_data: Dict[str, Any], openai_service: Any) -> Dict[str, Any]:
    """
    Verify the astrological accuracy of the chart using AI.

    Args:
        chart_data: The chart data to verify
        openai_service: OpenAI service for verification

    Returns:
        Dictionary with verification results

    Raises:
        ValueError: If OpenAI service is not provided or verification fails
    """
    if not openai_service:
        error_msg = "OpenAI service is required for astrological verification"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Create verification prompt
        messages = [
            {
                "role": "system",
                "content": "You are an expert astrologer specializing in verifying astrological charts. "
                          "Your task is to verify the accuracy of the chart data provided, including planetary positions, "
                          "house cusps, and aspects."
            },
            {
                "role": "user",
                "content": f"Please verify the following astrological chart data for accuracy. "
                           f"Check the planetary positions and house cusps if they appear correct. "
                           f"Chart data: {json.dumps(chart_data, indent=2)}"
            }
        ]

        # Call OpenAI API
        response = await openai_service.chat_completion(
            messages=messages,
            model="gpt-4",  # Use GPT-4 for best accuracy
            temperature=0.2,
            max_tokens=800
        )

        # Process response
        if not response or "choices" not in response or not response["choices"]:
            error_msg = "Invalid response from verification service"
            logger.error(error_msg)
            raise ValueError(error_msg)

        content = response["choices"][0]["message"]["content"]

        # Structure verification result
        verification_result = {
            "verified": True,  # Default to verified
            "confidence": 85,  # Default confidence
            "issues": [],
            "message": content
        }

        # Check for issues in the response
        content_lower = content.lower()
        if "incorrect" in content_lower or "error" in content_lower or "issue" in content_lower:
            verification_result["verified"] = False
            verification_result["confidence"] = 40

            # Extract issues (simplified approach)
            issues = []
            for line in content.split("\n"):
                if any(k in line.lower() for k in ["incorrect", "error", "issue", "problem"]):
                    issues.append(line.strip())

            verification_result["issues"] = issues

        return verification_result

    except Exception as e:
        error_msg = f"Error during astrological verification: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
