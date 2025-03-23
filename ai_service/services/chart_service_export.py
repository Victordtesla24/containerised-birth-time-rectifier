"""
Chart export functionality for chart service.

This module provides functions for exporting charts in various formats.
"""

import os
import logging
import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

def export_chart(chart_data: Dict[str, Any], chart_output_dir: Optional[str] = None,
                format: str = "pdf", include_interpretation: bool = True,
                include_aspects: bool = True, include_3d: bool = True,
                paper_size: str = "letter") -> Dict[str, Any]:
    """
    Generate and export a chart in the specified format with enhanced Vedic chart options.

    Args:
        chart_data: Chart data to export
        chart_output_dir: Output directory for chart files
        format: Export format (pdf, png, jpg, svg)
        include_interpretation: Whether to include astrological interpretation
        include_aspects: Whether to include aspect analysis
        include_3d: Whether to include 3D chart visualization
        paper_size: Paper size for PDF exports (letter, a4, legal)

    Returns:
        Dictionary containing export metadata including file path and download URL
    """
    try:
        # Validate chart data
        if not chart_data:
            raise ValueError("No chart data provided for export")

        required_fields = ["planets", "houses"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Generate export ID
        chart_id = chart_data.get("chart_id", f"chart_{uuid.uuid4().hex[:8]}")
        export_id = f"export_{uuid.uuid4().hex[:8]}"

        # Create export directory if it doesn't exist
        if chart_output_dir is None:
            raise ValueError("No chart output directory specified")

        export_dir = os.path.join(chart_output_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Create timestamp directory to avoid filename collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_subdir = os.path.join(export_dir, f"{chart_id}_{timestamp}")
        os.makedirs(export_subdir, exist_ok=True)

        # Define the output file path based on format
        file_extension = format.lower()
        output_filename = f"{chart_id}_{export_id}.{file_extension}"
        output_path = os.path.join(export_subdir, output_filename)

        # Import visualization utilities
        from ai_service.utils.chart_visualizer import (
            generate_chart_image,
            save_chart_as_pdf,
            generate_3d_chart,
            generate_multiple_charts,
            render_vedic_square_chart,
            render_vedic_chart,
            generate_comparison_chart
        )

        # Import PDF generation
        from ai_service.utils.pdf_generator import PDFGenerator

        # Import divisional charts
        from ai_service.utils.divisional_charts import generate_navamsa_chart

        # Add birth data information to help with PDF generation
        if "birth_data" not in chart_data and "birth_details" in chart_data:
            chart_data["birth_data"] = chart_data["birth_details"]

        if "birth_data" not in chart_data:
            chart_data["birth_data"] = {
                "date": chart_data.get("birth_date", ""),
                "time": chart_data.get("birth_time", ""),
                "location": chart_data.get("birth_location", ""),
                "latitude": chart_data.get("latitude", 0),
                "longitude": chart_data.get("longitude", 0),
                "timezone": chart_data.get("timezone", "UTC")
            }

        # Dictionary to track all generated files
        generated_files = {}

        # Determine chart style preference (default to North Indian for Vedic)
        chart_style = chart_data.get("preferences", {}).get("chart_style", "north_indian")
        chart_type = chart_data.get("calculation_details", {}).get("chart_type", "vedic").lower()

        # Generate the appropriate file based on format
        if format.lower() == "pdf":
            # Use the PDF generator for comprehensive report
            pdf_generator = PDFGenerator(output_dir=export_subdir)

            # Create enhanced options dictionary for PDF generation
            pdf_options = {
                "paper_size": paper_size,
                "include_interpretation": include_interpretation,
                "include_aspects": include_aspects,
                "include_3d": include_3d,
                "include_divisional": chart_type == "vedic",
                "chart_style": chart_style,
                "include_header_footer": True,
                "include_metadata": True,
                "high_quality": True
            }

            file_path = pdf_generator.generate_full_report(
                chart_data=chart_data,
                interpretation=chart_data.get("interpretation"),
                include_divisional=pdf_options["include_divisional"],
                include_3d=pdf_options["include_3d"],
                output_path=output_path,
                paper_size=pdf_options["paper_size"]
            )
            generated_files["main"] = file_path

        elif format.lower() in ["png", "jpg", "jpeg"]:
            # Generate chart image with the chart visualizer
            file_path = generate_chart_image(
                chart_data=chart_data,
                output_path=output_path,
                include_3d=include_3d,
                include_traditional=(chart_type == "vedic"),
                chart_style=chart_style
            )
            generated_files["main"] = file_path

            # Generate additional chart views if requested
            if include_3d:
                threedi_path = os.path.join(export_subdir, f"{chart_id}_3d.{file_extension}")
                threedi_file = generate_3d_chart(chart_data, threedi_path)
                generated_files["3d_chart"] = threedi_file

            # For Vedic charts, generate specific views
            if chart_type == "vedic":
                # Generate North Indian style chart
                north_indian_path = os.path.join(export_subdir, f"{chart_id}_north_indian.{file_extension}")
                north_indian_file = render_vedic_chart(chart_data, north_indian_path, style="north_indian")
                generated_files["north_indian_chart"] = north_indian_file

                # Generate South Indian style chart
                south_indian_path = os.path.join(export_subdir, f"{chart_id}_south_indian.{file_extension}")
                south_indian_file = render_vedic_chart(chart_data, south_indian_path, style="south_indian")
                generated_files["south_indian_chart"] = south_indian_file

                # Generate Navamsa chart if available
                if "divisional_charts" in chart_data and "D9" in chart_data["divisional_charts"]:
                    navamsa_path = os.path.join(export_subdir, f"{chart_id}_navamsa.{file_extension}")
                    try:
                        navamsa_data = chart_data["divisional_charts"]["D9"]
                        navamsa_file = render_vedic_chart(navamsa_data, navamsa_path, style=chart_style)
                        generated_files["navamsa_chart"] = navamsa_file
                    except Exception as e:
                        logger.warning(f"Failed to generate Navamsa chart: {e}")

        elif format.lower() == "svg":
            # Generate SVG chart with high quality for vector output
            vedic_output = render_vedic_chart(chart_data, output_path, style=chart_style)
            generated_files["main"] = vedic_output
        else:
            raise ValueError(f"Unsupported export format: {format}")

        # Generate comparison chart if rectification data is available
        if "original_chart" in chart_data and "rectified_chart" in chart_data:
            original_chart = chart_data["original_chart"]
            rectified_chart = chart_data["rectified_chart"]

            comparison_path = os.path.join(export_subdir, f"{chart_id}_comparison.{file_extension}")
            try:
                comparison_result = generate_comparison_chart(original_chart, rectified_chart, comparison_path)
                if isinstance(comparison_result, str):
                    generated_files["comparison_chart"] = comparison_result
                elif isinstance(comparison_result, dict) and "file_path" in comparison_result:
                    generated_files["comparison_chart"] = comparison_result["file_path"]
            except Exception as e:
                logger.warning(f"Failed to generate comparison chart: {e}")

        # Verify all file paths exist
        for key, path in list(generated_files.items()):
            if not path or not os.path.exists(path):
                logger.warning(f"File {key} not generated at {path}")
                generated_files.pop(key, None)
            else:
                # Add file size information
                generated_files[f"{key}_size"] = os.path.getsize(path)

        # Build relative URLs for client download
        base_url = f"/api/chart/download/{export_id}"
        download_url = f"{base_url}?format={format}"
        download_urls = {
            "main": download_url,
            "vedic": f"{base_url}/vedic" if "vedic_chart" in generated_files else None,
            "north_indian": f"{base_url}/north_indian" if "north_indian_chart" in generated_files else None,
            "south_indian": f"{base_url}/south_indian" if "south_indian_chart" in generated_files else None,
            "navamsa": f"{base_url}/navamsa" if "navamsa_chart" in generated_files else None,
            "3d": f"{base_url}/3d" if "3d_chart" in generated_files else None,
            "comparison": f"{base_url}/comparison" if "comparison_chart" in generated_files else None
        }

        # Create export metadata
        export_data = {
            "export_id": export_id,
            "chart_id": chart_id,
            "format": format,
            "generated_at": datetime.now().isoformat(),
            "file_paths": generated_files,
            "download_url": download_url,
            "download_urls": download_urls,
            "includes": {
                "interpretation": include_interpretation,
                "aspects": include_aspects,
                "3d": include_3d,
                "chart_style": chart_style,
                "chart_type": chart_type
            }
        }

        # Return export metadata
        return export_data
    except Exception as e:
        logger.error(f"Error exporting chart: {e}")
        logger.error(traceback.format_exc())
        raise

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
