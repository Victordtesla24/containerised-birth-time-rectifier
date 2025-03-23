from typing import Optional
from ai_service.services.chart_service import ChartService
from ai_service.database.repositories import ChartRepository
from ai_service.services.openai_service import OpenAIService

def get_chart_service(chart_output_dir: Optional[str] = None) -> ChartService:
    """Factory function to get chart service instance."""
    # ChartService only accepts chart_output_dir parameter
    return ChartService(chart_output_dir=chart_output_dir)
