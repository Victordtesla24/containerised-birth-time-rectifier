"""
Test router for AI model integration.
Provides endpoints for testing OpenAI service and model routing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List
import logging
import asyncio

# Import services
from ..services.openai_service import OpenAIService
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

@router.post("/test_model_routing", response_model=Dict[str, Any])
async def test_model_routing(data: Dict[str, Any]):
    """
    Test endpoint for model routing logic.

    Allows testing different task types to verify the model routing logic.

    Args:
        data: Dict containing:
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

    task_type = data.get("task_type", "explanation")
    prompt = data.get("prompt", "This is a test prompt.")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 100)

    try:
        # Generate completion with the specified task type
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type=task_type,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Return the result
        return {
            "task_type": task_type,
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
async def test_explanation_generation(data: Dict[str, Any]):
    """
    Test endpoint to generate an astrological explanation using OpenAI.

    This demonstrates the integration between the OpenAI service and the rectification model.

    Args:
        data: Dict containing:
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

    # Get parameters with defaults
    adjustment_minutes = data.get("adjustment_minutes", 15)
    reliability = data.get("reliability", "medium")
    questionnaire_data = data.get("questionnaire_data", {"responses": []})

    try:
        # Generate explanation using the rectification model
        explanation = await rectification_model._generate_explanation(
            adjustment_minutes=adjustment_minutes,
            reliability=reliability,
            questionnaire_data=questionnaire_data
        )

        # Return the result
        return {
            "explanation": explanation,
            "parameters": {
                "adjustment_minutes": adjustment_minutes,
                "reliability": reliability
            }
        }
    except Exception as e:
        logger.error(f"Error in test_explanation_generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating explanation: {str(e)}"
        )

@router.post("/test_rectification", response_model=Dict[str, Any])
async def test_rectification(data: Dict[str, Any]):
    """
    Test endpoint for birth time rectification.

    This tests the complete rectification process, including AI-based calculations
    if the OpenAI service is available.

    Args:
        data: Dict containing:
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

    # Get parameters
    birth_details = data.get("birth_details", {})
    questionnaire_data = data.get("questionnaire_data", {"responses": []})
    chart_data = data.get("chart_data")

    if not birth_details:
        raise HTTPException(
            status_code=400,
            detail="Birth details are required"
        )

    try:
        # Perform rectification
        results = await rectification_model.rectify_birth_time(
            birth_details=birth_details,
            questionnaire_data=questionnaire_data,
            original_chart=chart_data
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
async def get_usage_statistics():
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
        # Get usage statistics
        stats = openai_service.get_usage_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving usage statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving usage statistics: {str(e)}"
        )
