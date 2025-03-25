"""
Chart verification functionality for chart service.

This module provides functions for verifying astrological charts with OpenAI.
"""

import logging
import json
import asyncio
import time
import re
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from ai_service.api.services.openai import get_openai_service

logger = logging.getLogger(__name__)

# Make sure the verify_chart_with_openai function can be imported properly
__all__ = ['verify_chart_with_openai', 'create_verification_instructions',
           'prepare_chart_for_verification', 'apply_corrections',
           'validate_corrected_chart', 'get_zodiac_sign']

async def create_verification_instructions(chart_data: Dict[str, Any]) -> str:
    """
    Create instructions for chart verification.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verification instructions as a string
    """
    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", {})

    instructions = [
        "Verify the astrological chart data for accuracy and completeness:",
        "\nPlanetary Positions:",
    ]

    # Add planet data
    for planet, details in planets.items():
        sign = details.get("sign", "Unknown")
        longitude = details.get("longitude", 0)
        house = details.get("house", "Unknown")
        instructions.append(f"- {planet}: {sign} at {longitude:.2f}° in house {house}")

    # Add house data
    instructions.append("\nHouse Cusps:")
    for house, longitude in houses.items():
        if isinstance(longitude, dict):
            house_long = longitude.get("longitude", 0)
        else:
            house_long = float(longitude)
        sign = get_zodiac_sign(house_long)
        instructions.append(f"- House {house}: {sign} at {house_long % 30:.2f}°")

    # Add aspects if available
    if "aspects" in chart_data:
        instructions.append("\nMajor Aspects:")
        for aspect in chart_data.get("aspects", []):
            p1 = aspect.get("planet1", "Unknown")
            p2 = aspect.get("planet2", "Unknown")
            aspect_type = aspect.get("type", "Unknown")
            orb = aspect.get("orb", 0)
            instructions.append(f"- {p1} {aspect_type} {p2} (orb: {orb:.1f}°)")

    # Add verification instructions
    instructions.append("\nVerification Tasks:")
    instructions.append("1. Check if planets are in the correct signs")
    instructions.append("2. Verify house placements are consistent")
    instructions.append("3. Confirm aspects are calculated correctly")
    instructions.append("4. Check for any missing critical elements")

    return "\n".join(instructions)


def get_zodiac_sign(longitude: float) -> str:
    """
    Get the zodiac sign for a longitude value.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Zodiac sign name
    """
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    sign_index = int(longitude / 30) % 12
    return signs[sign_index]


