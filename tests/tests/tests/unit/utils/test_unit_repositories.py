"""
Component tests for repositories.py
Tests the functionality of database repositories with real file operations.
"""

import pytest
import os
import json
import asyncio
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from ai_service.database.repositories import ChartRepository

@pytest.fixture
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)

@pytest.fixture
def chart_repository(test_data_dir):
    """Create a ChartRepository instance with file storage."""
    charts_dir = os.path.join(test_data_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)
    return ChartRepository(db_pool=None, file_storage_path=charts_dir)

@pytest.fixture
def sample_chart_data():
    """Create sample chart data for testing."""
    return {
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York"
        },
        "planets": {
            "sun": {"longitude": 280.5, "latitude": 0.0, "distance": 0.98, "speed": 1.01},
            "moon": {"longitude": 135.8, "latitude": 5.1, "distance": 0.0025, "speed": 13.2},
            "mercury": {"longitude": 287.2, "latitude": -1.5, "distance": 0.92, "speed": 1.4}
        },
        "houses": [
            {"cusp": 0, "longitude": 15.5},
            {"cusp": 1, "longitude": 45.8},
            {"cusp": 2, "longitude": 75.9}
        ],
        "aspects": [
            {"planet1": "sun", "planet2": "moon", "aspect": "trine", "orb": 4.7},
            {"planet1": "moon", "planet2": "mercury", "aspect": "square", "orb": 2.3}
        ]
    }

@pytest.mark.asyncio
async def test_store_and_get_chart(chart_repository, sample_chart_data):
    """Test storing and retrieving a chart."""
    # Store the chart
    chart_id = await chart_repository.store_chart(sample_chart_data)

    # Verify the chart ID was returned
    assert chart_id is not None
    assert isinstance(chart_id, str)
    assert chart_id.startswith("chart_")

    # Verify chart was stored in file
    file_path = os.path.join(chart_repository.file_storage_path, f"{chart_id}.json")
    assert os.path.exists(file_path)

    # Retrieve the chart
    retrieved_chart = await chart_repository.get_chart(chart_id)

    # Verify chart data
    assert retrieved_chart is not None
    assert retrieved_chart["chart_id"] == chart_id
    assert retrieved_chart["birth_details"] == sample_chart_data["birth_details"]
    assert retrieved_chart["planets"] == sample_chart_data["planets"]
    assert retrieved_chart["houses"] == sample_chart_data["houses"]
    assert retrieved_chart["aspects"] == sample_chart_data["aspects"]
    assert "created_at" in retrieved_chart
    assert "updated_at" in retrieved_chart

@pytest.mark.asyncio
async def test_update_chart(chart_repository, sample_chart_data):
    """Test updating a chart."""
    # Store the chart
    chart_id = await chart_repository.store_chart(sample_chart_data)

    # Update the chart
    updated_data = sample_chart_data.copy()
    updated_data["birth_details"] = {
        **updated_data["birth_details"],
        "birth_time": "14:30:00"  # Changed birth time
    }
    updated_data["chart_id"] = chart_id

    # Perform the update
    result = await chart_repository.update_chart(chart_id, updated_data)

    # Verify the update result
    assert result is not None
    assert result["chart_id"] == chart_id
    assert result["birth_details"]["birth_time"] == "14:30:00"

    # Retrieve the chart again to confirm update
    retrieved_chart = await chart_repository.get_chart(chart_id)
    assert retrieved_chart["birth_details"]["birth_time"] == "14:30:00"

@pytest.mark.asyncio
async def test_delete_chart(chart_repository, sample_chart_data):
    """Test deleting a chart."""
    # Store the chart
    chart_id = await chart_repository.store_chart(sample_chart_data)

    # Verify the chart exists
    assert await chart_repository.get_chart(chart_id) is not None

    # Delete the chart
    result = await chart_repository.delete_chart(chart_id)

    # Verify the delete result
    assert result is True

    # Verify the chart no longer exists
    assert await chart_repository.get_chart(chart_id) is None

    # Check file was removed
    file_path = os.path.join(chart_repository.file_storage_path, f"{chart_id}.json")
    assert not os.path.exists(file_path)

@pytest.mark.asyncio
async def test_list_charts(chart_repository, sample_chart_data):
    """Test listing charts."""
    # Store multiple charts
    chart_ids = []
    for i in range(5):
        chart_data = sample_chart_data.copy()
        chart_data["birth_details"] = {
            **chart_data["birth_details"],
            "birth_time": f"{10+i}:00:00"  # Different times
        }
        chart_id = await chart_repository.store_chart(chart_data)
        chart_ids.append(chart_id)

    # List all charts
    charts = await chart_repository.list_charts(limit=10, offset=0)

    # Verify all charts are listed
    assert len(charts) == 5

    # Verify pagination
    charts_page_1 = await chart_repository.list_charts(limit=2, offset=0)
    charts_page_2 = await chart_repository.list_charts(limit=2, offset=2)
    charts_page_3 = await chart_repository.list_charts(limit=2, offset=4)

    assert len(charts_page_1) == 2
    assert len(charts_page_2) == 2
    assert len(charts_page_3) == 1

