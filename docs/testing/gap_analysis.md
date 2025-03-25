# Gap Analysis: Birth Time Rectifier Backend Services

## Overview

This document identifies gaps, simulations, and mockups in the backend services that do not align with production requirements. The analysis compares current implementation against the expected application flow detailed in the sequence diagram (`docs/architecture/sequence_diagram.md`). This updated analysis includes specific code-level issues and required implementation changes.

## Key Issues Summary

1. **Incomplete Astrological Calculations**: ⚠️ Core rectification and chart calculation functions contain fallbacks and simplified implementations that don't use proper astrological principles. While the base calculation implementation has improved, fallbacks still exist for missing astronomical libraries.

2. **Inconsistent Database Integration**: ⚠️ While database structure is properly defined, some code paths don't use the database connection correctly. This issue persists in current implementation.

3. **Incomplete OpenAI Integration**: ⚠️ OpenAI service exists but still isn't consistently integrated across all relevant components. The questionnaire service has improved integration, but chart verification and rectification processes remain inconsistent.

4. **Questionnaire Processing Limitations**: ✅ The questionnaire service has been significantly improved with proper contradiction detection and validation. Frontend components now properly handle inconsistent answers.

5. **Error Handling Gaps**: ⚠️ Edge cases in rectification and chart generation aren't properly handled, but some improvements have been made in validation checks.

6. **Workflow Misalignment**: ⚠️ Several components still don't follow the sequence diagram flow, particularly in the birth time rectification and chart export processes.

7. **Visualization Implementation Gaps**: ⚠️ Chart visualization functions exist and are well-implemented but still aren't properly integrated with export functionality.

8. **Dependency Fallbacks**: ⚠️ Multiple critical components continue to have fallback mechanisms that produce inaccurate results rather than failing appropriately.

9. **Session Management**: ✅ The session management is now properly implemented with Redis integration and proper error handling.

10. **WebSocket Implementation**: ⚠️ Real-time updates through WebSocket connections aren't consistently implemented, particularly for rectification progress updates.

## Detailed Findings with Code-Level Analysis

### Chart Service Implementations

| File | Line(s) | Status | Issue | Description |
|------|---------|--------|-------|-------------|
| `ai_service/services/chart_service.py` | 495-505 | ⚠️ UNRESOLVED | IMPLEMENTATION | Chart export functionality creates metadata but doesn't actually generate PDF or image files. |
| `ai_service/services/chart_service.py` | 412-427 | ⚠️ UNRESOLVED | GAP | Rectification doesn't properly leverage OpenAI integration despite service being available. |
| `ai_service/services/chart_service.py` | 263-313 | ⚠️ UNRESOLVED | GAP | `calculate_chart` provides a basic implementation but doesn't fully leverage AI for validation. |
| `ai_service/services/chart_service.py` | 372-393 | ⚠️ UNRESOLVED | FALLBACK | Chart comparison calculation uses simplified algorithm instead of proper astrological analysis. |
| `ai_service/services/chart_service.py` | 135-199 | ⚠️ UNRESOLVED | INCONSISTENT | Verification process has potential points of failure with limited recovery options. |
| `ai_service/services/chart_service.py` | 300-345 | ⚠️ UNRESOLVED | MOCK | Harmonic chart calculation doesn't properly implement divisional charts required for Vedic analysis. |
| `ai_service/services/chart_service.py` | 525-575 | ⚠️ NEW | INCOMPLETE | Chart generation function doesn't produce 3D visualizations as described in the user testing instructions. |

#### Code-Level Analysis:

**1. Chart Export Functionality Issue:**

**Current Implementation:**
```python
# In ai_service/services/chart_service_export.py
def export_chart(chart_data, chart_output_dir=None, format="pdf", ...):
    # ... processing code ...

    # Define the output file path based on format
    file_extension = format.lower()
    output_filename = f"{chart_id}_{export_id}.{file_extension}"
    output_path = os.path.join(export_subdir, output_filename)

    # Dictionary to track all generated files
    generated_files = {}

    # Generate the appropriate file based on format
    if format.lower() == "pdf":
        # Use the PDF generator for comprehensive report
        pdf_generator = PDFGenerator(output_dir=export_subdir)
        file_path = pdf_generator.generate_full_report(
            chart_data=chart_data,
            interpretation=chart_data.get("interpretation"),
            # ... other parameters
        )
        generated_files["main"] = file_path

    # ... other format handling ...

    # Verify all file paths exist - but doesn't properly handle failure
    for key, path in list(generated_files.items()):
        if not path or not os.path.exists(path):
            logger.warning(f"File {key} not generated at {path}")
            generated_files.pop(key, None)
        else:
            # Add file size information
            generated_files[f"{key}_size"] = os.path.getsize(path)

    # Create export metadata - returns even if no files were generated!
    export_data = {
        "export_id": export_id,
        "chart_id": chart_id,
        "format": format,
        "generated_at": datetime.now().isoformat(),
        "file_paths": generated_files,
        "download_url": download_url,
        # ... other metadata ...
    }

    # Return export metadata without confirming successful generation
    return export_data
```

