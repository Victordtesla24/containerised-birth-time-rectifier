"""
Chart comparison models for the Birth Time Rectifier API.
Defines data structures for comparing original and rectified charts.
"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Union

class DifferenceType(str, Enum):
    """Types of differences that can be detected between charts"""
    ASCENDANT_SHIFT = "ascendant_shift"
    MIDHEAVEN_SHIFT = "midheaven_shift"
    PLANET_SIGN_CHANGE = "planet_sign_change"
    PLANET_HOUSE_TRANSITION = "planet_house_transition"
    ASPECT_CHANGE = "aspect_change"
    ASPECT_FORMATION = "aspect_formation"
    ASPECT_DISSOLUTION = "aspect_dissolution"
    HOUSE_CUSP_SHIFT = "house_cusp_shift"

class PlanetaryPosition(BaseModel):
    """Position of a planet in a sign with degree"""
    sign: str
    degree: float

class AspectData(BaseModel):
    """Data about an astrological aspect"""
    type: str
    orb: float
    applying: bool = False

class ChartDifference(BaseModel):
    """Represents a single difference between two charts"""
    type: DifferenceType
    description: str
    significance: float = Field(default=0.0, ge=0.0, le=1.0)

    # Fields used based on difference type
    planet: Optional[str] = None
    planet1: Optional[str] = None
    planet2: Optional[str] = None
    house: Optional[int] = None

    # Positions
    chart1_position: Optional[PlanetaryPosition] = None
    chart2_position: Optional[PlanetaryPosition] = None

    # House transitions
    chart1_house: Optional[int] = None
    chart2_house: Optional[int] = None

    # Aspect changes
    chart1_aspect: Optional[AspectData] = None
    chart2_aspect: Optional[AspectData] = None

class ChartComparisonRequest(BaseModel):
    """Request parameters for chart comparison"""
    chart1_id: str
    chart2_id: str
    comparison_type: str = "differences"  # Can be "differences", "full", "summary"
    include_significance: bool = True

class ChartComparisonResponse(BaseModel):
    """Response containing chart comparison results"""
    comparison_id: str
    chart1_id: str
    chart2_id: str
    comparison_type: str
    differences: List[ChartDifference]
    summary: Optional[str] = None
    overall_impact: Optional[float] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "comparison_id": "comp_123456789",
                "chart1_id": "chrt_987654321",
                "chart2_id": "chrt_987654322",
                "comparison_type": "differences",
                "differences": [
                    {
                        "type": "ascendant_shift",
                        "description": "The Ascendant has shifted within Virgo",
                        "significance": 0.8,
                        "chart1_position": {
                            "sign": "Virgo",
                            "degree": 15.32
                        },
                        "chart2_position": {
                            "sign": "Virgo",
                            "degree": 18.75
                        }
                    },
                    {
                        "type": "planet_house_transition",
                        "description": "Mars has moved from the 3rd house to the 4th house",
                        "significance": 0.65,
                        "planet": "Mars",
                        "chart1_house": 3,
                        "chart2_house": 4
                    }
                ],
                "overall_impact": 0.72
            }
        }
    )
