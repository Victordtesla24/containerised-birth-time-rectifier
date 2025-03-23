# Birth Time Rectifier Gap Resolution Prompt

## Overview

This prompt is designed to guide AI in implementing precise, production-ready fixes for all identified gaps in the Birth Time Rectifier backend services. The implementation must follow proper software engineering practices without resorting to mockups, simulated fallbacks, or error masking.

## Context

The Birth Time Rectifier application has several critical implementation gaps that prevent it from functioning correctly in production. These gaps have been identified in the `gap_analysis.md` document and need comprehensive fixes that adhere to the expected application flow detailed in the sequence diagram.

## Implementation Requirements

1. **No Mockups or Simulations**: Implement real, fully functional code instead of mockups or simulations.
2. **No Fallback Mechanisms** that mask errors by returning inaccurate results.
3. **No Warning Suppression**: Do not ignore or suppress warnings; address the root causes.
4. **Complete Implementation**: Fully implement all required functionality without partial implementations.
5. **Proper Error Handling**: Implement comprehensive error handling for all edge cases.
6. **Consistent Integration**: Ensure consistent integration with all services, particularly OpenAI and database.
7. **Follow Sequence Diagram Flow**: Implementations must follow the sequence diagram flow in `docs/architecture/sequence_diagram.md`.
8. **Proper Validation**: Include validation for all inputs and outputs.

## Key Gap Areas

### 1. Chart Service Implementations

#### 1.1 Chart Export Functionality

**Current Issue**: The export function creates metadata but doesn't actually generate PDF or image files.