**Issues:**
1. The function logs warnings but doesn't fail if files aren't generated
2. It returns metadata even when no files were successfully created
3. It doesn't ensure that visualization utilities are actually called with proper parameters
4. There's no validation of file content beyond existence and size
5. No clear error handling for PDF generation or image creation failures

**Required Changes:**
```python
def export_chart(chart_data, chart_output_dir=None, format="pdf", ...):
    # ... existing initialization code ...

    # Track generation success
    generated_files = {}
    generation_success = False

    # Generate the appropriate file based on format
    if format.lower() == "pdf":
        try:
            # Use the PDF generator for comprehensive report
            pdf_generator = PDFGenerator(output_dir=export_subdir)

            file_path = pdf_generator.generate_full_report(
                chart_data=chart_data,
                interpretation=chart_data.get("interpretation"),
                # ... other parameters
            )

            # Verify file was created and has content
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                generated_files["main"] = file_path
                generation_success = True
            else:
                raise FileNotFoundError(f"PDF file not created or empty: {file_path}")

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise ChartExportError(f"Failed to generate PDF: {str(e)}")

    # ... similar improvements for other formats ...

    # Verify we have at least one generated file
    if not generation_success or not generated_files:
        raise ChartExportError(f"Failed to generate any files for format: {format}")

    # Create export metadata only when successful
    export_data = {
        "export_id": export_id,
        "chart_id": chart_id,
        "format": format,
        "generated_at": datetime.now().isoformat(),
        "file_paths": generated_files,
        "download_url": download_url,
        "generation_verified": True,
        # ... other metadata ...
    }

    return export_data
```

**Verification Criteria:**
1. Function must raise exceptions when file generation fails instead of returning metadata
2. Generated files must be verified for existence, size, and content validity
3. Each format should have appropriate validation (PDF structure, image dimensions)
4. Success should be confirmed before returning metadata
5. Tests should verify failure modes by mocking visualization utilities that fail

**2. OpenAI Integration for Rectification Issue:**

**Current Implementation:**
```python
# In ai_service/services/chart_service.py
async def update_chart_with_rectification(self, chart_id: str, rectification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a chart with rectification results.

    Args:
        chart_id: ID of the chart to update
        rectification_data: Rectification results

    Returns:
        Updated chart data
    """
    # This method is kept as is since it's not directly related to calculation but to database operations
    # Placeholder for the original implementation
    return {
        "chart_id": chart_id,
        "status": "updated",
        "rectification_applied": True,
        "updated_at": datetime.now().isoformat()
    }
```

**Issues:**
1. The method is a placeholder that doesn't actually update the chart with rectification results
2. There's no integration with OpenAI for verification despite the service being available
3. It doesn't interact with the database to update the chart
4. No validation of the rectification data is performed

**Required Changes:**
```python
async def update_chart_with_rectification(self, chart_id: str, rectification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a chart with rectification results and verify with OpenAI.

    Args:
        chart_id: ID of the chart to update
        rectification_data: Rectification results

    Returns:
        Updated chart data with verification
    """
    try:
        # Validate rectification data
        required_fields = ["rectified_time", "confidence", "method"]
        for field in required_fields:
            if field not in rectification_data:
                raise ValueError(f"Missing required field '{field}' in rectification data")

        # Get original chart from database
        from ai_service.database.repositories import ChartRepository
        chart_repo = ChartRepository()
        original_chart = await chart_repo.get_chart(chart_id)

        if not original_chart:
            raise ValueError(f"Chart not found with ID: {chart_id}")

        # Update chart with rectification data
        updated_chart = {**original_chart, **rectification_data}
        updated_chart["rectification_applied"] = True
        updated_chart["updated_at"] = datetime.now().isoformat()

        # Create differential to track changes
        time_difference_minutes = calculate_time_difference_minutes(
            original_chart.get("birth_time", ""),
            rectification_data.get("rectified_time", "")
        )

        updated_chart["rectification_details"] = {
            "original_time": original_chart.get("birth_time", ""),
            "rectified_time": rectification_data.get("rectified_time", ""),
            "time_difference_minutes": time_difference_minutes,
            "confidence": rectification_data.get("confidence", 0),
            "method": rectification_data.get("method", "unknown")
        }

        # Verify rectification with OpenAI if confidence is below threshold
        if rectification_data.get("confidence", 0) < 80:
            # Get OpenAI service
            from ai_service.api.services.openai import get_openai_service
            openai_service = get_openai_service()

            if openai_service:
                verification_result = await openai_service.verify_rectification(
                    original_chart=original_chart,
                    rectified_chart=updated_chart,
                    rectification_details=updated_chart["rectification_details"]
                )

                # Add verification data to chart
                updated_chart["verification"] = verification_result

        # Store updated chart in database
        stored_chart = await chart_repo.update_chart(chart_id, updated_chart)

        # Ensure the update was successful
        if not stored_chart:
            raise RuntimeError(f"Failed to update chart in database: {chart_id}")

        return stored_chart

    except Exception as e:
        logger.error(f"Error updating chart with rectification: {e}")
        logger.error(traceback.format_exc())
        raise
```

