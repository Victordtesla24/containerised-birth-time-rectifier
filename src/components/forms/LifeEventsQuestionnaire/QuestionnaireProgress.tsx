import React from 'react';

interface QuestionnaireProgressProps {
  currentQuestion: number;
  totalQuestions: number;
  confidence: number;
}

const QuestionnaireProgress: React.FC<QuestionnaireProgressProps> = ({
  currentQuestion,
  totalQuestions,
  confidence,
}) => {
  const progressPercentage = (currentQuestion / totalQuestions) * 100;
  const confidencePercentage = confidence * 100;

  return (
    <div className="questionnaire-progress">
      <div className="progress-container">
        <div className="progress-info">
          <span>Question {currentQuestion} of {totalQuestions}</span>
          <span>Confidence: {confidencePercentage.toFixed(1)}%</span>
        </div>
        <div className="progress-bar-container">
          <div
            className="progress-bar"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default QuestionnaireProgress;
