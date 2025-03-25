"""
WebSocket Events for Birth Time Rectifier API Gateway

This module provides functions for emitting events to WebSocket clients
through the WebSocket proxy.
"""

from typing import Dict, Any, Optional, List, Union
import logging
import asyncio
from datetime import datetime, timedelta
import json
import uuid
import traceback
import time

from api_gateway.websocket_proxy import proxy

# Configure logging
logger = logging.getLogger("api_gateway.websocket_events")

# Store for message and process tracking
_process_start_times: Dict[str, float] = {}

class MessageStore:
    """Store for failed WebSocket messages to enable retries."""

    def __init__(self):
        self.failed_events: Dict[str, List[Dict[str, Any]]] = {}
        self.max_stored_events = 50

    def add_failed_event(self, session_id: str, event: Dict[str, Any]) -> None:
        """Add a failed event to the store."""
        if session_id not in self.failed_events:
            self.failed_events[session_id] = []

        # Add event with metadata for better tracking
        event_with_meta = event.copy()
        if "failed_at" not in event_with_meta:
            event_with_meta["failed_at"] = datetime.now().isoformat()
        if "retry_count" not in event_with_meta:
            event_with_meta["retry_count"] = 0

        self.failed_events[session_id].append(event_with_meta)

        # Limit stored events to prevent memory issues
        if len(self.failed_events[session_id]) > self.max_stored_events:
            self.failed_events[session_id] = self.failed_events[session_id][-self.max_stored_events:]

    def get_failed_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all failed events for a session."""
        return self.failed_events.get(session_id, [])

    def clear_failed_events(self, session_id: str) -> None:
        """Clear all failed events for a session."""
        if session_id in self.failed_events:
            self.failed_events[session_id] = []

    def update_retry_count(self, session_id: str, event_id: str) -> None:
        """Update retry count for an event."""
        if session_id not in self.failed_events:
            return

        for event in self.failed_events[session_id]:
            if event.get("message_id") == event_id:
                event["retry_count"] = event.get("retry_count", 0) + 1
                event["last_retry"] = datetime.now().isoformat()

    def remove_event(self, session_id: str, event_id: str) -> None:
        """Remove an event from the store after successful delivery."""
        if session_id not in self.failed_events:
            return

        self.failed_events[session_id] = [
            event for event in self.failed_events[session_id]
            if event.get("message_id") != event_id
        ]

# Create a singleton message store
message_store = MessageStore()

async def emit_event(
    session_id: str,
    event_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    Emit an event to a WebSocket client with retry capabilities.

    Args:
        session_id: The session ID of the client
        event_type: The type of event to emit
        data: The data to send with the event

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Check if the session is connected
        if session_id not in proxy.active_connections or not proxy.active_connections[session_id]:
            logger.warning(f"Session {session_id} not connected, queuing event for later delivery")

            # Create the event payload
            payload = create_event_payload(event_type, data, session_id)

            # Store for later delivery
            if hasattr(proxy, "message_queues"):
                if session_id not in proxy.message_queues:
                    proxy.message_queues[session_id] = []
                proxy.message_queues[session_id].append(payload)
                logger.info(f"Event {event_type} queued for later delivery to session {session_id}")
                return True
            else:
                message_store.add_failed_event(session_id, payload)
                logger.warning(f"Message queues not available in proxy, stored in local message store")
                return False

        # Create the event payload
        payload = create_event_payload(event_type, data, session_id)

        # Send the event with retry logic
        return await send_event_with_retry(session_id, payload)

    except Exception as e:
        logger.error(f"Error emitting {event_type} event to session {session_id}: {e}")
        # Store failed events for potential retry
        try:
            message_store.add_failed_event(session_id, {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })
        except Exception as store_error:
            logger.error(f"Error storing failed event: {store_error}")
        return False

def create_event_payload(event_type: str, data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Create a standardized event payload."""
    # Generate a unique ID for the event if not provided
    message_id = data.get("message_id") or str(uuid.uuid4())

    # Create the event payload with consistent format
    payload = {
        "type": event_type,
        "data": data,
        "message_id": message_id,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }

    # Add any optional metadata from data
    for meta_key in ["chart_id", "rectification_id", "status"]:
        if meta_key in data:
            payload[meta_key] = data[meta_key]

    return payload