**Verification Criteria:**
1. Function must properly validate rectification data before processing
2. It should retrieve the original chart from the database
3. OpenAI verification should be called when confidence is below threshold
4. Database should be updated with the rectified data and verification results
5. Tests should verify proper handling of OpenAI verification failures

### Chart Visualization Issues

| File | Line(s) | Status | Issue | Description |
|------|---------|--------|-------|-------------|
| `ai_service/utils/chart_visualizer.py` | 49-109 | ⚠️ UNRESOLVED | INCOMPLETE | Vedic chart visualization implemented, but not integrated with export system. |
| `ai_service/utils/chart_visualizer.py` | 384-475 | ⚠️ UNRESOLVED | GAP | Chart image generation exists but isn't called by export functionality. |
| `ai_service/utils/chart_visualizer.py` | 477-567 | ⚠️ UNRESOLVED | MOCK | PDF generation function doesn't create production-quality reports. |
| `ai_service/utils/chart_visualizer.py` | 245-294 | ⚠️ UNRESOLVED | IMPLEMENTATION | Comparison chart visualization exists but isn't used in the API response. |
| `ai_service/utils/vedic_chart_renderer.py` | 90-125 | ✅ FIXED | IMPLEMENTATION | Proper Vedic chart renderer is now implemented with North Indian style chart format. |
| `ai_service/utils/vedic_chart_renderer.py` | 268-345 | ✅ FIXED | IMPLEMENTATION | Chart comparison visualization is properly implemented but not connected to API. |

#### Code-Level Analysis:

**1. Vedic Chart Visualization Integration Issue:**

**Current Implementation:**
```python
# In ai_service/utils/chart_visualizer.py
def generate_vedic_chart(chart_data, output_path=None, style="north_indian"):
    """Generate a Vedic chart visualization."""
    # Chart generation code but not connected to export system

    # Creates image but doesn't ensure it's used in exports
    # ...rendering code...

    return output_path
```

**Issues:**
1. Function creates charts but there's no integration with the export system
2. No verification that the generated file exists and has content
3. No error handling for visualization failures
4. The generated charts aren't properly connected to API responses

**Required Changes:**
```python
def generate_vedic_chart(chart_data, output_path=None, style="north_indian"):
    """
    Generate a Vedic chart visualization with proper export integration.

    Args:
        chart_data: Chart data to visualize
        output_path: Path to save the generated image
        style: Chart style ('north_indian' or 'south_indian')

    Returns:
        Dictionary with path and metadata about the generated chart
    """
    try:
        # Create directory if it doesn't exist
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        else:
            # Create a temporary file if no path provided
            output_dir = tempfile.gettempdir()
            chart_id = chart_data.get("chart_id", f"chart_{uuid.uuid4().hex[:8]}")
            output_path = os.path.join(output_dir, f"{chart_id}_{style}_vedic_chart.png")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Validate chart data
        required_fields = ["planets", "houses", "angles"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Generate the chart based on style
        if style == "north_indian":
            fig = _render_north_indian_chart(chart_data)
        elif style == "south_indian":
            fig = _render_south_indian_chart(chart_data)
        else:
            raise ValueError(f"Unsupported Vedic chart style: {style}")

        # Save the chart with proper quality settings
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        # Verify the file was created successfully
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Failed to create chart image at {output_path}")

        # Get file size and modification time for verification
        file_stats = os.stat(output_path)

        # Return metadata for export integration
        return {
            "file_path": output_path,
            "chart_style": style,
            "chart_type": "vedic",
            "file_size": file_stats.st_size,
            "created_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "verified": True
        }

    except Exception as e:
        logger.error(f"Error generating Vedic chart: {e}")
        logger.error(traceback.format_exc())
        raise
```

**Verification Criteria:**
1. Function should properly validate chart data before visualization
2. It should create the output directory if it doesn't exist
3. It must verify that the file was created successfully
4. The returned metadata should be usable by the export system
5. API routes should properly connect to this visualization function

**2. PDF Generation Issue:**

**Current Implementation:**
```python
# In ai_service/utils/chart_visualizer.py
def generate_chart_pdf(chart_data, output_path, include_interpretation=True):
    """Generate a PDF report for a chart."""
    # PDF generation code but lacks comprehensive production quality

    # Missing detailed error handling
    # ...incomplete PDF generation code...

    return output_path
```

**Issues:**
1. PDF generation doesn't create production-quality reports with complete content
2. No verification of PDF structure or content quality
3. Limited integration with interpretation data
4. No error handling for PDF creation failures
5. No proper formatting of planetary positions, aspects, etc.

