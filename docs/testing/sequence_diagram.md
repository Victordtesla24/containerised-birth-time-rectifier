sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as API Layer
    participant BE as Backend Services
    participant DB as Database

    %% Initial Flow - Session Initialization
    Note over User,DB: ❌ Missing: Session Management
    User->>FE: Visit application
    FE->>API: Should call: GET /api/session/init
    API--xFE: Missing endpoint implementation
    Note over FE,API: No session management<br/>currently implemented

    %% Birth Details Entry and Validation
    User->>FE: Enter birth location
    FE->>API: POST /api/geocode<br/>{query: "New York, USA"}
    API->>BE: Process location request
    BE->>DB: Query location database
    DB-->>BE: Return coordinates
    BE-->>API: Location data
    API-->>FE: {results: [{id: "loc_123", name: "New York City", country: "United States", latitude: 40.7128, longitude: -74.0060, timezone: "America/New_York"}]}

    User->>FE: Enter birth date and time
    FE->>API: POST /api/chart/validate<br/>{birth_date: "1990-01-15", birth_time: "14:30:00", latitude: 40.7128, longitude: -74.0060, timezone: "America/New_York"}
    API->>BE: Validate birth details
    BE-->>API: Validation result
    API-->>FE: {valid: true, errors: []}

    %% Chart Generation
    User->>FE: Request chart generation
    FE->>API: POST /api/chart/generate<br/>{birth_date: "1990-01-15", birth_time: "14:30:00", latitude: 40.7128, longitude: -74.0060, timezone: "America/New_York", options: {house_system: "placidus"}}
    API->>BE: Calculate astrological chart
    BE->>DB: Store chart data
    DB-->>BE: Return chart ID
    BE-->>API: Chart data
    API-->>FE: {chart_id: "chrt_123456", ascendant: {sign: "Virgo", degree: 15.32}, planets: [...], houses: [...]}

    %% Chart Visualization
    FE->>API: GET /api/chart/chrt_123456
    API->>BE: Retrieve chart
    BE->>DB: Query chart data
    DB-->>BE: Chart details
    BE-->>API: Complete chart data
    API-->>FE: {chart_id: "chrt_123456", ascendant: {sign: "Virgo", degree: 15.32}, planets: [...], houses: [...], aspects: [...]}

    %% Questionnaire
    User->>FE: Navigate to questionnaire
    FE->>API: GET /api/questionnaire
    API->>BE: Generate questionnaire
    BE-->>API: Questionnaire data
    API-->>FE: {questions: [{id: "q_001", text: "Have you experienced any major career changes?", type: "yes_no"}]}

    User->>FE: Answer question (Yes)
    FE->>API: POST /api/questionnaire/q_001/answer<br/>{question_id: "q_001", answer: "yes"}
    API->>BE: Process answer
    BE->>DB: Store answer
    BE-->>API: Next question
    API-->>FE: {status: "accepted", next_question_url: "/api/questionnaire/q_002"}

    User->>FE: Answer question (Date)
    FE->>API: POST /api/questionnaire/q_002/answer<br/>{question_id: "q_002", answer: {date: "2018-03-15", additional_notes: "Career change"}}
    API->>BE: Process answer
    BE->>DB: Store answer
    BE-->>API: Next question
    API-->>FE: {status: "accepted", next_question_url: "/api/questionnaire/q_003"}

    User->>FE: Complete questionnaire
    FE->>API: POST /api/questionnaire/complete<br/>{rectification_id: "rect_123456"}
    API->>BE: Finalize questionnaire
    BE-->>API: Completion status
    API-->>FE: {status: "processing", estimated_completion_time: "2023-06-15T13:30:00Z"}

    %% Birth Time Rectification
    FE->>API: POST /api/chart/rectify<br/>{chart_id: "chrt_123456", answers: [...], birth_time_range: {min_hours: 13, min_minutes: 0, max_hours: 16, max_minutes: 0}}
    API->>BE: Perform birth time rectification
    BE->>DB: Process answers and chart data
    Note over BE: AI analysis runs to<br/>determine optimal birth time
    DB-->>BE: Return analysis results
    BE-->>API: Rectification result
    API-->>FE: {rectification_id: "rect_123456", confidence_score: 87.5, original_birth_time: "14:30:00", rectified_birth_time: "15:12:00", rectified_chart_id: "chrt_234567"}

    %% Chart Comparison
    Note over User,DB: ❌ Incomplete Implementation: Chart Comparison
    FE->>API: GET /api/chart/compare?chart1_id=chrt_123456&chart2_id=chrt_234567
    API->>BE: Compare charts
    BE->>DB: Retrieve both charts
    DB-->>BE: Charts data
    BE-->>API: Comparison data
    API-->>FE: {differences: [{type: "ascendant_shift", chart1_position: {sign: "Virgo", degree: 15.32}, chart2_position: {sign: "Virgo", degree: 18.75}}, ...]}

    %% Interpretation
    Note over User,DB: ❌ Incomplete Implementation: Interpretation Service
    FE->>API: GET /api/interpretation?chart_id=chrt_234567
    API->>BE: Generate interpretation
    BE->>DB: Retrieve chart data
    DB-->>BE: Chart details
    BE-->>API: Personalized insights
    API-->>FE: {insights: [...]}

    %% Export Chart
    User->>FE: Request chart export
    FE->>API: POST /api/chart/export<br/>{chart_id: "chrt_234567", format: "pdf", include_interpretation: true}
    API->>BE: Generate export
    BE->>DB: Retrieve chart data
    DB-->>BE: Chart details
    BE-->>API: Export data
    API-->>FE: {export_id: "exp_123456", status: "processing", download_url: "/api/export/exp_123456/download"}

    FE->>API: GET /api/export/exp_123456/download
    API->>BE: Retrieve export
    BE-->>API: Export file
    API-->>FE: Binary file data (PDF)
    FE-->>User: Display downloadable chart
