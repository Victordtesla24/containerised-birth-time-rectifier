"""
Repository layer for database interaction.

This module provides repository classes for accessing different data entities.
"""

import logging
import traceback
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import asyncpg

from ai_service.database.connection import (
    get_db_pool,
    execute_query,
    fetch_one,
    fetch_all,
    fetch_val
)

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self):
        """Initialize repository."""
        self.table_name = None

    async def _ensure_schema(self, conn):
        """
        Ensure required schema exists.

        Args:
            conn: Database connection
        """
        raise NotImplementedError("Subclasses must implement _ensure_schema")

    async def _handle_db_error(self, error, operation, **kwargs):
        """
        Handle database errors consistently.

        Args:
            error: The exception
            operation: Description of the operation
            **kwargs: Additional context

        Raises:
            RuntimeError: Re-raises with context
        """
        error_details = f"{type(error).__name__}: {str(error)}"
        context = ', '.join(f"{k}={v}" for k, v in kwargs.items())

        logger.error(f"Database error during {operation} - {error_details} - {context}")
        logger.error(traceback.format_exc())

        raise RuntimeError(f"Failed to {operation}: {error_details}")

class ChartRepository(BaseRepository):
    """Repository for chart data."""

    def __init__(self):
        """Initialize chart repository."""
        super().__init__()
        self.table_name = "charts"

    async def _ensure_schema(self, conn):
        """
        Ensure charts table schema exists.

        Args:
            conn: Database connection
        """
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS charts (
                chart_id TEXT PRIMARY KEY,
                birth_date TEXT NOT NULL,
                birth_time TEXT NOT NULL,
                latitude NUMERIC NOT NULL,
                longitude NUMERIC NOT NULL,
                timezone TEXT NOT NULL,
                chart_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    async def store_chart(self, chart_data: Dict[str, Any]) -> str:
        """
        Store chart data in the database.

        Args:
            chart_data: Chart data to store

        Returns:
            ID of the stored chart

        Raises:
            RuntimeError: If database operations fail
        """
        # Generate chart ID if not present
        if 'chart_id' not in chart_data:
            chart_data['chart_id'] = f"chart_{uuid.uuid4().hex[:12]}"

        # Add timestamp if not present
        if 'created_at' not in chart_data:
            chart_data['created_at'] = datetime.now().isoformat()

        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Insert chart data
                await conn.execute(
                    '''
                    INSERT INTO charts (
                        chart_id, birth_date, birth_time,
                        latitude, longitude, timezone, chart_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (chart_id) DO UPDATE SET
                        birth_date = $2,
                        birth_time = $3,
                        latitude = $4,
                        longitude = $5,
                        timezone = $6,
                        chart_data = $7
                    ''',
                    chart_data['chart_id'],
                    chart_data['birth_date'],
                    chart_data['birth_time'],
                    chart_data['latitude'],
                    chart_data['longitude'],
                    chart_data['timezone'],
                    json.dumps(chart_data, cls=DateTimeEncoder)
                )

                logger.info(f"Chart {chart_data['chart_id']} stored in database")
                return chart_data['chart_id']
        except Exception as e:
            await self._handle_db_error(e, "store chart", chart_id=chart_data.get('chart_id', 'unknown'))
            return chart_data['chart_id']

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Get chart data from the database.

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query chart data
                row = await conn.fetchrow(
                    '''
                    SELECT
                        chart_id, birth_date, birth_time,
                        latitude, longitude, timezone, chart_data, created_at
                    FROM charts
                    WHERE chart_id = $1
                    ''',
                    chart_id
                )

                # Return chart data if found
                if row:
                    chart_data = json.loads(row['chart_data'])
                    # Add metadata fields if not in chart_data
                    chart_data.update({
                        'chart_id': row['chart_id'],
                        'birth_date': row['birth_date'],
                        'birth_time': row['birth_time'],
                        'latitude': float(row['latitude']),
                        'longitude': float(row['longitude']),
                        'timezone': row['timezone'],
                        'created_at': row['created_at'].isoformat()
                    })
                    return chart_data

                logger.info(f"Chart {chart_id} not found in database")
                return None
        except Exception as e:
            await self._handle_db_error(e, "get chart", chart_id=chart_id)
            return None

    async def delete_chart(self, chart_id: str) -> bool:
        """
        Delete chart from the database.

        Args:
            chart_id: ID of the chart to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Delete chart
                result = await conn.execute('DELETE FROM charts WHERE chart_id = $1', chart_id)

                # Parse result
                success = 'DELETE 1' in result
                if success:
                    logger.info(f"Chart {chart_id} deleted from database")
                else:
                    logger.info(f"Chart {chart_id} not found for deletion")
                return success
        except Exception as e:
            await self._handle_db_error(e, "delete chart", chart_id=chart_id)
            return False

    async def list_charts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List charts from the database.

        Args:
            limit: Maximum number of charts to return
            offset: Offset for pagination

        Returns:
            List of chart data

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query charts
                rows = await conn.fetch(
                    '''
                    SELECT
                        chart_id, birth_date, birth_time,
                        latitude, longitude, timezone, chart_data, created_at
                    FROM charts
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    ''',
                    limit, offset
                )

                # Parse results
                charts = []
                for row in rows:
                    chart_data = json.loads(row['chart_data'])
                    # Add metadata fields if not in chart_data
                    chart_data.update({
                        'chart_id': row['chart_id'],
                        'birth_date': row['birth_date'],
                        'birth_time': row['birth_time'],
                        'latitude': float(row['latitude']),
                        'longitude': float(row['longitude']),
                        'timezone': row['timezone'],
                        'created_at': row['created_at'].isoformat()
                    })
                    charts.append(chart_data)

                logger.info(f"Retrieved {len(charts)} charts from database")
                return charts
        except Exception as e:
            await self._handle_db_error(e, "list charts", limit=limit, offset=offset)
            return []

class RectificationRepository(BaseRepository):
    """Repository for rectification data."""

    def __init__(self):
        """Initialize rectification repository."""
        super().__init__()
        self.table_name = "rectifications"

    async def _ensure_schema(self, conn):
        """
        Ensure rectifications table schema exists.

        Args:
            conn: Database connection
        """
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rectifications (
                rectification_id TEXT PRIMARY KEY,
                chart_id TEXT REFERENCES charts(chart_id),
                original_birth_time TEXT NOT NULL,
                rectified_birth_time TEXT NOT NULL,
                confidence_score NUMERIC NOT NULL,
                rectification_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    async def store_rectification(self, rectification_data: Dict[str, Any]) -> str:
        """
        Store rectification data in the database.

        Args:
            rectification_data: Rectification data to store

        Returns:
            ID of the stored rectification

        Raises:
            RuntimeError: If database operations fail
        """
        # Generate rectification ID if not present
        if 'rectification_id' not in rectification_data:
            rectification_data['rectification_id'] = f"rect_{uuid.uuid4().hex[:12]}"

        rectification_id = rectification_data['rectification_id']

        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Insert rectification data
                await conn.execute(
                    '''
                    INSERT INTO rectifications (
                        rectification_id, chart_id, original_birth_time,
                        rectified_birth_time, confidence_score, rectification_data
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (rectification_id) DO UPDATE SET
                        chart_id = $2,
                        original_birth_time = $3,
                        rectified_birth_time = $4,
                        confidence_score = $5,
                        rectification_data = $6
                    ''',
                    rectification_id,
                    rectification_data['chart_id'],
                    rectification_data['original_birth_time'],
                    rectification_data['rectified_birth_time'],
                    rectification_data['confidence_score'],
                    json.dumps(rectification_data, cls=DateTimeEncoder)
                )

                logger.info(f"Rectification {rectification_id} stored in database")
                return rectification_id
        except Exception as e:
            await self._handle_db_error(e, "store rectification", rectification_id=rectification_id)
            return rectification_id

    async def get_rectification(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get rectification data from the database.

        Args:
            rectification_id: ID of the rectification to retrieve

        Returns:
            Rectification data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query rectification data
                row = await conn.fetchrow(
                    '''
                    SELECT
                        rectification_id, chart_id, original_birth_time,
                        rectified_birth_time, confidence_score,
                        rectification_data, created_at
                    FROM rectifications
                    WHERE rectification_id = $1
                    ''',
                    rectification_id
                )

                # Return rectification data if found
                if row:
                    rectification_data = json.loads(row['rectification_data'])
                    # Add metadata fields if not in rectification_data
                    rectification_data.update({
                        'rectification_id': row['rectification_id'],
                        'chart_id': row['chart_id'],
                        'original_birth_time': row['original_birth_time'],
                        'rectified_birth_time': row['rectified_birth_time'],
                        'confidence_score': float(row['confidence_score']),
                        'created_at': row['created_at'].isoformat()
                    })
                    return rectification_data

                logger.info(f"Rectification {rectification_id} not found in database")
                return None
        except Exception as e:
            await self._handle_db_error(e, "get rectification", rectification_id=rectification_id)
            return None

    async def get_rectifications_by_chart(self, chart_id: str) -> List[Dict[str, Any]]:
        """
        Get all rectifications for a specific chart.

        Args:
            chart_id: Chart ID to find rectifications for

        Returns:
            List of rectification data

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query rectifications
                rows = await conn.fetch(
                    '''
                    SELECT
                        rectification_id, chart_id, original_birth_time,
                        rectified_birth_time, confidence_score,
                        rectification_data, created_at
                    FROM rectifications
                    WHERE chart_id = $1
                    ORDER BY created_at DESC
                    ''',
                    chart_id
                )

                # Parse results
                rectifications = []
                for row in rows:
                    rectification_data = json.loads(row['rectification_data'])
                    # Add metadata fields if not in rectification_data
                    rectification_data.update({
                        'rectification_id': row['rectification_id'],
                        'chart_id': row['chart_id'],
                        'original_birth_time': row['original_birth_time'],
                        'rectified_birth_time': row['rectified_birth_time'],
                        'confidence_score': float(row['confidence_score']),
                        'created_at': row['created_at'].isoformat()
                    })
                    rectifications.append(rectification_data)

                logger.info(f"Retrieved {len(rectifications)} rectifications for chart {chart_id}")
                return rectifications
        except Exception as e:
            await self._handle_db_error(e, "get rectifications by chart", chart_id=chart_id)
            return []

class SessionRepository(BaseRepository):
    """Repository for session data."""

    def __init__(self):
        """Initialize session repository."""
        super().__init__()
        self.table_name = "sessions"

    async def _ensure_schema(self, conn):
        """
        Ensure sessions table schema exists.

        Args:
            conn: Database connection
        """
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        ''')

    async def store_session(self, session_data: Dict[str, Any]) -> str:
        """
        Store session data in the database.

        Args:
            session_data: Session data to store

        Returns:
            ID of the stored session

        Raises:
            RuntimeError: If database operations fail
        """
        # Generate session ID if not present
        if 'session_id' not in session_data:
            session_data['session_id'] = f"session_{uuid.uuid4().hex[:12]}"

        session_id = session_data['session_id']

        # Ensure expires_at is present
        if 'expires_at' not in session_data:
            # Default to 24 hours from now
            session_data['expires_at'] = (datetime.now().timestamp() + 24 * 60 * 60)

        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Insert session data
                await conn.execute(
                    '''
                    INSERT INTO sessions (session_id, data, expires_at)
                    VALUES ($1, $2, to_timestamp($3))
                    ON CONFLICT (session_id) DO UPDATE SET
                        data = $2,
                        expires_at = to_timestamp($3)
                    ''',
                    session_id,
                    json.dumps(session_data, cls=DateTimeEncoder),
                    session_data['expires_at']
                )

                logger.info(f"Session {session_id} stored in database")
                return session_id
        except Exception as e:
            await self._handle_db_error(e, "store session", session_id=session_id)
            return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from the database.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session data or None if not found or expired

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query session data
                row = await conn.fetchrow(
                    '''
                    SELECT session_id, data, created_at, expires_at
                    FROM sessions
                    WHERE session_id = $1 AND expires_at > CURRENT_TIMESTAMP
                    ''',
                    session_id
                )

                # Return session data if found and not expired
                if row:
                    session_data = json.loads(row['data'])
                    # Add metadata fields if not in session_data
                    session_data.update({
                        'session_id': row['session_id'],
                        'created_at': row['created_at'].isoformat(),
                        'expires_at': row['expires_at'].timestamp()
                    })
                    return session_data

                logger.info(f"Session {session_id} not found in database or expired")
                return None
        except Exception as e:
            await self._handle_db_error(e, "get session", session_id=session_id)
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from the database.

        Args:
            session_id: ID of the session to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Delete session
                result = await conn.execute('DELETE FROM sessions WHERE session_id = $1', session_id)

                # Parse result
                success = 'DELETE 1' in result
                if success:
                    logger.info(f"Session {session_id} deleted from database")
                else:
                    logger.info(f"Session {session_id} not found for deletion")
                return success
        except Exception as e:
            await self._handle_db_error(e, "delete session", session_id=session_id)
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from the database.

        Returns:
            Number of sessions deleted

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Delete expired sessions
                result = await conn.execute('DELETE FROM sessions WHERE expires_at <= CURRENT_TIMESTAMP')

                # Parse result
                count = int(result.split()[1]) if 'DELETE' in result else 0
                logger.info(f"Cleaned up {count} expired sessions")
                return count
        except Exception as e:
            await self._handle_db_error(e, "cleanup expired sessions")
            return 0

class QuestionnaireRepository(BaseRepository):
    """Repository for questionnaire data."""

    def __init__(self):
        """Initialize questionnaire repository."""
        super().__init__()
        self.table_name = "questionnaires"

    async def _ensure_schema(self, conn):
        """
        Ensure questionnaires table schema exists.

        Args:
            conn: Database connection
        """
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS questionnaires (
                questionnaire_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                chart_id TEXT REFERENCES charts(chart_id),
                questions JSONB NOT NULL,
                answers JSONB NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE
            )
        ''')

    async def store_questionnaire(self, questionnaire_data: Dict[str, Any]) -> str:
        """
        Store questionnaire data in the database.

        Args:
            questionnaire_data: Questionnaire data to store

        Returns:
            ID of the stored questionnaire

        Raises:
            RuntimeError: If database operations fail
        """
        # Generate questionnaire ID if not present
        if 'questionnaire_id' not in questionnaire_data:
            questionnaire_data['questionnaire_id'] = f"q_{uuid.uuid4().hex[:12]}"

        questionnaire_id = questionnaire_data['questionnaire_id']

        # Ensure required fields
        if 'answers' not in questionnaire_data:
            questionnaire_data['answers'] = {}

        if 'status' not in questionnaire_data:
            questionnaire_data['status'] = "initialized"

        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Prepare completed_at field
                completed_at = None
                if questionnaire_data.get('status') == 'completed' and 'completed_at' in questionnaire_data:
                    completed_at = questionnaire_data['completed_at']
                elif questionnaire_data.get('status') == 'completed':
                    completed_at = datetime.now()

                # Insert questionnaire data
                await conn.execute(
                    '''
                    INSERT INTO questionnaires (
                        questionnaire_id, session_id, chart_id, questions,
                        answers, status, completed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (questionnaire_id) DO UPDATE SET
                        session_id = $2,
                        chart_id = $3,
                        questions = $4,
                        answers = $5,
                        status = $6,
                        completed_at = $7
                    ''',
                    questionnaire_id,
                    questionnaire_data['session_id'],
                    questionnaire_data.get('chart_id'),
                    json.dumps(questionnaire_data['questions'], cls=DateTimeEncoder),
                    json.dumps(questionnaire_data['answers'], cls=DateTimeEncoder),
                    questionnaire_data['status'],
                    completed_at
                )

                logger.info(f"Questionnaire {questionnaire_id} stored in database")
                return questionnaire_id
        except Exception as e:
            await self._handle_db_error(e, "store questionnaire", questionnaire_id=questionnaire_id)
            return questionnaire_id

    async def get_questionnaire(self, questionnaire_id: str) -> Optional[Dict[str, Any]]:
        """
        Get questionnaire data from the database.

        Args:
            questionnaire_id: ID of the questionnaire to retrieve

        Returns:
            Questionnaire data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query questionnaire data
                row = await conn.fetchrow(
                    '''
                    SELECT
                        questionnaire_id, session_id, chart_id, questions,
                        answers, status, created_at, completed_at
                    FROM questionnaires
                    WHERE questionnaire_id = $1
                    ''',
                    questionnaire_id
                )

                # Return questionnaire data if found
                if row:
                    questionnaire_data = {
                        'questionnaire_id': row['questionnaire_id'],
                        'session_id': row['session_id'],
                        'chart_id': row['chart_id'],
                        'questions': json.loads(row['questions']),
                        'answers': json.loads(row['answers']),
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat()
                    }

                    if row['completed_at']:
                        questionnaire_data['completed_at'] = row['completed_at'].isoformat()

                    return questionnaire_data

                logger.info(f"Questionnaire {questionnaire_id} not found in database")
                return None
        except Exception as e:
            await self._handle_db_error(e, "get questionnaire", questionnaire_id=questionnaire_id)
            return None

    async def get_questionnaire_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest questionnaire for a session.

        Args:
            session_id: Session ID to find questionnaire for

        Returns:
            Questionnaire data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        pool = await get_db_pool()
        if not pool:
            raise RuntimeError("Database connection unavailable")

        try:
            async with pool.acquire() as conn:
                # Ensure schema
                await self._ensure_schema(conn)

                # Query latest questionnaire data
                row = await conn.fetchrow(
                    '''
                    SELECT
                        questionnaire_id, session_id, chart_id, questions,
                        answers, status, created_at, completed_at
                    FROM questionnaires
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                    ''',
                    session_id
                )

                # Return questionnaire data if found
                if row:
                    questionnaire_data = {
                        'questionnaire_id': row['questionnaire_id'],
                        'session_id': row['session_id'],
                        'chart_id': row['chart_id'],
                        'questions': json.loads(row['questions']),
                        'answers': json.loads(row['answers']),
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat()
                    }

                    if row['completed_at']:
                        questionnaire_data['completed_at'] = row['completed_at'].isoformat()

                    return questionnaire_data

                logger.info(f"No questionnaire found for session {session_id}")
                return None
        except Exception as e:
            await self._handle_db_error(e, "get questionnaire by session", session_id=session_id)
            return None

# Export the repository classes
__all__ = [
    'ChartRepository',
    'RectificationRepository',
    'SessionRepository',
    'QuestionnaireRepository'
]
