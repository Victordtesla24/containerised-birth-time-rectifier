# Implementation Suggestions for Gap Analysis

This document provides detailed suggestions for resolving the gaps identified in the gap analysis document. Each suggestion includes specific file and line numbers to target, along with implementation details.

## 1. Chart Service Improvements

### Chart Export Functionality
**File:** `ai_service/services/chart_service.py` (Lines 495-505)
**Issue:** Chart export returns metadata but doesn't generate actual files

**Implementation:**
```python
# in ai_service/services/chart_service.py, replace export_chart method

async def export_chart(self, chart_id: str, format: str = "pdf") -> Dict[str, Any]:
    """Generate an exportable version of a chart."""
    logger.info(f"Exporting chart {chart_id} in {format} format")

    # Retrieve chart data
    chart_data = await self.get_chart(chart_id)
    if not chart_data:
        raise ValueError(f"Chart not found: {chart_id}")

    # Create unique ID for the export
    export_id = f"export_{uuid.uuid4().hex[:10]}"

    # Determine export directory
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)

    # Create export path
    filename = f"{chart_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    export_path = os.path.join(export_dir, filename)

    # Generate the export based on requested format
    if format.lower() == "pdf":
        # Generate PDF file using reportlab
        pdf_path = f"{export_path}.pdf"
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(pdf_path, pagesize=letter)
        # Add chart details to PDF
        c.drawString(100, 750, f"Astrological Chart: {chart_id}")
        c.drawString(100, 730, f"Birth Date: {chart_data.get('birth_details', {}).get('birth_date', 'Unknown')}")
        c.drawString(100, 710, f"Birth Time: {chart_data.get('birth_details', {}).get('birth_time', 'Unknown')}")
        c.drawString(100, 690, f"Location: {chart_data.get('birth_details', {}).get('location', 'Unknown')}")

        # Add planets
        y_pos = 640
        c.drawString(100, 660, "Planetary Positions:")
        for planet in chart_data.get("planets", []):
            planet_name = planet.get("name", "Unknown")
            sign = planet.get("sign", "Unknown")
            degree = planet.get("degree", 0)
            c.drawString(120, y_pos, f"{planet_name}: {sign} {degree:.2f}°")
            y_pos -= 20

        # Add houses
        y_pos = 640
        c.drawString(300, 660, "House Cusps:")
        for house in chart_data.get("houses", []):
            house_num = house.get("number", 0)
            sign = house.get("sign", "Unknown")
            degree = house.get("degree", 0)
            c.drawString(320, y_pos, f"House {house_num}: {sign} {degree:.2f}°")
            y_pos -= 20

        c.save()
        download_url = f"/api/chart/download/{export_id}/pdf"

    elif format.lower() in ["jpg", "jpeg", "png"]:
        # Generate image using chart_visualizer
        img_path = f"{export_path}.{format.lower()}"
        from ai_service.utils.chart_visualizer import generate_chart_image
        generate_chart_image(chart_data, img_path)
        download_url = f"/api/chart/download/{export_id}/{format.lower()}"

    else:
        raise ValueError(f"Unsupported export format: {format}")

    # Store export metadata
    export_metadata = {
        "export_id": export_id,
        "chart_id": chart_id,
        "format": format,
        "file_path": export_path + f".{format.lower()}",
        "generated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "download_url": download_url
    }

    await self.chart_repository.store_export(export_id, export_metadata)

    return {
        "status": "success",
        "export_id": export_id,
        "chart_id": chart_id,
        "format": format,
        "generated_at": datetime.now().isoformat(),
        "download_url": download_url
    }
```

### Enhance Chart Visualization
**File:** `ai_service/utils/chart_visualizer.py` (Add to file)
**Issue:** Missing proper chart image generation