@pytest.mark.asyncio
async def test_store_and_get_rectification(chart_repository, sample_chart_data):
    """Test storing and retrieving a rectification."""
    # Store original chart
    original_chart_id = await chart_repository.store_chart(sample_chart_data)

    # Create rectified chart
    rectified_data = sample_chart_data.copy()
    rectified_data["birth_details"] = {
        **rectified_data["birth_details"],
        "birth_time": "12:15:30"  # Rectified time
    }
    rectified_chart_id = await chart_repository.store_chart(rectified_data)

    # Create rectification data
    rectification_id = f"rect_{uuid4().hex[:10]}"
    rectification_data = {
        "original_time": "12:00:00",
        "rectified_time": "12:15:30",
        "confidence": 85.7,
        "method": "life_events_analysis",
        "reasoning": "Based on major life events correlation with transits"
    }

    # Store rectification
    await chart_repository.store_rectification(
        rectification_id=rectification_id,
        chart_id=rectified_chart_id,
        original_chart_id=original_chart_id,
        rectification_data=rectification_data
    )

    # Retrieve rectification
    retrieved_rect = await chart_repository.get_rectification(rectification_id)

    # Verify rectification data
    assert retrieved_rect is not None
    assert retrieved_rect["rectification_id"] == rectification_id
    assert retrieved_rect["chart_id"] == rectified_chart_id
    assert retrieved_rect["original_chart_id"] == original_chart_id
    assert retrieved_rect["rectification_data"]["confidence"] == 85.7
    assert retrieved_rect["status"] == "completed"

@pytest.mark.asyncio
async def test_store_and_get_comparison(chart_repository, sample_chart_data):
    """Test storing and retrieving a chart comparison."""
    # Store two charts
    chart1_data = sample_chart_data.copy()
    chart1_id = await chart_repository.store_chart(chart1_data)

    chart2_data = sample_chart_data.copy()
    chart2_data["birth_details"]["birth_time"] = "14:30:00"
    chart2_id = await chart_repository.store_chart(chart2_data)

    # Create comparison data
    comparison_id = f"comp_{uuid4().hex[:10]}"
    comparison_data = {
        "chart1_id": chart1_id,
        "chart2_id": chart2_id,
        "differences": [
            {"planet": "sun", "difference_degrees": 0.0},
            {"planet": "moon", "difference_degrees": 31.5},
            {"planet": "ascendant", "difference_degrees": 37.2}
        ],
        "analysis": "The Moon and Ascendant positions show significant changes due to the 2.5 hour time difference."
    }

    # Store comparison
    await chart_repository.store_comparison(
        comparison_id=comparison_id,
        comparison_data=comparison_data
    )

    # Retrieve comparison
    retrieved_comp = await chart_repository.get_comparison(comparison_id)

    # Verify comparison data
    assert retrieved_comp is not None
    assert retrieved_comp["comparison_id"] == comparison_id
    assert retrieved_comp["chart1_id"] == chart1_id
    assert retrieved_comp["chart2_id"] == chart2_id
    assert len(retrieved_comp["comparison_data"]["differences"]) == 3

@pytest.mark.asyncio
async def test_store_and_get_export(chart_repository, sample_chart_data):
    """Test storing and retrieving a chart export."""
    # Store a chart
    chart_id = await chart_repository.store_chart(sample_chart_data)

    # Create export data
    export_id = f"export_{uuid4().hex[:10]}"
    export_file_path = f"/tmp/exports/chart_{chart_id}.pdf"
    download_url = f"/api/exports/{export_id}/download"
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()

    export_data = {
        "chart_id": chart_id,
        "file_path": export_file_path,
        "format": "pdf",
        "download_url": download_url,
        "expires_at": expires_at
    }

    # Store export
    await chart_repository.store_export(
        export_id=export_id,
        export_data=export_data
    )

    # Retrieve export
    retrieved_export = await chart_repository.get_export(export_id)

    # Verify export data
    assert retrieved_export is not None
    assert retrieved_export["export_id"] == export_id
    assert retrieved_export["chart_id"] == chart_id
    assert retrieved_export["file_path"] == export_file_path
    assert retrieved_export["format"] == "pdf"
    assert retrieved_export["download_url"] == download_url
