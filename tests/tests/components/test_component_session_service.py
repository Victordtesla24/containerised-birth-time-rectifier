"""
Unit tests for session service using real implementations.
Tests actual session management functionality without mocks or fallbacks.
"""

import pytest
import asyncio
import os
import json
import tempfile
from datetime import datetime
from typing import Dict, Any

from ai_service.api.services.session_service import SessionStore, get_session_store

class TestSessionService:
    """Test the session service with real storage."""

    @pytest.fixture
    def session_store(self):
        """Create a real SessionStore instance with temporary storage."""
        # Create a temporary directory for session storage
        temp_dir = tempfile.mkdtemp()

        # Create the session store with the temporary directory
        store = SessionStore(persistence_dir=temp_dir)

        # Return the store and cleanup function
        yield store

        # Clean up the temporary directory after tests
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_create_session(self, session_store):
        """Test creating a new session."""
        # Generate a unique session ID
        session_id = f"test-session-{datetime.now().timestamp()}"

        # Test session data
        session_data = {
            "user_id": "test-user",
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

        # Create session
        await session_store.create_session(session_id, session_data)

        # Verify session was created
        session = await session_store.get_session(session_id)

        # Check result
        assert session is not None
        assert isinstance(session, dict)
        assert "user_id" in session
        assert session["user_id"] == "test-user"
        assert "status" in session
        assert session["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_session(self, session_store):
        """Test updating an existing session."""
        # Generate a unique session ID
        session_id = f"test-session-{datetime.now().timestamp()}"

        # Initial session data
        initial_data = {
            "user_id": "test-user",
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "data": {"key1": "value1"}
        }

        # Create session
        await session_store.create_session(session_id, initial_data)

        # Update data
        update_data = {
            "status": "in_progress",
            "data": {"key1": "updated", "key2": "new_value"}
        }

        # Update session
        await session_store.update_session(session_id, update_data)

        # Retrieve updated session
        updated_session = await session_store.get_session(session_id)

        # Check result
        assert updated_session is not None
        assert "status" in updated_session
        assert updated_session["status"] == "in_progress"
        assert "data" in updated_session
        assert updated_session["data"]["key1"] == "updated"
        assert updated_session["data"]["key2"] == "new_value"

        # Original data should be preserved
        assert "user_id" in updated_session
        assert updated_session["user_id"] == "test-user"
        assert "created_at" in updated_session

    @pytest.mark.asyncio
    async def test_delete_session(self, session_store):
        """Test deleting a session."""
        # Generate a unique session ID
        session_id = f"test-session-{datetime.now().timestamp()}"

        # Create session
        await session_store.create_session(session_id, {"test": "data"})

        # Verify session exists
        session = await session_store.get_session(session_id)
        assert session is not None

        # Delete session
        await session_store.delete_session(session_id)

        # Verify session no longer exists
        deleted_session = await session_store.get_session(session_id)
        assert deleted_session is None

    @pytest.mark.asyncio
    async def test_nonexistent_session(self, session_store):
        """Test that getting a nonexistent session returns None."""
        # Try to get a session that doesn't exist
        session = await session_store.get_session("nonexistent-session")

        # Should return None, not throw an error
        assert session is None

    @pytest.mark.asyncio
    async def test_session_persistence(self, session_store):
        """Test that sessions persist across instances."""
        # Generate a unique session ID
        session_id = f"test-persistence-{datetime.now().timestamp()}"

        # Create session
        session_data = {"test": "persistence"}
        await session_store.create_session(session_id, session_data)

        # Create a new session store instance with the same persistence directory
        new_store = SessionStore(persistence_dir=session_store.persistence_dir)

        # Verify session exists in the new store
        session = await new_store.get_session(session_id)
        assert session is not None
        assert session["test"] == "persistence"

    @pytest.mark.asyncio
    async def test_get_all_sessions(self, session_store):
        """Test retrieving all sessions."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = f"test-multiple-{i}-{datetime.now().timestamp()}"
            session_ids.append(session_id)
            await session_store.create_session(session_id, {"index": i})

        # Get all sessions
        all_sessions = await session_store.get_all_sessions()

        # Verify we got at least our test sessions
        assert all_sessions is not None
        assert isinstance(all_sessions, dict)

        # Verify all our test sessions are included
        for session_id in session_ids:
            assert session_id in all_sessions
            assert "index" in all_sessions[session_id]