**Required Changes:**
```python
def generate_chart_pdf(chart_data, output_path, include_interpretation=True, include_aspects=True,
                      include_houses=True, include_transits=False, paper_size="letter"):
    """
    Generate a comprehensive production-quality PDF chart report.

    Args:
        chart_data: Chart data to include in the report
        output_path: Path to save the generated PDF
        include_interpretation: Whether to include astrological interpretation
        include_aspects: Whether to include aspect analysis
        include_houses: Whether to include house analysis
        include_transits: Whether to include transit analysis
        paper_size: Paper size for the PDF ('letter', 'a4', 'legal')

    Returns:
        Dictionary containing path and metadata about the generated PDF
    """
    try:
        # Import PDF generation tools
        from reportlab.lib.pagesizes import letter, A4, legal
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Validate chart data
        required_fields = ["planets", "houses", "angles"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Set page size
        if paper_size.lower() == "a4":
            page_size = A4
        elif paper_size.lower() == "legal":
            page_size = legal
        else:
            page_size = letter

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Prepare styles
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        heading_style = styles["Heading1"]
        subheading_style = styles["Heading2"]
        normal_style = styles["Normal"]

        # Create story (content) for the PDF
        story = []

        # Add title
        birth_details = chart_data.get("birth_details", {})
        name = birth_details.get("name", "Birth Chart")
        birth_date = birth_details.get("date", chart_data.get("date", ""))
        birth_time = birth_details.get("time", chart_data.get("time", ""))
        location = birth_details.get("location", "")

        title = f"Astrological Birth Chart: {name}"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # Add birth details
        birth_details_text = f"Born on {birth_date} at {birth_time}"
        if location:
            birth_details_text += f" in {location}"

        story.append(Paragraph(birth_details_text, normal_style))
        story.append(Spacer(1, 24))

        # Generate chart image for the PDF
        chart_image_path = _generate_chart_image_for_pdf(chart_data)
        if chart_image_path and os.path.exists(chart_image_path):
            # Add chart image
            story.append(Paragraph("Birth Chart", heading_style))
            story.append(Spacer(1, 12))
            story.append(Image(chart_image_path, width=400, height=400))
            story.append(Spacer(1, 24))

        # Add planetary positions
        story.append(Paragraph("Planetary Positions", heading_style))
        story.append(Spacer(1, 12))

        # Create planetary positions table
        planets_data = [["Planet", "Sign", "Degree", "House", "Retrograde"]]
        for planet_name, planet_data in chart_data.get("planets", {}).items():
            planets_data.append([
                planet_name.capitalize(),
                planet_data.get("sign", ""),
                f"{planet_data.get('longitude', 0) % 30:.2f}°",
                str(planet_data.get("house", "")),
                "Yes" if planet_data.get("retrograde", False) else "No"
            ])

        planets_table = Table(planets_data, colWidths=[100, 100, 80, 80, 80])
        planets_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(planets_table)
        story.append(Spacer(1, 24))

        # Add aspects if requested
        if include_aspects and "aspects" in chart_data:
            # ... aspect table generation code (similar to planets table) ...
            story.append(Paragraph("Planetary Aspects", heading_style))
            story.append(Spacer(1, 12))

            # Create aspects table
            aspects_data = [["Aspect", "Planets", "Orb", "Significance"]]
            for aspect in chart_data.get("aspects", [])[:10]:  # Limit to top 10 aspects
                aspects_data.append([
                    aspect.get("type", ""),
                    f"{aspect.get('planet1', '')} - {aspect.get('planet2', '')}",
                    f"{aspect.get('orb', 0):.2f}°",
                    aspect.get("significance", "")
                ])

            aspects_table = Table(aspects_data, colWidths=[80, 120, 80, 160])
            aspects_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(aspects_table)
            story.append(Spacer(1, 24))

        # Build the PDF
        doc.build(story)

        # Verify the file was created successfully
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Failed to create PDF at {output_path}")

        # Return metadata for export integration
        return {
            "file_path": output_path,
            "file_size": os.path.getsize(output_path),
            "created_at": datetime.now().isoformat(),
            "paper_size": paper_size,
            "includes": {
                "interpretation": include_interpretation,
                "aspects": include_aspects,
                "houses": include_houses,
                "transits": include_transits
            },
            "verified": True
        }

    except Exception as e:
        logger.error(f"Error generating chart PDF: {e}")
        logger.error(traceback.format_exc())
        raise
```

**Verification Criteria:**
1. PDF should include all major chart elements (planetary positions, aspects, etc.)
2. Function should properly handle various content inclusion options
3. The output should be properly formatted and professional looking
4. Error handling should catch and report all failure modes
5. Integration with the export system should be seamless

### Core Rectification Issues