**Implementation:**
```python
# Add to chart_visualizer.py

import matplotlib.pyplot as plt
import numpy as np
import math
from typing import Dict, Any, List
import os
from PIL import Image, ImageDraw, ImageFont

def generate_chart_image(chart_data: Dict[str, Any], output_path: str) -> None:
    """
    Generate visualization of an astrological chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Path to save the generated image
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(10, 10))

    # Draw the chart circle
    chart_circle = plt.Circle((0, 0), 0.9, fill=False, color='black', linewidth=2)
    ax.add_patch(chart_circle)

    # Draw the ascendant line (usually at 9 o'clock position)
    ax.plot([0, -0.9], [0, 0], 'r-', linewidth=2)

    # Calculate house cusps
    houses = chart_data.get("houses", [])
    house_angles = []

    for house in houses:
        # Convert house positions to angles (0 = Aries, 30 = Taurus, etc.)
        house_num = house.get("number", 0)
        sign = house.get("sign", "")
        degree = house.get("degree", 0)

        # Calculate sign index (0 = Aries, 1 = Taurus, etc.)
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate total angle (0 = Aries at 0°, 360 = Pisces at 30°)
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Convert to cartesian coordinates (rotate 90° counter-clockwise for traditional chart layout)
        x = 0.9 * math.cos(angle - math.pi/2)
        y = 0.9 * math.sin(angle - math.pi/2)

        # Store house cusp information
        house_angles.append((house_num, angle, x, y))

        # Draw house cusps
        ax.plot([0, x], [0, y], 'k-', linewidth=1)

        # Add house numbers
        text_x = 1.0 * math.cos(angle - math.pi/2)
        text_y = 1.0 * math.sin(angle - math.pi/2)
        ax.text(text_x, text_y, str(house_num), fontsize=12)

    # Plot planets
    planets = chart_data.get("planets", [])
    for planet in planets:
        name = planet.get("name", "")
        sign = planet.get("sign", "")
        degree = planet.get("degree", 0)

        # Calculate sign index (0 = Aries, 1 = Taurus, etc.)
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate total angle
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Plot at 75% of radius for planets
        x = 0.75 * math.cos(angle - math.pi/2)
        y = 0.75 * math.sin(angle - math.pi/2)

        # Plot planet
        ax.plot(x, y, 'bo', markersize=8)

        # Add planet symbol or abbreviation
        symbols = {
            "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
            "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"
        }

        symbol = symbols.get(name, name[:2])
        ax.text(x + 0.05, y + 0.05, symbol, fontsize=12)

    # Add chart title
    birth_details = chart_data.get("birth_details", {})
    birth_date = birth_details.get("birth_date", "")
    birth_time = birth_details.get("birth_time", "")
    location = birth_details.get("location", "")

    plt.title(f"Birth Chart\n{birth_date} {birth_time}\n{location}")

    # Set equal aspect ratio and remove axis ticks
    ax.set_aspect('equal')
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    plt.axis('off')

    # Save the chart
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
```

### OpenAI Integration for Rectification
**File:** `ai_service/services/chart_service.py` (Lines 412-427)
**Issue:** Rectification doesn't leverage OpenAI integration

