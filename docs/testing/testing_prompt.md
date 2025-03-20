# Objective
  - Create, execute, and monitor comprehensive integration tests for the Birth Time Rectifier application that use
  - ONLY REAL IMPLEMENTATIONS with no mocks, fallbacks, or simulated mechanisms.
  - The tests must follow the exact sequence flow outlined in the "ORIGINAL SEQUENCE DIAGRAM - FULL IMPLMENTATION" section in the@sequence_diagram.mddiagram and produce genuine outputs at each step.

## Key Files to Use
    * tests/integration/test_sequence_flow_real.py: Main test file to execute/update @test_sequence_flow_real.py
    * tests/test_data_source/input_birth_data.json: Source of birth data input @input_birth_data.json
    * tests/test_data_source/test_db.json: Storage for intermediate test results @test_db.json
    * tests/test_data_source/output_birt_data.json: Final output for rectification results @output_birt_data.json
    * tests/test_data_source/test_charts_data.json: Chart data for visualization @test_charts_data.json

### NON-NEGOTIABLE REQUIREMENTS
- NO MOCKS OR FALLBACKS:
   1. You must NOT use mockups, simulated fallback mechanisms, or hardcoded response values
   2. All API calls, astrological calculations, and chart generations must be REAL
   3. When encountering errors, fix the actual root cause, not the test
   4. If errors occur in backend services, modify the relevant files in @ai_service directory

- EXACT SEQUENCE FLOW IMPLEMENTATION:
   1. Strictly follow the "Original Sequence Diagram - Full Implementation" Section from @sequence_diagram.md
   2. Each step in the diagram must be implemented with corresponding API call
   3. For each sequence step, capture real outputs from the actual API responses
   4. DO NOT skip any step in the sequence diagram

- REAL DATA TRANSFORMATION PIPELINE:
   1. Input: Use birth data from @input_birth_data.json as user-provided information
   2. Processing: Use real APIs for geocoding, validation, chart generation, and rectification
   3. Output: Store complete results in @output_birt_data.json with full chart details
   4. Visualization: Create chart visualization data in @test_charts_data.json

- COMPREHENSIVE API TESTING:
   1. Test all exposed API endpoints including WebSocket connections
   2. Each API endpoint must receive real input and return real results
   3. The test must validate response integrity, not just successful status codes
   4. All endpoints must accurately follow the sequence diagram

### EXPECTED TESTING APPROACH
- Session Initialization:
   1. Create a real user session
   2. Store session ID for subsequent calls
   3. Validate session creation in @test_db.json

- Location Geocoding:
   1. Use real geocoding service to resolve location
   2. Store coordinates and timezone information
   3. No hardcoded fallback coordinates

- Chart Validation & Generation:
   1. Validate birth details with real astrological rules
   2. Generate actual birth chart with real calculations
   3. Verify chart data with OpenAI (real API call)
   4. Store complete chart in database

- Questionnaire Flow:
   1. Initialize real questionnaire session
   2. Generate authentic questions via API
   3. Submit meaningful answers for rectification
   4. Complete questionnaire with final submission

- Birth Time Rectification:
   1. Use real rectification algorithms
   2. Process questionnaire answers for adjustment
   3. Generate actual rectified birth time and chart
   4. Store rectification metadata and confidence levels

- Chart Comparison & Export:
   1. Compare original and rectified charts
   2. Generate meaningful differences analysis
   3. Create exportable chart formats
   4. Store comparison results in visualization data

## ERROR HANDLING GUIDELINES
- When encountering errors:

   1. ROOT CAUSE IDENTIFICATION:  @my-error-fixing-protocols.mdc
      * Perform deep diagnosis to find the true source of error
      * Trace through service calls to identify failing components
      * Log detailed error information for debugging

   2. SERVICE REPAIR PRIORITY: @my-error-fixing-protocols.mdc
      * Fix the actual service implementation causing the error
      * Look for failures in @ai_service modules that need correction
      * DO NOT mask errors with try/except blocks or fallbacks

    3. COMPONENT FIXING APPROACH: @my-error-fixing-protocols.mdc
       * If a calculation service fails, fix the calculation method
       * If an API endpoint is incorrect, update the endpoint handler
       * If data formats are inconsistent, standardize them properly

## DATABASE AND FILE SYSTEM PERSISTENCE:
    * Ensure all data is properly persisted in test files
    * Fix any issues with file read/write operations
    * Address database connection or schema issues if present

## IMPLEMENTATION VERIFICATION
   - Your test implementation must:
      - Successfully run end-to-end without errors
      - Generate complete and accurate data in all output files
      - Use real astrological calculations at every step
      - Follow the exact sequence diagram flow with no deviations
      - Fix any underlying issues in the application code rather than bypassing them
      - Never substitute real API calls with mocks or simulated responses

# CONCLUSION
   - The final integration test must validate the entire application flow using real data transformations, calculations, and APIs.
   - Success is measured by accurate rectification results derived from genuine astrological calculations and meaningful life event analysis, precisely matching the sequence diagram specification.
   - Any component that cannot meet these requirements must be fixed at its source.
@Web @Codebase