| File | Line(s) | Status | Issue | Description |
|------|---------|--------|-------|-------------|
| `ai_service/core/rectification/chart_calculator.py` | 21-39 | ⚠️ UNRESOLVED | FALLBACK | Creates dummy implementations when astrological libraries are not available. |
| `ai_service/core/rectification/chart_calculator.py` | 47-54 | ⚠️ UNRESOLVED | FALLBACK | Creates dummy implementation for timezone finder. |
| `ai_service/core/rectification/chart_calculator.py` | 98-102 | ⚠️ UNRESOLVED | FALLBACK | Uses fallback coordinates when GeoPos creation fails. |
| `ai_service/core/rectification/chart_calculator.py` | 148-158 | ⚠️ UNRESOLVED | MOCK | Creates placeholder data for outer planets if missing from ephemeris. |
| `ai_service/core/rectification/chart_calculator.py` | 251-279 | ⚠️ UNRESOLVED | GAP | Doesn't verify chart accuracy against Vedic astrological standards when requested. |
| `ai_service/core/rectification/main.py` | 58-62 | ⚠️ UNRESOLVED | FALLBACK | Mock implementation for OpenAI service when not available. |
| `ai_service/core/rectification/main.py` | 269-273 | ⚠️ UNRESOLVED | GAP | If Flatlib is not available, returns original time with very low confidence instead of using alternative calculation. |
| `ai_service/core/rectification/main.py` | 278-280 | ⚠️ UNRESOLVED | GAP | Returns original time with low confidence if no answers provided, without attempting alternative rectification methods. |
| `ai_service/core/rectification/main.py` | 388-393 | ⚠️ UNRESOLVED | GAP | If no candidate scores found in rectification, returns original time with medium confidence without exploring other techniques. |
| `ai_service/core/rectification/main.py` | 403-405 | ⚠️ UNRESOLVED | GAP | If best score is 0, returns original time with medium confidence without alternative analysis. |
| `ai_service/core/rectification/main.py` | 468-476 | ⚠️ UNRESOLVED | GAP | If Flatlib is not available, returns original time with very low confidence for transit analysis. |
| `ai_service/core/rectification/main.py` | 209-256 | ⚠️ UNRESOLVED | IMPLEMENTATION | MinimalChart implementation provides inaccurate planetary calculations. |
| `ai_service/core/rectification/main.py` | 508-562 | ⚠️ UNRESOLVED | INCONSISTENT | AI-assisted rectification doesn't consistently handle API response formats. |
| `ai_service/core/rectification/main.py` | 661-699 | ⚠️ UNRESOLVED | GAP | Transit analysis doesn't fully implement proper astrological significance evaluation. |

#### Code-Level Analysis:

**1. Astrological Library Fallback Issue:**

**Current Implementation:**
```python
# In ai_service/core/rectification/chart_calculator.py
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    logging.error("Swiss Ephemeris (swisseph) not available. This is REQUIRED for accurate calculations.")
    # Missing proper error handling, just logs an error and continues

# Later in the code:
if not SWISSEPH_AVAILABLE:
    # Returns dummy data instead of failing appropriately
    return {
        "chart_id": f"error_{uuid.uuid4().hex[:8]}",
        "status": "error",
        "timestamp": datetime.now().isoformat(),
    }
```

**Issues:**
1. Code detects missing dependencies but continues execution
2. Returns dummy data instead of raising appropriate exceptions
3. No fallback to alternative calculation method
4. Error handling is inconsistent across different dependency failures
5. The user may receive incorrect charts without clear notification

**Required Changes:**
```python
# Import with proper alternative library support
try:
    import pyswisseph as swe
    SWISSEPH_AVAILABLE = True
    CALCULATION_ENGINE = "pyswisseph"
except ImportError:
    try:
        # Alternative calculation library
        import flatlib.ephem
        FLATLIB_AVAILABLE = True
        SWISSEPH_AVAILABLE = False
        CALCULATION_ENGINE = "flatlib"
        logging.warning("Swiss Ephemeris not available, using flatlib as alternative.")
    except ImportError:
        FLATLIB_AVAILABLE = False
        SWISSEPH_AVAILABLE = False
        CALCULATION_ENGINE = None
        logging.critical("No astrological calculation libraries available. Cannot proceed.")
        # Don't continue silently - make this a fatal error
        raise ImportError("Required astrological libraries (swisseph or flatlib) are not available")

# Update the calculate_chart function to use alternative implementations
def calculate_chart(birth_dt, latitude, longitude, timezone_str, house_system='P'):
    """
    Calculate an astrological chart.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone_str: Timezone string
        house_system: House system to use

    Returns:
        Chart data dictionary

    Raises:
        ImportError: If no calculation libraries are available
        ValueError: If calculation fails
    """
    if not CALCULATION_ENGINE:
        raise ImportError("No astrological calculation libraries available")

    try:
        if CALCULATION_ENGINE == "pyswisseph":
            return _calculate_chart_swisseph(birth_dt, latitude, longitude, timezone_str, house_system)
        elif CALCULATION_ENGINE == "flatlib":
            return _calculate_chart_flatlib(birth_dt, latitude, longitude, timezone_str, house_system)
        else:
            raise ImportError("No valid calculation engine available")
    except Exception as e:
        logger.error(f"Chart calculation failed: {e}")
        logger.error(traceback.format_exc())
        # Provide clear error with details instead of dummy data
        raise ValueError(f"Failed to calculate chart: {str(e)}")
```

