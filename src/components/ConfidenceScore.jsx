import React from 'react';

/**
 * Confidence Score Component
 *
 * This component displays the confidence score for the birth time rectification
 * with visual indicators to show whether it's high enough to proceed directly
 * to rectification or requires additional questions.
 *
 * The component is a critical part of the UI/UX flow as it represents the
 * decision point H in the flow diagram, where:
 * G --> H{Confidence > 80%?}
 * H -->|Yes| I[Birth Time Rectification]
 * H -->|No| J[Additional Questions]
 */
const ConfidenceScore = ({ score, showAdditionalQuestions }) => {
  // Determine score status (high or low)
  const isHighConfidence = score >= 80;
  const scoreColor = isHighConfidence ? '#2ecc71' : '#e74c3c';

  return (
    <div className="confidence-score-container" data-testid="confidence-score-container">
      <h3>AI Analysis Confidence</h3>

      <div className="score-display" data-testid="confidence-score" data-value={score}>
        <div
          className="score-value"
          style={{
            color: scoreColor,
            fontSize: '2rem',
            fontWeight: 'bold'
          }}
        >
          {score.toFixed(1)}%
        </div>

        <div className="score-gauge">
          <div
            className="score-bar"
            style={{
              width: '100%',
              height: '10px',
              backgroundColor: '#e0e0e0',
              borderRadius: '5px',
              position: 'relative',
              marginTop: '10px'
            }}
          >
            <div
              className="score-fill"
              style={{
                width: `${score}%`,
                height: '100%',
                backgroundColor: scoreColor,
                borderRadius: '5px',
                position: 'absolute'
              }}
            />
              <div
                className="threshold-marker"
                style={{
                  position: 'absolute',
                  left: '80%',
                  top: '-5px',
                  height: '20px',
                  width: '2px',
                  backgroundColor: '#666',
                }}
                data-testid="threshold-marker"
              />
              <div
                className="threshold-label"
                style={{
                  position: 'absolute',
                  left: '80%',
                  bottom: '-20px',
                  transform: 'translateX(-50%)',
                  fontSize: '12px'
                }}
                data-testid="threshold-label"
              >
                80% threshold
              </div>
          </div>
        </div>
      </div>

      <div className="confidence-message" data-testid="confidence-message">
        {isHighConfidence ? (
          <p className="high-confidence" data-testid="high-confidence-message">
            <strong>High confidence achieved.</strong> We can proceed with birth time rectification.
          </p>
        ) : (
          <p className="low-confidence" data-testid="low-confidence-message">
            <strong>More information needed.</strong> Please answer additional questions to improve accuracy.
          </p>
        )}
      </div>

      {/* Add explicit path information for the flow diagram */}
      <div className="flow-path-info" style={{ display: 'none' }} data-testid="flow-path-info">
        Path: G → H → {isHighConfidence ? 'I [Birth Time Rectification]' : 'J [Additional Questions]'}
      </div>

      {!isHighConfidence && showAdditionalQuestions && (
        <button
          className="additional-questions-button"
          data-testid="continue-questions"
        >
          Continue to Additional Questions
        </button>
      )}
    </div>
  );
};

export default ConfidenceScore;