**Implementation:**
```python
# Replace rectify_chart method in ai_service/services/chart_service.py

async def rectify_chart(self, chart_id: str, questionnaire_id: str, answers: List[Dict[str, Any]], include_details: bool = False) -> Dict[str, Any]:
    """
    Rectify a chart based on questionnaire answers using AI analysis algorithm.

    Args:
        chart_id: ID of the chart to rectify
        questionnaire_id: ID of the questionnaire with answers
        answers: List of question/answer pairs
        include_details: Whether to include detailed rectification process

    Returns:
        Dictionary with rectified chart details
    """
    logger.info(f"Rectifying chart {chart_id} using questionnaire {questionnaire_id}")

    # Get the original chart
    original_chart = await self.get_chart(chart_id)
    if not original_chart:
        raise ValueError(f"Chart not found: {chart_id}")

    # Extract birth details from chart
    birth_details = original_chart.get("birth_details", {})
    birth_date = birth_details.get("birth_date", "")
    birth_time = birth_details.get("birth_time", "")
    latitude = birth_details.get("latitude", 0)
    longitude = birth_details.get("longitude", 0)
    timezone = birth_details.get("timezone", "UTC")

    # Parse birth datetime
    birth_dt = self._parse_datetime(birth_date, birth_time, timezone)

    # Track rectification process steps
    rectification_steps = []
    rectification_steps.append("Retrieved original chart data")

    # Use AI analysis for advanced rectification if OpenAI service is available
    ai_rectification_result = None
    if self.openai_service:
        try:
            rectification_steps.append("Starting AI-powered birth time analysis")

            # Format existing chart data for OpenAI analysis
            chart_planets = []
            for planet in original_chart.get("planets", []):
                if isinstance(planet, dict):
                    chart_planets.append({
                        "name": planet.get("name"),
                        "sign": planet.get("sign"),
                        "degree": planet.get("degree", 0),
                        "house": planet.get("house", 0)
                    })

            # Prepare data for AI analysis
            rectification_prompt = {
                "task": "birth_time_rectification",
                "birth_details": {
                    "date": birth_date,
                    "time": birth_time,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone
                },
                "questionnaire_data": {
                    "questions_and_answers": answers,
                    "total_questions": len(answers)
                },
                "chart_data": {
                    "ascendant": original_chart.get("ascendant", {}),
                    "planets": chart_planets
                },
                "requirements": [
                    "Analyze questionnaire answers for timing indicators",
                    "Apply astrological principles to determine the most likely birth time",
                    "Provide confidence level and explanation for the rectification",
                    "Specify adjustment in minutes (positive or negative) from original time"
                ]
            }

            rectification_steps.append("Sending data to OpenAI for astrological analysis")

            # Get rectification from OpenAI
            response = await self.openai_service.generate_completion(
                prompt=json.dumps(rectification_prompt),
                task_type="birth_time_rectification",
                max_tokens=1000,
                temperature=0.2  # Lower temperature for more deterministic results
            )

            if response and "content" in response:
                rectification_steps.append("Received AI analysis results")

                # Parse the AI response
                content = response["content"]

                # Extract JSON if embedded in text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    ai_result = json.loads(json_match.group(0))
                else:
                    try:
                        ai_result = json.loads(content)
                    except json.JSONDecodeError:
                        # Extract key information from text response
                        time_pattern = re.search(r'rectified_time["\s:]+([0-2]?[0-9]:[0-5][0-9])', content)
                        confidence_pattern = re.search(r'confidence["\s:]+(\d+\.?\d*)', content)
                        adjustment_pattern = re.search(r'adjustment_minutes["\s:]+(-?\d+)', content)

                        ai_result = {}
                        if time_pattern:
                            ai_result["rectified_time"] = time_pattern.group(1)
                        if confidence_pattern:
                            ai_result["confidence"] = float(confidence_pattern.group(1))
                        if adjustment_pattern:
                            ai_result["adjustment_minutes"] = int(adjustment_pattern.group(1))

                        explanation_lines = [line for line in content.split('\n') if 'explanation' not in line.lower() and len(line) > 20]
                        if explanation_lines:
                            ai_result["explanation"] = explanation_lines[0]

                # Extract rectification details
                if "rectified_time" in ai_result:
                    ai_adjusted_time = ai_result["rectified_time"]
                    ai_confidence = ai_result.get("confidence", 75.0)
                    ai_explanation = ai_result.get("explanation", "Birth time rectified using AI analysis")
                    ai_adjustment_minutes = ai_result.get("adjustment_minutes", 0)

                    # Parse the AI-suggested time
                    if ":" in ai_adjusted_time:
                        hours, minutes = map(int, ai_adjusted_time.split(":")[:2])

                        # Create adjusted datetime
                        rectified_time_dt = birth_dt.replace(hour=hours, minute=minutes)

                        # Format as string for display
                        rectified_time = rectified_time_dt.strftime("%H:%M")

                        ai_rectification_result = {
                            "rectified_time": rectified_time_dt,
                            "confidence": ai_confidence,
                            "explanation": ai_explanation,
                            "adjustment_minutes": ai_adjustment_minutes,
                            "methods_used": ["ai_analysis", "questionnaire_analysis"],
                        }

                        rectification_steps.append(f"AI analysis successful: adjusted time to {rectified_time}")
        except Exception as e:
            logger.error(f"Error in AI rectification analysis: {e}")
            rectification_steps.append(f"Error in AI analysis: {str(e)}")

    # Use traditional rectification if AI analysis failed or isn't available
    if not ai_rectification_result:
        rectification_steps.append("Using comprehensive astrological methods for rectification")

        # Perform real rectification using comprehensive algorithm
        from ai_service.core.rectification import comprehensive_rectification

        # Process rectification using actual astrological calculations
        rectification_result = await comprehensive_rectification(
            birth_dt=birth_dt,
            latitude=float(latitude),
            longitude=float(longitude),
            timezone=timezone,
            answers=answers
        )

        # Extract rectified time from results
        rectified_time_dt = rectification_result.get("rectified_time")
        if not rectified_time_dt:
            raise ValueError("Rectification failed to return a valid time")

        # Format the rectified time
        rectified_time = rectified_time_dt.strftime("%H:%M")

        # Get confidence score from calculation
        confidence_score = rectification_result.get("confidence", 0)
        explanation = rectification_result.get("explanation", "")
        adjustment_minutes = rectification_result.get("adjustment_minutes", 0)
        methods_used = rectification_result.get("methods_used", [])

        rectification_steps.append(f"Traditional rectification completed: adjusted time to {rectified_time}")
    else:
        # Use AI rectification result
        rectified_time_dt = ai_rectification_result["rectified_time"]
        rectified_time = rectified_time_dt.strftime("%H:%M")
        confidence_score = ai_rectification_result["confidence"]
        explanation = ai_rectification_result["explanation"]
        adjustment_minutes = ai_rectification_result["adjustment_minutes"]
        methods_used = ai_rectification_result["methods_used"]

    # Generate new chart with rectified time
    rectified_chart = await self.generate_chart(
        birth_date=birth_date,
        birth_time=rectified_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        location=birth_details.get("location", ""),
        verify_with_openai=True  # Perform verification on rectified chart
    )

    # Add rectification metadata
    rectified_chart["original_chart_id"] = chart_id
    rectified_chart["questionnaire_id"] = questionnaire_id
    rectified_chart["rectification_process"] = {
        "method": "ai_powered_astrological_analysis" if ai_rectification_result else "comprehensive_astrological_analysis",
        "original_time": birth_time,
        "adjusted_time": rectified_time,
        "adjustment_minutes": adjustment_minutes,
        "confidence_score": confidence_score,
        "methods_used": methods_used,
        "explanation": explanation,
        "process_steps": rectification_steps
    }

    # Create response
    rectification_id = f"rect_{uuid.uuid4().hex[:8]}"
    result = {
        "status": "complete",
        "rectification_id": rectification_id,
        "original_chart_id": chart_id,
        "rectified_chart_id": rectified_chart["chart_id"],
        "original_time": birth_time,
        "rectified_time": rectified_time,
        "confidence_score": confidence_score,
        "explanation": explanation
    }

    if include_details:
        result["details"] = {
            "process": "ai_powered_analysis" if ai_rectification_result else "comprehensive_astrological_analysis",
            "adjustment_minutes": adjustment_minutes,
            "answers_analyzed": len(answers),
            "methods_used": methods_used,
            "process_steps": rectification_steps
        }

    return result
```