**Verification Criteria:**
1. Function must fail with clear error messages when dependencies are missing
2. Alternative calculation methods should be properly implemented
3. Error handling should be consistent across all calculation paths
4. No dummy data should be returned in error cases
5. Tests should verify behavior with and without required libraries

**2. Timezone Finder Fallback Issue:**

**Current Implementation:**
```python
# In ai_service/core/rectification/chart_calculator.py
try:
    from timezonefinder import TimezoneFinder
    TZ_FINDER_AVAILABLE = True
except ImportError:
    TZ_FINDER_AVAILABLE = False
    logging.warning("timezonefinder not available. Using simplified timezone lookup.")

# Later in the code:
def get_timezone_from_coordinates(latitude, longitude):
    if not TZ_FINDER_AVAILABLE:
        # Returns hardcoded fallback without proper warning
        return "UTC"
```

**Issues:**
1. Code silently falls back to UTC timezone without clear notification
2. No attempt to use alternative timezone lookup methods
3. No validation of coordinates before lookup
4. No proper error handling for lookup failures

**Required Changes:**
```python
def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Get timezone string from geographic coordinates with robust fallbacks.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        IANA timezone string (e.g., 'America/New_York')

    Raises:
        ValueError: If timezone cannot be determined
    """
    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise ValueError(f"Invalid latitude: {latitude} (must be between -90 and 90)")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Invalid longitude: {longitude} (must be between -180 and 180)")

    # Try primary method: TimezoneFinder
    if TZ_FINDER_AVAILABLE:
        try:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

            if timezone_str:
                return timezone_str

            # If exact lookup fails, try with a small radius
            timezone_str = tf.closest_timezone_at(lat=latitude, lng=longitude, delta_degree=1)
            if timezone_str:
                return timezone_str
        except Exception as e:
            logger.warning(f"TimezoneFinder lookup failed: {e}")

    # Try alternative method: Geopy with Nominatim
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="birth_time_rectifier")
        location = geolocator.reverse(f"{latitude}, {longitude}", language="en")

        if location and location.raw.get("address", {}).get("country_code"):
            country_code = location.raw["address"]["country_code"].upper()
            # Use country code to estimate timezone
            import pytz
            for tz in pytz.all_timezones:
                if country_code in tz:
                    logger.info(f"Found timezone {tz} for coordinates using country code")
                    return tz
    except Exception as e:
        logger.warning(f"Geopy timezone lookup failed: {e}")

    # Last resort: Use UTC with clear warning
    logger.warning(f"Could not determine timezone for coordinates ({latitude}, {longitude}). Using UTC.")
    return "UTC"
```

**Verification Criteria:**
1. Function should try multiple methods to determine timezone
2. It should validate coordinates before lookup
3. Clear warnings should be logged when falling back to UTC
4. Tests should verify behavior with and without TimezoneFinder
5. Documentation should clearly indicate fallback behavior

**3. Outer Planets Calculation Issue:**

**Current Implementation:**
```python
# In ai_service/core/rectification/chart_calculator.py
# When outer planets are missing from ephemeris:
if planet_name in ["Uranus", "Neptune", "Pluto"] and planet_data is None:
    # Creates placeholder data with inaccurate positions
    planet_data = {
        "longitude": random.uniform(0, 360),  # Random position!
        "latitude": 0,
        "distance": 0,
        "speed": 0
    }
```

**Issues:**
1. Creates completely random positions for missing outer planets
2. No indication to the user that the data is fabricated
3. Could lead to completely incorrect astrological interpretations
4. No attempt to use alternative calculation methods

**Required Changes:**
```python
def calculate_outer_planet_position(jd: float, planet_id: int) -> Dict[str, Any]:
    """
    Calculate accurate positions for outer planets using Swiss Ephemeris.

    Args:
        jd: Julian day for calculation
        planet_id: Swiss Ephemeris planet ID

    Returns:
        Dictionary with planet position data

    Raises:
        EphemerisError: If Swiss Ephemeris is not available
        ValueError: If calculation fails with Swiss Ephemeris
    """
    if not SWISSEPH_AVAILABLE:
        raise EphemerisError("Swiss Ephemeris not available for outer planet calculation")

    try:
        # Calculate planet positions with high precision
        result, status = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)

        # Extract coordinates
        longitude = result[0]  # Longitude in degrees
        latitude = result[1]   # Latitude in degrees
        distance = result[2]   # Distance in AU
        speed_lon = result[3]  # Speed in longitude (deg/day)

        # Determine if planet is retrograde
        retrograde = speed_lon < 0

        # Calculate sign
        sign_num = int(longitude / 30) % 12
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        sign = signs[sign_num]

        return {
            "longitude": longitude,
            "latitude": latitude,
            "distance": distance,
            "speed": speed_lon,
            "sign": sign,
            "retrograde": retrograde
        }
    except Exception as e:
        logger.error(f"Error calculating planet position with Swiss Ephemeris: {e}")
        raise ValueError(f"Failed to calculate planet position: {str(e)}")

# In the main chart calculation function:
# Replace the random placeholder with:
if planet_name in ["Uranus", "Neptune", "Pluto"] and planet_data is None:
    # Instead of random data, raise an error
    raise EphemerisError(f"Cannot calculate position for {planet_name}. Required ephemeris data is missing.")
```

