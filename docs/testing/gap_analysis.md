graph TD
    %% Main Categories of Gaps
    subgraph "Critical Implementation Gaps"
        G1[API Router Issue:<br/>Workaround with dual-registration]
        G2[Chart Comparison Service:<br/>Incomplete implementation]
        G3[Session Management:<br/>Missing implementation]
        G4[Authentication/Authorization:<br/>Not implemented]
    end

    subgraph "Documentation Gaps"
        D1[Interpretation Service:<br/>Documentation incomplete]
        D2[Questionnaire Flow:<br/>Multi-step process not fully documented]
        D3[AI Analysis Processing:<br/>Data flow not clearly defined]
    end

    subgraph "Integration Gaps"
        I1[Frontend-Backend Error Handling:<br/>Not standardized]
        I2[Real-time Updates:<br/>WebSocket integration missing]
        I3[Birth Time Rectification:<br/>Progress tracking incomplete]
    end

    %% Relationships between gaps
    G1 -->|Leads to| I1
    G1 -->|Makes development<br/>more complex| G3
    G2 -->|Affects| I2
    G3 -->|Impacts| G4
    G3 -->|Prevents| I3
    D1 -->|Causes| I1
    D3 -->|Results in| I2
    D2 -->|Complicates| I3
    G4 -->|Weakens| D1

    %% Impact Areas
    subgraph "Affected Application Areas"
        A1[User Experience]
        A2[Security]
        A3[Developer Productivity]
        A4[Application Scalability]
    end

    %% Connect gaps to impact areas
    G1 -.->|Impacts| A3
    G2 -.->|Impacts| A1
    G3 -.->|Impacts| A1
    G3 -.->|Impacts| A2
    G4 -.->|Critically impacts| A2
    I1 -.->|Impacts| A1
    I2 -.->|Impacts| A1
    I3 -.->|Impacts| A1
    D1 -.->|Impacts| A3
    D2 -.->|Impacts| A3
    D3 -.->|Impacts| A3
    A3 -.->|Affects| A4

    %% Severity Classification
    classDef critical fill:#ff6666,stroke:#333,stroke-width:2px;
    classDef high fill:#ffcc66,stroke:#333,stroke-width:2px;
    classDef medium fill:#ffff99,stroke:#333,stroke-width:2px;
    classDef low fill:#e1ffe1,stroke:#333,stroke-width:1px;
    classDef impact fill:#e6e6ff,stroke:#333,stroke-width:1px;

    class G1,G3,G4 critical;
    class G2,I1,I2 high;
    class D1,D2,D3,I3 medium;
    class A1,A2,A3,A4 impact;

    %% Recommended Solutions
    subgraph "Recommended Solutions"
        S1["1. Fix API Router:\nCorrect FastAPI configuration to properly handle /api prefix"]
        S2["2. Implement Session Management:\nDevelop session init, validation, and persistence"]
        S3["3. Add Authentication/Authorization:\nImplement JWT or similar token-based system"]
        S4["4. Complete Chart Comparison Service:\nFinalize implementation with proper data structures"]
        S5["5. Add Real-time Updates:\nImplement WebSockets for long-running processes"]
    end

    %% Connect gaps to solutions
    G1 -.->|Solved by| S1
    G3 -.->|Solved by| S2
    G4 -.->|Solved by| S3
    G2 -.->|Solved by| S4
    I2 -.->|Solved by| S5

    classDef solution fill:#d4f4ff,stroke:#0078d7,stroke-width:1px;
    class S1,S2,S3,S4,S5 solution;
