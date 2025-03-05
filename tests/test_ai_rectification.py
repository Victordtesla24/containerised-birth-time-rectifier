"""
Tests for the AI birth time rectification model.
Validates the full functionality of the unified model.
"""

import os
import sys
import pytest
import torch
import logging

# Add the root directory to the path so we can import from the ai_service module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AI rectification model
from ai_service.models.unified_model import UnifiedRectificationModel

# Set up logging
logger = logging.getLogger(__name__)

# Skip if torch is not available
pytorch_available = True
try:
    import torch
except ImportError:
    pytorch_available = False

@pytest.mark.skipif(not pytorch_available, reason="PyTorch not available")
class TestAIRectificationModel:
    """Test suite for the AI rectification model."""

    @pytest.fixture(scope="class")
    def model(self):
        """Create a test instance of the unified model."""
        return UnifiedRectificationModel(
            model_name="bert-base-uncased",
            device="cpu",
            num_hours=24
        )

    def test_model_initialization(self, model):
        """Test that the model initializes correctly."""
        assert model is not None
        assert isinstance(model, UnifiedRectificationModel)
        assert model.device == "cpu"
        assert model.num_hours == 24

    def test_model_forward_pass(self, model):
        """Test the model's forward pass."""
        # Create dummy input data
        input_ids = torch.randint(0, 1000, (1, 10))
        attention_mask = torch.ones(1, 10)
        birth_data = {
            "latitude": torch.tensor([40.7128]),
            "longitude": torch.tensor([-74.0060]),
            "hour": torch.tensor([12]),
            "minute": torch.tensor([0]),
            "day": torch.tensor([1]),
            "month": torch.tensor([1]),
            "asc_degree": torch.tensor([15.5]),
            "moon_degree": torch.tensor([25.3])
        }

        # Run forward pass
        weighted_output, task_outputs = model(input_ids, attention_mask, birth_data)

        # Check outputs
        assert weighted_output is not None
        assert isinstance(weighted_output, torch.Tensor)
        assert weighted_output.shape == (1, 24)  # Batch size 1, 24 hours

        # Check task outputs
        assert "tattva" in task_outputs
        assert "nadi" in task_outputs
        assert "kp" in task_outputs

    def test_process_birth_data(self, model):
        """Test processing of birth data."""
        birth_data = {
            "latitude": torch.tensor([40.7128]),
            "longitude": torch.tensor([-74.0060]),
            "hour": torch.tensor([12]),
            "minute": torch.tensor([0]),
            "day": torch.tensor([1]),
            "month": torch.tensor([1])
        }

        # Process birth data
        features = model._process_birth_data(birth_data)

        # Check output
        assert features is not None
        assert isinstance(features, torch.Tensor)
        assert features.shape[0] == 1  # Batch size 1

    def test_prediction_with_text(self, model):
        """Test prediction with text input."""
        # Sample text
        text = "I was born in New York City. My birth time is around noon."

        # Sample birth data
        birth_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "birth_date": "1990-01-01",
            "birth_time": "12:00"
        }

        # Make prediction
        result = model.predict(text, birth_data, return_details=True)

        # Check result
        assert result is not None
        assert "predicted_hour" in result
        assert 0 <= result["predicted_hour"] < 24
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 100
        assert "reliability_level" in result

    def test_confidence_calculation(self, model):
        """Test confidence calculation."""
        # Create dummy probability distribution
        probs = torch.softmax(torch.randn(24), dim=0)

        # Dummy task outputs
        task_outputs = {
            "tattva": torch.randn(1, 24),
            "nadi": torch.randn(1, 24),
            "kp": torch.randn(1, 24)
        }

        # Sample text
        text = "I was born in New York City. My birth time is around noon."

        # Sample birth data
        birth_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "birth_date": "1990-01-01",
            "birth_time": "12:00"
        }

        # Get predicted hour
        predicted_hour = torch.argmax(probs).item()

        # Calculate confidence
        confidence, agreement_scores, task_agreement, has_pattern = model._calculate_confidence(
            probs, task_outputs, predicted_hour, text, birth_data
        )

        # Check result
        assert 0 <= confidence <= 100
        assert "exact_match" in agreement_scores
        assert "hour_window" in agreement_scores
        assert "pattern" in agreement_scores
        assert 0 <= task_agreement <= 1
        assert isinstance(has_pattern, bool)

    def test_save_and_load(self, model, tmpdir):
        """Test saving and loading the model."""
        # Save model
        save_path = os.path.join(tmpdir, "test_model.pt")
        model.save(save_path)

        # Check that file exists
        assert os.path.exists(save_path)

        # Load model
        loaded_model = UnifiedRectificationModel.load(save_path, device="cpu")

        # Check loaded model
        assert loaded_model is not None
        assert isinstance(loaded_model, UnifiedRectificationModel)
        assert loaded_model.device == "cpu"
        assert loaded_model.num_hours == 24

    def test_hour_ranges_calculation(self, model):
        """Test calculation of hour ranges."""
        # Create dummy probability distribution with peaks
        probs = torch.zeros(24)
        probs[10] = 0.3  # Peak at 10
        probs[11] = 0.2  # Adjacent to peak
        probs[12] = 0.1  # Adjacent to peak
        probs[18] = 0.2  # Another peak
        probs[4] = 0.1   # Another smaller peak
        probs = torch.softmax(probs, dim=0)

        # Calculate hour ranges
        ranges = model._calculate_hour_ranges(probs)

        # Check result
        assert ranges is not None
        assert len(ranges) > 0
        assert "start" in ranges[0]
        assert "end" in ranges[0]
        assert "probability" in ranges[0]
        assert ranges[0]["probability"] > 0.0
