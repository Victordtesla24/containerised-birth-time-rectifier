"""
Test router for AI model integration.
Provides endpoints for testing OpenAI service and model routing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import asyncio

# Import services
from ..services.openai import OpenAIService
from ...models.unified_model import UnifiedRectificationModel

# Configure logging
logger = logging.getLogger(__name__)

# Create router with dual-registration pattern support
router = APIRouter(
    tags=["ai_integration_test"],
    responses={404: {"description": "Not found"}}
)

# Initialize OpenAI service
openai_service = None
try:
    openai_service = OpenAIService()
    logger.info("OpenAI service initialized in test router")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI service in test router: {e}")

# Initialize UnifiedRectificationModel
rectification_model = None
try:
    rectification_model = UnifiedRectificationModel()
    logger.info("Rectification model initialized in test router")
except Exception as e:
    logger.error(f"Failed to initialize rectification model in test router: {e}")

# Define request models
class ModelRoutingRequest(BaseModel):
    task_type: str = Field("explanation", description="Type of task (rectification, explanation, auxiliary)")
    prompt: str = Field("This is a test prompt.", description="Test prompt to send to the model")
    temperature: float = Field(0.7, description="Model temperature setting")
    max_tokens: int = Field(100, description="Maximum tokens to generate")

class ExplanationRequest(BaseModel):
    adjustment_minutes: int = Field(15, description="Birth time adjustment in minutes")
    reliability: str = Field("medium", description="Reliability rating (low, medium, high)")
    questionnaire_data: Dict[str, Any] = Field(default_factory=lambda: {"responses": []},
                                            description="Optional questionnaire data")

class RectificationRequest(BaseModel):
    birth_details: Dict[str, Any] = Field(..., description="Birth details")
    questionnaire_data: Dict[str, Any] = Field(default_factory=lambda: {"responses": []},
                                            description="Questionnaire responses")
    chart_data: Optional[Dict[str, Any]] = Field(None, description="Optional chart data")

@router.post("/test_model_routing", response_model=Dict[str, Any])
async def test_model_routing(data: ModelRoutingRequest):
    """
    Test endpoint for model routing logic.

    Allows testing different task types to verify the model routing logic.

    Args:
        data: ModelRoutingRequest containing:
            - task_type: Type of task ("rectification", "explanation", or other)
            - prompt: Test prompt to send to the model

    Returns:
        Dict with routing results and model details
    """
    if not openai_service:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service not available"
        )

    try:
        # Generate completion with the specified task type
        response = await openai_service.generate_completion(
            prompt=data.prompt,
            task_type=data.task_type,
            max_tokens=data.max_tokens,
            temperature=data.temperature
        )

        # Return the result
        return {
            "task_type": data.task_type,
            "model_used": response["model_used"],
            "result": response["content"],
            "token_usage": response["tokens"],
            "cost": response["cost"],
            "response_time": response["response_time"]
        }
    except Exception as e:
        logger.error(f"Error in test_model_routing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing model routing: {str(e)}"
        )

@router.post("/test_explanation", response_model=Dict[str, Any])
async def test_explanation_generation(data: ExplanationRequest):
    """
    Test endpoint to generate an astrological explanation using OpenAI.

    This demonstrates the integration between the OpenAI service and the rectification model.

    Args:
        data: ExplanationRequest containing:
            - adjustment_minutes: Birth time adjustment in minutes
            - reliability: Reliability rating
            - questionnaire_data: Optional questionnaire data

    Returns:
        Dict with the generated explanation and usage statistics
    """
    if not rectification_model:
        raise HTTPException(
            status_code=503,
            detail="Rectification model not available"
        )

    try:
        # Generate explanation using the rectification model
        explanation = await rectification_model._generate_explanation(
            adjustment_minutes=data.adjustment_minutes,
            reliability=data.reliability,
            questionnaire_data=data.questionnaire_data
        )

        # Return the result
        return {
            "explanation": explanation,
            "parameters": {
                "adjustment_minutes": data.adjustment_minutes,
                "reliability": data.reliability
            }
        }
    except Exception as e:
        logger.error(f"Error in test_explanation_generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating explanation: {str(e)}"
        )

@router.post("/test_rectification", response_model=Dict[str, Any])
async def test_rectification(data: RectificationRequest):
    """
    Test endpoint for birth time rectification.

    This tests the complete rectification process, including AI-based calculations
    if the OpenAI service is available.

    Args:
        data: RectificationRequest containing:
            - birth_details: Birth details
            - questionnaire_data: Questionnaire responses
            - chart_data: Optional chart data

    Returns:
        Dict with rectification results
    """
    if not rectification_model:
        raise HTTPException(
            status_code=503,
            detail="Rectification model not available"
        )

    if not data.birth_details:
        raise HTTPException(
            status_code=400,
            detail="Birth details are required"
        )

    try:
        # Perform rectification
        results = await rectification_model.rectify_birth_time(
            birth_details=data.birth_details,
            questionnaire_data=data.questionnaire_data,
            original_chart=data.chart_data
        )

        # Return the results
        return results
    except Exception as e:
        logger.error(f"Error in test_rectification: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing rectification: {str(e)}"
        )

@router.get("/usage_statistics", response_model=Dict[str, Any])
async def get_test_usage_statistics():
    """
    Get current OpenAI API usage statistics.

    This is useful for monitoring and cost tracking.

    Returns:
        Dict with usage statistics
    """
    if not openai_service:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service not available"
        )

    try:
        # Make a sample API call to ensure we have statistics to report
        # Only if there are no calls recorded yet
        stats = openai_service.get_usage_statistics()
        if stats["calls_made"] == 0:
            logger.info("No API calls recorded, generating a test call")
            await openai_service.generate_completion(
                prompt="This is a test prompt to generate usage statistics.",
                task_type="auxiliary",
                max_tokens=10,
                temperature=0.5
            )
            # Get updated statistics
            stats = openai_service.get_usage_statistics()

        return stats
    except Exception as e:
        logger.error(f"Error retrieving usage statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving usage statistics: {str(e)}"
        )