async def send_event_with_retry(session_id: str, payload: Dict[str, Any], max_retries: int = 3) -> bool:
    """Send an event with automatic retry on failure."""
    # Get the client WebSocket
    if not proxy.active_connections.get(session_id):
        logger.warning(f"No active connections for session {session_id}")
        message_store.add_failed_event(session_id, payload)
        return False

    client_ws = proxy.active_connections[session_id][0]
    retry_count = 0
    delay = 0.5  # Initial delay in seconds

    while retry_count <= max_retries:
        try:
            # Send the event
            await client_ws.send_json(payload)
            logger.info(f"Emitted {payload.get('type')} event to session {session_id}")
            return True
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"Error sending event to session {session_id}, retry {retry_count}/{max_retries}: {e}")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to send event after {max_retries} retries: {e}")
                # Store the failed event for later retry
                message_store.add_failed_event(session_id, payload)
                return False

    return False

async def retry_failed_events(session_id: str) -> int:
    """
    Retry sending previously failed events for a session.

    Returns:
        Number of successfully resent events
    """
    if not proxy.active_connections.get(session_id):
        logger.warning(f"Cannot retry events for session {session_id}: not connected")
        return 0

    # Try events from WebSocket proxy message queue first if available
    retried = 0
    if hasattr(proxy, "message_queues") and session_id in proxy.message_queues:
        queue_copy = proxy.message_queues[session_id].copy()
        proxy.message_queues[session_id] = []

        for event in queue_copy:
            try:
                success = await send_event_with_retry(session_id, event, max_retries=1)
                if success:
                    retried += 1
                else:
                    # Put back in queue
                    proxy.message_queues[session_id].append(event)
            except Exception as e:
                logger.error(f"Error retrying queued event: {e}")
                proxy.message_queues[session_id].append(event)

    # Then try from local message store
    failed_events = message_store.get_failed_events(session_id)
    if not failed_events:
        return retried

    # Copy to avoid modification during iteration
    events_to_retry = failed_events.copy()

    # Clear the failed events (successful ones won't be re-added)
    message_store.clear_failed_events(session_id)

    # Retry each failed event
    for event in events_to_retry:
        # Update retry metadata
        event_id = event.get("message_id")
        if event_id:
            message_store.update_retry_count(session_id, event_id)

        # Skip events that have been retried too many times
        if event.get("retry_count", 0) > 5:
            logger.warning(f"Skipping event that has been retried too many times: {event_id}")
            message_store.add_failed_event(session_id, event)  # Keep in store for manual inspection
            continue

        # Add retry flag to indicate this is a retry
        event["is_retry"] = True
        event["retry_timestamp"] = datetime.now().isoformat()

        # Attempt to send the event
        success = await send_event_with_retry(session_id, event, max_retries=1)
        if success:
            retried += 1
            # Remove from the failed events
            if event_id:
                message_store.remove_event(session_id, event_id)
        else:
            # Re-add to the failed events
            message_store.add_failed_event(session_id, event)

    logger.info(f"Retried {retried} events for session {session_id}")
    return retried

