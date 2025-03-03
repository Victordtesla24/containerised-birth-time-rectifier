"""
Chart router for the Birth Time Rectifier API.
Handles all astrological chart related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, time
import logging
import pytz

from ai_service.services.chart_service import ChartService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
chart_router = APIRouter(tags=["charts"])

# Define models
class PlanetData(BaseModel):
    name: str
    sign: str
    house: int
    degree: float
    retrograde: bool = False
    longitude: Optional[float] = None
    latitude: Optional[float] = None

class HouseData(BaseModel):
    number: int
    sign: str
    degree: float

class AspectData(BaseModel):
    planet1: str
    planet2: str
    aspect_type: Optional[str] = "conjunction"
    orb: float

class ChartData(BaseModel):
    ascendant: Union[float, Dict[str, Union[str, float, None]]]
    planets: List[PlanetData]
    houses: List[HouseData]
    aspects: List[AspectData]

class ChartRequest(BaseModel):
    birthDate: str = Field(..., description="Birth date in format YYYY-MM-DD")
    birthTime: str = Field(..., description="Birth time in format HH:MM or HH:MM:SS")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude between -90 and 90 degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude between -180 and 180 degrees")
    timezone: str = Field(..., description="Timezone name (e.g. 'Asia/Kolkata', 'America/New_York')")
    chartType: str = Field(..., description="Chart type to generate: 'd1', 'd9', or 'all'")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options for chart calculation")

class ChartResponse(BaseModel):
    d1Chart: ChartData
    d9Chart: Optional[ChartData] = None

# Dependency to get ChartService instance
def get_chart_service():
    return ChartService()

@chart_router.post("/charts", response_model=ChartResponse)
async def generate_charts(
    request: ChartRequest,
    chart_service: ChartService = Depends(get_chart_service)
):
    """
    Generate astrological charts (D1 and optionally D9) for the given birth details.

    Returns both D1 and D9 charts if chartType is 'all'.
    """
    try:
        # Extract options if provided
        options = request.options or {}
        house_system = options.get("houseSystem", "placidus")
        ayanamsa = options.get("ayanamsa", 23.6647)  # Default to Lahiri ayanamsa
        node_type = options.get("nodeType", "true")  # Default to true node
        zodiac_type = options.get("zodiacType", "sidereal")  # Default to sidereal

        # Generate D1 chart
        d1_chart_data = chart_service.generate_chart(
            birth_date=request.birthDate,
            birth_time=request.birthTime,
            latitude=request.latitude,
            longitude=request.longitude,
            timezone=request.timezone,
            house_system=house_system,
            ayanamsa=ayanamsa,
            node_type=node_type,
            zodiac_type=zodiac_type
        )

        # Format the chart data for API response
        d1_chart = ChartData(
            ascendant=d1_chart_data["ascendant"],
            planets=[PlanetData(**planet) for planet in d1_chart_data["planets"]],
            houses=[HouseData(**house) for house in d1_chart_data["houses"]],
            aspects=[AspectData(**aspect) for aspect in d1_chart_data["aspects"]]
        )

        d9_chart = None
        if request.chartType in ['d9', 'all']:
            try:
                # For D9 chart, we'll need to implement navamsa calculation in the future
                # For now, we'll return the D1 chart as a placeholder
                logger.warning("D9 chart calculation not yet implemented, returning D1 chart as placeholder")
                d9_chart = d1_chart

                # TODO: Implement proper D9 calculation in chart_calculator.py
                # and then update this code to use it
            except Exception as e:
                logger.error(f"Error calculating D9 chart: {e}")
                # Continue without D9 chart

        return ChartResponse(
            d1Chart=d1_chart,
            d9Chart=d9_chart
        )

    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")

@chart_router.post("/chart/compare", response_model=Dict[str, Any])
async def compare_charts(
    original_chart: ChartRequest,
    rectified_chart: ChartRequest,
    chart_service: ChartService = Depends(get_chart_service)
):
    """
    Compare two charts and calculate the differences between them.
    """
    try:
        # Generate both charts
        original = await generate_charts(original_chart, chart_service)
        rectified = await generate_charts(rectified_chart, chart_service)

        # Convert the Pydantic models to dictionaries for comparison
        original_dict = original.d1Chart.model_dump()
        rectified_dict = rectified.d1Chart.model_dump()

        # Compare the charts
        differences = chart_service.compare_charts(original_dict, rectified_dict)

        return differences

    except Exception as e:
        logger.error(f"Error comparing charts: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing charts: {str(e)}")

@chart_router.get("/chart/options", response_model=Dict[str, Any])
async def get_chart_options():
    """
    Get available options for chart generation.
    """
    return {
        "houseSystems": [
            {"id": "placidus", "name": "Placidus"},
            {"id": "koch", "name": "Koch"},
            {"id": "equal", "name": "Equal"},
            {"id": "whole_sign", "name": "Whole Sign"},
            {"id": "porphyrius", "name": "Porphyry"},
            {"id": "regiomontanus", "name": "Regiomontanus"},
            {"id": "campanus", "name": "Campanus"}
        ],
        "ayanamsas": [
            {"id": 23.6647, "name": "Lahiri (Default)"},
            {"id": 24.0, "name": "Chitra Paksha"},
            {"id": 22.0, "name": "Raman"}
        ],
        "nodeTypes": [
            {"id": "true", "name": "True Node"},
            {"id": "mean", "name": "Mean Node"}
        ],
        "zodiacTypes": [
            {"id": "sidereal", "name": "Sidereal (Vedic)"},
            {"id": "tropical", "name": "Tropical (Western)"}
        ]
    }
