import React from 'react';

interface QuestionnaireCompleteProps {
  confidence: number;
  questionsAnswered: number;
  totalQuestions: number;
}

const QuestionnaireComplete: React.FC<QuestionnaireCompleteProps> = ({
  confidence,
  questionsAnswered,
  totalQuestions,
}) => {
  const confidencePercentage = confidence * 100;

  return (
    <div className="questionnaire-complete">
      <h2>Questionnaire Complete!</h2>
      <div className="completion-stats">
        <p>You answered {questionsAnswered} out of {totalQuestions} questions.</p>
        <p>Confidence level: {confidencePercentage.toFixed(1)}%</p>
      </div>
      <div className="completion-message">
        <p>Thank you for completing the questionnaire. Your responses will help us provide a more accurate birth time rectification.</p>
        <p>The analysis is being processed...</p>
      </div>
    </div>
  );
};

export default QuestionnaireComplete;