async def emit_rectification_progress(
    session_id: str,
    progress: int,
    message: str,
    chart_id: str,
    rectification_id: str = "unknown",
    status: str = "processing",
    result: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    stage: Optional[str] = None,
    sub_stage: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Emit detailed rectification progress updates to WebSocket clients.

    This enhanced implementation provides comprehensive progress information including:
    - Current stage and sub-stage of the rectification process
    - Detailed metrics about the computation
    - Time estimates for completion
    - Visual indicators for progress monitoring
    - Stage-specific details relevant to the current operation

    Args:
        session_id: Session ID for the client
        progress: Overall progress percentage (0-100)
        message: Human-readable progress message
        chart_id: ID of the chart being rectified
        rectification_id: ID of the rectification process
        status: Current status (processing, completed, error)
        result: Optional result data (for completed status)
        details: Optional additional details about the progress
        stage: Current rectification stage (e.g., "analyzing_answers", "calculating_transits")
        sub_stage: Optional sub-stage for more granular progress reporting
        metrics: Optional performance metrics like memory usage, computation time, etc.

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Create progress visualization for better client display
    progress_visualization = generate_progress_visualization(progress)

    # Determine current stage if not provided
    if not stage:
        stage_info = get_stage_info(progress)
        stage = stage_info.get("stage", "unknown")

    # Generate stage-specific progress visualization
    stage_visualization = generate_stage_visualization(stage or "unknown", progress)

    # Calculate time remaining
    estimated_seconds_remaining = _calculate_estimated_time(progress)
    time_remaining = format_time_remaining(estimated_seconds_remaining)

    # Get completed and pending stages
    completed_stages = get_completed_stages(progress)

    # Generate stage analysis with actionable insights
    stage_analysis = generate_progress_analysis(progress, stage or "unknown", status)

    # Compile detailed metrics
    detailed_metrics = {
        "current_progress": progress,
        "progress_rate": metrics.get("progress_rate", 0.5) if metrics else 0.5,  # progress % per second
        "memory_usage": metrics.get("memory_usage", get_process_memory_usage()) if metrics else get_process_memory_usage(),
        "cpu_usage": metrics.get("cpu_usage", get_process_cpu_usage()) if metrics else get_process_cpu_usage(),
        "api_latency": metrics.get("api_latency", get_api_latency_average()) if metrics else get_api_latency_average(),
        "expected_progress": get_expected_progress_at_time(),
        "progress_comparison": progress - get_expected_progress_at_time(),  # positive = faster than expected
    }

    # Generate astrological analysis details based on current stage
    astrological_details = {}
    if stage == "analyzing_answers":
        astrological_details = {
            "indicators_found": details.get("indicators_found", 0) if details else 0,
            "answer_quality": details.get("answer_quality", "medium") if details else "medium",
            "confidence_level": details.get("confidence_level", 0) if details else 0,
            "analysis_method": "AI-powered astrological pattern recognition"
        }
    elif stage == "calculating_transits":
        astrological_details = {
            "transits_analyzed": details.get("transits_analyzed", 0) if details else 0,
            "significant_transits": details.get("significant_transits", 0) if details else 0,
            "analysis_method": "Transit-based verification"
        }
    elif stage == "verifying_chart":
        astrological_details = {
            "verification_method": "Multi-technique Vedic and Western analysis",
            "verification_confidence": details.get("verification_confidence", 0) if details else 0
        }

    # Stage data for response
    stage_data = {
        "name": stage or "unknown",
        "sub_stage": sub_stage,
        "progress": calculate_stage_progress(stage or "unknown", progress),
        "visualization": stage_visualization,
        "analysis": stage_analysis,
        "details": astrological_details
    }

    # Create payload with comprehensive progress information
    payload = {
        "type": "rectification_progress",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "data": {
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "session_id": session_id,
            "progress": progress,
            "status": status,
            "message": message,
            "stage": stage_data,
            "time_estimate": {
                "seconds_remaining": estimated_seconds_remaining,
                "formatted_time": time_remaining.get("formatted", ""),
                "minutes_remaining": time_remaining.get("minutes", 0),
                "seconds_elapsed": int(time.time() - _process_start_times.get(session_id, time.time()))
            },
            "progress_tracking": {
                "visualization": progress_visualization,
                "completed_stages": completed_stages,
                "current_stage_index": len(completed_stages),
                "total_stages": 9,  # Total number of stages in rectification process
                "progress_rate": detailed_metrics["progress_rate"],
                "progress_comparison": detailed_metrics["progress_comparison"]
            },
            "performance_metrics": detailed_metrics
        }
    }

    # Add detailed astrological context if available
    if details and "astrological_context" in details:
        payload["data"]["astrological_context"] = details["astrological_context"]

    # Add result data for completed status
    if status == "completed" and result:
        payload["data"]["result"] = extract_result_summary(result)

    # Add error information if status is error
    if status == "error" and details and "error" in details:
        payload["data"]["error"] = {
            "message": details["error"].get("message", "Unknown error"),
            "code": details["error"].get("code", "UNKNOWN_ERROR"),
            "recovery_steps": details["error"].get("recovery_steps", [])
        }

    # Emit the event
    return await emit_event(session_id, "rectification_progress", payload["data"])

def calculate_stage_progress(stage: str, overall_progress: int) -> int:
    """
    Calculate progress within the current stage.

    Args:
        stage: Current processing stage
        overall_progress: Overall progress percentage (0-100)

    Returns:
        Progress percentage within current stage (0-100)
    """
    # Define stage ranges (when each stage starts and ends in the overall progress)
    stage_ranges = {
        "initialization": (0, 5),
        "data_collection": (5, 15),
        "astrological_analysis": (15, 40),
        "birth_time_determination": (40, 70),
        "chart_calculation": (70, 85),
        "verification": (85, 95),
        "finalization": (95, 100)
    }

    # Get stage range
    stage_range = stage_ranges.get(stage, (0, 100))
    stage_start, stage_end = stage_range

    # If we're past this stage, progress is 100%
    if overall_progress > stage_end:
        return 100

    # If we haven't reached this stage, progress is 0%
    if overall_progress < stage_start:
        return 0

    # Calculate progress within stage
    stage_width = stage_end - stage_start
    if stage_width <= 0:
        return 100  # Prevent division by zero

    stage_progress = ((overall_progress - stage_start) / stage_width) * 100
    return int(stage_progress)

def get_completed_stages(overall_progress: int) -> List[Dict[str, Any]]:
    """
    Get list of completed stages based on overall progress.

    Args:
        overall_progress: Overall progress percentage (0-100)

    Returns:
        List of completed stages with metadata
    """
    # Define stages with their progress thresholds
    all_stages = [
        {"name": "initialization", "threshold": 5, "description": "Setting up rectification process"},
        {"name": "data_collection", "threshold": 15, "description": "Collecting astrological data"},
        {"name": "astrological_analysis", "threshold": 40, "description": "Analyzing astrological factors"},
        {"name": "birth_time_determination", "threshold": 70, "description": "Determining precise birth time"},
        {"name": "chart_calculation", "threshold": 85, "description": "Calculating final birth chart"},
        {"name": "verification", "threshold": 95, "description": "Verifying rectification accuracy"},
        {"name": "finalization", "threshold": 100, "description": "Finalizing results"}
    ]

    # Return stages that have been completed based on the overall progress
    completed_stages = [stage for stage in all_stages if overall_progress >= stage["threshold"]]
    return completed_stages

def get_stage_info_by_name(stage_name: str) -> Dict[str, Any]:
    """
    Get stage information by stage name.

    Args:
        stage_name: Name of the stage

    Returns:
        Stage information dictionary
    """
    # Map of stage information by name
    stage_info_map = {
        "initialization": {
            "stage": "initialization",
            "description": "Setting up rectification process",
            "expected_duration": "30 seconds",
            "complexity_weight": 0.5
        },
        "data_collection": {
            "stage": "data_collection",
            "description": "Collecting birth data and astrological information",
            "expected_duration": "1-2 minutes",
            "complexity_weight": 1.0
        },
        # Add other stages as needed
    }

    # Return the stage info if it exists, otherwise return a default
    if stage_name in stage_info_map:
        return stage_info_map[stage_name]
    else:
        # Return a default stage info if the stage name is not found
        return {
            "stage": stage_name,
            "description": "Processing",
            "expected_duration": "Unknown",
            "complexity_weight": 1.0
        }

def get_stage_info(progress: int) -> Dict[str, Any]:
    """
    Get stage information based on progress percentage with enhanced details.

    Args:
        progress: Progress percentage (0-100)

    Returns:
        Dictionary with stage information
    """
    # Updated stage mapping with more detailed progress steps
    if progress < 5:
        return {
            "stage": "initialization",
            "description": "Setting up rectification process",
            "expected_duration": "30 seconds",
            "complexity_weight": 0.5
        }
    elif progress < 15:
        return {
            "stage": "data_collection",
            "description": "Collecting birth data and astrological information",
            "expected_duration": "1-2 minutes",
            "complexity_weight": 0.7
        }
    elif progress < 40:
        return {
            "stage": "astrological_analysis",
            "description": "Analyzing astrological factors and birth details",
            "expected_duration": "2-5 minutes",
            "complexity_weight": 1.2
        }
    elif progress < 70:
        return {
            "stage": "birth_time_determination",
            "description": "Determining precise birth time through astrological methods",
            "expected_duration": "3-7 minutes",
            "complexity_weight": 1.5
        }
    elif progress < 85:
        return {
            "stage": "chart_calculation",
            "description": "Calculating final birth chart with rectified time",
            "expected_duration": "1-2 minutes",
            "complexity_weight": 0.8
        }
    elif progress < 95:
        return {
            "stage": "verification",
            "description": "Verifying rectification accuracy and results",
            "expected_duration": "1-2 minutes",
            "complexity_weight": 0.9
        }
    else:
        return {
            "stage": "finalization",
            "description": "Finalizing and storing rectification results",
            "expected_duration": "30 seconds",
            "complexity_weight": 0.5
        }

def format_time_duration(seconds: int) -> str:
    """
    Format seconds into a human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} {secs} second{'s' if secs > 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"

def generate_progress_analysis(progress: int, stage: str, status: str) -> Dict[str, Any]:
    """
    Generate an analysis of the current progress status.

    Args:
        progress: Current progress percentage (0-100)
        stage: Current processing stage
        status: Current status (processing, completed, failed)

    Returns:
        Dictionary with progress analysis
    """
    analysis = {
        "stage_summary": "",
        "time_quality": "normal",
        "progress_quality": "normal",
        "recommendations": []
    }

    # Generate stage summary
    if progress < 20:
        analysis["stage_summary"] = "Early processing stages - collecting and preparing data for analysis"
    elif progress < 50:
        analysis["stage_summary"] = "Core analysis in progress - evaluating astrological factors to determine birth time"
    elif progress < 80:
        analysis["stage_summary"] = "Advanced analysis phase - refining birth time based on astrological calculations"
    else:
        analysis["stage_summary"] = "Final processing stages - verifying results and finishing calculations"

    # Determine progress quality
    if status == "processing":
        if progress > 0:
            stage_info = get_stage_info_by_name(stage)
            expected_progress = get_expected_progress_at_time()

            if abs(progress - expected_progress) < 10:
                analysis["progress_quality"] = "normal"
            elif progress > expected_progress + 10:
                analysis["progress_quality"] = "faster than expected"
                analysis["recommendations"].append("Progress is faster than expected - results may be available sooner")
            else:
                analysis["progress_quality"] = "slower than expected"
                analysis["recommendations"].append("Processing is taking longer than usual - complex chart or data")

    return analysis

def get_expected_progress_at_time() -> int:
    """
    Calculate expected progress based on elapsed time.
    In a full implementation, this would use historical data.

    Returns:
        Expected progress percentage
    """
    # Simplified implementation - would normally use historical data
    return 50  # Placeholder value

def get_process_memory_usage() -> float:
    """
    Get current process memory usage in MB.

    Returns:
        Memory usage in MB (0.0 if not available)
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert to MB
    except (ImportError, Exception):
        return 0.0

def get_process_cpu_usage() -> float:
    """
    Get current process CPU usage percentage.

    Returns:
        CPU usage percentage (0.0 if not available)
    """
    try:
        import psutil
        process = psutil.Process()
        return process.cpu_percent(interval=0.1)
    except (ImportError, Exception):
        return 0.0

def get_api_latency_average() -> float:
    """
    Get average API latency in milliseconds.
    In a full implementation, this would track actual API calls.

    Returns:
        API latency in ms (0.0 if not available)
    """
    # Simplified implementation - would normally calculate from metrics
    return 250.0  # Placeholder value

def generate_stage_visualization(stage: str, progress: int) -> Dict[str, Any]:
    """
    Generate a visual representation of progress across all stages.

    Args:
        stage: Current stage
        progress: Overall progress percentage

    Returns:
        Dictionary with stage visualization data
    """
    # Define all stages and their progress ranges
    stages = [
        {"name": "initialization", "range": (0, 5), "symbol": "🔄"},
        {"name": "data_collection", "range": (5, 15), "symbol": "📊"},
        {"name": "astrological_analysis", "range": (15, 40), "symbol": "🔎"},
        {"name": "birth_time_determination", "range": (40, 70), "symbol": "⏱️"},
        {"name": "chart_calculation", "range": (70, 85), "symbol": "📝"},
        {"name": "verification", "range": (85, 95), "symbol": "✓"},
        {"name": "finalization", "range": (95, 100), "symbol": "🏁"}
    ]

    # Mark each stage as current, completed, or upcoming
    stage_statuses = []
    for s in stages:
        if s["name"] == stage:
            status = "current"
        elif progress >= s["range"][1]:
            status = "completed"
        elif progress >= s["range"][0]:
            status = "in_progress"
        else:
            status = "upcoming"

        stage_progress = calculate_stage_progress(s["name"], progress)

        stage_statuses.append({
            "name": s["name"],
            "status": status,
            "progress": stage_progress,
            "symbol": s["symbol"]
        })

    # Create a visualization string
    visualization = " → ".join([f"{s['symbol']}" if s['status'] == 'completed' else
                              f"[{s['symbol']}]" if s['status'] == 'current' else
                              f"{s['symbol']}" for s in stage_statuses])

    return {
        "stages": stage_statuses,
        "visualization": visualization,
        "current_stage": stage,
        "current_stage_index": next((i for i, s in enumerate(stage_statuses) if s["name"] == stage), 0)
    }

def get_confidence_description(confidence: float) -> str:
    """
    Get human-readable description of confidence level.

    Args:
        confidence: Confidence value (0-100)

    Returns:
        Confidence description
    """
    if confidence >= 90:
        return "Very high confidence"
    elif confidence >= 75:
        return "High confidence"
    elif confidence >= 60:
        return "Good confidence"
    elif confidence >= 45:
        return "Moderate confidence"
    elif confidence >= 30:
        return "Low confidence"
    else:
        return "Very low confidence"

def generate_progress_visualization(progress: int) -> Dict[str, Any]:
    """
    Generate a visual representation of progress.

    Args:
        progress: Progress percentage (0-100)

    Returns:
        Dictionary with visualization data
    """
    # Number of segments in progress bar
    segments = 20
    completed_segments = int((progress / 100) * segments)

    # Generate progress bar
    progress_bar = "█" * completed_segments + "░" * (segments - completed_segments)

    # Calculate color based on progress (goes from red to green)
    r = max(0, int(255 * (1 - progress / 100)))
    g = max(0, int(255 * (progress / 100)))
    b = 0

    # Format as hex
    color = f"#{r:02x}{g:02x}{b:02x}"

    return {
        "bar": progress_bar,
        "segments": segments,
        "completed": completed_segments,
        "color": color,
        "text": f"{progress}%"
    }

def _calculate_estimated_time(progress: int) -> float:
    """
    Calculate estimated total time based on progress percentage.

    Args:
        progress: Current progress percentage

    Returns:
        Estimated total time in seconds
    """
    # This is a heuristic calculation based on the rectification process
    if progress < 10:
        # Early stages are usually quick
        return 180  # 3 minutes
    elif progress < 30:
        # AI analysis phase
        return 300  # 5 minutes
    elif progress < 60:
        # Calculation-heavy phase
        return 420  # 7 minutes
    else:
        # Final stages
        return 480  # 8 minutes

def format_time_remaining(seconds_remaining: Union[int, float]) -> Dict[str, Union[int, str]]:
    """
    Format time remaining in a human-readable way.

    Args:
        seconds_remaining: Remaining time in seconds

    Returns:
        Dictionary with formatted time values
    """
    # Convert float to int
    seconds_remaining = int(seconds_remaining)

    if seconds_remaining <= 0:
        return {
            "seconds": 0,
            "formatted": "Complete",
            "formatted_long": "Complete"
        }

    minutes, seconds = divmod(seconds_remaining, 60)
    hours, minutes = divmod(minutes, 60)

    # Short format (e.g., "2m 30s")
    if hours > 0:
        formatted = f"{hours}h {minutes}m"
    elif minutes > 0:
        formatted = f"{minutes}m {seconds}s"
    else:
        formatted = f"{seconds}s"

    # Long format (e.g., "2 minutes 30 seconds")
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or (hours == 0 and minutes == 0):
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    formatted_long = ", ".join(parts)

    return {
        "hours": int(hours),
        "minutes": int(minutes),
        "seconds": int(seconds),
        "total_seconds": seconds_remaining,
        "formatted": formatted,
        "formatted_long": formatted_long
    }

def extract_result_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a summary of rectification results for WebSocket event.

    Args:
        result: Full rectification result

    Returns:
        Dictionary with summarized result information
    """
    # Extract key information from the result
    summary = {
        "original_time": result.get("original_time", "Unknown"),
        "rectified_time": result.get("rectified_time_str", result.get("rectified_time", "Unknown")),
        "confidence": result.get("confidence", 0),
        "method": result.get("method", "Unknown")
    }

    # Add time difference if available
    if "time_difference" in result:
        summary["time_difference"] = result["time_difference"]
    elif "original_time" in result and "rectified_time_str" in result:
        original = result["original_time"]
        rectified = result["rectified_time_str"]

        # Calculate time difference if both times are available as strings
        try:
            from datetime import datetime
            # Handle different time formats
            format_with_seconds = "%H:%M:%S"
            format_without_seconds = "%H:%M"

            try:
                original_time = datetime.strptime(original, format_with_seconds).time()
            except ValueError:
                original_time = datetime.strptime(original, format_without_seconds).time()

            try:
                rectified_time = datetime.strptime(rectified, format_with_seconds).time()
            except ValueError:
                rectified_time = datetime.strptime(rectified, format_without_seconds).time()

            # Calculate difference in minutes
            original_minutes = original_time.hour * 60 + original_time.minute
            rectified_minutes = rectified_time.hour * 60 + rectified_time.minute

            # Handle cross-midnight cases
            if abs(rectified_minutes - original_minutes) > 720:
                # If difference is more than 12 hours, adjust by 24 hours
                if rectified_minutes > original_minutes:
                    rectified_minutes -= 1440  # Subtract 24 hours in minutes
                else:
                    original_minutes -= 1440

            difference = rectified_minutes - original_minutes
            minutes = abs(difference)
            direction = "earlier" if difference < 0 else "later"

            summary["time_difference"] = {
                "minutes": minutes,
                "direction": direction,
                "formatted": f"{minutes} minutes {direction}"
            }
        except Exception as e:
            logger.warning(f"Failed to calculate time difference: {e}")

    # Add astrological factors if available
    if "astrological_factors" in result:
        summary["key_factors"] = result["astrological_factors"][:3] if len(result["astrological_factors"]) > 3 else result["astrological_factors"]

    # Add chart changes if available
    if "chart_changes" in result:
        summary["chart_changes"] = {
            "ascendant_change": result["chart_changes"].get("ascendant_change"),
            "house_cusps_shifted": result["chart_changes"].get("house_cusps_shifted", False),
            "planets_house_shifts": result["chart_changes"].get("planets_house_shifts", [])
        }

    # Add a brief explanation if available
    if "explanation" in result:
        # Truncate long explanations
        explanation = result["explanation"]
        if len(explanation) > 200:
            explanation = explanation[:197] + "..."
        summary["brief_explanation"] = explanation

    return summary

async def emit_rectification_status_update(
    session_id: str,
    chart_id: str,
    current_step: str,
    total_steps: int,
    current_step_index: int,
    method_name: str,
    confidence: float,
    estimated_time_remaining: int,
    status: str = "processing",
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Emit detailed rectification status update with step-by-step information.

    Args:
        session_id: Session ID to send event to
        chart_id: ID of the chart being rectified
        current_step: Name of the current rectification step
        total_steps: Total number of steps in the process
        current_step_index: Index of the current step (1-based)
        method_name: Name of the rectification method being used
        confidence: Current confidence level (0-100)
        estimated_time_remaining: Estimated time remaining in seconds
        status: Status string (processing, completed, failed)
        details: Optional detailed information for current step

    Returns:
        True if event was emitted successfully, False otherwise
    """
    try:
        # Calculate progress percentage
        progress = int((current_step_index / total_steps) * 100) if total_steps > 0 else 0

        # Ensure progress is within bounds
        progress = max(0, min(100, progress))

        # Format time remaining
        time_info = format_time_remaining(estimated_time_remaining)

        # Create event data
        event_data = {
            "chart_id": chart_id,
            "status": status,
            "progress": progress,
            "step": {
                "name": current_step,
                "index": current_step_index,
                "total": total_steps,
                "progress": f"{current_step_index}/{total_steps}"
            },
            "method": method_name,
            "confidence": confidence,
            "time_remaining": time_info,
            "timestamp": time.time()
        }

        # Add progress visualization
        event_data["progress_visualization"] = generate_progress_visualization(progress)

        # Add details if provided
        if details:
            event_data["details"] = details

        # Emit the event
        return await emit_event(session_id, "rectification_status", event_data)

    except Exception as e:
        logger.error(f"Error emitting rectification status update: {e}")
        logger.error(traceback.format_exc())
        return False

async def emit_rectification_complete(
    session_id: str,
    chart_id: str,
    rectification_id: str,
    result: Dict[str, Any]
) -> bool:
    """
    Emit a rectification complete event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        chart_id: The chart ID that was rectified
        rectification_id: The ID of the rectification process
        result: The rectification result data

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Validate inputs
        if not session_id or not chart_id or not rectification_id:
            logger.error("Missing required parameters for rectification complete event")
            return False

        # Create the event data
        event_data = {
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "status": "complete",
            "progress": 100,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "message": "Birth time rectification completed successfully"
        }

        # Add information about accuracy and confidence
        if "confidence_score" in result:
            confidence = result["confidence_score"]

            if confidence >= 90:
                event_data["confidence_level"] = "very high"
                event_data["message"] += " with very high confidence"
            elif confidence >= 75:
                event_data["confidence_level"] = "high"
                event_data["message"] += " with high confidence"
            elif confidence >= 60:
                event_data["confidence_level"] = "medium"
                event_data["message"] += " with medium confidence"
            else:
                event_data["confidence_level"] = "low"
                event_data["message"] += " with low confidence"

        # Emit the event
        success = await emit_event(session_id, "rectification_complete", event_data)

        if not success:
            logger.warning(f"Failed to send rectification complete event to session {session_id}")

        return success

    except Exception as e:
        logger.error(f"Error emitting rectification complete event: {e}")
        logger.error(traceback.format_exc())
        return False

async def emit_rectification_error(
    session_id: str,
    chart_id: str,
    rectification_id: str,
    error_message: str,
    error_code: str = "RECTIFICATION_ERROR",
    recovery_instructions: Optional[str] = None
) -> bool:
    """
    Emit a rectification error event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        chart_id: The chart ID being rectified
        rectification_id: The ID of the rectification process
        error_message: The error message
        error_code: An error code for classification
        recovery_instructions: Optional instructions for recovering from the error

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Create the error event data
        event_data = {
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": {
                "message": error_message,
                "code": error_code
            }
        }

        # Add recovery instructions if provided
        if recovery_instructions:
            event_data["error"]["recovery_instructions"] = recovery_instructions

        # Categorize the error
        if "timeout" in error_message.lower() or "deadline" in error_message.lower():
            event_data["error"]["category"] = "timeout"
            if not recovery_instructions:
                event_data["error"]["recovery_instructions"] = "Please try again later when the system is less busy."
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            event_data["error"]["category"] = "permission"
            if not recovery_instructions:
                event_data["error"]["recovery_instructions"] = "Please verify your account has access to this feature."
        elif "validation" in error_message.lower() or "invalid" in error_message.lower():
            event_data["error"]["category"] = "validation"
            if not recovery_instructions:
                event_data["error"]["recovery_instructions"] = "Please check your input data and try again."
        else:
            event_data["error"]["category"] = "general"
            if not recovery_instructions:
                event_data["error"]["recovery_instructions"] = "Please try again or contact support if the issue persists."

        # Emit the error event
        return await emit_event(session_id, "rectification_error", event_data)

    except Exception as e:
        logger.error(f"Error emitting rectification error event: {e}")
        logger.error(traceback.format_exc())

        # Try a simplified error message as a last resort
        try:
            simple_error = {
                "type": "error",
                "chart_id": chart_id,
                "message": f"Error: {error_message}",
                "timestamp": datetime.now().isoformat()
            }

            if session_id in proxy.active_connections and proxy.active_connections[session_id]:
                await proxy.active_connections[session_id][0].send_json(simple_error)
                return True
        except Exception:
            pass

        return False
