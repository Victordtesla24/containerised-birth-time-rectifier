RUN THE FOLLOWING AND FOLLOW THE INSTRUCTIONS WITHOUT OVERCOMPLICATING IT.

  'docker exec birth-rectifier-ai python -m pytest tests/integration/test_sequence_flow_real.py -v --no-header --tb=native'

  When analyzing the results, please:
   1. Verify that real API endpoints are being called (OpenAI, astrological calculations) by checking for actual data variations in output
   2. Confirm that NO fallback or mock mechanisms are activated during testing
   3. Identify ANY discrepancies between the test output and the expected flow in the sequence diagram
   4. Highlight specific errors with their root causes in the backend codebase, not in the test itself
   5. Suggest minimal, targeted fixes to the backend code (not the test code) that would resolve any issues

  The implementation should exactly match:
   - The calculation flow in "Original Sequence Diagram - Full Implementation" @sequence_diagram.md
   - The questionnaire interaction pattern in "Consolidated API Questionnaire Flow" @sequence_diagram.md
   - Real astrological calculations with NO simulated data

  After each test run, examine tests/test_data_source/output_birt_data.json to verify: @output_birt_data.json
   - Rectification calculations produced real timestamps with meaningful differences
   - Chart data contains actual astrological positions, not placeholder values
   - Each API call produced unique, calculation-based results

 ### Database Schema Verification
  - The test connects to PostgreSQL but doesn't verify schema integrity before starting tests
  - Add pre-test verification to ensure tables like `charts`, `rectifications`, etc. exist with proper columns

 ### Enhanced Error Tracking
  - Implement detailed error capture across the test flow that logs the exact point of failure
  - Add transaction tracking to trace API requests through the entire system

 ### Ephemeris Data Verification
  - Add validation step to ensure ephemeris files are properly loaded before testing
  - Current ephemeris path setup exists but doesn't validate file presence or integrity

 ### OpenAI API Rate Limit Handling
  - Add intelligent retry mechanisms with exponential backoff
  - Implement request batching to prevent hitting OpenAI API limits during testing

 ### Resource Cleanup
  - Current test attempts cleanup but needs more robust garbage collection between test phases
  - Add explicit database clearing between test runs to prevent leaking state

 ```python
  async def verify_database_schema():
      """Verify required database tables and columns exist before testing."""
     # ... existing code ...

  async def verify_ephemeris_files():
      """Ensure all required ephemeris files are present and valid."""
     # ... existing code ...
 ```

 ### Strict Exception Handling Policy
  - Modify error handlers to always raise exceptions rather than returning fallback values
  - Add these assertion checks after every critical API call:
 ```python
 # Force failure on fallbacks - add to test_sequence_flow_real.py @test_sequence_flow_real.py
  def assert_no_fallbacks(response_data):
      """Ensure no fallback mechanisms were triggered in the response."""
      assert not response_data.get("used_fallback", False), "Fallback mechanism was used!"
      assert not response_data.get("simulated", False), "Simulation was used instead of real calculation!"
      if "error" in response_data and "fallback" in response_data["error"].lower():
          raise AssertionError(f"Error suggests fallback: {response_data['error']}")
 ```

 ### Override Environment Variables
 - Set environment flags to disable fallbacks explicitly:
 ```python
 # Add to test setup
  os.environ["DISABLE_FALLBACKS"] = "true"
  os.environ["FORCE_REAL_API"] = "true"
  os.environ["STRICT_VALIDATION"] = "true"
 ```

 ### Targeted Code Inspection
  - Add runtime inspection that detects if function implementations change during test execution:
 ```python
 # Add function signature verification
  original_signatures = {}
  def register_function_signature(func):
      """Register function signature to detect runtime replacement."""
      original_signatures[func.__name__] = hash(inspect.getsource(func))

  def verify_no_runtime_replacement():
      """Verify no functions were replaced with simpler implementations."""
      for name, original_hash in original_signatures.items():
          func = globals().get(name)
          if func and hash(inspect.getsource(func)) != original_hash:
              raise AssertionError(f"Function {name} was replaced during test execution!")
 ```
### Granular Test Steps
  - Break down the large test into smaller, more focused tests that run sequentially
  - Add detailed assertions after each API call that verify specific response properties

 ### Service-Specific Exception Handlers
  - Implement custom exception classes for each service component:
 ```python
 # exceptions.py
  class ChartServiceError(Exception):
      """Base exception for chart service errors."""
      pass

  class GeocodingError(Exception):
      """Exception raised for geocoding service errors."""
      pass

  class RectificationError(Exception):
      """Exception raised for rectification service errors."""
      pass
 ```

 ### Code Tracing and Logging
  - Enhance logging with transaction IDs that follow requests through services:
 ```python
 # Add to test setup
  import uuid
  def get_trace_id():
      """Generate a trace ID for the current request."""
      return str(uuid.uuid4())

  os.environ["TRACE_ID"] = get_trace_id()
 ```

 ### Test Result Analysis
  - Add result file analysis that compares output against expected schema:

  ```python
  def validate_output_against_schema(file_path, schema):
      """Validate output file against expected schema."""
      with open(file_path, 'r') as f:
          data = json.load(f)

      validation_errors = []
      # Recursively check all properties defined in schema
      # ... implementation ...

      if validation_errors:
          raise AssertionError(f"Output validation failed: {validation_errors}")
 ```
@input_birth_data.json @test_charts_data.json @test_db.json @output_birt_data.json @test_sequence_flow_real.py @docker-compose.yml @ai_service.Dockerfile @api_gateway.Dockerfile @.env @sequence_diagram.md @ai_service @rectification @api_gateway @api @docker-compose 