**Verification Criteria:**
1. Function must raise clear errors when ephemeris data is missing
2. No random or fabricated data should be returned
3. Error messages should indicate the specific missing planet
4. Tests should verify behavior with missing ephemeris data
5. Documentation should clearly indicate requirements for outer planet calculations

**4. Vedic Chart Verification Issue:**

**Current Implementation:**
```python
# In ai_service/core/rectification/chart_calculator.py
# Missing implementation for Vedic chart verification
```

**Issues:**
1. No verification of chart against Vedic astrological standards
2. No validation of nakshatra positions
3. No calculation of Vedic divisional charts
4. No verification of ayanamsa application

**Required Changes:**
```python
async def _verify_vedic_standards(chart_data: Dict[str, Any], birth_dt: datetime) -> Dict[str, Any]:
    """
    Verify chart calculations against Vedic astrological standards.

    This checks for:
    1. Proper nakshatra placements
    2. Correct rashi (sign) calculations
    3. Accurate ayanamsa application
    4. Proper dignities and debilities
    5. Correct varga (divisional chart) calculations

    Args:
        chart_data: Chart data to verify
        birth_dt: Birth datetime

    Returns:
        Verified chart data with any necessary corrections
    """
    try:
        # Import Vedic-specific modules
        from ai_service.core.rectification.vedic_calculation import (
            get_nakshatra_from_longitude,
            calculate_varga_charts,
            calculate_planet_dignity,
            calculate_shadbala,
            get_ayanamsha_value,
            verify_vedic_coordinates,
            calculate_planetary_avasthas,
            calculate_dasa_periods
        )

        # Add ayanamsha information with proper calculation
        ayanamsha_value = get_ayanamsha_value(birth_dt)
        chart_data["ayanamsha"] = {
            "value": ayanamsha_value,
            "type": "Lahiri",  # Default standard for Vedic astrology
            "verified": True
        }

        # First, verify that all coordinates are properly adjusted for ayanamsha
        verified_coords = verify_vedic_coordinates(chart_data, ayanamsha_value)
        if verified_coords.get("corrections", []):
            logger.info(f"Applied {len(verified_coords['corrections'])} ayanamsha corrections")
            # Apply the corrections to the chart data
            for correction in verified_coords.get("corrections", []):
                item_type = correction.get("type")
                item_name = correction.get("name")
                corrected_longitude = correction.get("corrected_longitude")

                if item_type == "planet" and item_name in chart_data.get("planets", {}):
                    chart_data["planets"][item_name]["longitude"] = corrected_longitude
                    chart_data["planets"][item_name]["corrected"] = True
                elif item_type == "house" and item_name.isdigit():
                    house_index = int(item_name) - 1
                    if 0 <= house_index < len(chart_data.get("houses", [])):
                        chart_data["houses"][house_index]["longitude"] = corrected_longitude
                        chart_data["houses"][house_index]["corrected"] = True
                elif item_type == "angle" and item_name in chart_data.get("angles", {}):
                    chart_data["angles"][item_name]["longitude"] = corrected_longitude
                    chart_data["angles"][item_name]["corrected"] = True

        # Verify and add nakshatra positions
        chart_data["nakshatras"] = {}
        for planet_name, planet_data in chart_data.get("planets", {}).items():
            longitude = planet_data.get("longitude", 0)

            # Calculate nakshatra
            nakshatra_info = get_nakshatra_from_longitude(longitude)

            # Store nakshatra information
            chart_data["nakshatras"][planet_name] = nakshatra_info

            # Add to planet data
            planet_data["nakshatra"] = nakshatra_info.get("name")
            planet_data["nakshatra_pada"] = nakshatra_info.get("pada")
            planet_data["nakshatra_longitude"] = nakshatra_info.get("longitude")
            planet_data["nakshatra_lord"] = nakshatra_info.get("lord")

        # Calculate and verify varga (divisional) charts - MANDATORY for Vedic astrology
        varga_charts = calculate_varga_charts(chart_data)
        chart_data["varga_charts"] = varga_charts

        # Verify all required divisional charts are present
        required_vargas = ["D1", "D9", "D3", "D7", "D10", "D12"]
        missing_vargas = [v for v in required_vargas if v not in varga_charts]

        if missing_vargas:
            missing_vargas_str = ', '.join(missing_vargas)
            logger.error(f"Missing critical divisional charts: {missing_vargas_str}")
            raise ValueError(f"Vedic verification failed: Missing required divisional charts: {missing_vargas_str}")

        # Calculate dasa periods (Vimshottari dasa)
        chart_data["dasa_periods"] = calculate_dasa_periods(
            birth_dt=birth_dt,
            moon_longitude=chart_data.get("planets", {}).get("moon", {}).get("longitude", 0),
            ayanamsha=ayanamsha_value
        )

        # Verify overall chart integrity
        chart_data["verification_details"] = {
            "verified_against": "vedic_standards",
            "verified_at": datetime.now().isoformat(),
            "verification_status": "verified",
            "ayanamsha": ayanamsha_value,
            "ayanamsha_type": "Lahiri"
        }

        return chart_data

    except ImportError as ie:
        logger.error(f"Error importing Vedic calculation modules: {ie}")
        # Don't fall back to simplified implementation - raise the error for proper handling
        raise ValueError(f"Vedic calculation modules not available: {str(ie)}")
    except Exception as e:
        logger.error(f"Error during Vedic verification: {e}")
        logger.error(traceback.format_exc())
        # Don't return unverified chart - raise the error for proper handling
        raise ValueError(f"Vedic verification failed: {str(e)}")
```

