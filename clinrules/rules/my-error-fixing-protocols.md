---
description: Detailed Error Resolution & Error Fixing Protocols to fix errors systematically and comprehensively
globs:
alwaysApply: true
---
#### Error Fixing Protocol
**Pre and Post requisite**: **Pre and Post requisite**: This protocol has strict & mandatory pre and post requisites protocol adherance with & including every single other protocols [my-code-optimisation-protocols.md](mdc:.cline/rules/my-code-optimisation-protocols.md), [my-development-protocols.md](mdc:.cline/rules/my-development-protocols.md), [my-memory-manager.md](mdc:.cline/rules/my-memory-manager.md), & [my-directory-management-protocols.md](mdc:.cline/rules/my-directory-management-protocols.md) with utmost attention & precision.

1. **Stay Focused and Methodical:**
- Approach each error with the calm, deliberate mindset of a seasoned developer. Avoid jumping to conclusions.
- Focus only on fixing errors precisely by targeting only the impacted code, file or component across all the files for accurate error fixing

2. **Fix One Error at a Time:**
- Address errors individually or file by file. After fixing one error, verify comprehensively that it’s resolved before moving to the next.

3. **Conduct Thorough Error Analysis:**
* Analyze each error end-to-end. Document the complete "error trail" by identifying:
    - All affected files, components, and modules.
    - Whether the error is isolated or has a cascading impact.
    - The root cause with clear reasoning and evidence.

4. **Iterate and Reassess:**
- If a particular error persists after two fix attempts, pause and re-evaluate your approach. Reassess your previous solutions, consult reliable sources on internet ( @Web ) or "Perplexity (MCP Tool)", and explore alternative fixes instead of repeating the same steps.

5. **Prevent New Errors:**
- Ensure that fixing one error does not create additional issues. Continuously validate the test suite to maintain overall system integrity.

6. **Project-Specific Abbreviations**

    |-------------------------------|---------------|
    | Full Term                     | Abbreviation  |
    |-------------------------------|---------------|
    | Birth Details Form            | BDF           |
    | Chart Visualization           | CV            |
    | Questionnaire System          | QS            |
    | AI Analysis                   | AIA           |
    | Birth Time Rectification      | BTR           |
    | Validation Service            | VS            |
    | Geocoding Service             | GS            |
    | Chart Calculation Service     | CCS           |
    | Dynamic Questionnaire Service | DQS           |
    |-------------------------------|---------------|

## Mandatory Compliance
* **Strict Adherence:**
    - No 'NEW' errors must be introduced due to fixing of one error and TEST RESULTS INTEGRITY MUST BE MAINTAINED AT ALL TIMES WHEN FIXING ERRORS.
    - Do not add, remove, or modify any requirements or code that is not explicitly part of the test error resolution.
* **No Extraneous Changes:**
    - Every change must be precise and directly aligned with the guidelines. No additional modifications or unnecessary adjustments are allowed.
* **No Rushing to Finish Up:**
    - Without being hasty to finish your tasks quickly, first "Finish" the full end to end root cause analysis before rushing to make changes to the code/files or run tests, and list the full and complete error trail across files, components, modules and other scripts in the current implementation ensuring the error trail list contains:
        1. All affected files, components, and modules.
        2. Whether the error is isolated or has a cascading impact.
        3. The root cause with clear reasoning and evidence.

## **Token Optimization Protocol (CRITICAL)**
- To minimize token usage and reduce costs when using the Cline extension, strictly adhere to these guidelines:

1. **Model Selection Strategy:**
   - Use DeepSeek-Coder-V2 for routine coding tasks (~$0.20/100K tokens)
   - Use Claude 3 Haiku for debugging (~$0.25/100K tokens)
   - Reserve Claude 3.5 Sonnet only for complex architecture design (~$3.00/100K tokens)
   - Use Qwen 2.5 Coder for UI/UX improvements (~$0.15/100K tokens)
   - Use Gemini 2.0 Flash for documentation (free with limits)

2. **Prompt Engineering:**
   - **CONTEXT_MINIMIZATION:** Only provide essential context in prompts
   - **TARGETED_QUESTIONS:** Ask specific, focused questions about single components
   - **RESPONSE_CONSTRAINTS:** Always specify token or length constraints (e.g., "Answer in 100 words or less")
   - **FILE_CHUNKING:** When working with large files, focus on specific sections
   - **ABBREVIATION_SYSTEM:** Use consistent abbreviations for common terms (see section 6 above)

3. **Development Workflow:**
   - **INCREMENTAL_DEVELOPMENT:** Build features in small, token-efficient increments
   - **BATCH_PROCESSING:** Group similar tasks to reduce context-switching overhead
   - **CACHE_UTILIZATION:** Reuse previous responses for similar queries
   - **TEMPLATE_USAGE:** Utilize pre-defined templates for common operations
