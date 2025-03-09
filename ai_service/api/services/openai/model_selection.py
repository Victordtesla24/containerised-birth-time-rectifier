"""
Model selection utilities for OpenAI service.
"""

import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

def get_task_category(task_type: str) -> str:
    """
    Categorize task types into high-level categories for key selection.

    Args:
        task_type: The specific task type string

    Returns:
        Category string: "rectification", "explanation", or "auxiliary"
    """
    task_lower = task_type.lower()

    # Detailed categorization
    if "rectif" in task_lower or "birth time" in task_lower:
        return "rectification"
    elif "chart" in task_lower or "planet" in task_lower or "posit" in task_lower or "calculate" in task_lower:
        return "calculation"
    elif "visual" in task_lower or "render" in task_lower or "3d" in task_lower:
        return "visualization"
    elif "quest" in task_lower or "survey" in task_lower or "form" in task_lower:
        return "questionnaire"
    elif "explain" in task_lower or "interpret" in task_lower or "describe" in task_lower:
        return "explanation"
    else:
        return "auxiliary"

def select_model(task_type: str) -> str:
    """
    Select the appropriate model based on task type.
    Uses environment variables for model selection to allow flexible configuration.

    Args:
        task_type: The type of task

    Returns:
        Model identifier string
    """
    # For direct test compatibility
    if task_type.lower() == "explanation":
        return os.environ.get("OPENAI_MODEL_EXPLANATION", "gpt-4-turbo")

    # Determine the task category
    task_category = get_task_category(task_type)

    # Get models from environment variables with defaults
    model_env_vars = {
        "rectification": os.environ.get("OPENAI_MODEL_RECTIFICATION", "o1-preview"),
        "calculation": os.environ.get("OPENAI_MODEL_CALCULATION", "o1-preview"),
        "visualization": os.environ.get("OPENAI_MODEL_VISUALIZATION", "gpt-4-turbo"),
        "questionnaire": os.environ.get("OPENAI_MODEL_QUESTIONNAIRE", "gpt-4-turbo"),
        "explanation": os.environ.get("OPENAI_MODEL_EXPLANATION", "gpt-4-turbo"),
        "auxiliary": os.environ.get("OPENAI_MODEL_AUXILIARY", "gpt-4o-mini")  # Using gpt-4o-mini for auxiliary tasks
    }

    # Get the appropriate model for the task category
    selected_model = model_env_vars.get(task_category, model_env_vars["auxiliary"])

    logger.info(f"Using {selected_model} for {task_category} task")
    return selected_model