## 2. Database Implementation Issues

### Standardize Error Handling
**File:** `ai_service/database/repositories.py` (Line 29-42)
**Issue:** Inconsistent error handling

**Implementation:**
```python
# Add this helper method to ai_service/database/repositories.py

async def _execute_db_operation(self, operation_name: str, operation_func, *args, **kwargs):
    """
    Execute a database operation with standardized error handling.

    Args:
        operation_name: Name of the operation for logging
        operation_func: Async function to execute
        *args, **kwargs: Arguments to pass to operation_func

    Returns:
        Result of the operation

    Raises:
        ValueError: If operation fails
    """
    try:
        # Ensure DB is initialized
        await self._ensure_initialized()

        # Check if DB pool is available
        if not self.db_pool:
            raise ValueError(f"Database connection is not available for {operation_name}")

        # Execute the operation
        return await operation_func(*args, **kwargs)
    except asyncpg.PostgresError as db_error:
        # Handle database-specific errors
        logger.error(f"Database error in {operation_name}: {db_error}")

        # Categorize errors for better handling
        if isinstance(db_error, asyncpg.UndefinedTableError):
            # Table doesn't exist - this should never happen with proper initialization
            logger.critical(f"Table doesn't exist in {operation_name}. Database may not be initialized properly.")
            raise ValueError(f"Database schema error: {str(db_error)}")
        elif isinstance(db_error, asyncpg.UniqueViolationError):
            # Unique constraint violation
            logger.warning(f"Unique constraint violation in {operation_name}")
            raise ValueError(f"Duplicate entry: {str(db_error)}")
        elif isinstance(db_error, asyncpg.ForeignKeyViolationError):
            # Foreign key constraint violation
            logger.warning(f"Foreign key violation in {operation_name}")
            raise ValueError(f"Referenced entity doesn't exist: {str(db_error)}")
        elif isinstance(db_error, asyncpg.InsufficientPrivilegeError):
            # Permission error
            logger.critical(f"Insufficient database privileges in {operation_name}")
            raise ValueError(f"Database permission error: {str(db_error)}")
        else:
            # Generic database error
            raise ValueError(f"Database operation '{operation_name}' failed: {str(db_error)}")
    except Exception as e:
        # Handle non-database errors
        logger.error(f"Error in {operation_name}: {str(e)}")
        raise ValueError(f"{operation_name} failed: {str(e)}")
```

