"""
WebSocket Service for Birth Time Rectifier

This module provides a WebSocket service for real-time communication
with clients, including progress updates for long-running processes.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    WebSocket manager for real-time updates and progress tracking.

    This class provides methods to send progress updates, error notifications,
    and other real-time events to connected clients via WebSockets.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections = {}
        self.session_data = {}

    async def connect(self, websocket, session_id: str) -> None:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection object
            session_id: Unique session identifier
        """
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_message": None,
            "client_info": {}
        }
        logger.info(f"Client connected with session_id: {session_id}")

        # Send confirmation message
        await self.send_message(
            session_id,
            "connection_established",
            {"status": "connected", "message": "Connection established"}
        )

    async def disconnect(self, session_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            session_id: Unique session identifier
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Client disconnected: {session_id}")

    async def send_message(self, session_id: str, message_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to a connected client.

        Args:
            session_id: Session identifier for the client
            message_type: Type of message (e.g., "progress_update", "error", "complete")
            data: Message payload

        Returns:
            True if the message was sent successfully, False otherwise
        """
        if session_id not in self.active_connections:
            logger.warning(f"Cannot send message to disconnected client: {session_id}")
            return False

        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        try:
            await self.active_connections[session_id].send_json(message)
            self.session_data[session_id]["last_message"] = {
                "type": message_type,
                "timestamp": datetime.now().isoformat()
            }
            return True
        except Exception as e:
            logger.error(f"Error sending message to client {session_id}: {e}")
            return False

    async def emit_rectification_progress(
        self,
        session_id: str,
        progress: int,
        message: str,
        chart_id: str,
        rectification_id: str,
        status: str = "processing",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a rectification progress update to a client.

        Args:
            session_id: Session identifier for the client
            progress: Progress percentage (0-100)
            message: Progress message
            chart_id: ID of the chart being rectified
            rectification_id: ID of the rectification process
            status: Current status (processing, complete, error)
            details: Optional detailed progress information

        Returns:
            True if the update was sent successfully, False otherwise
        """
        # Validate inputs
        if not session_id or not chart_id or not rectification_id:
            logger.error("Missing required parameters for rectification progress update")
            return False

        # Ensure progress is within valid range
        progress = max(0, min(100, progress))

        # Create timestamp
        timestamp = datetime.now().isoformat()

        # Create a structured progress data object
        data = {
            "progress": progress,
            "message": message,
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "status": status,
            "timestamp": timestamp,
            "type": "rectification_progress"
        }

        # Create more detailed progress information based on the stage
        # This provides better client feedback than just a percentage
        current_stage = ""
        techniques = []

        if progress < 10:
            current_stage = "Initializing"
            techniques = ["Preparing data", "Configuring rectification parameters"]
        elif progress >= 10 and progress < 30:
            current_stage = "Loading birth data"
            techniques = ["Calculating initial chart", "Validating birth information"]
        elif progress >= 30 and progress < 60:
            # Basic analysis stage
            current_stage = "Analyzing birth data"
            techniques = details.get("techniques", []) if details else []
            if not techniques:
                techniques = [
                    "Initial chart analysis",
                    "Birth time range determination",
                    "Analyzing planetary positions"
                ]
        elif progress >= 60 and progress < 80:
            # AI enhancement stage
            current_stage = "AI analysis"
            techniques = details.get("techniques", []) if details else []
            if not techniques:
                techniques = [
                    "Astrological pattern recognition",
                    "Transit analysis",
                    "Life event correlation"
                ]
        elif progress >= 80 and progress < 95:
            # Final stage
            current_stage = "Finalizing results"
            techniques = details.get("techniques", []) if details else []
            if not techniques:
                techniques = [
                    "Result validation",
                    "Chart generation",
                    "Comparing rectification methods"
                ]
        elif progress >= 95:
            current_stage = "Completing rectification"
            techniques = ["Generating final chart", "Preparing results"]

        # Add stage and techniques information
        data["current_stage"] = current_stage
        data["techniques"] = techniques

        # Estimate remaining time if in the middle of the process
        if progress > 10 and progress < 90:
            # Get process start time if available
            if details and "start_time" in details:
                start_time = details["start_time"]
                elapsed_seconds = (datetime.now() - start_time).total_seconds()
                if elapsed_seconds > 0 and progress > 0:
                    # Estimate total time based on elapsed time and progress
                    total_estimated_seconds = (elapsed_seconds / progress) * 100
                    remaining_seconds = total_estimated_seconds - elapsed_seconds

                    # Only add time estimate if it's reasonable
                    if 0 < remaining_seconds < 3600:  # Between 0 and 1 hour
                        data["estimated_seconds_remaining"] = int(remaining_seconds)
                        data["elapsed_seconds"] = int(elapsed_seconds)

        # Add detailed information if provided
        if details:
            # Filter out any invalid or sensitive data before sending
            valid_detail_keys = [
                "techniques", "current_step", "total_steps", "time_remaining",
                "phase", "factors_analyzed", "candidate_times", "confidence_levels",
                "rectification_methods", "method_confidences", "chart_changes",
                "significant_aspects", "house_cusps_changes"
            ]

            filtered_details = {k: v for k, v in details.items() if k in valid_detail_keys}
            data["details"] = filtered_details

        # Add subscription channel for easier client handling
        data["channel"] = f"rectification:{chart_id}"

        # Add message sequence ID for client message ordering
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                # Send the message with retry logic
                success = await self.send_message(session_id, "rectification_progress", data)

                if success:
                    logger.info(f"Sent rectification progress update ({progress}%) to session {session_id} for chart {chart_id}")
                    return True
                else:
                    logger.warning(f"Failed to send rectification progress update (attempt {attempt + 1}/{retry_attempts})")
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Error sending rectification progress update (attempt {attempt + 1}/{retry_attempts}): {e}")
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

        # All attempts failed
        logger.error(f"Failed to send rectification progress after {retry_attempts} attempts")
        return False

    async def resend_progress_history(self, session_id: str) -> bool:
        """
        Resend progress history to a client after reconnection.

        Args:
            session_id: Session identifier for the client

        Returns:
            True if history was resent successfully, False otherwise
        """
        if session_id not in self.session_data or "progress_history" not in self.session_data[session_id]:
            logger.info(f"No progress history available for session {session_id}")
            return False

        progress_history = self.session_data[session_id]["progress_history"]
        if not progress_history:
            return True

        # Send all history events with a special flag
        success = True
        for progress_event in progress_history:
            event_data = {**progress_event, "is_history": True}
            if not await self.send_message(session_id, "rectification_progress_history", event_data):
                success = False

        # Send the current status based on the most recent event
        latest = progress_history[-1]
        await self.send_message(
            session_id,
            "rectification_current_status",
            {
                "progress": latest["progress"],
                "message": latest["message"],
                "status": latest["status"],
                "timestamp": latest["timestamp"]
            }
        )

        return success

    async def emit_rectification_complete(
        self,
        session_id: str,
        chart_id: str,
        rectification_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        Send a rectification completion notification to a client.

        Args:
            session_id: Session identifier for the client
            chart_id: ID of the chart being rectified
            rectification_id: ID of the rectification process
            result: Rectification results

        Returns:
            True if the notification was sent successfully, False otherwise
        """
        # Prepare data with required fields
        data = {
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "status": "complete",
            "progress": 100,
            "timestamp": datetime.now().isoformat(),
            "channel": f"rectification:{chart_id}",
            "type": "rectification_complete",
            "message": "Birth time rectification completed successfully"
        }

        # Sanitize and include important result data
        if result:
            # Exclude any potentially sensitive fields
            sanitized_result = {}
            allowed_fields = [
                "rectified_time", "original_time", "confidence_score",
                "rectified_chart_id", "explanation", "time_shift_minutes",
                "rectification_method", "method_confidence", "significant_changes",
                "house_changes", "planet_house_changes"
            ]

            for field in allowed_fields:
                if field in result:
                    sanitized_result[field] = result[field]

            data["result"] = sanitized_result

        # Send with retry logic
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                success = await self.send_message(session_id, "rectification_complete", data)

                if success:
                    logger.info(f"Sent rectification completion notification to session {session_id} for chart {chart_id}")
                    return True
                else:
                    logger.warning(f"Failed to send rectification completion notification (attempt {attempt + 1}/{retry_attempts})")
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Error sending rectification completion notification (attempt {attempt + 1}/{retry_attempts}): {e}")
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

        # All attempts failed
        logger.error(f"Failed to send rectification completion after {retry_attempts} attempts")
        return False

    async def emit_rectification_error(
        self,
        session_id: str,
        chart_id: str,
        rectification_id: str,
        error_message: str,
        error_code: str = "RECTIFICATION_ERROR"
    ) -> bool:
        """
        Send a rectification error notification to a client.

        Args:
            session_id: Session identifier for the client
            chart_id: ID of the chart
            rectification_id: ID of the rectification process
            error_message: Human-readable error message
            error_code: Error code for programmatic handling

        Returns:
            True if the notification was sent successfully, False otherwise
        """
        data = {
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "error_message": error_message,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "type": "rectification_error",
            "channel": f"rectification:{chart_id}",
            "status": "error"
        }

        # Add message sequence ID for client message ordering
        data["sequence_id"] = str(uuid.uuid4())

        try:
            # Send the error notification
            success = await self.send_message(session_id, "rectification_error", data)

            if success:
                logger.info(f"Sent rectification error notification to session {session_id} for chart {chart_id}")
                return True
            else:
                logger.warning(f"Failed to send rectification error notification to session {session_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending rectification error notification: {e}")
            return False

    async def broadcast_rectification_status(
        self,
        chart_id: str,
        status_data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Broadcast a rectification status update to all connected clients.

        Args:
            chart_id: ID of the chart being rectified
            status_data: Status data to broadcast, containing:
                - status: Current status (e.g., "started", "analyzing", "completed")
                - message: Status message
                - progress: Progress percentage (0-100)
                - details: Optional detailed status information

        Returns:
            Dictionary mapping session IDs to success/failure status
        """
        if not chart_id:
            logger.error("Missing chart_id for rectification status broadcast")
            return {}

        # Ensure required fields are in status_data
        required_fields = ["status", "message"]
        for field in required_fields:
            if field not in status_data:
                logger.error(f"Missing required field '{field}' in status_data")
                return {}

        # Ensure progress is provided and within valid range
        progress = status_data.get("progress", 0)
        status_data["progress"] = max(0, min(100, progress))

        # Add timestamp and channel information
        status_data["timestamp"] = datetime.now().isoformat()
        status_data["channel"] = f"rectification:{chart_id}"
        status_data["chart_id"] = chart_id
        status_data["type"] = "rectification_status"

        # Add a unique sequence ID for message ordering
        status_data["sequence_id"] = str(uuid.uuid4())

        # Broadcast to all connected clients
        results = {}
        for session_id, websocket in self.active_connections.items():
            try:
                success = await self.send_message(session_id, "rectification_status", status_data)
                results[session_id] = success

                if success:
                    logger.debug(f"Broadcast rectification status to session {session_id}")
                else:
                    logger.warning(f"Failed to broadcast rectification status to session {session_id}")
            except Exception as e:
                logger.error(f"Error broadcasting rectification status to session {session_id}: {e}")
                results[session_id] = False

        # Log summary of broadcast results
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Broadcast rectification status to {success_count}/{len(results)} connected clients")

        return results

    async def broadcast_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Broadcast a message to all connected clients.

        Args:
            message_type: Type of message
            data: Message payload

        Returns:
            Dictionary mapping session IDs to send success status
        """
        results = {}
        for session_id in self.active_connections:
            results[session_id] = await self.send_message(session_id, message_type, data)
        return results

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for a client."""
        return self.session_data.get(session_id)

# Singleton instance
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """
    Get the WebSocket manager instance (singleton).

    Returns:
        WebSocketManager instance
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
