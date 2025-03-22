"""
Utilities for request tracing and transaction tracking.
"""
import os
import uuid
import asyncio
import logging
import contextvars
import functools
import time
import json
from typing import Optional, Dict, Any, Callable, Awaitable, Union, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Create a context variable to store the current trace ID
# Note: default is None but it can store str values
trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('trace_id', default=None)

# Custom Context class to hold various trace identifiers
class Context:
    """Class to store context information for request tracing."""

    def __init__(self):
        """Initialize with default values."""
        self.trace_id = None
        self.request_id = None
        self.session_id = None
        self.user_id = None

def get_trace_id() -> str:
    """
    Get the current trace ID from the context or environment.
    If not found, generate a new one.

    Returns:
        Current trace ID
    """
    trace_id = trace_id_var.get()
    if trace_id is None:
        # Try to get from environment
        trace_id = os.environ.get("TRACE_ID")
        if trace_id is None:
            # Generate a new trace ID
            trace_id = str(uuid.uuid4())
        # Set in context var
        trace_id_var.set(trace_id)
    return trace_id

def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Set trace ID in the context.

    Args:
        trace_id: Optional trace ID to set. If None, a new one will be generated.

    Returns:
        The trace ID that was set
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())

    trace_id_var.set(trace_id)
    return trace_id

def with_trace_id(func):
    """
    Decorator for adding trace ID propagation to regular functions.

    Args:
        func: The function to wrap

    Returns:
        Wrapped function with trace ID handling
    """
    def wrapper(*args, trace_id=None, **kwargs):
        # Use provided trace ID or retrieve current one
        current_trace_id = trace_id or get_trace_id()

        # Set trace ID in context
        token = trace_id_var.set(current_trace_id)

        try:
            # Call the function
            return func(*args, **kwargs)
        finally:
            # Reset context to previous value
            trace_id_var.reset(token)

    return wrapper

def with_async_trace_id(func):
    """
    Decorator for adding trace ID propagation to async functions.

    Args:
        func: The async function to wrap

    Returns:
        Wrapped async function with trace ID handling
    """
    async def wrapper(*args, trace_id=None, **kwargs):
        # Use provided trace ID or retrieve current one
        current_trace_id = trace_id or get_trace_id()

        # Set trace ID in context
        token = trace_id_var.set(current_trace_id)

        try:
            # Run the async function with the trace ID
            return await func(*args, trace_id=current_trace_id, **kwargs)
        finally:
            # Reset the context
            trace_id_var.reset(token)

    return wrapper

class TracingContextManager:
    """
    Context manager for trace ID propagation.

    Example:
        with TracingContextManager(trace_id='custom-id'):
            # Code inside this block will have access to the trace ID
            current_id = get_trace_id()
    """
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or get_trace_id()
        self.token = None

    def __enter__(self):
        self.token = trace_id_var.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            trace_id_var.reset(self.token)

class AsyncTracingContextManager:
    """
    Async context manager for trace ID propagation.

    Example:
        async with AsyncTracingContextManager(trace_id='custom-id'):
            # Async code inside this block will have access to the trace ID
            current_id = get_trace_id()
    """
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or get_trace_id()
        self.token = None

    async def __aenter__(self):
        self.token = trace_id_var.set(self.trace_id)
        return self.trace_id

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            trace_id_var.reset(self.token)

def trace_log(message: str, level: str = "info", **kwargs):
    """
    Log a message with the current trace ID.

    Args:
        message: The message to log
        level: The log level (debug, info, warning, error, critical)
        **kwargs: Additional key-value pairs to include in the log
    """
    trace_id = get_trace_id()

    log_data = {
        "trace_id": trace_id,
        **kwargs
    }

    # Format log message with trace ID prefix
    formatted_message = f"[{trace_id}] {message}"

    # Log at the appropriate level
    if level == "debug":
        logger.debug(formatted_message, extra=log_data)
    elif level == "info":
        logger.info(formatted_message, extra=log_data)
    elif level == "warning":
        logger.warning(formatted_message, extra=log_data)
    elif level == "error":
        logger.error(formatted_message, extra=log_data)
    elif level == "critical":
        logger.critical(formatted_message, extra=log_data)
    else:
        # Default to info
        logger.info(formatted_message, extra=log_data)

class HeaderInjector:
    """Injects trace IDs into request headers."""

    def __init__(self, context: Context):
        """Initialize with a context instance."""
        self.context = context

    def inject_headers(self, headers: Dict[str, str]) -> None:
        """Inject trace IDs into headers."""
        if self.context.trace_id:
            headers["X-Trace-ID"] = self.context.trace_id
        if self.context.request_id:
            headers["X-Request-ID"] = self.context.request_id
        if self.context.session_id:
            headers["X-Session-ID"] = self.context.session_id
        if self.context.user_id:
            headers["X-User-ID"] = self.context.user_id

    def set(self, key: str, value: Any) -> None:
        """Set a context value."""
        setattr(self.context, key, value)

    def get(self, key: str) -> Optional[str]:
        """Get a context value."""
        return getattr(self.context, key, None)

