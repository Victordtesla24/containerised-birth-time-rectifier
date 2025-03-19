"""
Chart Interpretation Router

This module provides endpoints for generating astrological chart interpretations.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import json
from datetime import datetime

# Import utilities and models
from ai_service.api.routers.consolidated_chart.utils import retrieve_chart

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["interpretation"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Chart not found or interpretation not available"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for response
class PlanetInterpretation(BaseModel):
    planet: str
    sign: str
    house: Optional[int]
    degree: Optional[float]
    description: str
    keywords: List[str]

class HouseInterpretation(BaseModel):
    house: int
    sign: str
    description: str
    keywords: List[str]

class AspectInterpretation(BaseModel):
    aspect_type: str
    planet1: str
    planet2: str
    description: str
    is_harmonious: bool
    strength: float

class InterpretationResponse(BaseModel):
    chart_id: str
    planets: List[PlanetInterpretation]
    houses: List[HouseInterpretation]
    aspects: Optional[List[AspectInterpretation]]
    overall: str
    personality_profile: Optional[str]
    life_path: Optional[str]
    interpretation: Optional[Dict[str, Any]]

@router.get("/interpretation", response_model=InterpretationResponse)
async def get_interpretation(
    chart_id: str = Query(..., description="ID of the chart to interpret")
):
    """
    Generate an astrological interpretation for a chart.

    This endpoint retrieves a chart by ID and provides a detailed interpretation
    of its planets, houses, aspects, and overall meaning.
    """
    try:
        # Log the request
        logger.info(f"Generating interpretation for chart: {chart_id}")

        # Retrieve the chart
        chart_data = retrieve_chart(chart_id)

        # Check if chart exists
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chart not found: {chart_id}"
            )

        # Handle the case when chart_data is a string (JSON)
        if isinstance(chart_data, str):
            try:
                chart_data = json.loads(chart_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse chart data as JSON: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse chart data: {str(e)}"
                )

        # Extract planets from chart data
        planets_data = []
        if "planets" in chart_data:
            if isinstance(chart_data["planets"], dict):
                # Handle dictionary format (name: data pairs)
                for planet_name, planet_info in chart_data["planets"].items():
                    planet_info["name"] = planet_name
                    planets_data.append(planet_info)
            elif isinstance(chart_data["planets"], list):
                # Handle list format (list of planet objects)
                planets_data = chart_data["planets"]

        # Extract houses data
        houses_data = []
        if "houses" in chart_data:
            if isinstance(chart_data["houses"], dict):
                # Handle dictionary format (house_number: data pairs)
                for house_num, house_info in chart_data["houses"].items():
                    house_info["house_number"] = int(house_num)
                    houses_data.append(house_info)
            elif isinstance(chart_data["houses"], list):
                # Handle list format (list of house objects)
                houses_data = chart_data["houses"]

        # Extract aspects data
        aspects_data = chart_data.get("aspects", [])

        # Create planet interpretations
        planets = []
        for planet in planets_data:
            planet_name = planet.get("name", "Unknown")
            sign = planet.get("sign", "Unknown")

            planets.append(PlanetInterpretation(
                planet=planet_name,
                sign=sign,
                house=planet.get("house"),
                degree=planet.get("degree", planet.get("longitude")),
                description=f"{planet_name} in {sign} emphasizes qualities of {get_sign_keywords(sign)}.",
                keywords=get_planet_keywords(planet_name)
            ))

        # Create house interpretations
        houses = []
        for house in houses_data:
            house_num = house.get("house_number", 0)
            sign = house.get("sign", "Unknown")

            houses.append(HouseInterpretation(
                house=house_num,
                sign=sign,
                description=f"House {house_num} in {sign} indicates {get_house_description(house_num)}.",
                keywords=get_house_keywords(house_num)
            ))

        # Create aspect interpretations
        aspects = []
        for aspect in aspects_data:
            aspect_type = aspect.get("aspect", aspect.get("type", "Unknown"))
            planet1 = aspect.get("planet1", "Unknown")
            planet2 = aspect.get("planet2", "Unknown")

            aspects.append(AspectInterpretation(
                aspect_type=aspect_type,
                planet1=planet1,
                planet2=planet2,
                description=f"The {aspect_type} between {planet1} and {planet2} suggests {get_aspect_description(aspect_type)}.",
                is_harmonious=is_harmonious_aspect(aspect_type),
                strength=aspect.get("orb", 5.0)
            ))

        # Create overall interpretation
        overall = "This birth chart reveals a unique individual with a complex blend of energies. The chart's key themes suggest a personality that balances intellectual curiosity with emotional depth."

        # Create personality profile
        personality_profile = "Your chart indicates a natural ability to balance multiple perspectives. You likely have strong communication skills and a desire for harmony in relationships. Your analytical abilities are complemented by intuitive insights."

        # Create life path interpretation
        life_path = "Your life path appears to involve developing mastery in communication and relationship building. There may be challenges around balancing personal freedom with responsibility to others. Your growth comes through embracing both structure and spontaneity."

        # Return the interpretation
        return InterpretationResponse(
            chart_id=chart_id,
            planets=planets,
            houses=houses,
            aspects=aspects,
            overall=overall,
            personality_profile=personality_profile,
            life_path=life_path,
            interpretation={
                "summary": overall,
                "personality": personality_profile,
                "life_path": life_path,
                "planet_details": [p.dict() for p in planets],
                "house_details": [h.dict() for h in houses],
                "aspect_details": [a.dict() for a in aspects]
            }
        )

    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error generating interpretation: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate interpretation: {str(e)}"
        )


def get_planet_keywords(planet: str) -> List[str]:
    """Get keywords for a planet"""
    keywords = {
        "Sun": ["identity", "ego", "vitality", "purpose"],
        "Moon": ["emotions", "instincts", "nurturing", "subconscious"],
        "Mercury": ["communication", "intellect", "perception", "learning"],
        "Venus": ["love", "beauty", "harmony", "values"],
        "Mars": ["action", "desire", "energy", "courage"],
        "Jupiter": ["expansion", "growth", "optimism", "philosophy"],
        "Saturn": ["discipline", "responsibility", "limitations", "maturity"],
        "Uranus": ["innovation", "rebellion", "originality", "awakening"],
        "Neptune": ["spirituality", "imagination", "compassion", "transcendence"],
        "Pluto": ["transformation", "power", "regeneration", "intensity"],
        "Rahu": ["obsession", "expansion", "desire", "ambition"],
        "Ketu": ["liberation", "spirituality", "isolation", "loss"],
        "Ascendant": ["self-image", "appearance", "identity", "approach to life"]
    }
    return keywords.get(planet, ["energy", "influence", "expression"])

def get_house_description(house: int) -> str:
    """Get description for a house"""
    descriptions = {
        1: "your self-image and personal identity",
        2: "your resources, values, and self-worth",
        3: "your communication style and learning approach",
        4: "your foundation, home, and family connections",
        5: "your creative expression and joy",
        6: "your work habits, health, and service to others",
        7: "your partnerships and one-on-one relationships",
        8: "your areas of transformation and shared resources",
        9: "your higher education, philosophy, and expansion",
        10: "your career path and public reputation",
        11: "your social groups, hopes, and humanitarian efforts",
        12: "your unconscious patterns and spiritual growth"
    }
    return descriptions.get(house, "an important area of life focus")

def get_house_keywords(house: int) -> List[str]:
    """Get keywords for a house"""
    keywords = {
        1: ["identity", "appearance", "first impressions", "beginnings"],
        2: ["possessions", "values", "money", "security"],
        3: ["communication", "siblings", "learning", "local environment"],
        4: ["home", "family", "roots", "emotional foundation"],
        5: ["creativity", "romance", "children", "pleasure"],
        6: ["work", "health", "routines", "service"],
        7: ["partnerships", "contracts", "open enemies", "balance"],
        8: ["transformation", "shared resources", "intimacy", "regeneration"],
        9: ["higher learning", "travel", "philosophy", "expansion"],
        10: ["career", "authority", "public image", "achievements"],
        11: ["friends", "groups", "hopes", "humanitarian concerns"],
        12: ["unconscious", "spirituality", "hidden things", "self-undoing"]
    }
    return keywords.get(house, ["life area", "experience", "focus"])

def get_aspect_description(aspect: str) -> str:
    """Get description for an aspect"""
    descriptions = {
        "Conjunction": "a powerful merging of energies that intensifies their expression",
        "Sextile": "harmonious opportunities for growth and development",
        "Square": "tension that creates motivation for change and overcoming challenges",
        "Trine": "natural talents and easy flow of compatible energies",
        "Opposition": "awareness through relationships and the integration of polarities",
        "Quincunx": "adjustments needed between energies that don't naturally work together",
        "conjunction": "a powerful merging of energies that intensifies their expression",
        "sextile": "harmonious opportunities for growth and development",
        "square": "tension that creates motivation for change and overcoming challenges",
        "trine": "natural talents and easy flow of compatible energies",
        "opposition": "awareness through relationships and the integration of polarities",
        "quincunx": "adjustments needed between energies that don't naturally work together"
    }
    return descriptions.get(aspect, "a significant relationship between these planetary energies")

def is_harmonious_aspect(aspect: str) -> bool:
    """Determine if an aspect is harmonious"""
    harmonious = ["Trine", "Sextile", "trine", "sextile"]
    neutral = ["Conjunction", "conjunction"]
    return aspect in harmonious
