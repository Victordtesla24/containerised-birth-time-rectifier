"""
Chart exporting functionality for chart service.

This module provides functions for exporting astrological charts in various formats.
"""

import logging
import os
import base64
import json
from typing import Dict, Any, Optional, List, Tuple, Union, cast
from datetime import datetime
import traceback
import tempfile
import uuid

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Import chart visualization functions
from ai_service.utils.chart_visualizer import (
    create_chart_image,
    save_chart_as_pdf_report as save_chart_as_pdf
)

logger = logging.getLogger(__name__)

class ChartExportError(Exception):
    """Exception raised when chart export fails."""
    pass

def export_chart_as_image(chart_data: Dict[str, Any], output_dir: str, format: str = "png") -> str:
    """
    Export chart as an image file.

    Args:
        chart_data: Chart data to export
        output_dir: Directory to save the image
        format: Image format (png, jpg, svg)

    Returns:
        Path to the exported image

    Raises:
        ChartExportError: If export fails
    """
    if not chart_data:
        raise ChartExportError("No chart data provided")

    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Create a temporary filename based on chart ID
        chart_id = chart_data.get("chart_id", datetime.now().strftime("%Y%m%d%H%M%S"))
        output_file = os.path.join(output_dir, f"chart_{chart_id}.{format}")

        # Generate chart image
        output_path = create_chart_image(chart_data, output_file)
        logger.info(f"Chart exported as image to {output_path}")

        return output_path

    except Exception as e:
        error_msg = f"Failed to export chart as image: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise ChartExportError(error_msg)

def export_chart_as_pdf(chart_data: Dict[str, Any], output_dir: str, title: Optional[str] = None) -> str:
    """
    Export chart as a PDF report.

    Args:
        chart_data: Chart data to export
        output_dir: Directory to save the PDF
        title: Title for the PDF

    Returns:
        Path to the exported PDF

    Raises:
        ChartExportError: If export fails
    """
    if not chart_data:
        raise ChartExportError("No chart data provided")

    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Create a temporary filename based on chart ID
        chart_id = chart_data.get("chart_id", datetime.now().strftime("%Y%m%d%H%M%S"))
        output_file = os.path.join(output_dir, f"chart_{chart_id}.pdf")

        # Generate chart PDF
        output_path = save_chart_as_pdf(chart_data, output_file, title=title)
        logger.info(f"Chart exported as PDF to {output_path}")

        return output_path

    except Exception as e:
        error_msg = f"Failed to export chart as PDF: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise ChartExportError(error_msg)

def export_chart(chart_data: Dict[str, Any], chart_output_dir: Optional[str] = None,
                formats: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Export chart in multiple formats.

    Args:
        chart_data: Chart data to export
        chart_output_dir: Directory to save the exports
        formats: List of formats to export (png, pdf, json)

    Returns:
        Dictionary mapping format to file path

    Raises:
        ChartExportError: If export fails
    """
    if not chart_data:
        raise ChartExportError("No chart data provided")

    if not formats:
        formats = ["png", "pdf", "json"]

    if not chart_output_dir:
        chart_output_dir = tempfile.mkdtemp(prefix="chart_export_")

    os.makedirs(chart_output_dir, exist_ok=True)

    try:
        # Generate a unique ID for this export if not available
        if "chart_id" not in chart_data:
            chart_data["chart_id"] = f"chart_{uuid.uuid4().hex[:12]}"

        chart_id = chart_data["chart_id"]
        logger.info(f"Exporting chart {chart_id} in formats: {formats}")

        result = {}

        for fmt in formats:
            if fmt == "png":
                output_path = export_chart_as_image(chart_data, chart_output_dir, format="png")
                result["png"] = output_path
            elif fmt == "pdf":
                output_path = export_chart_as_pdf(chart_data, chart_output_dir)
                result["pdf"] = output_path
            elif fmt == "json":
                # Export as JSON
                json_path = os.path.join(chart_output_dir, f"chart_{chart_id}.json")
                with open(json_path, 'w') as f:
                    json.dump(chart_data, f, indent=2)
                result["json"] = json_path
            else:
                logger.warning(f"Unsupported export format: {fmt}")

        return result

    except Exception as e:
        error_msg = f"Failed to export chart: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise ChartExportError(error_msg)

def get_content_type(format: str) -> str:
    """
    Get the content type for a file format.

    Args:
        format: File format (pdf, png, jpg, svg, json)

    Returns:
        Content type string
    """
    content_types = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "svg": "image/svg+xml",
        "json": "application/json"
    }
    return content_types.get(format, "application/octet-stream")
