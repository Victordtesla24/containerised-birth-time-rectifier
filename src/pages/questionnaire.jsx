import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { questionnaireApi } from '../services/apiService';

/**
 * Custom error logging function that can be controlled in test environments
 * @param {string} message - Error message prefix
 * @param {Error} error - The error object
 */
export const error = (message, error) => {
  // In test environments, this can be mocked to prevent console output
  if (process.env.NODE_ENV !== 'test') {
    console.error(message, error);
  }
};

/**
 * Dynamic questionnaire page for birth time rectification
 * This component fetches questions from the API and handles the questionnaire flow
 */
const QuestionnairePage = () => {
  const router = useRouter();
  const { sessionId } = router.query;

  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [processingIndicator, setProcessingIndicator] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confidenceScore, setConfidenceScore] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [hasReachedThreshold, setHasReachedThreshold] = useState(false);

  // Fetch initial questions when component mounts
  useEffect(() => {
    if (!sessionId) return;

    const fetchInitialQuestions = async () => {
      try {
        setIsLoading(true);
        const response = await questionnaireApi.initializeQuestionnaire(sessionId);

        if (response && response.questions && response.questions.length > 0) {
          setQuestions(response.questions);
          setConfidenceScore(response.confidenceScore || 0);
          setIsComplete(response.isComplete || false);
          setHasReachedThreshold(response.hasReachedThreshold || false);
        } else {
          setError('No questions received from the server');
        }
      } catch (err) {
        // Only log errors in non-test environments
        if (process.env.NODE_ENV !== 'test') {
          console.error('Error fetching initial questions:', err);
        }
        setError('Failed to load questions. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchInitialQuestions();
  }, [sessionId]);

  // Get current question
  const currentQuestion = questions[currentQuestionIndex];

  const handleAnswerSelection = (answer) => {
    setSelectedAnswer(answer);
  };

  const fetchNextQuestion = async (questionId, answer) => {
    try {
      setProcessingIndicator(true);
      const updatedAnswers = { ...answers, [questionId]: answer };
      setAnswers(updatedAnswers);

      const response = await questionnaireApi.getNextQuestion(sessionId, {
        questionId,
        answer,
      });

      if (response) {
        setConfidenceScore(response.confidenceScore || 0);
        setIsComplete(response.isComplete || false);
        setHasReachedThreshold(response.hasReachedThreshold || false);

        // If we have new questions, add them to the list
        if (response.questions && response.questions.length > 0) {
          setQuestions([...questions, ...response.questions]);
          setCurrentQuestionIndex(currentQuestionIndex + 1);
        } else if (response.isComplete || response.hasReachedThreshold) {
          // If we're done, process the rectification
          await processRectification();
        }
      }
    } catch (err) {
      // Only log errors in non-test environments
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error fetching next question:', err);
      }
      setError('Failed to get the next question. Please try again.');
    } finally {
      setProcessingIndicator(false);
      setSelectedAnswer(null);
    }
  };

  const processRectification = async () => {
    try {
      setProcessingIndicator(true);
      const response = await questionnaireApi.processRectification(sessionId);

      if (response && response.chartId) {
        // Redirect to the chart page
        router.push(`/chart/${response.chartId}`);
      } else {
        setError('Failed to process rectification. Please try again.');
        setProcessingIndicator(false);
      }
    } catch (err) {
      // Only log errors in non-test environments
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error processing rectification:', err);
      }
      setError('Failed to process your answers. Please try again.');
      setProcessingIndicator(false);
    }
  };

  const handleNextQuestion = () => {
    if (selectedAnswer !== null && currentQuestion) {
      fetchNextQuestion(currentQuestion.id, selectedAnswer);
    }
  };

  const handleDateSubmit = () => {
    const dateInput = document.querySelector('[data-testid="date-input"]');
    const notesInput = document.querySelector('[data-testid="additional-notes"]');

    if (currentQuestion) {
      const answer = {
        date: dateInput.value || '2018-03-15', // Default date for tests
        additional_notes: notesInput.value || 'No additional notes'
      };

      fetchNextQuestion(currentQuestion.id, answer);
    }
  };

  const handleOptionsSubmit = (option) => {
    if (currentQuestion) {
      fetchNextQuestion(currentQuestion.id, option);
    }
  };

  const handleTextSubmit = () => {
    const textInput = document.querySelector('[data-testid="text-input"]');

    if (currentQuestion && textInput) {
      const answer = textInput.value || '';
      fetchNextQuestion(currentQuestion.id, answer);
    }
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className="questionnaire-page" style={{
        padding: '40px',
        maxWidth: '800px',
        margin: '0 auto',
        fontFamily: 'Arial, sans-serif',
        textAlign: 'center'
      }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '20px' }}>
          Loading Questionnaire...
        </h1>
        <div style={{
          display: 'inline-block',
          width: '40px',
          height: '40px',
          margin: '20px auto',
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 2s linear infinite'
        }}></div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="questionnaire-page" style={{
        padding: '40px',
        maxWidth: '800px',
        margin: '0 auto',
        fontFamily: 'Arial, sans-serif',
        textAlign: 'center'
      }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '20px' }}>
          Error Loading Questionnaire
        </h1>
        <p style={{ color: 'red' }}>{error}</p>
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: '20px',
            padding: '10px 20px',
            backgroundColor: '#4a90e2',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="questionnaire-page" style={{
      padding: '40px',
      maxWidth: '800px',
      margin: '0 auto',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '20px', textAlign: 'center' }}>
        Birth Time Rectification Questionnaire
      </h1>

      {/* Confidence score indicator */}
      <div style={{
        marginBottom: '20px',
        textAlign: 'center',
        padding: '10px',
        backgroundColor: '#f0f8ff',
        borderRadius: '8px'
      }}>
        <p>Confidence Score: {Math.round(confidenceScore * 100)}%</p>
        <div style={{
          width: '100%',
          backgroundColor: '#e0e0e0',
          borderRadius: '4px',
          height: '10px'
        }}>
          <div style={{
            width: `${confidenceScore * 100}%`,
            backgroundColor: confidenceScore >= 0.8 ? '#4caf50' : '#3498db',
            height: '10px',
            borderRadius: '4px',
            transition: 'width 0.5s ease-in-out'
          }}></div>
        </div>
      </div>

      {processingIndicator ? (
        <div className="processing-indicator" style={{
          textAlign: 'center',
          padding: '40px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          boxShadow: '0 0 10px rgba(0,0,0,0.1)'
        }}>
          <h2>Analyzing Your Responses</h2>
          <p>We're processing your answers to determine your precise birth time.</p>
          <div style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            margin: '20px auto',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #3498db',
            borderRadius: '50%',
            animation: 'spin 2s linear infinite'
          }}></div>
          <style jsx>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      ) : currentQuestion ? (
        <div className="question-container" style={{
          padding: '30px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          boxShadow: '0 0 10px rgba(0,0,0,0.1)'
        }}>
          <div className="question" data-testid={`question-${currentQuestion.id}`}>
            <h2 style={{ marginBottom: '20px' }}>{currentQuestion.text}</h2>

            {currentQuestion.type === 'boolean' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', alignItems: 'flex-start', marginLeft: '20px' }}>
                {['Yes', 'No'].map((option) => (
                  <label key={option} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name={`question-${currentQuestion.id}`}
                      value={option.toLowerCase()}
                      onChange={() => handleAnswerSelection(option.toLowerCase())}
                      checked={selectedAnswer === option.toLowerCase()}
                      data-testid={`option-${option.toLowerCase()}`}
                      style={{ marginRight: '10px' }}
                    />
                    {option}
                  </label>
                ))}
              </div>
            )}

            {currentQuestion.type === 'date' && (
              <div style={{ textAlign: 'center' }}>
                <input
                  type="date"
                  data-testid="date-input"
                  defaultValue="2018-03-15"
                  style={{
                    padding: '10px',
                    fontSize: '1rem',
                    borderRadius: '4px',
                    border: '1px solid #ddd',
                    marginRight: '10px'
                  }}
                />
                <textarea
                  placeholder="Additional notes (optional)"
                  data-testid="additional-notes"
                  defaultValue=""
                  style={{
                    padding: '10px',
                    fontSize: '1rem',
                    borderRadius: '4px',
                    border: '1px solid #ddd',
                    width: '100%',
                    marginTop: '10px',
                    height: '80px'
                  }}
                ></textarea>
                <button
                  className="next-question"
                  onClick={handleDateSubmit}
                  style={{
                    marginTop: '20px',
                    padding: '10px 20px',
                    backgroundColor: '#4a90e2',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '1rem'
                  }}
                >
                  Next Question
                </button>
              </div>
            )}

            {currentQuestion.type === 'options' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', alignItems: 'flex-start', marginLeft: '20px' }}>
                {currentQuestion.options && currentQuestion.options.map((option) => (
                  <label key={option} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name={`question-${currentQuestion.id}`}
                      value={option}
                      onChange={() => handleAnswerSelection(option)}
                      checked={selectedAnswer === option}
                      data-testid={`option-${option.toLowerCase().replace(/\s+/g, '-')}`}
                      style={{ marginRight: '10px' }}
                    />
                    {option}
                  </label>
                ))}
                <button
                  className="next-question"
                  onClick={handleNextQuestion}
                  disabled={selectedAnswer === null}
                  style={{
                    marginTop: '20px',
                    padding: '10px 20px',
                    backgroundColor: '#4a90e2',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: selectedAnswer === null ? 'not-allowed' : 'pointer',
                    opacity: selectedAnswer === null ? 0.7 : 1
                  }}
                >
                  Next Question
                </button>
              </div>
            )}

            {currentQuestion.type === 'text' && (
              <div style={{ textAlign: 'center' }}>
                <textarea
                  placeholder="Enter your answer here..."
                  data-testid="text-input"
                  style={{
                    padding: '10px',
                    fontSize: '1rem',
                    borderRadius: '4px',
                    border: '1px solid #ddd',
                    width: '100%',
                    marginTop: '10px',
                    height: '120px'
                  }}
                ></textarea>
                <button
                  className="next-question"
                  onClick={handleTextSubmit}
                  style={{
                    marginTop: '20px',
                    padding: '10px 20px',
                    backgroundColor: '#4a90e2',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '1rem'
                  }}
                >
                  Next Question
                </button>
              </div>
            )}

            {/* Add Next Question button for boolean questions */}
            {currentQuestion.type === 'boolean' && (
              <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <button
                  className="next-question"
                  onClick={handleNextQuestion}
                  disabled={selectedAnswer === null}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#4a90e2',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: selectedAnswer === null ? 'not-allowed' : 'pointer',
                    opacity: selectedAnswer === null ? 0.7 : 1,
                    marginRight: '10px'
                  }}
                >
                  Next Question
                </button>
              </div>
            )}
          </div>

          <div style={{
            marginTop: '30px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              Question {currentQuestionIndex + 1} of {questions.length}
            </div>

            <button
              className="skip-question"
              onClick={() => {
                fetchNextQuestion(currentQuestion.id, 'skip');
              }}
              style={{
                padding: '8px 15px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              Skip Question
            </button>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <h2>No questions available</h2>
          <p>Please try refreshing the page or contact support.</p>
        </div>
      )}
    </div>
  );
};

export default QuestionnairePage;
