import React, { useState } from 'react';

/**
 * Additional Questions Component
 *
 * This component is displayed when the confidence score is below 80% and
 * handles the collection of additional information to improve AI analysis.
 * It represents node J in the UI/UX flow diagram and the J → G path:
 *
 * H -->|No| J[Additional Questions]
 * J --> G[AI Analysis]
 */
const AdditionalQuestions = ({ questions, onSubmit, isSubmitting = false }) => {
  const [answers, setAnswers] = useState({});

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prevAnswers => ({
      ...prevAnswers,
      [questionId]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(answers);
  };

  if (!questions || questions.length === 0) {
    return (
      <div className="no-questions-container" data-testid="no-additional-questions">
        <p>No additional questions available. Please try again later.</p>
        {/* Add a hidden element to indicate the flow path */}
        <div style={{ display: 'none' }} data-testid="flow-path-info">
          Path: H → J [Additional Questions] (No questions available)
        </div>
      </div>
    );
  }

  return (
    <div className="additional-questions" data-testid="additional-questions">
      <h2>Additional Questions</h2>
      {/* Add a hidden element to indicate the flow path */}
      <div style={{ display: 'none' }} data-testid="flow-path-info">
        Path: H → J [Additional Questions] → G [AI Analysis]
      </div>
      <p className="questions-intro">
        Please answer the following questions to help improve the accuracy of your birth time rectification.
        These questions are specifically chosen based on your initial chart and responses.
      </p>

      <form onSubmit={handleSubmit} data-testid="additional-questions-form">
        {questions.map((question, index) => (
          <div
            key={question.id}
            className="additional-question"
            data-testid={`additional-question-${index + 1}`}
          >
            <h3 className="question-text">
              {index + 1}. {question.text}
            </h3>

            {question.type === 'multiple-choice' && (
              <div className="options-container">
                {question.options.map(option => (
                  <div className="option" key={option.value}>
                    <input
                      type="radio"
                      id={`${question.id}-${option.value}`}
                      name={question.id}
                      value={option.value}
                      checked={answers[question.id] === option.value}
                      onChange={() => handleAnswerChange(question.id, option.value)}
                      data-testid={`option-${question.id}-${option.value}`}
                    />
                    <label htmlFor={`${question.id}-${option.value}`}>
                      {option.label}
                    </label>
                  </div>
                ))}
              </div>
            )}

            {question.type === 'yes-no' && (
              <div className="yes-no-container">
                <div className="option">
                  <input
                    type="radio"
                    id={`${question.id}-yes`}
                    name={question.id}
                    value="yes"
                    checked={answers[question.id] === 'yes'}
                    onChange={() => handleAnswerChange(question.id, 'yes')}
                    data-testid="answer-yes"
                  />
                  <label htmlFor={`${question.id}-yes`}>Yes</label>
                </div>
                <div className="option">
                  <input
                    type="radio"
                    id={`${question.id}-no`}
                    name={question.id}
                    value="no"
                    checked={answers[question.id] === 'no'}
                    onChange={() => handleAnswerChange(question.id, 'no')}
                    data-testid="answer-no"
                  />
                  <label htmlFor={`${question.id}-no`}>No</label>
                </div>
              </div>
            )}

            {question.type === 'text' && (
              <div className="text-container">
                <textarea
                  id={question.id}
                  name={question.id}
                  rows="3"
                  value={answers[question.id] || ''}
                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                  placeholder="Enter your answer here..."
                  data-testid={`text-answer-${question.id}`}
                />
              </div>
            )}
          </div>
        ))}

        <div className="submit-container">
          <button
            type="submit"
            disabled={isSubmitting || Object.keys(answers).length < questions.length}
            className="submit-button"
            data-testid="submit-additional"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Additional Information'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdditionalQuestions;