**Verification Criteria:**
1. Function must properly verify all aspects of Vedic chart calculation
2. It should calculate and validate all required divisional charts
3. Nakshatra positions should be accurately calculated and verified
4. Ayanamsha application should be properly verified
5. Tests should verify behavior with various birth data inputs

**5. WebSocket Implementation Issue:**

**Current Implementation:**
```python
# In ai_service/services/websocket_service.py
# Missing implementation for real-time rectification progress updates
```

**Issues:**
1. WebSocket service exists but isn't used for rectification progress updates
2. No real-time feedback during long-running rectification process
3. Client has no way to know the current status of rectification
4. No error handling for WebSocket connection failures

**Required Changes:**
```python
# In ai_service/core/rectification/main.py
# Add progress reporting to rectification process:

async def comprehensive_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None,
    chart_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None  # Add session_id parameter
) -> Dict[str, Any]:
    """
    Perform comprehensive birth time rectification with real-time progress updates.
    """
    # Initialize options
    if options is None:
        options = {}

    # Get WebSocket manager for progress updates if session_id is provided
    websocket_manager = None
    if session_id:
        from ai_service.services.websocket_service import get_websocket_manager
        websocket_manager = get_websocket_manager()

    # Generate unique rectification ID
    rectification_id = f"rect_{uuid.uuid4().hex[:10]}"

    # Report initial progress
    if websocket_manager and session_id:
        await websocket_manager.emit_rectification_progress(
            session_id=session_id,
            progress=5,
            message="Starting rectification process",
            chart_id=chart_id or "unknown",
            rectification_id=rectification_id,
            status="processing",
            details={
                "start_time": datetime.now()
            }
        )

    try:
        # Verify ephemeris files
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_progress(
                session_id=session_id,
                progress=10,
                message="Verifying astronomical data",
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id
            )

        verified = await verify_ephemeris_files()
        if not verified:
            raise ValueError("Swiss Ephemeris files not available for rectification")

        # Calculate original chart
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_progress(
                session_id=session_id,
                progress=20,
                message="Calculating initial chart",
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id
            )

        original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

        # Execute primary rectification method
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_progress(
                session_id=session_id,
                progress=40,
                message="Analyzing questionnaire answers",
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id,
                details={
                    "techniques": ["Questionnaire analysis", "Event correlation"]
                }
            )

        # ... existing rectification code ...

        # Report AI analysis progress
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_progress(
                session_id=session_id,
                progress=70,
                message="Performing AI-assisted analysis",
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id,
                details={
                    "techniques": ["AI pattern recognition", "Astrological validation"]
                }
            )

        # ... more rectification code ...

        # Report completion
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_complete(
                session_id=session_id,
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id,
                result={
                    "rectified_time": rectified_time.isoformat(),
                    "confidence_score": confidence,
                    "time_shift_minutes": int((rectified_time - birth_dt).total_seconds() / 60)
                }
            )

        # Return result
        return result

    except Exception as e:
        # Report error through WebSocket
        if websocket_manager and session_id:
            await websocket_manager.emit_rectification_error(
                session_id=session_id,
                chart_id=chart_id or "unknown",
                rectification_id=rectification_id,
                error_message=str(e),
                error_code="RECTIFICATION_ERROR"
            )

        # Re-raise the exception
        raise
```

**Verification Criteria:**
1. WebSocket updates should be sent at key points in the rectification process
2. Progress percentage should accurately reflect the current stage
3. Error handling should properly report failures through WebSocket
4. Client should receive completion notification with results
5. Tests should verify WebSocket message sequence and content
