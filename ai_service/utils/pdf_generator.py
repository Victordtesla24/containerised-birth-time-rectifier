"""
PDF Generator for Birth Time Rectifier.

This module provides functionality to generate high-quality PDFs of astrological charts.
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import io
import base64

from reportlab.lib.pagesizes import letter, A4, legal
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.pdfgen import canvas

# Configure logging
logger = logging.getLogger(__name__)

class PDFGenerator:
    """
    PDF Generator for astrological charts.

    This class provides methods to create professional-quality PDF reports
    containing charts, interpretations, and other astrological information.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the PDF generator.

        Args:
            output_dir: Directory for saving PDF files (optional)
        """
        self.output_dir = output_dir

        # Create styles for PDF content
        self.styles = getSampleStyleSheet()

        # Add custom styles
        self.styles.add(ParagraphStyle(
            name='Title',
            fontName='Helvetica-Bold',
            fontSize=16,
            alignment=1,  # Center
            spaceAfter=12
        ))

        self.styles.add(ParagraphStyle(
            name='Heading1',
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='Heading2',
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceAfter=8
        ))

        self.styles.add(ParagraphStyle(
            name='Normal',
            fontName='Helvetica',
            fontSize=10,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='Interpretation',
            fontName='Helvetica',
            fontSize=10,
            leftIndent=10,
            spaceAfter=10
        ))

        # Create a mapping of paper sizes
        self.paper_sizes = {
            'letter': letter,
            'a4': A4,
            'legal': legal
        }

    def generate_full_report(self, chart_data: Dict[str, Any], interpretation: Optional[Dict[str, Any]] = None,
                           include_divisional: bool = True, include_3d: bool = True,
                           output_path: Optional[str] = None, paper_size: str = 'letter') -> str:
        """
        Generate a comprehensive PDF report for an astrological chart.

        Args:
            chart_data: Chart data to include in the report
            interpretation: Interpretation text to include
            include_divisional: Whether to include divisional charts
            include_3d: Whether to include 3D visualization
            output_path: Path to save the PDF
            paper_size: Paper size ('letter', 'a4', 'legal')

        Returns:
            Path to the generated PDF file
        """
        # Create temporary files for chart images
        image_files = self._generate_chart_images(chart_data, include_3d, include_divisional)

        # Create the PDF document
        if not output_path:
            if self.output_dir:
                os.makedirs(self.output_dir, exist_ok=True)
                output_path = os.path.join(self.output_dir, f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            else:
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    output_path = tmp.name

        # Ensure directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Get appropriate page size
        page_size = self.paper_sizes.get(paper_size.lower(), letter)

        # Create the PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Build the PDF content
        story = []

        # Add title
        self._add_title(story, chart_data)

        # Add main chart
        self._add_main_chart(story, image_files.get('main'))

        # Add birth details
        self._add_birth_details(story, chart_data)

        # Add planet positions
        self._add_planet_positions(story, chart_data)

        # Add house cusps
        self._add_house_cusps(story, chart_data)

        # Add aspects
        if include_divisional:
            self._add_aspects(story, chart_data)

        # Add page break before interpretation
        story.append(PageBreak())

        # Add interpretation if available
        if interpretation:
            self._add_interpretation(story, interpretation)

        # Add divisional charts if requested
        if include_divisional and 'divisional' in image_files:
            story.append(PageBreak())
            self._add_divisional_charts(story, chart_data, image_files.get('divisional', {}))

        # Add 3D chart if requested
        if include_3d and 'three_d' in image_files:
            story.append(PageBreak())
            self._add_3d_chart(story, image_files.get('three_d'))

        # Add comparison chart if available
        if 'comparison' in image_files:
            story.append(PageBreak())
            self._add_comparison_chart(story, chart_data, image_files.get('comparison'))

        # Build the PDF
        doc.build(
            story,
            onFirstPage=self._add_header_footer,
            onLaterPages=self._add_header_footer
        )

        # Clean up temporary image files
        self._cleanup_temp_files(image_files)

        return output_path

    def _generate_chart_images(self, chart_data: Dict[str, Any], include_3d: bool,
                             include_divisional: bool) -> Dict[str, Any]:
        """
        Generate all required chart images for the PDF report.

        Args:
            chart_data: Chart data to visualize
            include_3d: Whether to include 3D visualization
            include_divisional: Whether to include divisional charts

        Returns:
            Dictionary mapping image types to temporary file paths
        """
        from ai_service.utils.chart_visualizer import (
            render_vedic_square_chart,
            render_vedic_chart,
            generate_3d_chart,
            generate_chart_image,
            generate_planet_table
        )

        image_files = {}

        # Create a temporary directory for images
        temp_dir = tempfile.mkdtemp()

        try:
            # Generate main chart
            main_chart_path = os.path.join(temp_dir, "main_chart.png")
            image_files['main'] = render_vedic_square_chart(chart_data, main_chart_path)

            # Generate 3D chart if requested
            if include_3d:
                three_d_path = os.path.join(temp_dir, "3d_chart.png")
                try:
                    image_files['three_d'] = generate_3d_chart(chart_data, three_d_path)
                except Exception as e:
                    logger.warning(f"Failed to generate 3D chart: {e}")

            # Generate planet table
            planet_table_path = os.path.join(temp_dir, "planet_table.png")
            try:
                image_files['planet_table'] = generate_planet_table(chart_data, planet_table_path)
            except Exception as e:
                logger.warning(f"Failed to generate planet table: {e}")

            # Generate divisional charts if requested and available
            if include_divisional and "divisional_charts" in chart_data:
                divisional_images = {}

                for varga_code, varga_chart in chart_data["divisional_charts"].items():
                    if varga_code in ["D9", "D3", "D7"] and isinstance(varga_chart, dict):
                        varga_path = os.path.join(temp_dir, f"{varga_code}_chart.png")
                        try:
                            divisional_images[varga_code] = render_vedic_chart(
                                varga_chart,
                                varga_path,
                                style="north_indian"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to generate {varga_code} chart: {e}")

                if divisional_images:
                    image_files['divisional'] = divisional_images

            # Generate comparison chart if available
            if "original_chart" in chart_data and "rectified_chart" in chart_data:
                from ai_service.utils.chart_visualizer import generate_comparison_chart

                comparison_path = os.path.join(temp_dir, "comparison_chart.png")
                try:
                    comparison_result = generate_comparison_chart(
                        chart_data["original_chart"],
                        chart_data["rectified_chart"],
                        comparison_path
                    )

                    if isinstance(comparison_result, str):
                        image_files['comparison'] = comparison_result
                    elif isinstance(comparison_result, dict) and "file_path" in comparison_result:
                        image_files['comparison'] = comparison_result["file_path"]
                except Exception as e:
                    logger.warning(f"Failed to generate comparison chart: {e}")

        except Exception as e:
            logger.error(f"Error generating chart images: {e}")

        return image_files

    def _add_header_footer(self, canvas: canvas.Canvas, doc: SimpleDocTemplate) -> None:
        """
        Add header and footer to PDF pages.

        Args:
            canvas: ReportLab canvas
            doc: ReportLab document
        """
        # Save the state of our canvas so we can draw on it
        canvas.saveState()

        # Header
        header_text = "Birth Chart Analysis"
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(doc.width/2 + doc.leftMargin, doc.height + doc.topMargin - 0.25*inch, header_text)

        # Footer with page number
        footer_text = f"Page {canvas.getPageNumber()}"
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(doc.width/2 + doc.leftMargin, doc.bottomMargin - 0.25*inch, footer_text)

        # Date on the right side of the footer
        date_text = datetime.now().strftime("%Y-%m-%d")
        canvas.drawRightString(doc.width + doc.leftMargin - 0.25*inch, doc.bottomMargin - 0.25*inch, date_text)

        # Restore the state of our canvas
        canvas.restoreState()

    def _add_title(self, story: List, chart_data: Dict[str, Any]) -> None:
        """
        Add title section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
        """
        # Get name if available
        name = chart_data.get("name", "")
        if not name and "birth_data" in chart_data:
            name = chart_data["birth_data"].get("name", "")

        if name:
            title = f"Birth Chart Analysis for {name}"
        else:
            title = "Birth Chart Analysis"

        story.append(Paragraph(title, self.styles['Title']))
        story.append(Spacer(1, 0.25*inch))

    def _add_main_chart(self, story: List, chart_image_path: Optional[str]) -> None:
        """
        Add main chart image to PDF.

        Args:
            story: ReportLab story list
            chart_image_path: Path to chart image
        """
        if chart_image_path and os.path.exists(chart_image_path):
            # Add a heading for the chart
            story.append(Paragraph("Birth Chart", self.styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))

            # Add the chart image, scaled to fit the page width
            img = Image(chart_image_path, width=6*inch, height=6*inch)
            story.append(img)
            story.append(Spacer(1, 0.25*inch))

    def _add_birth_details(self, story: List, chart_data: Dict[str, Any]) -> None:
        """
        Add birth details section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
        """
        # Get birth details
        birth_details = {}

        if "birth_data" in chart_data:
            birth_details = chart_data["birth_data"]
        elif "birth_details" in chart_data:
            birth_details = chart_data["birth_details"]

        if birth_details:
            # Add a heading for birth details
            story.append(Paragraph("Birth Details", self.styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))

            # Create a table for birth details
            data = []

            # Add date and time
            date = birth_details.get("date", "")
            time = birth_details.get("time", "")
            if date:
                data.append(["Date of Birth:", date])
            if time:
                data.append(["Time of Birth:", time])

            # Add location
            location = birth_details.get("location", "")
            if location:
                data.append(["Location:", location])

            # Add coordinates
            latitude = birth_details.get("latitude", None)
            longitude = birth_details.get("longitude", None)
            if latitude is not None and longitude is not None:
                lat_dir = "N" if latitude >= 0 else "S"
                lon_dir = "E" if longitude >= 0 else "W"
                data.append(["Coordinates:", f"{abs(latitude):.4f}° {lat_dir}, {abs(longitude):.4f}° {lon_dir}"])

            # Add timezone
            timezone = birth_details.get("timezone", "")
            if timezone:
                data.append(["Timezone:", timezone])

            # Create the table if we have data
            if data:
                table = Table(data, colWidths=[1.5*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.25*inch))

    def _add_planet_positions(self, story: List, chart_data: Dict[str, Any]) -> None:
        """
        Add planet positions section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
        """
        # Get planets
        planets = chart_data.get("planets", {})

        if planets:
            # Add a heading for planet positions
            story.append(Paragraph("Planetary Positions", self.styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))

            # Create a table for planet positions
            data = [["Planet", "Sign", "Longitude", "House", "Retrograde"]]

            # Sort planets in traditional order
            traditional_order = [
                "Sun", "Moon", "Mercury", "Venus", "Mars",
                "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
                "North Node", "South Node", "Chiron"
            ]

            sorted_planets = []

            # First add planets in traditional order
            for planet_name in traditional_order:
                # Check case-insensitive match
                for key in planets:
                    if key.lower() == planet_name.lower():
                        sorted_planets.append((key, planets[key]))
                        break

            # Then add any remaining planets
            for planet_name, planet_data in planets.items():
                if not any(name.lower() == planet_name.lower() for name, _ in sorted_planets):
                    sorted_planets.append((planet_name, planet_data))

            # Add data for each planet
            for planet_name, planet_data in sorted_planets:
                # Extract planet information
                sign = planet_data.get("sign", "")
                longitude = planet_data.get("longitude", 0)
                house = planet_data.get("house", "")
                retrograde = "Yes" if planet_data.get("retrograde", False) else "No"

                # Format longitude
                formatted_longitude = f"{longitude:.2f}°"

                # Add row to table
                data.append([planet_name, sign, formatted_longitude, str(house), retrograde])

            # Create the table
            table = Table(data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right-align longitudes
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Center house numbers
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Center retrograde indicator
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25*inch))

    def _add_house_cusps(self, story: List, chart_data: Dict[str, Any]) -> None:
        """
        Add house cusps section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
        """
        # Get houses
        houses = chart_data.get("houses", [])

        if houses:
            # Add a heading for house cusps
            story.append(Paragraph("House Cusps", self.styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))

            # Create a table for house cusps
            data = [["House", "Sign", "Longitude"]]

            # Add data for each house
            for i, house in enumerate(houses):
                house_num = i + 1

                # Handle different house data formats
                if isinstance(house, dict):
                    sign = house.get("sign", "")
                    longitude = house.get("longitude", 0)
                else:
                    # If houses is just a list of longitudes
                    longitude = house
                    sign_num = int(longitude / 30) % 12
                    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                    sign = signs[sign_num]

                # Format longitude
                formatted_longitude = f"{longitude:.2f}°"

                # Add row to table
                data.append([str(house_num), sign, formatted_longitude])

            # Create the table
            table = Table(data, colWidths=[0.8*inch, 1.5*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center house numbers
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right-align longitudes
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25*inch))

    def _add_aspects(self, story: List, chart_data: Dict[str, Any]) -> None:
        """
        Add aspects section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
        """
        # Get aspects
        aspects = chart_data.get("aspects", [])

        if aspects:
            # Add a heading for aspects
            story.append(Paragraph("Planetary Aspects", self.styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))

            # Create a table for aspects
            data = [["Aspect", "Planets", "Orb", "Application"]]

            # Add data for each aspect
            for aspect in aspects:
                if isinstance(aspect, dict):
                    aspect_type = aspect.get("type", "")
                    planet1 = aspect.get("planet1", "")
                    planet2 = aspect.get("planet2", "")
                    orb = aspect.get("orb", 0)
                    applying = aspect.get("applying", False)

                    # Format planets
                    planets = f"{planet1} - {planet2}"

                    # Format orb
                    formatted_orb = f"{orb:.2f}°"

                    # Format application
                    application = "Applying" if applying else "Separating"

                    # Add row to table
                    data.append([aspect_type.capitalize(), planets, formatted_orb, application])

            # Create the table
            table = Table(data, colWidths=[1.2*inch, 2.5*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right-align orbs
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Center application
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25*inch))

    def _add_interpretation(self, story: List, interpretation: Dict[str, Any]) -> None:
        """
        Add interpretation section to PDF.

        Args:
            story: ReportLab story list
            interpretation: Interpretation data
        """
        # Add a heading for interpretation
        story.append(Paragraph("Chart Interpretation", self.styles['Heading1']))
        story.append(Spacer(1, 0.1*inch))

        # Add overall interpretation if available
        overall = interpretation.get("overall", "")
        if overall:
            story.append(Paragraph("Overall", self.styles['Heading2']))
            story.append(Paragraph(overall, self.styles['Interpretation']))
            story.append(Spacer(1, 0.1*inch))

        # Add planet interpretations if available
        planets = interpretation.get("planets", {})
        if planets:
            story.append(Paragraph("Planetary Positions", self.styles['Heading2']))

            for planet, text in planets.items():
                story.append(Paragraph(f"{planet}:", self.styles['Heading2']))
                story.append(Paragraph(text, self.styles['Interpretation']))
                story.append(Spacer(1, 0.1*inch))

        # Add house interpretations if available
        houses = interpretation.get("houses", {})
        if houses:
            story.append(Paragraph("House Placements", self.styles['Heading2']))

            for house, text in houses.items():
                story.append(Paragraph(f"House {house}:", self.styles['Heading2']))
                story.append(Paragraph(text, self.styles['Interpretation']))
                story.append(Spacer(1, 0.1*inch))

        # Add aspect interpretations if available
        aspects = interpretation.get("aspects", [])
        if aspects:
            story.append(Paragraph("Planetary Aspects", self.styles['Heading2']))

            for aspect in aspects:
                if isinstance(aspect, dict):
                    aspect_type = aspect.get("type", "")
                    planet1 = aspect.get("planet1", "")
                    planet2 = aspect.get("planet2", "")
                    interpretation_text = aspect.get("interpretation", "")

                    title = f"{planet1} {aspect_type} {planet2}:"
                    story.append(Paragraph(title, self.styles['Heading2']))
                    story.append(Paragraph(interpretation_text, self.styles['Interpretation']))
                    story.append(Spacer(1, 0.1*inch))

    def _add_divisional_charts(self, story: List, chart_data: Dict[str, Any],
                             divisional_images: Dict[str, str]) -> None:
        """
        Add divisional charts section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
            divisional_images: Dictionary of divisional chart image paths
        """
        if divisional_images:
            # Add a heading for divisional charts
            story.append(Paragraph("Divisional Charts (Vargas)", self.styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))

            # Add explanation
            explanation = """
            Divisional charts (Vargas) are specialized charts derived from the birth chart that
            provide detailed insights into specific areas of life. Each divisional chart focuses
            on different aspects and domains of the native's life.
            """
            story.append(Paragraph(explanation, self.styles['Normal']))
            story.append(Spacer(1, 0.2*inch))

            # Mapping of varga codes to their descriptions
            varga_descriptions = {
                "D1": "Rashi (Birth Chart): Overall life and personality",
                "D2": "Hora: Wealth and prosperity",
                "D3": "Drekkana: Siblings and courage",
                "D4": "Chaturthamsha: Fortune, property, and education",
                "D7": "Saptamsha: Children and progeny",
                "D9": "Navamsha: Spouse, marriage, and dharma",
                "D10": "Dashamsha: Career and profession",
                "D12": "Dwadashamsha: Parents and ancestry",
                "D16": "Shodashamsha: Vehicles and comfort",
                "D20": "Vimshamsha: Spiritual practice and religious activities",
                "D24": "Chaturvimshamsha: Education and knowledge",
                "D27": "Saptavimshamsha: Strength and weakness",
                "D30": "Trimsamsha: Misfortunes and challenges",
                "D40": "Khavedamsha: Auspicious and inauspicious effects",
                "D45": "Akshavedamsha: General good and bad effects",
                "D60": "Shashtyamsha: General karmic effects"
            }

            # Add each divisional chart
            for varga_code, image_path in sorted(divisional_images.items()):
                if os.path.exists(image_path):
                    # Add heading for this varga
                    description = varga_descriptions.get(varga_code, f"{varga_code} Chart")
                    story.append(Paragraph(description, self.styles['Heading2']))
                    story.append(Spacer(1, 0.1*inch))

                    # Add the chart image
                    img = Image(image_path, width=5*inch, height=5*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.25*inch))

    def _add_3d_chart(self, story: List, image_path: Optional[str]) -> None:
        """
        Add 3D chart section to PDF.

        Args:
            story: ReportLab story list
            image_path: Path to 3D chart image
        """
        if image_path and os.path.exists(image_path):
            # Add a heading for 3D chart
            story.append(Paragraph("3D Planetary Positions", self.styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))

            # Add explanation
            explanation = """
            This 3D visualization shows the positions of planets in the zodiac from a three-dimensional
            perspective. The ecliptic plane represents the apparent path of the Sun as seen from Earth,
            while the positions of planets are shown relative to this plane.
            """
            story.append(Paragraph(explanation, self.styles['Normal']))
            story.append(Spacer(1, 0.15*inch))

            # Add the 3D chart image
            img = Image(image_path, width=6*inch, height=5*inch)
            story.append(img)
            story.append(Spacer(1, 0.25*inch))

    def _add_comparison_chart(self, story: List, chart_data: Dict[str, Any], image_path: Optional[str]) -> None:
        """
        Add comparison chart section to PDF.

        Args:
            story: ReportLab story list
            chart_data: Chart data
            image_path: Path to comparison chart image
        """
        if image_path and os.path.exists(image_path):
            # Add a heading for comparison chart
            story.append(Paragraph("Chart Comparison", self.styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))

            # Get original and rectified birth times if available
            original_time = ""
            rectified_time = ""

            if "original_chart" in chart_data and "rectified_chart" in chart_data:
                original_chart = chart_data["original_chart"]
                rectified_chart = chart_data["rectified_chart"]

                if "birth_details" in original_chart:
                    original_time = original_chart["birth_details"].get("time", "")
                elif "birth_data" in original_chart:
                    original_time = original_chart["birth_data"].get("time", "")

                if "birth_details" in rectified_chart:
                    rectified_time = rectified_chart["birth_details"].get("time", "")
                elif "birth_data" in rectified_chart:
                    rectified_time = rectified_chart["birth_data"].get("time", "")

            # Add explanation with times if available
            if original_time and rectified_time:
                explanation = f"""
                This comparison shows the original chart (birth time: {original_time})
                and the rectified chart (birth time: {rectified_time}). The rectification
                process adjusts the birth time to match life events and create a more accurate chart.
                """
            else:
                explanation = """
                This comparison shows the original chart and the rectified chart. The rectification
                process adjusts the birth time to match life events and create a more accurate chart.
                """

            story.append(Paragraph(explanation, self.styles['Normal']))
            story.append(Spacer(1, 0.15*inch))

            # Add the comparison chart image
            img = Image(image_path, width=6.5*inch, height=5*inch)
            story.append(img)
            story.append(Spacer(1, 0.25*inch))

    def _cleanup_temp_files(self, image_files: Dict[str, Any]) -> None:
        """
        Clean up temporary image files.

        Args:
            image_files: Dictionary of image file paths
        """
        try:
            # Remove main image
            if 'main' in image_files and os.path.exists(image_files['main']):
                os.unlink(image_files['main'])

            # Remove 3D image
            if 'three_d' in image_files and os.path.exists(image_files['three_d']):
                os.unlink(image_files['three_d'])

            # Remove planet table image
            if 'planet_table' in image_files and os.path.exists(image_files['planet_table']):
                os.unlink(image_files['planet_table'])

            # Remove divisional images
            if 'divisional' in image_files:
                for path in image_files['divisional'].values():
                    if os.path.exists(path):
                        os.unlink(path)

            # Remove comparison image
            if 'comparison' in image_files and os.path.exists(image_files['comparison']):
                os.unlink(image_files['comparison'])

        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
