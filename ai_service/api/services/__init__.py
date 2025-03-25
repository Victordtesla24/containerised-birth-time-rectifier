"""
Services package for API operations.
"""

# Don't import at module level to prevent circular imports
__all__ = ["OpenAIService", "QuestionnaireService", "DynamicQuestionnaireService", "get_questionnaire_service"]

# Define __getattr__ to dynamically import when the attribute is accessed
def __getattr__(name):
    """
    Dynamically import modules when attributes are accessed.
    This prevents circular imports while maintaining the API.

    Args:
        name: The name of the attribute being accessed

    Returns:
        The requested attribute or raises AttributeError
    """
    if name == "OpenAIService":
        from .openai import OpenAIService as _OpenAIService
        return _OpenAIService
    elif name == "QuestionnaireService":
        from .questionnaire_service import QuestionnaireService as _QuestionnaireService
        return _QuestionnaireService
    elif name == "DynamicQuestionnaireService":
        from .dynamic_questionnaire_service import DynamicQuestionnaireService as _DynamicQuestionnaireService
        return _DynamicQuestionnaireService
    elif name == "get_questionnaire_service":
        from .questionnaire_service import get_questionnaire_service as _get_questionnaire_service
        return _get_questionnaire_service

    raise AttributeError(f"module {__name__} has no attribute {name}")
