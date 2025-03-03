# Birth Time Rectifier Developer Guide

## Introduction

This guide provides technical information for developers working on the Birth Time Rectifier application. It covers architecture, implementation details, and specific guidelines for ensuring accuracy in astrological calculations.

## Table of Contents

1. [Application Architecture](#application-architecture)
2. [Development Environment Setup](#development-environment-setup)
3. [Chart Generation System](#chart-generation-system)
4. [Ensuring Calculation Accuracy](#ensuring-calculation-accuracy)
5. [API Implementation](#api-implementation)
6. [Frontend Components](#frontend-components)
7. [Testing Guidelines](#testing-guidelines)
8. [Project Workflows](#project-workflows)
9. [Troubleshooting](#troubleshooting)

## Application Architecture

The Birth Time Rectifier follows a client-server architecture:

### Backend Architecture
- **FastAPI Framework**: Provides API endpoints for chart generation, questionnaire handling, and birth time rectification
- **Swiss Ephemeris Integration**: Core library for precise astronomical calculations
- **AI Service**: TensorFlow-based system for analyzing life events and providing birth time rectification
- **Data Storage**: PostgreSQL for persistent data and Redis for caching

### Frontend Architecture
- **React with TypeScript**: Component-based UI development
- **Redux**: State management for complex application state
- **D3.js**: Visualization library for rendering astrological charts
- **Axios**: HTTP client for API communication

### High-Level Data Flow

```
User Input → API Endpoints → Chart Generation Service →
Swiss Ephemeris Calculations → Chart Data →
Frontend Rendering → User Interaction
```

## Development Environment Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Docker and Docker Compose (optional)

### Backend Setup

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/yourusername/birth-time-rectifier.git
   cd birth-time-rectifier
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:
   ```bash
   uvicorn ai_service.main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd src
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

## Chart Generation System

The chart generation system is a core component responsible for calculating planetary positions, house systems, and aspects.

### Core Calculation Modules

- `ai_service/core/ephemeris.py`: Interface to Swiss Ephemeris
- `ai_service/core/chart_calculator.py`: Handles core chart calculations
- `ai_service/core/house_systems.py`: Implements different house system calculations
- `ai_service/core/aspects.py`: Calculates planetary aspects and their interpretations

### Astrological Calculation Flow

1. Receive birth details (date, time, location)
2. Calculate precise coordinates and timezone
3. Initialize Swiss Ephemeris with correct parameters
4. Calculate planetary positions
5. Apply ayanamsa correction (sidereal zodiac adjustment)
6. Calculate houses based on selected house system
7. Calculate aspects between planets
8. Generate comprehensive chart data

## Ensuring Calculation Accuracy

Based on analysis of calculation discrepancies, the following measures must be implemented to ensure accuracy:

### Critical Parameters for Accurate Chart Generation

#### 1. Ayanamsa Configuration
```python
# Example implementation in chart_calculator.py
def calculate_chart(birth_data, ayanamsa=23.6647):
    """
    Calculate astrological chart with precise ayanamsa setting

    Args:
        birth_data: Birth details including date, time, location
        ayanamsa: Ayanamsa value, defaults to 23.6647 (Lahiri)
    """
    # Set ayanamsa in Swiss Ephemeris
    swe.set_sid_mode(swe.SIDM_USER, ayanamsa, 0)

    # Continue with calculations...
```

#### 2. House System Selection

The implementation must support multiple house systems, with clear documentation of differences:

```python
# Example implementation in house_systems.py
HOUSE_SYSTEMS = {
    'placidus': swe.HOUSES_PLACIDUS,
    'koch': swe.HOUSES_KOCH,
    'whole_sign': swe.HOUSES_WHOLE_SIGN,
    'equal': swe.HOUSES_EQUAL,
    'bhava': swe.HOUSES_BHAVA  # For Vedic charts
}

def calculate_houses(jd_ut, lat, lon, house_system='placidus'):
    """Calculate house cusps using the specified house system"""
    if house_system not in HOUSE_SYSTEMS:
        raise ValueError(f"Unsupported house system: {house_system}")

    house_flags = HOUSE_SYSTEMS[house_system]
    # Calculate houses and return results
```

#### 3. Time Zone Handling

Precise time zone handling is critical, especially for historical dates:

```python
# Example implementation in time_utils.py
def get_timezone_offset(date, location):
    """
    Get timezone offset for a specific date and location

    This handles historical timezone changes correctly.
    """
    # Use timezonefinder and pytz to determine the timezone
    # Special handling for historical timezone changes
```

#### 4. Node Calculation Methods

Support both Mean and True Node calculations:

```python
# Example in node_calculator.py
def calculate_nodes(jd_ut, node_type='true'):
    """
    Calculate lunar nodes

    Args:
        jd_ut: Julian day in UT
        node_type: 'mean' or 'true'
    """
    if node_type == 'mean':
        node_flag = swe.NODBIT_MEAN
    else:  # true nodes
        node_flag = swe.NODBIT_OSCU

    # Calculate and return node positions
```

### Validation and Verification

To ensure accuracy, implement validation against known reference charts:

```python
# Example in tests/test_chart_validation.py
def test_known_chart_accuracy():
    """Test chart accuracy against known reference charts"""
    # Test data for the chart in kundli-final.pdf
    test_data = {
        "date": "1985-10-24",
        "time": "14:30:00",
        "lat": 18.5204,
        "lon": 73.8567,
        "location": "Pune, India"
    }

    expected = {
        "ascendant": {"sign": "Aquarius", "degree": 1.08},
        "sun": {"sign": "Libra", "degree": 7.24, "house": 9},
        # Add other expected planet positions
    }

    # Generate chart with the same parameters as the reference
    chart = generate_test_chart(
        test_data,
        ayanamsa=23.6647,
        house_system="whole_sign"
    )

    # Assert expected positions match actual positions
    assert chart.ascendant.sign == expected["ascendant"]["sign"]
    assert abs(chart.ascendant.degree - expected["ascendant"]["degree"]) < 0.1
    # More assertions for other planets
```

## API Implementation

The API layer provides endpoints for chart generation and manipulation as specified in the implementation plan.

### RESTful API Design

#### Chart Generation Endpoints

```python
# Example from api/routers/chart_router.py
@router.post("/generate", response_model=ChartData)
async def generate_chart(chart_request: ChartRequest):
    """Generate astrological chart from birth details"""
    # Process request and generate chart
    chart_data = chart_service.generate_chart(
        birth_date=chart_request.birth_date,
        birth_time=chart_request.birth_time,
        latitude=chart_request.latitude,
        longitude=chart_request.longitude,
        location_name=chart_request.location_name,
        house_system=chart_request.house_system,
        ayanamsa=chart_request.ayanamsa,
        node_calculation=chart_request.node_calculation
    )

    return chart_data
```

### Error Handling

Implement proper error handling for all API endpoints:

```python
# Example error handling
@router.post("/generate", response_model=ChartData)
async def generate_chart(chart_request: ChartRequest):
    try:
        chart_data = chart_service.generate_chart(...)
        return chart_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SwissEphemerisError as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
```

## Frontend Components

### Chart Visualization Component

The chart visualization component should render accurate astrological charts using D3.js:

```typescript
// Example pseudocode for src/components/ChartVisualization.tsx
interface ChartProps {
  chartData: ChartData;
  viewType: 'circle' | 'table';
  showAspects: boolean;
}

const ChartVisualization: React.FC<ChartProps> = ({
  chartData,
  viewType,
  showAspects
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (chartData && svgRef.current) {
      if (viewType === 'circle') {
        renderCircularChart(svgRef.current, chartData, showAspects);
      } else {
        renderTableView(svgRef.current, chartData);
      }
    }
  }, [chartData, viewType, showAspects]);

  return (
    <div className="chart-container">
      <svg ref={svgRef} className="chart-svg" viewBox="0 0 600 600" />
      {/* Additional controls */}
    </div>
  );
};

// Chart rendering functions
function renderCircularChart(svg: SVGSVGElement, data: ChartData, showAspects: boolean) {
  // D3.js implementation for circular chart
  // Includes zodiac wheel, house divisions, planets, and aspects
}

function renderTableView(svg: SVGSVGElement, data: ChartData) {
  // Implementation for tabular view of chart data
}
```

### Data Flow for Chart Visualization

```
API Request → Chart Data → Redux Store → Chart Component → D3.js Rendering → User Interaction
```

## Testing Guidelines

### Unit Testing

Write comprehensive unit tests for all calculation functions:

```python
# Example test case for chart calculation
def test_planet_positions():
    """Test calculation of planetary positions"""
    # Test data
    date = "2000-01-01"
    time = "12:00:00"
    lat = 0.0
    lon = 0.0

    # Calculate
    result = calculate_planet_positions(date, time, lat, lon)

    # Assert that results are within expected ranges
    assert 270 <= result["sun"]["longitude"] <= 290  # Approximate Capricorn position
    # More assertions
```

### Integration Testing

Test the integration between components:

```python
# Example integration test
def test_chart_generation_api():
    """Test chart generation through the API"""
    # Make request to test client
    response = client.post(
        "/api/charts/generate",
        json={
            "birth_date": "2000-01-01",
            "birth_time": "12:00:00",
            "latitude": 0.0,
            "longitude": 0.0,
            "location_name": "Greenwich, UK",
            "house_system": "placidus",
            "ayanamsa": 23.6647
        }
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "planets" in data
    assert "houses" in data
    assert "ascendant" in data
```

## Project Workflows

### Development Workflow

Follow these principles when working on the project:

1. **Fail Fast & Iterative Approach**:
   - Implement small, incremental changes
   - Test frequently and roll back if issues are detected
   - Prioritize quick detection and focused solutions

2. **Code Quality**:
   - Follow PEP 8 for Python code
   - Use TypeScript for frontend development
   - Document all functions and modules
   - Maintain test coverage

3. **Pull Request Process**:
   - Create feature branches for new work
   - Include tests with all changes
   - Request code reviews
   - Address feedback before merging

## Troubleshooting

### Common Issues in Chart Generation

#### Incorrect Planetary Positions

**Symptoms**: Planets appear in incorrect signs or at wrong degrees.

**Potential Causes**:
- Incorrect ayanamsa value
- Wrong ephemeris date/time conversion
- Timezone handling issues

**Solutions**:
- Verify ayanamsa setting matches expected value (23.6647° for Lahiri)
- Confirm proper Julian Day conversion
- Check timezone offset calculation

#### House System Discrepancies

**Symptoms**: Houses are assigned to incorrect signs or house cusps are at unexpected degrees.

**Potential Causes**:
- Different house system than expected
- Incorrect ascendant calculation
- Geocoding precision issues

**Solutions**:
- Explicitly specify house system (Placidus, Whole Sign, etc.)
- Verify ascendant calculation algorithm
- Use precise coordinates for location

#### Node Calculation Differences

**Symptoms**: Rahu and Ketu positions differ from reference charts.

**Potential Causes**:
- Using Mean vs. True Node calculations
- Different ayanamsa application to nodes

**Solutions**:
- Explicitly specify node calculation method
- Ensure consistent ayanamsa application

## Conclusion

By implementing these guidelines, developers can ensure accurate chart calculations that match reference expectations, while maintaining the system's extensibility and maintainability. The focus on precise ayanamsa settings, house system implementation, timezone handling, and node calculation methods will address the discrepancies identified in the analysis.

## Resources

- [Swiss Ephemeris Documentation](https://www.astro.com/swisseph/swephprg.htm)
- [D3.js Documentation](https://d3js.org/getting-started)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
