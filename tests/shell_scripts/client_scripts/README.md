# Birth Time Rectifier API Testing Suite

This directory contains shell scripts for testing the Birth Time Rectifier API endpoints according to the sequence diagrams specified in the project documentation.

## Available Scripts

1. **run_all_tests.sh** - Main script that provides a menu to run all tests or individual test scripts following the exact sequence from the Original Sequence Diagram
2. **birth_time_rectifier_tester.sh** - Tests basic API functionality (session, geocoding, chart generation)
3. **advanced_api_tester.sh** - Tests advanced API functionality (questionnaire, rectification, comparison)
4. **websocket_tester.sh** - Tests WebSocket connections for real-time updates
5. **openai_integration_tester.sh** - Tests OpenAI integration and questionnaire flow with confidence tracking
6. **rectification_algorithm_tester.sh** - Tests rectification algorithms, chart comparisons with details, interpretations
7. **test_endpoints.sh** - Simple script to test individual API endpoints
8. **session.sh** - Utilities for session management

## Requirements

- Bash 4.0 or higher
- curl
- bc (basic calculator)
- websocat (for WebSocket tests - install with `brew install websocat` on macOS)
- jq (optional, for better JSON formatting - install with `brew install jq` on macOS)

## Usage

### Running All Tests According to Sequence Diagram

```bash
./run_all_tests.sh
# Select option 6 to run all tests in sequence
```

This will run tests in the exact order specified in the "Original Sequence Diagram - Full Implementation" section from docs/architecture/sequence_diagram.md:

1. Session Initialization (User visits app -> Frontend requests session initialization)
2. WebSocket Connection for Real-time Updates (enables tracking progress throughout the flow)
3. OpenAI Integration with Chart Verification (Chart verification process using OpenAI)
4. Questionnaire Flow and Rectification (Answer questionnaire -> Request rectification)
5. Detailed Chart Analysis and Interpretation (Compare charts -> Chart interpretation -> Export)

### Testing Basic API Functionality

```bash
./birth_time_rectifier_tester.sh
```

This script will:
- Check if servers are running
- Create a session
- Prompt for birth details
- Test geocoding
- Validate birth details
- Generate and retrieve a birth chart

### Testing Advanced API Functionality

```bash
./advanced_api_tester.sh --session=SESSION_ID --chart=CHART_ID
```

This script will:
- Get and answer questionnaire questions
- Complete questionnaire
- Request birth time rectification
- Compare original and rectified charts
- Export chart

### Testing WebSocket Connections

```bash
./websocket_tester.sh [--session=SESSION_ID]
```

This script will:
- Connect to the WebSocket server
- Display real-time messages
- Test sending events

### Testing OpenAI Integration with Confidence Tracking

```bash
./openai_integration_tester.sh [--session=SESSION_ID] [--chart=CHART_ID] [--threshold=90]
```

This script will:
- Create or use an existing chart with OpenAI verification
- Start a WebSocket connection in the background
- Run through the questionnaire until reaching the confidence threshold
- Request birth time rectification
- Compare charts
- Show WebSocket messages received during the process

### Testing Rectification Algorithms & Chart Interpretation

```bash
./rectification_algorithm_tester.sh [--session=SESSION_ID] [--chart=CHART_ID] [--rectified=RECTIFIED_CHART_ID] [--threshold=90]
```

This script will:
- Provide detailed analysis of planetary positions in both original and rectified charts
- Test chart comparison endpoint with detailed differences analysis
- Test chart interpretation endpoints for both charts
- Analyze rectification algorithm techniques and weights
- Test chart export functionality in multiple formats (PDF, JSON, PNG)
- Test comparison export functionality
- Save all results and exports to a results directory

## Implementation Details

These scripts test the full implementation sequence diagram as specified in:
- docs/architecture/sequence_diagram.md "Original Sequence Diagram - Full Implementation" section
- docs/architecture/api_architecture.md
- docs/architecture/unified_api_gateway_diagram.md

The sequence follows:
1. Session initialization
2. Birth details collection and geocoding
3. Chart generation with OpenAI verification
4. Questionnaire with answer analysis until confidence threshold (90% by default)
5. Birth time rectification with algorithm analysis
6. Detailed chart comparison
7. Chart interpretation for original and rectified charts
8. Export charts and comparison in various formats

## Examples

### Generate a new chart and test the full flow

```bash
./run_all_tests.sh
# Select option 6 to run all tests according to the sequence diagram
```

### Test just the OpenAI integration with a higher confidence threshold

```bash
./openai_integration_tester.sh --threshold=95
```

### Test rectification algorithms with existing charts

```bash
./rectification_algorithm_tester.sh --session=SESSION_ID --chart=ORIGINAL_CHART_ID --rectified=RECTIFIED_CHART_ID
```

### Test a specific session's WebSocket connection

```bash
./websocket_tester.sh --session=your-session-id
```
