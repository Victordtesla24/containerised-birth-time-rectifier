import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LifeEventsQuestionnaireProps,
  QuestionResponse,
  QuestionState,
  QuestionnaireSubmitData
} from './types';
import {
  QuestionnaireResponse,
  DynamicQuestion,
  QuestionAnswer,
  BirthDetails,
  QuestionOption
} from '@/types';

// Add type declaration for process.env if needed
declare const process: {
  env: {
    NEXT_PUBLIC_API_URL?: string;
  };
};

// Confidence threshold for birth time rectification
const CONFIDENCE_THRESHOLD = 90;

// Maximum number of question fetch attempts
const MAX_FETCH_ATTEMPTS = 3;

// Import question components from index
import {
  YesNoQuestion,
  MultipleChoiceQuestion,
  DateQuestion,
  TextQuestion
} from './question-types';

// Import components
import Question from './Question';
import QuestionnaireProgress from './QuestionnaireProgress';
import QuestionnaireComplete from './QuestionnaireComplete';

const LifeEventsQuestionnaire: React.FC<LifeEventsQuestionnaireProps> = ({
  birthDetails,
  onSubmit,
  onProgress,
  isLoading = false,
  initialData
}) => {
  const router = useRouter();
  const [questions, setQuestions] = useState<DynamicQuestion[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, QuestionAnswer>>({});
  const [confidenceScore, setConfidenceScore] = useState<number>(0);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionFetchAttempts, setQuestionFetchAttempts] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [chartData, setChartData] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [questionHistory, setQuestionHistory] = useState<DynamicQuestion[]>([]);
  const [answerHistory, setAnswerHistory] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  // Function to fetch the initial chart data for more accurate question generation
  const fetchInitialChart = async () => {
    if (!birthDetails) return;
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Transform data to expected API format with proper date validation
      const apiPayload = {
        birthDate: formatDateSafely(
          birthDetails?.birthDate,
          birthDetails?.approximateTime
        ),
        birthTime: birthDetails?.approximateTime || '00:00:00',
        latitude: birthDetails?.coordinates?.latitude || 0,
        longitude: birthDetails?.coordinates?.longitude || 0,
        timezone: birthDetails?.timezone || 'UTC',
        chartType: 'all'
      };

      const response = await fetch(`${apiUrl}/api/chart/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiPayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        let errorMessage = `Failed to fetch initial chart data (Status: ${response.status})`;

        if (errorData?.detail) {
          if (Array.isArray(errorData.detail)) {
            // Format validation errors
            errorMessage = `Validation error: ${errorData.detail.map((err: any) => err.msg).join(', ')}`;
          } else {
            errorMessage = `Error: ${errorData.detail}`;
          }
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      setChartData(data);

      // Generate a session ID if not already set
      if (!sessionId) {
        setSessionId(`session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);
      }

      return data;
    } catch (error) {
      console.error('Error fetching initial chart:', error);
      setError(`Failed to initialize questionnaire: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return null;
    }
  };

  // Function to fetch questions from the API
  const fetchQuestions = async (chartData?: any) => {
    if (questionFetchAttempts >= MAX_FETCH_ATTEMPTS) {
      setError(`Failed to fetch questions after ${MAX_FETCH_ATTEMPTS} attempts. Please try again later.`);
      return;
    }

    setIsLoadingQuestions(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Ensure all required fields are present in the birthDetails object
      const enhancedBirthDetails = {
        ...birthDetails,
        // Ensure approximateTime is present and in the correct format (HH:MM:SS)
        approximateTime: birthDetails.approximateTime ||
                        (birthDetails.hasOwnProperty('birthTime') ? (birthDetails as any).birthTime + ((birthDetails as any).birthTime.length === 5 ? ':00' : '') : '00:00:00'),
        // Ensure gender is present and has a valid value
        gender: birthDetails.gender || 'unknown',
        // Ensure birthLocation is present with a fallback value that's descriptive
        birthLocation: birthDetails.birthLocation || (birthDetails as any).location || 'Unknown Location',
        // Additional field mapping for API compatibility
        name: birthDetails.name || 'Anonymous User',
        // Ensure coordinates are properly formatted with fallbacks
        latitude: parseFloat(String(birthDetails?.coordinates?.latitude || (birthDetails as any)?.latitude || '0')),
        longitude: parseFloat(String(birthDetails?.coordinates?.longitude || (birthDetails as any)?.longitude || '0')),
        // Ensure timezone is present
        timezone: birthDetails.timezone || 'UTC',
        // Add birthDate in consistent format
        birthDate: formatDateSafely(birthDetails?.birthDate, birthDetails?.approximateTime)
      };

      console.log('Sending questionnaire request with birthDetails:', JSON.stringify(enhancedBirthDetails, null, 2));

      // Prepare the request payload
      const payload = {
        birthDetails: enhancedBirthDetails,
        currentConfidence: confidenceScore,
        previousAnswers: Object.keys(answers).length > 0 ? answers : [],
        chartData: chartData || null,
        sessionId: sessionId || `session_${Date.now()}`,
        questionHistory: questionHistory.map((q: DynamicQuestion) => q.id),
        answerHistory: answerHistory,
        maxQuestions: 5 // Limit questions per batch
      };

      console.log('Full questionnaire request payload:', JSON.stringify(payload, null, 2));

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

      const response = await fetch(`${apiUrl}/api/questionnaire/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          errorData = { detail: `Failed to parse error response: ${e}` };
        }

        let errorMessage = `Failed to fetch questions (Status: ${response.status})`;

        if (errorData?.detail) {
          if (Array.isArray(errorData.detail)) {
            // Format validation errors in a more structured way
            const validationErrors = errorData.detail.map((err: any) => {
              const location = Array.isArray(err.loc) ? err.loc.join('.') : err.loc;
              return `${location}: ${err.msg}`;
            }).join('\n');

            console.error('API validation errors:', validationErrors);
            errorMessage = `Validation error: ${validationErrors}`;
          } else {
            errorMessage = `Error: ${errorData.detail}`;
          }
        }

        console.error('API request failed:', {
          status: response.status,
          statusText: response.statusText,
          errorData
        });

        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('Questionnaire API response:', JSON.stringify(data, null, 2));

      if (!data.questions || data.questions.length === 0) {
        console.warn('No questions received from the server, using fallback questions');
        throw new Error('No questions received from the server');
      }

      // Update state with the new questions
      setQuestions(data.questions);
      setCurrentQuestionIndex(0);

      // Update session ID if provided
      if (data.sessionId) {
        setSessionId(data.sessionId);
      }

      // Update confidence score if provided
      if (typeof data.confidenceScore === 'number') {
        setConfidenceScore(data.confidenceScore);
        updateProgress(data.confidenceScore);
      }

      return data;
    } catch (error) {
      console.error('Error fetching questions:', error);
      setError(`Failed to fetch questions: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setQuestionFetchAttempts((prev: number) => prev + 1);

      // If we have no questions yet, try to use fallback questions
      if (questions.length === 0) {
        const fallbackQuestions = generateFallbackQuestions();
        if (fallbackQuestions.length > 0) {
          console.log('Using fallback questions due to API error');
          setQuestions(fallbackQuestions);
          setCurrentQuestionIndex(0);
        }
      }

      return null;
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Generate fallback questions if API fails
  const generateFallbackQuestions = (): DynamicQuestion[] => {
    return [
      {
        id: 'fallback_1',
        text: 'Have you experienced any major career changes in the last 5 years?',
        type: 'yes_no',
        weight: 1
      },
      {
        id: 'fallback_2',
        text: 'When did you meet your current partner or have a significant relationship begin?',
        type: 'date',
        weight: 1
      },
      {
        id: 'fallback_3',
        text: 'Have you moved to a new location in the last 10 years?',
        type: 'yes_no',
        weight: 1
      },
      {
        id: 'fallback_4',
        text: 'Have you experienced any significant health issues?',
        type: 'yes_no',
        weight: 1
      },
      {
        id: 'fallback_5',
        text: 'When did you start your current job or career path?',
        type: 'date',
        weight: 1
      }
    ];
  };

  // Update progress and notify parent component
  const updateProgress = useCallback((score: number) => {
    const progressValue = Math.min(Math.round(score), 100);
    setProgress(progressValue);

    if (onProgress) {
      onProgress({
        answeredQuestions: Object.keys(answers).length,
        totalQuestions: questions.length,
        confidence: progressValue
      });
    }
  }, [onProgress]);

  // Handle answer selection
  const handleAnswerSelect = async (answer: string) => {
    if (isLoadingQuestions || isLoading) return;

    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;

    // Update answers state
    const updatedAnswers = {
      ...answers,
      [currentQuestion.id]: {
        questionId: currentQuestion.id,
        question: currentQuestion.text,
        answer
      }
    };
    setAnswers(updatedAnswers);

    // Add to question and answer history
    setQuestionHistory(prev => [...prev, currentQuestion]);
    setAnswerHistory(prev => [...prev, answer]);

    // Process the answer and determine next steps
    await processAnswer(currentQuestion, answer, updatedAnswers);
  };

  // Process the answer and determine next steps
  const processAnswer = async (
    question: DynamicQuestion,
    answer: string,
    updatedAnswers: Record<string, QuestionAnswer>
  ) => {
    try {
      // If this is the last question in the current batch
      if (currentQuestionIndex >= questions.length - 1) {
        // Check if we've reached the confidence threshold
        if (confidenceScore >= CONFIDENCE_THRESHOLD) {
          // We have enough confidence, complete the questionnaire
          setIsComplete(true);
          updateProgress(100);
        } else {
          // We need more questions, fetch the next batch
          setIsLoadingQuestions(true);

          // Prepare the request payload with the updated answers
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const payload = {
            birthDetails,
            currentConfidence: confidenceScore,
            previousAnswers: updatedAnswers,
            chartData,
            sessionId,
            questionHistory: [...questionHistory, question].map(q => q.id),
            answerHistory: [...answerHistory, answer]
          };

          const response = await fetch(`${apiUrl}/api/questionnaire/generate`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(10000)
          });

          if (!response.ok) {
            throw new Error(`Failed to fetch next questions (Status: ${response.status})`);
          }

          const data = await response.json();

          if (!data.questions || data.questions.length === 0) {
            // If no more questions, check if we have enough confidence
            if (data.confidenceScore >= CONFIDENCE_THRESHOLD) {
              setConfidenceScore(data.confidenceScore);
              updateProgress(data.confidenceScore);
              setIsComplete(true);
            } else {
              throw new Error('No more questions available, but confidence threshold not reached');
            }
          } else {
            // Update with new questions
            setQuestions(data.questions);
            setCurrentQuestionIndex(0);

            // Update confidence score
            if (typeof data.confidenceScore === 'number') {
              setConfidenceScore(data.confidenceScore);
              updateProgress(data.confidenceScore);
            }

            // Update session ID if provided
            if (data.sessionId) {
              setSessionId(data.sessionId);
            }
          }
        }
      } else {
        // Move to the next question in the current batch
        setCurrentQuestionIndex(prev => prev + 1);
      }
    } catch (error) {
      console.error('Error processing answer:', error);
      setError(`Failed to process your answer: ${error instanceof Error ? error.message : 'Unknown error'}`);

      // If we have more questions in the current batch, continue with those
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(prev => prev + 1);
      } else {
        // Try to generate fallback questions
        const fallbackQuestions = generateFallbackQuestions().filter(
          q => !questionHistory.some(hq => hq.id === q.id)
        );

        if (fallbackQuestions.length > 0) {
          setQuestions(fallbackQuestions);
          setCurrentQuestionIndex(0);
        } else {
          // If we can't generate more questions, complete with what we have
          setIsComplete(true);
        }
      }
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Handle questionnaire submission
  const handleSubmitQuestionnaire = async () => {
    if (isLoading) return;

    try {
      setIsSubmitting(true);

      // Construct the response object
      const questionnaireResponse: QuestionnaireSubmitData = {
        answers: Object.values(answers).reduce((acc: Record<string, string>, curr) => {
          acc[curr.questionId] = curr.answer;
          return acc;
        }, {}),
        confidence: Math.min(95, Math.max(0, Object.keys(answers).length * 0.05)),
        questionIds: Object.values(answers).map(a => a.questionId)
      };

      await onSubmit?.(questionnaireResponse);
    } catch (error) {
      console.error('Error submitting questionnaire:', error);
      setError(`Failed to submit questionnaire: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Initialize the questionnaire
  useEffect(() => {
    const initializeQuestionnaire = async () => {
      if (!birthDetails) return;

      // If we have initial data, use it
      if (initialData) {
        if (initialData.hasOwnProperty('questions')) {
          setQuestions((initialData as any).questions);
        }
        if (initialData.confidenceScore) {
          setConfidenceScore(initialData.confidenceScore);
          updateProgress(initialData.confidenceScore);
        }
        if (initialData.sessionId) {
          setSessionId(initialData.sessionId);
        }
        if (initialData.answers) {
          // Convert answers object to Record<string, QuestionAnswer>
          const answersMap: Record<string, QuestionAnswer> = {};
          initialData.answers.forEach((answer: QuestionAnswer) => {
            answersMap[answer.questionId] = answer;
          });
          setAnswers(answersMap);
        }
        return;
      }

      // Otherwise, fetch initial chart and questions
      setIsLoadingQuestions(true);

      try {
        const chartData = await fetchInitialChart();
        if (chartData) {
          await fetchQuestions(chartData);
        }
      } catch (error) {
        console.error('Error initializing questionnaire:', error);
        setError(`Failed to initialize questionnaire: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsLoadingQuestions(false);
      }
    };

    initializeQuestionnaire();
  }, [birthDetails, initialData]);

  // Calculate progress
  useEffect(() => {
    if (onProgress && questions.length > 0) {
      const progress = (Object.keys(answers).length / questions.length) * 100;
      onProgress({
        answeredQuestions: Object.keys(answers).length,
        totalQuestions: questions.length,
        confidence: progress
      });
    }
  }, [answers, questions, onProgress]);

  // Navigate to the next question
  const goToNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  // Navigate to the previous question
  const goToPreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response: QuestionnaireSubmitData = {
        answers: Object.values(answers).reduce((acc: Record<string, string>, curr) => {
          acc[curr.questionId] = curr.answer;
          return acc;
        }, {}),
        confidence: Math.min(95, Math.max(0, Object.keys(answers).length * 0.05)),
        questionIds: Object.values(answers).map(a => a.questionId)
      };

      await onSubmit?.(response);
    } catch (err) {
      console.error("Error submitting questionnaire:", err);
      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render the current question
  const renderQuestion = () => {
    if (isLoadingQuestions) {
      return (
        <div className="loading-container flex flex-col items-center justify-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Loading next question...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="error-container bg-red-50 border border-red-200 rounded-md p-4 mb-6">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => {
              setError(null);
              fetchQuestions(chartData);
            }}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      );
    }

    if (isComplete) {
      return (
        <div className="completion-container text-center p-6 bg-green-50 border border-green-200 rounded-md">
          <h3 className="text-xl font-semibold text-green-800 mb-2">Questionnaire Complete!</h3>
          <p className="text-green-700 mb-4">
            Thank you for completing the questionnaire. Your confidence score is {confidenceScore}%.
          </p>
          <button
            onClick={handleSubmitQuestionnaire}
            disabled={isLoading}
            className={`px-6 py-3 rounded-md text-white font-medium ${
              isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isLoading ? 'Processing...' : 'Submit Results'}
          </button>
        </div>
      );
    }

    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) {
      return (
        <div className="error-container bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-yellow-700">No questions available. Please try again later.</p>
          <button
            onClick={() => fetchQuestions(chartData)}
            className="mt-4 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
          >
            Retry
          </button>
        </div>
      );
    }

    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestion.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="question-container"
        >
          <h3 className="text-xl font-semibold mb-4">{currentQuestion.text}</h3>

          {renderQuestionComponent(currentQuestion, answers[currentQuestion.id]?.answer || '', handleAnswerSelect)}
        </motion.div>
      </AnimatePresence>
    );
  };

  // If there are no questions, show a loading or error state
  if (questions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] w-full">
        {isLoading || isLoadingQuestions ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-4"></div>
            <p className="text-gray-600">Loading questionnaire...</p>
          </div>
        ) : (
          // Show the start button if not yet started
          <div className="w-full max-w-3xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6">
              <h2 className="text-2xl font-bold text-white">Life Events Questionnaire</h2>
              <p className="text-indigo-100">
                Answer questions about life events to help us rectify your birth time
              </p>
            </div>

            <div className="p-6 text-center">
              <p className="text-lg text-gray-700 mb-6">
                This questionnaire will ask about significant events in your life to help improve the accuracy of your birth time rectification.
              </p>

              <button
                data-testid="start-questionnaire"
                onClick={() => {
                  setHasStarted(true);
                  fetchQuestions(chartData);
                }}
                className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 shadow-md transition-all duration-300"
              >
                Start Questionnaire
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Show the start button if not yet started
  if (!hasStarted) {
    return (
      <div className="w-full max-w-3xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6">
          <h2 className="text-2xl font-bold text-white">Life Events Questionnaire</h2>
          <p className="text-indigo-100">
            Answer questions about life events to help us rectify your birth time
          </p>
        </div>

        <div className="p-6 text-center">
          <p className="text-lg text-gray-700 mb-6">
            This questionnaire will ask about significant events in your life to help improve the accuracy of your birth time rectification.
          </p>

          <button
            data-testid="start-questionnaire"
            onClick={() => {
              setHasStarted(true);
              fetchQuestions(chartData);
            }}
            className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 shadow-md transition-all duration-300"
          >
            Start Questionnaire
          </button>
        </div>
      </div>
    );
  }

  // Get the current question
  const currentQuestion = questions[currentQuestionIndex];

  // Check if we have answered the current question
  const isCurrentQuestionAnswered = !!answers[currentQuestion.id];

  // Check if we have answered all questions
  const allQuestionsAnswered = questions.every(q => !!answers[q.id]);

  return (
    <div className="w-full max-w-3xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6">
        <h2 className="text-2xl font-bold text-white">Life Events Questionnaire</h2>
        <p className="text-indigo-100">
          Answer these questions to help us rectify your birth time
        </p>
      </div>

      <div className="p-6">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{Object.keys(answers).length} of {questions.length} questions</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${(Object.keys(answers).length / questions.length) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Question number indicator */}
        <div className="flex items-center mb-6">
          <span className="text-lg font-medium text-gray-700">
            Question {currentQuestionIndex + 1} of {questions.length}
          </span>
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={goToPreviousQuestion}
              disabled={currentQuestionIndex === 0}
              className={`px-3 py-1 rounded ${
                currentQuestionIndex === 0
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={goToNextQuestion}
              disabled={currentQuestionIndex === questions.length - 1 || !isCurrentQuestionAnswered}
              className={`px-3 py-1 rounded ${
                currentQuestionIndex === questions.length - 1 || !isCurrentQuestionAnswered
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'
              }`}
            >
              Next
            </button>
          </div>
        </div>

        {/* Current question */}
        <form onSubmit={handleSubmit}>
          <div className="mb-8">
            {renderQuestion()}
          </div>

          {/* Navigation and submit buttons */}
          <div className="flex justify-between mt-8">
            <div>
              {currentQuestionIndex > 0 && (
                <button
                  type="button"
                  onClick={goToPreviousQuestion}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Previous Question
                </button>
              )}
            </div>
            <div className="flex gap-3">
              {currentQuestionIndex < questions.length - 1 ? (
                <button
                  type="button"
                  onClick={goToNextQuestion}
                  disabled={!isCurrentQuestionAnswered}
                  className={`px-4 py-2 ${
                    isCurrentQuestionAnswered
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  } rounded-md`}
                >
                  Next Question
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!allQuestionsAnswered || isSubmitting}
                  className={`px-4 py-2 ${
                    !allQuestionsAnswered || isSubmitting
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-green-600 text-white hover:bg-green-700'
                  } rounded-md`}
                >
                  {isSubmitting ? (
                    <span className="flex items-center">
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Processing...
                    </span>
                  ) : (
                    'Submit Answers'
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-200 text-red-700 rounded-md">
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

// Helper function to format date safely
const formatDateSafely = (dateStr: string | undefined, timeStr: string | undefined = '00:00:00') => {
  if (!dateStr) return new Date().toISOString().split('T')[0];

  try {
    // Handle different date formats
    let formattedDate = dateStr;

    // If date contains slashes, convert to ISO format
    if (dateStr.includes('/')) {
      const parts = dateStr.split('/');
      if (parts.length === 3) {
        // Assume MM/DD/YYYY format
        formattedDate = `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
      }
    }

    // Ensure time is in proper format
    let formattedTime = timeStr || '00:00:00';
    if (formattedTime.length <= 5) {
      formattedTime = `${formattedTime}:00`;
    }

    return `${formattedDate}T${formattedTime}`;
  } catch (error) {
    console.error('Error formatting date:', error);
    return new Date().toISOString().split('T')[0];
  }
};

// Render the appropriate question component based on type
const renderQuestionComponent = (
  question: DynamicQuestion,
  value: string,
  onChange: (answer: string) => void
) => {
  switch (question.type) {
    case 'yes_no':
      return (
        <YesNoQuestion
          question={question}
          value={value}
          onChange={onChange}
        />
      );
    case 'multiple_choice':
      return (
        <MultipleChoiceQuestion
          question={question}
          value={value}
          onChange={onChange}
        />
      );
    case 'date':
      return (
        <DateQuestion
          question={question}
          value={value}
          onChange={onChange}
        />
      );
    case 'text':
      return (
        <TextQuestion
          question={question}
          value={value}
          onChange={onChange}
        />
      );
    default:
      return <div>Unknown question type: {question.type}</div>;
  }
};

export default LifeEventsQuestionnaire;