### Update Database Methods
**File:** `ai_service/database/repositories.py` (Multiple methods)
**Issue:** Inconsistent implementation across repository methods

**Implementation:**
```python
# Update store_chart method to use standardized error handling

async def store_chart(self, chart_id: str, chart_data: Dict[str, Any]) -> None:
    """Store chart data in the database."""

    async def _store_operation(chart_id, chart_data):
        # Store timestamp
        now = datetime.now()
        chart_data["created_at"] = chart_data.get("created_at", now.isoformat())
        chart_data["updated_at"] = now.isoformat()

        # Insert or update chart
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO charts (chart_id, chart_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (chart_id)
                DO UPDATE SET
                    chart_data = $2,
                    updated_at = $4
            ''', chart_id, json.dumps(chart_data), now, now)

        logger.info(f"Chart {chart_id} stored in database")
        return True

    return await self._execute_db_operation("store_chart", _store_operation, chart_id, chart_data)

# Also update get_chart, update_chart, delete_chart, list_charts, etc. using the same pattern
```

### Store Comparison Method
**File:** `ai_service/database/repositories.py` (Lines 162-181)
**Issue:** Lacks proper validation and error handling

**Implementation:**
```python
# Update store_comparison method with proper validation and error handling

async def store_comparison(self, comparison_id: str, comparison_data: Dict[str, Any]) -> None:
    """
    Store comparison data.

    Args:
        comparison_id: Comparison identifier
        comparison_data: Comparison data
    """
    # Validate input data
    if not comparison_id:
        raise ValueError("Comparison ID is required")

    if not comparison_data:
        raise ValueError("Comparison data is required")

    # Ensure required fields are present
    chart1_id = comparison_data.get("chart1_id")
    chart2_id = comparison_data.get("chart2_id")

    if not chart1_id or not chart2_id:
        raise ValueError("Both chart IDs are required for comparison")

    async def _store_comparison_operation(comparison_id, comparison_data, chart1_id, chart2_id):
        # Verify charts exist first
        chart1_exists = False
        chart2_exists = False

        async with self.db_pool.acquire() as conn:
            # Check if charts exist
            chart1_row = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart1_id)
            chart2_row = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart2_id)

            chart1_exists = chart1_row is not None
            chart2_exists = chart2_row is not None

        if not chart1_exists:
            raise ValueError(f"Chart 1 with ID {chart1_id} does not exist")

        if not chart2_exists:
            raise ValueError(f"Chart 2 with ID {chart2_id} does not exist")

        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO comparisons (
                    comparison_id, chart1_id, chart2_id, comparison_data, created_at
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (comparison_id)
                DO UPDATE SET
                    comparison_data = $4
            ''',
            comparison_id, chart1_id, chart2_id,
            json.dumps(comparison_data),
            datetime.now())

        logger.info(f"Comparison {comparison_id} stored")
        return True

    return await self._execute_db_operation(
        "store_comparison",
        _store_comparison_operation,
        comparison_id, comparison_data, chart1_id, chart2_id
    )
```