class TransactionTracker:
    """Track API transactions and function calls throughout the request flow."""

    def __init__(self):
        """Initialize a new transaction tracker."""
        self.current_transaction = None
        self.transactions = []
        self.current_phase = None
        self.trace_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.metadata = {}

    def start_transaction(self, name: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start a new transaction.

        Args:
            name: Name of the transaction
            details: Additional details about the transaction

        Returns:
            Transaction data dictionary
        """
        transaction = {
            "name": name,
            "phase": self.current_phase,
            "trace_id": self.trace_id,
            "start_time": datetime.now(),
            "end_time": None,
            "duration_ms": None,
            "status": "in_progress",
            "details": details or {},
            "error": None,
            "parent_transaction": self.current_transaction["name"] if self.current_transaction else None
        }

        # Set the parent transaction to simplify building a transaction tree
        if self.current_transaction:
            self.current_transaction["child_transactions"] = self.current_transaction.get("child_transactions", []) + [name]

        # Update current transaction
        previous_transaction = self.current_transaction
        self.current_transaction = transaction
        self.transactions.append(transaction)

        logger.info(f"Transaction started: {name} (Trace: {self.trace_id})")
        return transaction

    def end_transaction(self, status: str = "completed", error: Optional[Exception] = None) -> Optional[Dict[str, Any]]:
        """
        End the current transaction.

        Args:
            status: Status of the transaction (completed, failed, etc.)
            error: Exception if the transaction failed

        Returns:
            The completed transaction data or None if no transaction was active
        """
        if not self.current_transaction:
            logger.warning("Attempting to end a transaction when none is active")
            return None

        self.current_transaction["end_time"] = datetime.now()
        self.current_transaction["status"] = status

        # Calculate duration in milliseconds
        start = self.current_transaction["start_time"]
        end = self.current_transaction["end_time"]
        duration_ms = (end - start).total_seconds() * 1000
        self.current_transaction["duration_ms"] = round(duration_ms, 2)

        if error:
            self.current_transaction["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "details": getattr(error, "details", None)
            }
            logger.error(f"Transaction failed: {self.current_transaction['name']} - {error}")
        else:
            logger.info(f"Transaction completed: {self.current_transaction['name']} in {duration_ms:.2f}ms")

        # Return to parent transaction if it exists
        parent_name = self.current_transaction.get("parent_transaction")
        if parent_name:
            for t in self.transactions:
                if t["name"] == parent_name and t["status"] == "in_progress":
                    self.current_transaction = t
                    break
        else:
            self.current_transaction = None

        return self.current_transaction

    def set_phase(self, phase: str) -> None:
        """
        Set the current processing phase.

        Args:
            phase: Name of the current phase (e.g., 'geocoding', 'chart_calculation')
        """
        self.current_phase = phase
        logger.info(f"Entering phase: {phase} (Trace: {self.trace_id})")

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the transaction tracker.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_transaction_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all transactions.

        Returns:
            Summary dictionary
        """
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": datetime.now(),
            "total_duration_ms": (datetime.now() - self.start_time).total_seconds() * 1000,
            "transaction_count": len(self.transactions),
            "phases": list(set(t["phase"] for t in self.transactions if t["phase"])),
            "error_count": sum(1 for t in self.transactions if t.get("error")),
            "metadata": self.metadata,
            "transactions": self.transactions
        }

    def get_transaction_tree(self) -> Dict[str, Any]:
        """
        Get a hierarchical tree of transactions.

        Returns:
            Tree structure of transactions
        """
        # Start with root transactions (no parent)
        roots = [t for t in self.transactions if not t.get("parent_transaction")]

        def build_tree(transaction):
            """Recursively build transaction tree."""
            result = transaction.copy()
            child_names = transaction.get("child_transactions", [])
            if child_names:
                result["children"] = []
                for name in child_names:
                    for t in self.transactions:
                        if t["name"] == name and t.get("parent_transaction") == transaction["name"]:
                            result["children"].append(build_tree(t))
            return result

        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": datetime.now(),
            "transactions": [build_tree(root) for root in roots]
        }


def track_transaction(func):
    """
    Decorator to track a function as a transaction.

    Args:
        func: Function to track

    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get or create tracker from environment or create new
        from ai_service.utils.dependency_container import get_container
        try:
            container = get_container()
            tracker = container.get("transaction_tracker", None)
        except (ImportError, ValueError):
            # Fall back to function attribute if container not available
            tracker = getattr(wrapper, '_tracker', None)

        if not tracker:
            tracker = TransactionTracker()
            # Store in function attribute as fallback
            setattr(wrapper, '_tracker', tracker)

            # Try to register in container
            try:
                container = get_container()
                container.register("transaction_tracker", lambda: tracker)
            except (ImportError, ValueError):
                pass

        # Start transaction with function name and args summary
        # Don't include full args content as it could be large
        args_summary = {
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        }

        # Include class name if it's a method
        transaction_name = func.__name__
        if args and hasattr(args[0], '__class__'):
            try:
                class_name = args[0].__class__.__name__
                transaction_name = f"{class_name}.{transaction_name}"
            except (AttributeError, IndexError):
                pass

        tracker.start_transaction(transaction_name, {"args_summary": args_summary})

        try:
            # Call the original function
            result = await func(*args, **kwargs)
            # End transaction with success
            tracker.end_transaction()
            return result
        except Exception as e:
            # End transaction with error
            tracker.end_transaction(status="failed", error=e)
            # Re-raise the exception
            raise

    return wrapper


# Global transaction tracker for the current request
_current_tracker = None

def get_current_tracker() -> TransactionTracker:
    """
    Get the current transaction tracker or create a new one.

    Returns:
        TransactionTracker instance
    """
    global _current_tracker
    if not _current_tracker:
        _current_tracker = TransactionTracker()
    return _current_tracker


def reset_tracker() -> None:
    """Reset the current transaction tracker."""
    global _current_tracker
    _current_tracker = None
