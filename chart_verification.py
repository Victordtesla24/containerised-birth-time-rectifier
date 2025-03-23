import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

async def _verify_chart_with_openai(self, chart_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Verify chart data using OpenAI for astrological accuracy.

    This method sends chart data to OpenAI to validate astrological calculations,
    detect errors, and apply corrections if needed.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verified chart data with corrections applied, or None if verification failed
    """
    # Get OpenAI service for verification
    try:
        from ai_service.services.openai_service import get_openai_service
        openai_service = get_openai_service()

        if not openai_service:
            logger.warning("OpenAI service unavailable for chart verification")
            return None

        # Extract key chart information for the verification prompt
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", [])

        # Format the data for the verification prompt
        verification_data = {
            "chart_type": chart_data.get("chart_type", "tropical"),
            "planets": planets,
            "houses": houses,
            "angles": {
                "ascendant": chart_data.get("ascendant", {})
            }
        }

        # Add birth details if available
        if "birth_details" in chart_data:
            verification_data["birth_details"] = chart_data["birth_details"]

        # Request verification from OpenAI
        verification_result = await openai_service.verify_chart_calculations(verification_data)

        if not verification_result:
            logger.warning("OpenAI verification returned empty result")
            return None

        # Extract verification results
        verified = verification_result.get("verified", False)
        confidence = verification_result.get("confidence", 0)
        corrections = verification_result.get("corrections", [])

        # Apply corrections if available and verification passed
        if verified and corrections:
            logger.info(f"Applying {len(corrections)} corrections from OpenAI verification")

            # Apply each correction to the chart data
            for correction in corrections:
                if "object" in correction and "corrected_value" in correction:
                    object_name = correction["object"]
                    corrected_value = correction["corrected_value"]

                    # Apply correction to planets
                    if object_name in planets:
                        planets[object_name]["longitude"] = corrected_value
                        planets[object_name]["corrected_by"] = "openai_verification"

                    # Apply correction to houses
                    for house in houses:
                        if house.get("house") == object_name:
                            house["longitude"] = corrected_value
                            house["corrected_by"] = "openai_verification"

                    # Apply correction to ascendant if needed
                    if object_name == "ascendant" and "ascendant" in chart_data:
                        chart_data["ascendant"]["longitude"] = corrected_value
                        chart_data["ascendant"]["corrected_by"] = "openai_verification"

        # Add verification metadata
        chart_data["verification"] = {
            "verified_with_ai": True,
            "verification_date": datetime.now().isoformat(),
            "confidence": confidence,
            "status": "verified" if verified else "failed",
            "message": verification_result.get("message", ""),
            "corrections_applied": len(corrections) > 0
        }

        return chart_data

    except Exception as e:
        logger.error(f"Error during OpenAI chart verification: {e}")
        return None