## 3. Core Rectification Issues

### Alternative Calculations for Flatlib Fallback
**File:** `ai_service/core/rectification.py` (Lines 269-273)
**Issue:** Returns original time with low confidence if Flatlib is not available

**Implementation:**
```python
# Replace calculate_chart function with robust implementation

def calculate_chart(birth_date: datetime, latitude: float, longitude: float, timezone_str: str) -> Any:
    """
    Calculate astrological chart for a specific birth time using available libraries.

    Args:
        birth_date: Birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Birth location timezone

    Returns:
        Chart object (flatlib.Chart or custom dict)
    """
    # Format date
    dt_str = birth_date.strftime('%Y/%m/%d')
    time_str = birth_date.strftime('%H:%M')

    # Convert timezone to offset format (+/-HH:MM)
    timezone = pytz.timezone(timezone_str)
    offset = timezone.utcoffset(birth_date)
    hours, remainder = divmod(offset.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    offset_str = f"{'+' if hours >= 0 else '-'}{abs(int(hours)):02d}:{abs(int(minutes)):02d}"

    try:
        # Try using flatlib first
        from flatlib.datetime import Datetime
        from flatlib.geopos import GeoPos
        from flatlib.chart import Chart

        date = Datetime(dt_str, time_str, offset_str)
        pos = GeoPos(f"{abs(latitude)}{'n' if latitude >= 0 else 's'}",
                   f"{abs(longitude)}{'e' if longitude >= 0 else 'w'}")

        # Calculate and return the chart
        return Chart(date, pos)
    except ImportError:
        logger.warning("Flatlib not available, using Swiss Ephemeris")

        try:
            # Use Swiss Ephemeris as alternative
            import swisseph as swe

            # Initialize ephemeris path
            ephemeris_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ephemeris")
            swe.set_ephe_path(ephemeris_path)

            # Convert to Julian day
            jul_day = swe.julday(
                birth_date.year,
                birth_date.month,
                birth_date.day,
                birth_date.hour + birth_date.minute/60.0
            )

            # Calculate house cusps and ascendant
            houses, ascmc = swe.houses(jul_day, latitude, longitude, b'P')

            # Extract ascendant
            ascendant_lon = ascmc[0]

            # Calculate planet positions
            planets = {}
            for planet_id in range(10):  # 0-9 are major planets
                position, speed = swe.calc_ut(jul_day, planet_id)
                planets[planet_id] = {
                    'longitude': position[0],
                    'latitude': position[1],
                    'distance': position[2],
                    'speed': speed[0]
                }

            # Convert to zodiac signs
            def lon_to_sign(lon):
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo
