import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig, AutoTokenizer
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any, Mapping, TypeVar, cast
import logging
import os
import json
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class TaskHead(nn.Module):
    def __init__(self, hidden_size: int, output_size: int):
        super().__init__()
        self.dense = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(0.1)
        self.out_proj = nn.Linear(hidden_size, output_size)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        x = self.dropout(features)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x

class UnifiedRectificationModel(nn.Module):
    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        device: Optional[str] = None,
        num_hours: int = 24,
        model_path: Optional[str] = None
    ):
        super().__init__()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.num_hours = num_hours

        if model_path and os.path.exists(model_path):
            # Load pre-trained model from saved path
            self._load_from_path(model_path)
        else:
            # Initialize from pre-trained transformer
            self.config = AutoConfig.from_pretrained(model_name)
            self.transformer = AutoModel.from_pretrained(model_name)

            # Task-specific heads
            self.task_heads = nn.ModuleDict({
                'tattva': TaskHead(self.config.hidden_size, num_hours),  # 24-hour prediction
                'nadi': TaskHead(self.config.hidden_size, num_hours),
                'kp': TaskHead(self.config.hidden_size, num_hours)
            })

            # Birth data projection
            self.birth_data_projection = nn.Linear(8, self.config.hidden_size)  # Project 8 features to hidden_size

            # Task weights (learnable)
            self.task_weights = nn.Parameter(torch.ones(3) / 3)

        # Initialize tokenizer if needed
        self.tokenizer = None

        self.to(self.device)
        logger.info(f"Initialized unified rectification model on device: {self.device}")

    def _load_from_path(self, path: str):
        """Load model from saved path."""
        checkpoint = torch.load(path, map_location=self.device)

        # Load config and initialize transformer
        if 'config' in checkpoint:
            self.config = checkpoint['config']
        else:
            # Default to BERT if no config
            self.config = AutoConfig.from_pretrained('bert-base-uncased')

        # Initialize transformer and load weights
        self.transformer = AutoModel.from_config(self.config)

        # Initialize task heads
        self.task_heads = nn.ModuleDict({
            'tattva': TaskHead(self.config.hidden_size, self.num_hours),
            'nadi': TaskHead(self.config.hidden_size, self.num_hours),
            'kp': TaskHead(self.config.hidden_size, self.num_hours)
        })

        # Initialize birth data projection
        self.birth_data_projection = nn.Linear(8, self.config.hidden_size)

        # Initialize task weights
        self.task_weights = nn.Parameter(torch.ones(3) / 3)

        # Load state dict
        if 'state_dict' in checkpoint:
            self.load_state_dict(checkpoint['state_dict'])

        logger.info(f"Loaded model from {path}")

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        birth_data: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        # Get transformer features
        outputs = self.transformer(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        sequence_output = outputs.last_hidden_state
        pooled_output = sequence_output[:, 0, :]  # Use [CLS] token

        # Process birth data
        birth_features = self._process_birth_data(birth_data)

        # Combine text and birth data features
        combined_features = pooled_output + birth_features

        # Apply task heads
        task_outputs = {}
        for task_name, task_head in self.task_heads.items():
            task_outputs[task_name] = task_head(combined_features)

        # Combine task outputs with learned weights
        normalized_weights = torch.softmax(self.task_weights, dim=0)
        weighted_outputs = torch.zeros_like(task_outputs['tattva'])

        for i, (task_name, output) in enumerate(task_outputs.items()):
            weighted_outputs += normalized_weights[i] * output

        return weighted_outputs, task_outputs

    def _process_birth_data(self, birth_data: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Process numerical birth data (latitude, longitude, etc.)

        Args:
            birth_data: Dictionary with birth data features

        Returns:
            Processed features tensor
        """
        # Extract and normalize features
        features = []
        if 'latitude' in birth_data and 'longitude' in birth_data:
            # Normalize coordinates to [-1, 1]
            lat = birth_data['latitude'] / 90.0
            lon = birth_data['longitude'] / 180.0
            features.extend([lat, lon])
        else:
            # Default if missing
            features.extend([torch.zeros(1, device=self.device), torch.zeros(1, device=self.device)])

        # Add time features
        if 'hour' in birth_data and 'minute' in birth_data:
            # Normalize hour to [0, 1]
            hour = birth_data['hour'] / 24.0
            # Normalize minute to [0, 1]
            minute = birth_data['minute'] / 60.0
            features.extend([hour, minute])
        else:
            features.extend([torch.zeros(1, device=self.device), torch.zeros(1, device=self.device)])

        # Add date features
        if 'day' in birth_data and 'month' in birth_data:
            # Normalize day to [0, 1]
            day = birth_data['day'] / 31.0
            # Normalize month to [0, 1]
            month = birth_data['month'] / 12.0
            features.extend([day, month])
        else:
            features.extend([torch.zeros(1, device=self.device), torch.zeros(1, device=self.device)])

        # Add astro features if available
        if 'asc_degree' in birth_data and 'moon_degree' in birth_data:
            # Normalize degrees to [0, 1]
            asc = birth_data['asc_degree'] / 360.0
            moon = birth_data['moon_degree'] / 360.0
            features.extend([asc, moon])
        else:
            features.extend([torch.zeros(1, device=self.device), torch.zeros(1, device=self.device)])

        # Stack features and project
        features_tensor = torch.stack(features).unsqueeze(0).transpose(1, 2)  # [1, 1, 8]
        projected_features = self.birth_data_projection(features_tensor.squeeze(1))  # [1, 8] -> [1, hidden_size]

        return projected_features

    def predict(
        self,
        text: Union[str, List[str]],
        birth_data: Dict[str, float],
        tokenizer = None,
        return_details: bool = False
    ) -> Union[Dict[str, Any], Tuple[int, float, str, Dict[str, float]]]:
        """
        Predict birth time rectification from text and birth data.

        Args:
            text: Input text(s) describing life events
            birth_data: Dictionary with birth data (lat, lon, birth_date, birth_time)
            tokenizer: Tokenizer for text processing (will be initialized if None)
            return_details: Whether to return detailed outputs

        Returns:
            If return_details=False: Tuple of (adjusted_hour, confidence, reliability_level, confidence_breakdown)
            If return_details=True: Dictionary with detailed prediction information
        """
        self.eval()

        # Initialize tokenizer if needed
        if tokenizer is None:
            if self.tokenizer is None:
                self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
            tokenizer = self.tokenizer

        # Process text input
        if isinstance(text, str):
            text = [text]

        # Tokenize text
        encoded_input = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors='pt'
        ).to(self.device)

        # Process birth data
        birth_tensor_data = {}
        birth_date = birth_data.get('birth_date')
        birth_time = birth_data.get('birth_time')

        # Parse date and time
        if birth_date and birth_time:
            try:
                if isinstance(birth_date, str):
                    date_obj = datetime.strptime(birth_date, '%Y-%m-%d')
                    day = date_obj.day
                    month = date_obj.month
                else:
                    day = int(birth_data.get('day', 1))
                    month = int(birth_data.get('month', 1))

                if isinstance(birth_time, str):
                    time_parts = re.split(r'[:.]', birth_time)
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                else:
                    hour = int(birth_data.get('hour', 0))
                    minute = int(birth_data.get('minute', 0))

                birth_tensor_data.update({
                    'day': torch.tensor([day], device=self.device).float(),
                    'month': torch.tensor([month], device=self.device).float(),
                    'hour': torch.tensor([hour], device=self.device).float(),
                    'minute': torch.tensor([minute], device=self.device).float()
                })
            except Exception as e:
                logger.warning(f"Error parsing birth date/time: {e}")

        # Add coordinates
        if 'latitude' in birth_data and 'longitude' in birth_data:
            birth_tensor_data.update({
                'latitude': torch.tensor([birth_data['latitude']], device=self.device).float(),
                'longitude': torch.tensor([birth_data['longitude']], device=self.device).float()
            })

        # Add astro data if available
        if 'asc_degree' in birth_data and 'moon_degree' in birth_data:
            birth_tensor_data.update({
                'asc_degree': torch.tensor([birth_data['asc_degree']], device=self.device).float(),
                'moon_degree': torch.tensor([birth_data['moon_degree']], device=self.device).float()
            })

        # Make prediction
        with torch.no_grad():
            weighted_output, task_outputs = self(
                encoded_input.input_ids,
                encoded_input.attention_mask,
                birth_tensor_data
            )

            # Get hour predictions from each task
            hour_predictions: Dict[str, int] = {}
            task_confidences = {}

            for task_name, output in task_outputs.items():
                probs = torch.softmax(output, dim=1)[0]
                predicted_idx = int(torch.argmax(probs).item())

                # Get confidence as probability
                confidence = float(probs[predicted_idx].item())

                # Get distribution properties
                entropy = float(-torch.sum(probs * torch.log(probs + 1e-10)).item())
                top3_indices = torch.topk(probs, 3).indices.tolist()
                top3_probs = torch.topk(probs, 3).values.tolist()

                hour_predictions[task_name] = predicted_idx

                # Create the distribution dictionary with explicit iteration
                distribution_dict = {}
                for i in range(self.num_hours):
                    key = str(i)
                    value = float(probs[i].item())
                    distribution_dict[key] = value

                # Create the top3 list with explicit iteration
                top3_list = []
                for i, idx in enumerate(top3_indices):
                    top3_list.append((idx, float(top3_probs[i])))

                task_confidences[task_name] = {
                    'confidence': confidence,
                    'entropy': entropy,
                    'distribution': distribution_dict,
                    'top3': top3_list
                }

            # Get overall prediction
            weighted_probs = torch.softmax(weighted_output, dim=1)[0]
            predicted_hour = int(torch.argmax(weighted_probs).item())

            # Calculate confidence and reliability level
            input_quality, quality_details = self._assess_input_quality(text[0], birth_data)

            confidence, agreement_scores, task_agreement, has_pattern = self._calculate_confidence(
                weighted_probs,
                task_outputs,
                predicted_hour,
                text[0] if len(text) == 1 else " ".join(text),
                birth_data
            )

            reliability_level = self._get_reliability_level(
                confidence,
                agreement_scores,
                input_quality,
                quality_details,
                task_confidences,
                has_pattern
            )

            # Calculate alternative hour ranges
            hour_ranges = self._calculate_hour_ranges(weighted_probs)

            # Return result based on requested format
            if return_details:
                return {
                    'predicted_hour': predicted_hour,
                    'confidence': confidence,
                    'reliability_level': reliability_level,
                    'input_quality': input_quality,
                    'quality_details': quality_details,
                    'task_predictions': hour_predictions,
                    'task_confidences': task_confidences,
                    'agreement_scores': agreement_scores,
                    'has_meaningful_pattern': has_pattern,
                    'hour_ranges': hour_ranges,
                    'task_agreement': task_agreement
                }
            else:
                confidence_breakdown = {
                    'task_agreement': task_agreement,
                    'input_quality': input_quality,
                    'pattern_strength': 0.8 if has_pattern else 0.3
                }

                return predicted_hour, confidence, reliability_level, confidence_breakdown

    def _calculate_hour_ranges(self, probs: torch.Tensor) -> List[Dict[str, Any]]:
        """
        Calculate hour ranges with significant probability mass.
        """
        # Sort indices by probability
        sorted_indices = torch.argsort(probs, descending=True)

        ranges = []

        # Get the first index and convert to int explicitly
        first_idx = sorted_indices[0]
        first_idx_int = int(first_idx.item())

        # Initialize the current range with explicit int values
        current_range = {'start': first_idx_int, 'end': first_idx_int}

        # Get the probability value and convert to float explicitly
        current_sum = float(probs[first_idx].item())

        # Find 50% confidence range
        for i in range(1, len(sorted_indices)):
            # Get the current index and convert to int
            idx = sorted_indices[i]
            hour = int(idx.item())

            # Get the probability and convert to float
            prob = float(probs[idx].item())

            # Check if adjacent to current range
            if hour == current_range['start'] - 1 or hour == current_range['end'] + 1:
                # Extend range
                current_range['start'] = min(current_range['start'], hour)
                current_range['end'] = max(current_range['end'], hour)
                current_sum += prob
            else:
                # Start new range if substantial probability
                if prob > 0.1:  # Only include significant probabilities
                    ranges.append({
                        'start': current_range['start'],
                        'end': current_range['end'],
                        'probability': current_sum
                    })
                    current_range = {'start': hour, 'end': hour}
                    current_sum = prob

        # Add last range
        ranges.append({
            'start': current_range['start'],
            'end': current_range['end'],
            'probability': current_sum
        })

        # Sort by probability
        ranges.sort(key=lambda x: x['probability'], reverse=True)

        return ranges[:3]  # Return top 3 ranges

    def _calculate_confidence(
        self,
        final_prediction: torch.Tensor,
        task_outputs: Dict[str, torch.Tensor],
        predicted_hour: int,
        input_text: str,
        birth_data: Dict[str, float]
    ) -> Tuple[float, Dict[str, float], float, bool]:
        """
        Calculate confidence score for the prediction.

        Returns:
            Tuple of (confidence_score, agreement_scores, task_agreement, has_pattern)
        """
        # 1. Calculate confidence from probability distribution
        probs = final_prediction.cpu().numpy()
        predicted_prob = probs[predicted_hour]

        # Calculate entropy (lower is better)
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        max_entropy = -np.log(1.0 / len(probs))  # Max possible entropy
        entropy_score = 1.0 - (entropy / max_entropy)

        # Calculate peakedness (higher is better)
        sorted_probs = np.sort(probs)[::-1]
        top3_ratio = sorted_probs[0] / (sorted_probs[1] + sorted_probs[2] + 1e-10)
        peakedness = min(1.0, top3_ratio * 2.0)  # Scale appropriately

        # 2. Calculate technique agreement
        task_predictions: Dict[str, int] = {}
        for task_name, output in task_outputs.items():
            task_probs = torch.softmax(output, dim=1)[0]
            task_pred = int(torch.argmax(task_probs).item())
            task_predictions[task_name] = task_pred

        agreement_scores = {}

        # Direct technique agreement (exact hour match)
        agreement_scores['exact_match'] = self._calculate_technique_agreement(
            task_predictions, predicted_hour, window=0
        )

        # Relaxed agreement (1 hour window)
        agreement_scores['hour_window'] = self._calculate_technique_agreement(
            task_predictions, predicted_hour, window=1
        )

        # Pattern agreement (check if techniques follow a consistent pattern)
        pattern_score, has_pattern = self._detect_time_patterns(task_predictions, predicted_hour)
        agreement_scores['pattern'] = pattern_score

        # 3. Calculate quality-adjusted confidence
        # Assess quality of input data
        input_quality, _ = self._assess_input_quality(input_text, birth_data)

        # Overall agreement score (weighted average)
        technique_agreement = (
            0.4 * agreement_scores['exact_match'] +
            0.4 * agreement_scores['hour_window'] +
            0.2 * agreement_scores['pattern']
        )

        # Overall confidence calculation
        base_confidence = (
            0.35 * predicted_prob +
            0.25 * entropy_score +
            0.15 * peakedness +
            0.25 * technique_agreement
        )

        # Apply quality adjustment
        final_confidence = base_confidence * (0.7 + 0.3 * input_quality)

        # Clip and scale to percentage
        confidence_percentage = max(0.0, min(1.0, final_confidence)) * 100.0

        return confidence_percentage, agreement_scores, technique_agreement, has_pattern

    def _detect_time_patterns(
        self,
        task_predictions: Dict[str, int],
        predicted_hour: int
    ) -> Tuple[float, bool]:
        """
        Detect meaningful patterns in technique predictions.

        Returns:
            Tuple of (pattern_score, has_meaningful_pattern)
        """
        predictions = list(task_predictions.values())

        # Check for linear pattern
        if len(predictions) < 2:
            return 0.0, False

        # Sort predictions
        sorted_preds = sorted(predictions)

        # Check if predictions form an arithmetic sequence
        differences = [sorted_preds[i+1] - sorted_preds[i] for i in range(len(sorted_preds)-1)]

        # Perfect sequence would have all differences equal
        is_arithmetic = len(set(differences)) <= 1

        # Check if predictions are clustered
        max_diff = max(sorted_preds) - min(sorted_preds)
        is_clustered = max_diff <= 3

        # Check if predicted hour is within the range of technique predictions
        is_within_range = min(predictions) <= predicted_hour <= max(predictions)

        # Calculate pattern score
        pattern_score = 0.0

        if is_arithmetic and max_diff > 0:
            pattern_score = 0.8  # Strong arithmetic sequence
        elif is_clustered:
            pattern_score = 0.6  # Clustered predictions
        elif is_within_range:
            pattern_score = 0.4  # At least within range

        # Determine if there's a meaningful pattern
        has_meaningful_pattern = pattern_score >= 0.4

        return pattern_score, has_meaningful_pattern

    def _calculate_technique_agreement(
        self,
        task_predictions: Dict[str, int],
        predicted_hour: int,
        window: int = 0
    ) -> float:
        """
        Calculate agreement between different technique predictions.

        Args:
            task_predictions: Dictionary of technique predictions
            predicted_hour: Overall predicted hour
            window: Hour window for considering agreement

        Returns:
            Agreement score (0-1)
        """
        if not task_predictions:
            return 0.0

        # Count agreements
        agreements = 0

        for technique, hour in task_predictions.items():
            if window == 0:
                # Exact match
                if hour == predicted_hour:
                    agreements += 1
            else:
                # Within window
                lower_bound = (predicted_hour - window) % 24
                upper_bound = (predicted_hour + window) % 24

                if lower_bound <= upper_bound:
                    if lower_bound <= hour <= upper_bound:
                        agreements += 1
                else:
                    # Window wraps around midnight
                    if hour >= lower_bound or hour <= upper_bound:
                        agreements += 1

        return agreements / len(task_predictions)

    def _assess_input_quality(
        self,
        input_text: str,
        birth_data: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Assess the quality of input data for prediction.

        Args:
            input_text: Input text describing life events
            birth_data: Birth data dictionary

        Returns:
            Tuple of (overall_quality, quality_details)
        """
        quality_details = {}

        # 1. Text quality
        text_length = len(input_text.split())
        if text_length < 20:
            text_length_score = 0.3
        elif text_length < 50:
            text_length_score = 0.6
        elif text_length < 100:
            text_length_score = 0.8
        else:
            text_length_score = 1.0

        quality_details['text_length'] = text_length_score

        # Check for time-related keywords
        time_keywords = ['morning', 'afternoon', 'evening', 'night', 'am', 'pm', 'noon', 'midnight', 'hour', 'o\'clock']
        has_time_keywords = any(keyword in input_text.lower() for keyword in time_keywords)
        quality_details['has_time_keywords'] = 1.0 if has_time_keywords else 0.5

        # Check for life event descriptions
        life_event_keywords = ['born', 'birth', 'marriage', 'job', 'career', 'education', 'move', 'travel', 'relationship', 'health']
        life_event_count = sum(1 for keyword in life_event_keywords if keyword in input_text.lower())
        life_event_score = min(1.0, life_event_count / 5.0)
        quality_details['life_event_score'] = life_event_score

        # 2. Birth data quality
        birth_data_score = 0.0
        required_fields = ['latitude', 'longitude', 'birth_date']

        # Check for required fields
        for field in required_fields:
            if field in birth_data and birth_data[field] is not None:
                birth_data_score += 1.0 / len(required_fields)

        quality_details['birth_data_score'] = birth_data_score

        # 3. Check coordinate validity
        coord_score = 0.0
        if 'latitude' in birth_data and 'longitude' in birth_data:
            coord_score = self._assess_coordinate_validity(
                birth_data['latitude'], birth_data['longitude']
            )
        quality_details['coordinate_validity'] = coord_score

        # Overall input quality (weighted average)
        overall_quality = (
            0.35 * text_length_score +
            0.15 * quality_details['has_time_keywords'] +
            0.20 * life_event_score +
            0.20 * birth_data_score +
            0.10 * coord_score
        )

        return overall_quality, quality_details

    def _assess_coordinate_validity(self, lat: float, lon: float) -> float:
        """
        Assess the validity of geographical coordinates.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Validity score (0-1)
        """
        # Check latitude bounds
        valid_lat = -90.0 <= lat <= 90.0

        # Check longitude bounds
        valid_lon = -180.0 <= lon <= 180.0

        # Return combined score
        if valid_lat and valid_lon:
            return 1.0
        elif valid_lat or valid_lon:
            return 0.5
        else:
            return 0.0

    def _get_reliability_level(
        self,
        confidence: float,
        agreement_scores: Dict[str, float],
        input_quality: float,
        quality_details: Dict[str, float],
        task_confidences: Dict[str, Dict[str, Any]],
        has_meaningful_pattern: bool
    ) -> str:
        """
        Determine reliability level of the prediction.

        Args:
            confidence: Overall confidence percentage
            agreement_scores: Dictionary of agreement scores
            input_quality: Input quality score
            quality_details: Detailed quality metrics
            task_confidences: Detailed confidences for each technique
            has_meaningful_pattern: Whether a meaningful pattern was detected

        Returns:
            Reliability level string
        """
        # Check for highest confidence
        if (confidence >= 85 and
            agreement_scores['exact_match'] >= 0.7 and
            input_quality >= 0.7 and
            has_meaningful_pattern):
            return "very high"

        # Check for high confidence
        if (confidence >= 75 and
            agreement_scores['hour_window'] >= 0.6 and
            input_quality >= 0.6):
            return "high"

        # Check for moderate confidence
        if (confidence >= 60 and
            agreement_scores['hour_window'] >= 0.5 and
            input_quality >= 0.5):
            return "moderate"

        # Check for low confidence
        if (confidence >= 40 and
            agreement_scores['hour_window'] >= 0.3):
            return "low"

        # Everything else is very low
        return "very low"

    def save(self, path: str):
        """Save model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save model state
        checkpoint = {
            'state_dict': self.state_dict(),
            'config': self.config
        }

        torch.save(checkpoint, path)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: Optional[str] = None) -> 'UnifiedRectificationModel':
        """Load model from disk."""
        model = cls(device=device, model_path=path)
        return model

    def finetune(
        self,
        dataset: List[Dict[str, Any]],
        tokenizer = None,
        learning_rate: float = 5e-5,
        batch_size: int = 8,
        num_epochs: int = 3
    ):
        """
        Finetune the model on a dataset.

        Args:
            dataset: List of data items, each with 'text', 'birth_data', and 'hour' fields
            tokenizer: Tokenizer to use (will be initialized if None)
            learning_rate: Learning rate for optimization
            batch_size: Training batch size
            num_epochs: Number of training epochs
        """
        from torch.utils.data import DataLoader, Dataset
        from torch.optim import AdamW
        import random

        # Set model to training mode
        self.train()

        # Initialize tokenizer if needed
        if tokenizer is None:
            if self.tokenizer is None:
                self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
            tokenizer = self.tokenizer

        # Create dataset
        class RectificationDataset(Dataset):
            def __init__(self, data, tokenizer):
                self.data = data
                self.tokenizer = tokenizer

            def __len__(self):
                return len(self.data)

            def __getitem__(self, idx):
                item = self.data[idx]

                # Tokenize text
                encoded = self.tokenizer(
                    item['text'],
                    padding='max_length',
                    truncation=True,
                    max_length=512,
                    return_tensors='pt'
                )

                # Process birth data
                birth_data = {}
                for key, value in item['birth_data'].items():
                    if key in ['latitude', 'longitude', 'hour', 'minute', 'day', 'month', 'asc_degree', 'moon_degree']:
                        birth_data[key] = torch.tensor([float(value)])

                # Get target hour
                target_hour = item['hour']

                return {
                    'input_ids': encoded.input_ids.squeeze(0),
                    'attention_mask': encoded.attention_mask.squeeze(0),
                    'birth_data': birth_data,
                    'hour': torch.tensor(target_hour, dtype=torch.long)
                }

        # Create dataloader
        train_dataset = RectificationDataset(dataset, tokenizer)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        # Create optimizer
        optimizer = AdamW(self.parameters(), lr=learning_rate)

        # Training loop
        for epoch in range(num_epochs):
            total_loss = 0

            for batch in train_loader:
                # Move batch to device
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)

                birth_data = {}
                for key, value in batch['birth_data'].items():
                    birth_data[key] = value.to(self.device)

                target_hours = batch['hour'].to(self.device)

                # Forward pass
                optimizer.zero_grad()
                weighted_output, task_outputs = self(input_ids, attention_mask, birth_data)

                # Calculate loss
                loss_fn = nn.CrossEntropyLoss()
                loss = loss_fn(weighted_output, target_hours)

                # Task-specific losses
                task_losses = {}
                for task_name, output in task_outputs.items():
                    task_loss = loss_fn(output, target_hours)
                    task_losses[task_name] = task_loss
                    loss += 0.2 * task_loss  # Add task losses with lower weight

                # Backward pass and optimization
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            # Report epoch results
            avg_loss = total_loss / len(train_loader)
            logger.info(f"Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.4f}")

        # Set back to eval mode
        self.eval()

        return self
