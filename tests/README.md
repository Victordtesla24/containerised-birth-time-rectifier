# Birth Time Rectifier Test Suite

This directory contains test scripts for the Birth Time Rectifier application.

## Main Test Script

The main test script is `test_consolidated_api_flow.py`, which tests the complete API flow from session initialization to chart export.

## Enhancements

The `test_consolidated_api_flow_enhancements.py` file contains additional helper functions to enhance the test script with:

1. **Improved Chart Visualization**: Enhanced visualization of charts with side-by-side comparison between original and rectified charts.

2. **Enhanced Export Functionality**: Improved export functionality with better error handling and recovery options.

3. **Safe Dictionary Access**: Helper functions for safely accessing dictionary values without triggering linter errors.

4. **Chart Data Extraction**: Utility functions for extracting chart data from various response structures.

5. **File Download Capability**: Functions for downloading exported chart files.

## Usage

To run the test script with all enhancements:

```bash
python -m tests.test_consolidated_api_flow --export
```

### Command-line Arguments

- `--verbose`: Enable verbose logging
- `--dry-run`: Print what would be done without executing API calls
- `--test-type`: Type of test flow to run (`interactive` or `default`)
- `--retry`: Number of retries for API requests
- `--backoff`: Backoff factor for retries
- `--export`: Export chart after rectification

## Error Handling

The test script includes robust error handling with recovery strategies for different failure scenarios:

1. If chart generation fails, the script will provide detailed error information.
2. If rectification fails, the script will attempt to visualize the original chart.
3. If export fails, the script will attempt to export the original chart instead.

## Visualization

The test script includes ASCII-based visualization of:

1. Planetary positions in houses and signs
2. Confidence score progress bars
3. Side-by-side comparison between original and rectified charts
4. Highlighted differences between charts
