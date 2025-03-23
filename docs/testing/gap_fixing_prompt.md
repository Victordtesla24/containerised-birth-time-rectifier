Start by implementing the Chart Service fixes first as they form the foundation for other components. Ensure each implementation is complete before moving to the next area

As a 10x Engineer, implement the missing functionality in the following python files, ***SYSTEMATICALLY & ONE BY ONE***, fully align with the sequence diagram (docs/architecture/sequence_diagram.md), following **EVERY SINGLE** ***CRITICAL REQUIREMENTS*** resolving ***EVERY SINGLE GAP BELOW*** and those identified in the gap analysis document (docs/testing/gap_analysis.md).

## ***CRITICAL REQUIREMENTS***
  1. Implement COMPLETE solutions with NO mockups, fallbacks, or simplified implementations.
  2. Every solution must follow the exact flow described in the "ORIGINAL SEQUENCE DIAGRAM - FULL IMPLEMENTATION" section.
  3. Ensure proper integration between all components (Frontend, API Layer, Backend Services, OpenAI, Database).
  4. Implement robust error handling for all edge cases WITHOUT resorting to simplified fallbacks.
  5. Focus on resolving ALL unresolved gaps in the analysis document - no partial implementations.

## IMPLEMENTATION AREAS (Follow this exact order)
 - Start by implementing the Chart Service, then core rectification fixes first as they form the foundation for other components and then follow the gap fixing order exactly how they have been written below. Ensure each implementation is complete before moving to the next area

### 1. CHART SERVICE IMPLEMENTATIONS
Fix the following files:
- ai_service/services/chart_service.py:
  - Lines 495-505: Complete chart export functionality that actually generates PDF/image files
  - Lines 412-427: Implement proper OpenAI integration for rectification
  - Lines 263-313: Enhance calculate_chart to fully leverage AI for validation
  - Lines 372-393: Replace simplified algorithm with proper astrological analysis for chart comparison
  - Lines 135-199: Improve verification process with robust recovery options
  - Lines 300-345: Implement proper divisional charts for Vedic analysis
  - Lines 525-575: Add 3D visualization capabilities as specified in testing instructions

### 2. CORE RECTIFICATION FUNCTIONALITY
Fix the following files:
- ai_service/core/rectification/chart_calculator.py:
  - Lines 21-39: Replace dummy implementations with actual astrological libraries
  - Lines 47-54: Implement proper timezone finder
  - Lines 98-102: Replace fallback coordinates with robust geolocation handling
  - Lines 148-158: Replace placeholder data with actual ephemeris calculations
  - Lines 251-279: Implement verification against Vedic astrological standards

### 3. CHART VISUALIZATION INTEGRATION
Fix the following files:
- ai_service/utils/chart_visualizer.py:
  - Lines 49-109: Integrate Vedic chart visualization with export system
  - Lines 384-475: Connect chart image generation to export functionality
  - Lines 477-567: Implement production-quality PDF generation
  - Lines 245-294: Include comparison chart visualization in API responses

### 4. DATABASE IMPLEMENTATION
Fix the following files:
- ai_service/database/repositories.py:
  - Lines 29-42: Implement comprehensive error handling for database failures
  - Lines 162-181: Add proper validation and error handling for store_comparison
  - Lines 252-288: Standardize error handling across all repository methods
  - Lines 363-375: Add file existence verification before storing export metadata
  - Lines 450-497: Complete database error categorization for all failure modes

- ai_service/core/rectification.py:
  - Lines 58-62: Replace mock OpenAI implementation with actual service
  - Lines 269-273, 278-280, 388-393, 403-405, 468-476: Replace all fallbacks with alternative calculation methods
  - Lines 209-256: Enhance MinimalChart to provide accurate planetary calculations
  - Lines 508-562: Standardize AI-assisted rectification response handling
  - Lines 661-699: Implement proper astrological significance evaluation for transit analysis

### 5. QUESTIONNAIRE SERVICE COMPLETION
Fix the following files:
- ai_service/api/services/questionnaire_service.py:
  - Lines 820-835: Enhance complete_questionnaire with comprehensive answer analysis
  - Lines 432-467: Improve answer analysis to properly link responses to astrological factors
  - Lines 617-659: Enhance birth time indicator extraction with sophisticated pattern recognition

### 6. API ROUTING ENHANCEMENTS
Fix the following files:
- ai_service/api/routers/questionnaire.py:
  - Lines 495-518: Add comprehensive error handling and proper OpenAI integration
  - Lines 631-681: Implement detailed progress information for rectification status

- ai_service/api/routers/chart.py:
  - Lines 153-178: Enhance chart comparison with deeper astrological interpretation
  - Lines 180-210: Complete export functionality with proper file generation
  - Lines 235-299: Add file existence verification before serving downloads

- api_gateway/main.py:
  - Lines 295-329: Implement enhanced error handling with proper retry logic

### 7. OPENAI INTEGRATION
Fix the following files:
- ai_service/services/chart_service.py, ai_service/core/rectification.py:
  - Standardize OpenAI usage throughout the application
  - Implement consistent verification process using OpenAI
  - Improve error handling for OpenAI verification failures

- ai_service/api/services/questionnaire_service.py:
  - Lines 873-954: Enhance analysis of responses to provide deep astrological insights

- ai_service/api/routers/questionnaire.py:
  - Lines 495-640: Implement structured prompt strategy for rectification process

### 8. WEBSOCKET IMPLEMENTATION
Fix the following files:
- api_gateway/websocket_proxy.py:
  - Lines 190-220: Add proper message validation and error recovery mechanisms

- api_gateway/websocket_events.py:
  - Lines 20-50: Implement detailed progress information for rectification process

- src/services/api/WebSocketService.ts:
  - Lines 45-88: Add proper connection failure handling and reconnection logic

## VERIFICATION REQUIREMENTS

1. Each implementation must align with the sequence diagram flow
2. No mockups, simplified algorithms, or fallbacks are acceptable
3. Every error case must be properly handled with appropriate recovery mechanisms
4. All components must communicate correctly according to the sequence diagram
5. Verify each implementation against the requirements in the gap analysis document
6. Remove all ⚠️ UNRESOLVED markers from the gap analysis document when fixed