**Required Implementation**:
```python
def export_chart(chart_data, chart_output_dir=None, format="pdf", ...):
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

#### 1.2 OpenAI Integration for Rectification

**Current Issue**: The rectification process doesn't properly leverage OpenAI integration.

**Required Implementation**:
```python
async def update_chart_with_rectification(self, chart_id: str, rectification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a chart with rectification results and verify with OpenAI.
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

### 2. Chart Visualization Issues

#### 2.1 Vedic Chart Visualization Integration

**Current Issue**: Vedic chart visualization exists but isn't properly integrated with the export system.

**Required Implementation**:
```python
def generate_vedic_chart(chart_data, output_path=None, style="north_indian"):
    """
    Generate a Vedic chart visualization with proper export integration.
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

#### 2.2 PDF Generation Enhancement

**Current Issue**: PDF generation function doesn't create production-quality reports.

**Required Implementation**:
```python
def generate_chart_pdf(chart_data, output_path, include_interpretation=True, include_aspects=True,
                      include_houses=True, include_transits=False, paper_size="letter"):
    """
    Generate a comprehensive production-quality PDF chart report.
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

### 3. Core Rectification Issues

#### 3.1 Astrological Library Fallback Issue

**Current Issue**: Code creates dummy implementations when astrological libraries are not available instead of using proper fallbacks.

**Required Implementation**:
```python
# Import with proper alternative library support
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
    CALCULATION_ENGINE = "swisseph"
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
    """Calculate astrological chart with proper fallback mechanisms."""
    if CALCULATION_ENGINE is None:
        raise EphemerisError("No calculation engines available. Cannot generate chart.")

    if CALCULATION_ENGINE == "swisseph":
        return _calculate_chart_swisseph(birth_dt, latitude, longitude, timezone_str, house_system)
    elif CALCULATION_ENGINE == "flatlib":
        return _calculate_chart_flatlib(birth_dt, latitude, longitude, timezone_str, house_system)
    else:
        # This should never happen due to import checks above, but as a safeguard:
        raise EphemerisError("Unknown calculation engine. Cannot generate chart.")
```

#### 3.2 Transit Analysis Enhancement

**Current Issue**: If Flatlib is not available, returns original time with very low confidence for transit analysis.

**Required Implementation**:
```python
def transit_analysis(birth_dt, latitude, longitude, timezone, events, answers=None):
    """
    Perform transit analysis for birth time rectification with multiple calculation engines.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        events: List of life events
        answers: Optional questionnaire answers

    Returns:
        Tuple of (rectified_datetime, confidence_score)
    """
    try:
        # First attempt with primary engine (Flatlib)
        if FLATLIB_AVAILABLE:
            try:
                return _transit_analysis_flatlib(birth_dt, latitude, longitude, timezone, events, answers)
            except Exception as e:
                logger.warning(f"Error in primary transit analysis: {e}")
                # Continue to fallback methods

        # Second attempt with SwissEph
        if SWISSEPH_AVAILABLE:
            try:
                return _transit_analysis_swisseph(birth_dt, latitude, longitude, timezone, events, answers)
            except Exception as e:
                logger.warning(f"Error in secondary transit analysis: {e}")
                # Continue to fallback methods

        # Fallback to event-based rectification if both primary methods fail
        if events and len(events) >= 3:
            # Use event-based rectification method
            return _event_based_rectification(birth_dt, latitude, longitude, timezone, events)

        # If all else fails, try to use answers if available
        if answers and len(answers) >= 5:
            # Use answer-based rectification
            return _answer_based_rectification(birth_dt, answers)

        # If we've exhausted all methods, we cannot proceed with rectification
        logger.error("All transit analysis methods failed. Cannot rectify birth time.")
        raise RectificationError("All transit analysis methods failed")

    except Exception as e:
        logger.error(f"Error in transit analysis: {e}")
        logger.error(traceback.format_exc())
        # Don't return low confidence result; raise the error so user knows rectification failed
        raise RectificationError(f"Transit analysis failed: {str(e)}")
```

#### 3.3 No Answers Rectification Enhancement

**Current Issue**: Returns original time with low confidence if no answers provided, without attempting alternative rectification methods.

**Required Implementation**:
```python
def rectify_birth_time(birth_dt, latitude, longitude, timezone_str, answers=None, events=None):
    """
    Rectify birth time using multiple methods and fallbacks.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone_str: Timezone string
        answers: Optional questionnaire answers
        events: Optional list of life events

    Returns:
        Dict with rectified time and confidence
    """
    # Track all attempted methods and their results
    attempted_methods = []
    error_messages = []

    # Try answer-based rectification first if answers are available
    if answers and len(answers) >= 3:
        try:
            rectified_dt, confidence = answer_based_rectification(birth_dt, latitude, longitude, timezone_str, answers)
            attempted_methods.append({"method": "answer_based", "confidence": confidence})
            # If confidence is high enough, return immediately
            if confidence >= 75:
                return {
                    "rectified_time": rectified_dt,
                    "confidence": confidence,
                    "method": "answer_based",
                    "attempted_methods": attempted_methods
                }
        except Exception as e:
            error_messages.append(f"Answer-based rectification failed: {str(e)}")

    # Try event-based rectification if events are available
    if events and len(events) >= 2:
        try:
            rectified_dt, confidence = event_based_rectification(birth_dt, latitude, longitude, timezone_str, events)
            attempted_methods.append({"method": "event_based", "confidence": confidence})
            # If confidence is high enough, return immediately
            if confidence >= 70:
                return {
                    "rectified_time": rectified_dt,
                    "confidence": confidence,
                    "method": "event_based",
                    "attempted_methods": attempted_methods
                }
        except Exception as e:
            error_messages.append(f"Event-based rectification failed: {str(e)}")

    # Try transit analysis as another method
    try:
        rectified_dt, confidence = transit_analysis(birth_dt, latitude, longitude, timezone_str, events)
        attempted_methods.append({"method": "transit_analysis", "confidence": confidence})
        # If confidence is high enough, return immediately
        if confidence >= 65:
            return {
                "rectified_time": rectified_dt,
                "confidence": confidence,
                "method": "transit_analysis",
                "attempted_methods": attempted_methods
            }
    except Exception as e:
        error_messages.append(f"Transit analysis failed: {str(e)}")

    # Try AI-assisted rectification as a last resort
    try:
        rectified_dt, confidence = ai_rectification(birth_dt, latitude, longitude, timezone_str, answers, events)
        attempted_methods.append({"method": "ai_assisted", "confidence": confidence})
        return {
            "rectified_time": rectified_dt,
            "confidence": confidence,
            "method": "ai_assisted",
            "attempted_methods": attempted_methods
        }
    except Exception as e:
        error_messages.append(f"AI-assisted rectification failed: {str(e)}")

    # If all methods have been attempted but none yielded a good result,
    # take the result with the highest confidence
    if attempted_methods:
        best_method = max(attempted_methods, key=lambda x: x["confidence"])
        # Get the result from the method with highest confidence
        for method_name, method_func in [
            ("answer_based", answer_based_rectification),
            ("event_based", event_based_rectification),
            ("transit_analysis", transit_analysis),
            ("ai_assisted", ai_rectification)
        ]:
            if method_name == best_method["method"]:
                try:
                    params = [birth_dt, latitude, longitude, timezone_str]
                    if method_name == "answer_based":
                        params.append(answers)
                    elif method_name in ["event_based", "transit_analysis"]:
                        params.append(events)
                    elif method_name == "ai_assisted":
                        params.extend([answers, events])

                    rectified_dt, _ = method_func(*params)
                    return {
                        "rectified_time": rectified_dt,
                        "confidence": best_method["confidence"],
                        "method": best_method["method"],
                        "attempted_methods": attempted_methods,
                        "warning": "Limited confidence in rectification. Multiple methods attempted."
                    }
                except Exception:
                    # If we can't re-run the best method, fall back to a more drastic approach
                    pass

    # If we've made it here, all methods failed
    raise RectificationError(f"All rectification methods failed: {', '.join(error_messages)}")
```

### 4. WebSocket Implementation

#### 4.1 WebSocket Reconnection Logic

**Current Issue**: WebSocket client doesn't properly handle connection failures and reconnection logic.

**Required Implementation**:
```typescript
class WebSocketService extends EventEmitter {
    private ws: WebSocket | null = null;
    private url: string;
    private sessionId: string;
    private reconnectAttempt: number = 0;
    private maxReconnectAttempts: number = 5;
    private reconnectInterval: number = 1000; // Start with 1 second
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private pingInterval: ReturnType<typeof setInterval> | null = null;
    private lastPongTime: number = 0;
    private connectionStatus = {
        connected: false,
        connecting: false,
        reconnecting: false
    };

    constructor(url: string, sessionId: string) {
        super();
        this.url = url;
        this.sessionId = sessionId;
        this.lastPongTime = Date.now();
    }

    public connect(): void {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return; // Already connected or connecting
        }

        this.connectionStatus.connecting = true;
        this.emit('connecting');

        try {
            // Construct URL with session ID
            const fullUrl = `${this.url}/${this.sessionId}`;
            this.ws = new WebSocket(fullUrl);

            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onerror = this.handleError.bind(this);
            this.ws.onclose = this.handleClose.bind(this);

            // Set up ping interval for connection health monitoring
            this.setupPingInterval();
        } catch (error) {
            this.handleError(error as Event);
        }
    }

    public disconnect(): void {
        this.stopReconnectTimer();
        this.stopPingInterval();

        if (this.ws) {
            try {
                this.ws.close();
            } catch (e) {
                console.error('Error closing WebSocket:', e);
            }
            this.ws = null;
        }

        this.connectionStatus.connected = false;
        this.connectionStatus.connecting = false;
        this.connectionStatus.reconnecting = false;
        this.emit('disconnected');
    }

    public send(data: any): boolean {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.log('Cannot send message, WebSocket is not open');
            return false;
        }

        try {
            // Ensure data has a timestamp
            if (typeof data === 'object' && data !== null) {
                data.timestamp = new Date().toISOString();
            }

            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.ws.send(message);
            return true;
        } catch (error) {
            this.log('Error sending message:', error);
            this.emit('send_error', error);
            return false;
        }
    }

    private handleOpen(event: Event): void {
        this.log('WebSocket connection established');
        this.reconnectAttempt = 0; // Reset reconnect attempt counter on successful connection

        this.connectionStatus.connected = true;
        this.connectionStatus.connecting = false;
        this.connectionStatus.reconnecting = false;

        this.emit('connected');

        // Send authentication message
        this.send({
            type: 'authenticate',
            session_id: this.sessionId,
            timestamp: new Date().toISOString()
        });
    }

    private handleMessage(event: MessageEvent): void {
        try {
            const data = JSON.parse(event.data);

            // Handle different message types
            if (data.type === 'pong') {
                this.lastPongTime = Date.now();
                return; // Don't emit pong messages
            } else if (data.type === 'connection_status') {
                this.handleConnectionStatusMessage(data);
            } else if (data.type === 'error') {
                this.handleErrorMessage(data);
            } else if (data.type === 'rectification_progress') {
                this.handleRectificationProgressMessage(data);
            } else {
                // Generic message handling
                this.emit('message', data);
            }
        } catch (error) {
            this.log('Error parsing message:', event.data, error);
            this.emit('parse_error', { error, rawData: event.data });
        }
    }

    private handleError(event: Event): void {
        this.log('WebSocket error:', event);
        this.emit('error', event);

        // Don't attempt reconnect here, let onclose handle it
        // as error is typically followed by close
    }

    private handleClose(event: CloseEvent): void {
        this.log(`WebSocket closed: ${event.code} - ${event.reason}`);

        this.connectionStatus.connected = false;
        this.stopPingInterval();

        // Attempt reconnection with exponential backoff
        if (this.reconnectAttempt < this.maxReconnectAttempts) {
            this.connectionStatus.reconnecting = true;

            const delay = this.calculateReconnectDelay();
            this.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempt + 1}/${this.maxReconnectAttempts})`);

            this.emit('reconnecting', {
                attempt: this.reconnectAttempt + 1,
                maxAttempts: this.maxReconnectAttempts,
                delay
            });

            this.reconnectTimer = setTimeout(() => {
                this.reconnectAttempt++;
                this.connect();
            }, delay);
        } else {
            this.connectionStatus.reconnecting = false;
            this.emit('max_reconnect_attempts', {
                attempts: this.maxReconnectAttempts,
                code: event.code,
                reason: event.reason
            });
        }
    }

    private calculateReconnectDelay(): number {
        // Exponential backoff with jitter