async def _perform_verification_check(
    openai_service: Any,
    verification_prompt: str,
    chart_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform verification check with OpenAI.

    Args:
        openai_service: OpenAI service instance
        verification_prompt: Verification instructions
        chart_data: Chart data to verify

    Returns:
        Verification results

    Raises:
        RuntimeError: If verification check fails
    """
    if not openai_service:
        error_msg = "OpenAI service is not available for verification"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # Send request to OpenAI
        response = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert astrologer reviewing chart data for accuracy."},
                {"role": "user", "content": verification_prompt}
            ],
            temperature=0.2,
            max_tokens=600
        )

        # Extract verification result
        verification_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not verification_text:
            raise RuntimeError("Empty verification result from OpenAI")

        # Process verification result
        result = {
            "verified": True,
            "chart_id": chart_data.get("chart_id", str(uuid.uuid4())),
            "verification_result": verification_text,
            "issues": []
        }

        # Check for reported issues
        issue_pattern = r"issue|problem|error|incorrect|missing|invalid"
        if re.search(issue_pattern, verification_text.lower()):
            result["verified"] = False

            # Extract issues (simple approach, could be enhanced)
            issues = []
            for line in verification_text.split("\n"):
                if re.search(issue_pattern, line.lower()):
                    issues.append(line.strip())

            result["issues"] = issues

        return result

    except Exception as e:
        error_msg = f"Verification check failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

async def verify_chart_with_openai(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify chart data using OpenAI service.

    Args:
        chart_data: Chart data to verify

    Returns:
        Dictionary with verification results

    Raises:
        ValueError: If chart data is invalid
        RuntimeError: If OpenAI verification fails
    """
    if not chart_data:
        error_msg = "Cannot verify empty chart data"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Verifying chart data with OpenAI")

    # Get OpenAI service
    openai_service = get_openai_service()

    if not openai_service:
        error_msg = "OpenAI service is not available for verification"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Create verification instructions
    verification_prompt = await create_verification_instructions(chart_data)

    # Perform verification check
    try:
        verification_result = await _perform_verification_check(
            openai_service,
            verification_prompt,
            chart_data
        )

        logger.info("Chart verification completed successfully")
        return verification_result

    except Exception as e:
        error_msg = f"Chart verification failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

def prepare_chart_for_verification(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare chart data for verification by extracting relevant information.

    Args:
        chart_data: The complete chart data

    Returns:
        Dictionary with relevant chart data for verification
    """
    # Extract only the data needed for verification
    birth_details = chart_data.get("birth_details", {})
    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", {})
    aspects = chart_data.get("aspects", [])

    # Create verification data structure
    verification_data = {
        "birth_details": birth_details,
        "planets": planets,
        "houses": houses,
        "aspects": aspects
    }

    return verification_data

def apply_corrections(chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply corrections to chart data based on verification results.

    Args:
        chart_data: Original chart data
        corrections: List of corrections to apply

    Returns:
        Corrected chart data

    Raises:
        ValueError: If corrections cannot be applied
    """
    try:
        # Create a deep copy of the original chart data
        corrected_chart = json.loads(json.dumps(chart_data))

        # Process each correction
        for correction in corrections:
            correction_type = correction.get("type")
            target = correction.get("target")
            value = correction.get("value")

            if not correction_type or not target or value is None:
                logger.warning(f"Skipping invalid correction: {correction}")
                continue

            if correction_type == "planet_position":
                # Format: "planet_position.{planet_name}.{property}"
                parts = target.split(".")
                if len(parts) >= 3:
                    planet_name = parts[1]
                    property_name = parts[2]

                    # Check if planet exists
                    if planet_name in corrected_chart.get("planets", {}):
                        # Apply correction
                        corrected_chart["planets"][planet_name][property_name] = value
                        logger.info(f"Corrected {planet_name} {property_name} to {value}")
                    else:
                        logger.warning(f"Cannot correct nonexistent planet: {planet_name}")

            elif correction_type == "house_cusp":
                # Format: "house_cusp.{house_number}"
                parts = target.split(".")
                if len(parts) >= 2:
                    house_number = parts[1]

                    # Check if house exists
                    if house_number in corrected_chart.get("houses", {}):
                        # Apply correction
                        if isinstance(value, dict):
                            for k, v in value.items():
                                corrected_chart["houses"][house_number][k] = v
                            logger.info(f"Corrected House {house_number} with values: {value}")
                        else:
                            corrected_chart["houses"][house_number]["longitude"] = value
                            logger.info(f"Corrected House {house_number} longitude to {value}")
                    else:
                        logger.warning(f"Cannot correct nonexistent house: {house_number}")

            elif correction_type == "aspect":
                # Format: "aspect.{aspect_id}" or general aspect correction
                if "." in target:
                    aspect_id = target.split(".")[1]

                    # Find aspect by ID or by planets
                    aspect_found = False
                    for i, aspect in enumerate(corrected_chart.get("aspects", [])):
                        if (str(aspect.get("id")) == aspect_id or
                            (aspect.get("planet1") == value.get("planet1") and
                             aspect.get("planet2") == value.get("planet2"))):

                            # Update aspect
                            for k, v in value.items():
                                corrected_chart["aspects"][i][k] = v

                            aspect_found = True
                            logger.info(f"Corrected aspect between {value.get('planet1')} and {value.get('planet2')}")
                            break

                    if not aspect_found and isinstance(value, dict):
                        # Add new aspect
                        if all(k in value for k in ["planet1", "planet2", "type", "orb"]):
                            new_aspect = value.copy()
                            new_aspect["id"] = len(corrected_chart.get("aspects", [])) + 1
                            corrected_chart.setdefault("aspects", []).append(new_aspect)
                            logger.info(f"Added new aspect between {value.get('planet1')} and {value.get('planet2')}")
                        else:
                            logger.warning(f"Cannot add incomplete aspect: {value}")
                else:
                    # General aspect correction not supported
                    logger.warning(f"General aspect correction not supported: {correction}")

            elif correction_type == "birth_detail":
                # Format: "birth_detail.{detail_name}"
                parts = target.split(".")
                if len(parts) >= 2:
                    detail_name = parts[1]

                    # Apply correction to birth details
                    corrected_chart.setdefault("birth_details", {})[detail_name] = value
                    logger.info(f"Corrected birth detail {detail_name} to {value}")

            else:
                logger.warning(f"Unknown correction type: {correction_type}")

        return corrected_chart
    except Exception as e:
        error_msg = f"Failed to apply corrections: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def validate_corrected_chart(chart_data: Dict[str, Any]) -> bool:
    """
    Validate corrected chart data for integrity and consistency.

    Args:
        chart_data: Chart data to validate

    Returns:
        True if chart is valid, False otherwise
    """
    try:
        # Check if required sections exist
        if "planets" not in chart_data:
            logger.error("Validation failed: 'planets' section missing")
            return False

        if "houses" not in chart_data:
            logger.error("Validation failed: 'houses' section missing")
            return False

        # Check if key planets exist
        required_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        for planet in required_planets:
            if planet not in chart_data.get("planets", {}):
                logger.error(f"Validation failed: Required planet '{planet}' missing")
                return False

        # Check if houses are complete (1-12)
        for i in range(1, 13):
            house_key = str(i)
            if house_key not in chart_data.get("houses", {}):
                logger.error(f"Validation failed: House {house_key} missing")
                return False

        # Check longitude ranges
        for planet, data in chart_data.get("planets", {}).items():
            longitude = data.get("longitude")
            if longitude is not None and (longitude < 0 or longitude >= 360):
                logger.error(f"Validation failed: Invalid longitude {longitude} for {planet}")
                return False

        for house_key, data in chart_data.get("houses", {}).items():
            longitude = data.get("longitude")
            if longitude is not None and (longitude < 0 or longitude >= 360):
                logger.error(f"Validation failed: Invalid longitude {longitude} for House {house_key}")
                return False

        # Check aspects for validity
        for aspect in chart_data.get("aspects", []):
            if "planet1" not in aspect or "planet2" not in aspect:
                logger.error("Validation failed: Aspect missing planet references")
                return False

            if aspect.get("planet1") == aspect.get("planet2"):
                logger.error(f"Validation failed: Self-aspect for {aspect.get('planet1')}")
                return False

            orb = aspect.get("orb")
            if orb is not None and orb > 10:  # Maximum reasonable orb
                logger.error(f"Validation failed: Unreasonable orb {orb} for aspect")
                return False

        # If we reach here, chart passes basic validation
        return True

    except Exception as e:
        logger.error(f"Chart validation error: {e}")
        return False
