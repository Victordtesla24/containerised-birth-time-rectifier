# Token Optimization for Birth Time Rectifier Project

## 1. Token Usage Tracking

```javascript
// Add this to your monitoring setup
const tokenTracker = {
  dailyUsage: 0,
  maxDaily: 100000, // Adjust based on budget

  track: function(promptTokens, responseTokens) {
    const total = promptTokens + responseTokens;
    this.dailyUsage += total;
    console.log(`Used ${total} tokens (${promptTokens} prompt, ${responseTokens} response)`);
    console.log(`Daily total: ${this.dailyUsage} / ${this.maxDaily} (${((this.dailyUsage/this.maxDaily)*100).toFixed(1)}%)`);

    // Alert if approaching limit
    if (this.dailyUsage > this.maxDaily * 0.8) {
      console.warn("⚠️ Approaching daily token limit");
    }
  }
};
```

## 2. Model Selection Strategy

| Task Type | Recommended Model | Avg Cost |
|-----------|-------------------|----------|
| Simple coding tasks | DeepSeek-Coder-V2 | $0.20/100K tokens |
| Debugging | Claude 3 Haiku | $0.25/100K tokens |
| Architecture design | Claude 3.5 Sonnet | $3.00/100K tokens |
| UI/UX improvements | Qwen 2.5 Coder | $0.15/100K tokens |
| Documentation | Gemini 2.0 Flash | Free (with limits) |

## 3. Component-Specific Optimization

### Birth Details Form
- Limit context to validation logic only
- Use template prompts for common field validations
- Example: "Optimize the date validation in Birth Details Form at line X"

### Chart Generation & Visualization
- Cache common astrological calculations
- Use abbreviated planet/house references
- Template-based prompt for chart elements
- Example: "Implement planet position calculation for Mars only"

### Questionnaire System
- Template-based questions with minimal context
- Focus prompts on specific question logic only
- Example: "Add validation to question #3 about childhood memories"

### AI Analysis
- Break analysis into discrete steps
- Only include relevant chart elements in each prompt
- Example: "Analyze house placement for career indicators only"

## 4. Prompt Templates (Token-Optimized)

### Chart Generation Prompt
```
Generate chart calculation for:
- DOB: ${date}
- Time: ${time}
- Location: ${lat},${long}
Focus only on [specific aspect] calculation.
```

### Debugging Prompt
```
Error in ${component} at line ${lineNum}.
Error message: ${error}
Likely cause: ${hypothesis}
Suggest fix within 100 tokens.
```

### Feature Implementation Prompt
```
Implement ${featureName} with these constraints:
1. ${constraint1}
2. ${constraint2}
Respond with minimal code only.
```

## 5. Monitoring & Optimization Cycle

1. Track token usage daily
2. Identify high-consumption patterns
3. Optimize prompts for frequent requests
4. Switch to lighter models for routine tasks
5. Review weekly to identify optimization opportunities

## 6. Cline-Specific Optimization Rules

Add these rules to your `.clinerules` file:

```
### Token Optimization Protocol
- CONTEXT_MINIMIZATION: Only provide essential context in prompts
- TARGETED_QUESTIONS: Ask specific, focused questions about single components
- MODEL_SELECTION: Use the most cost-effective model for each task type
- TEMPLATE_USAGE: Utilize pre-defined templates for common operations
- BATCH_PROCESSING: Group similar tasks to reduce context-switching overhead
- INCREMENTAL_DEVELOPMENT: Build features in small, token-efficient increments
- RESPONSE_CONSTRAINTS: Always specify token or length constraints in prompts
- FILE_CHUNKING: When working with large files, focus on specific sections
- CACHE_UTILIZATION: Reuse previous responses for similar queries
- ABBREVIATION_SYSTEM: Use consistent abbreviations for common terms
```

## 7. Project-Specific Abbreviations

To further reduce token usage, use these abbreviations in your prompts:

| Full Term | Abbreviation |
|-----------|--------------|
| Birth Details Form | BDF |
| Chart Visualization | CV |
| Questionnaire System | QS |
| AI Analysis | AIA |
| Birth Time Rectification | BTR |
| Validation Service | VS |
| Geocoding Service | GS |
| Chart Calculation Service | CCS |
| Dynamic Questionnaire Service | DQS |

## 8. Implementation in CI/CD

Add token usage monitoring to your CI/CD pipeline:

```yaml
token-monitoring:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Track token usage
      run: |
        node scripts/track-token-usage.js
    - name: Alert if over threshold
      if: ${{ env.TOKEN_USAGE > env.TOKEN_THRESHOLD }}
      run: |
        echo "::warning::Token usage exceeding threshold!"
```
