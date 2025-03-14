import React, { useState, useEffect, useCallback, useRef } from 'react';
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
    NEXT_PUBLIC_AI_SERVICE_URL?: string;
    NODE_ENV?: string;
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

export const LifeEventsQuestionnaire: React.FC<LifeEventsQuestionnaireProps> = ({
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

  // Refs for initialization tracking
  const hasInitializedRef = useRef(false);
  const initInProgressRef = useRef(false);

  // Refs for progress data comparison
  const progressDataRef = useRef<{ answeredQuestions: number; totalQuestions: number; confidence: number } | null>(null);

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
  const fetchQuestions = async () => {
    try {
      setIsLoadingQuestions(true);
      setError(null);

      // Prepare the request data with the correct types
      const requestData: {
        birthDetails: BirthDetails;
        answers: QuestionAnswer[];
        confidenceScore: number;
      } = {
        birthDetails,
        answers: Object.entries(answers).map(([questionId, answer]) => ({
          questionId,
          question: questionId, // Using ID as question text as a fallback
          answer: answer.toString()
        })),
        confidenceScore
      };

      // Add initialData to the request if it exists and has answers
      if (initialData && initialData.answers) {
        requestData.answers = [
          ...initialData.answers,
          ...Object.entries(answers).map(([questionId, answer]) => ({
            questionId,
            question: questionId, // Using ID as question text as a fallback
            answer: answer.toString()
          }))
        ];
      }

      // Log before API call
      console.log('Sending questionnaire request:', JSON.stringify(requestData, null, 2));

      // Get the AI service URL from environment variables or use default
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
      const response = await fetch(`${apiUrl}/questionnaire`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      // Handle non-200 responses
      if (!response.ok) {
        let errorMessage = `API responded with status ${response.status}`;
        let errorData: any = {};

        try {
          errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch (e) {
          // If we can't parse the error as JSON, just use the status
        }

        // Set the error and mark as complete if it's a submission error
        const isSubmissionError =
          requestData.answers.length > 0 &&
          (errorMessage.includes('submission') || response.status === 500);

        setError(`Failed to fetch questions: ${errorMessage}`);

        // For submission errors, mark the questionnaire as complete
        if (isSubmissionError) {
          setIsComplete(true);
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('Questionnaire API response:', JSON.stringify(data, null, 2));

      // Handle case where API returns an array of questions directly
      let questions = [];
      if (Array.isArray(data)) {
        // API returned an array of questions directly
        questions = data;
        console.log('API returned an array of questions');
      } else if (data.questions && Array.isArray(data.questions)) {
        // API returned an object with questions property
        questions = data.questions;
        console.log('API returned an object with questions property');
      } else {
        console.log('API response format not recognized:', data);
        setError('Invalid response format from API. Please try again.');
        throw new Error('No questions received from the server');
      }

      if (!questions || questions.length === 0) {
        const errorMessage = 'No questions received from the server';
        setError(errorMessage);
        throw new Error(errorMessage);
      }

      // Update state with the new questions
      setQuestions(questions);
      setCurrentQuestionIndex(0);

      // Update session ID if provided
      if (data.sessionId) {
        setSessionId(data.sessionId);
      }

      // Update confidence score if provided
      if (typeof data.confidenceScore === 'number') {
        setConfidenceScore(data.confidenceScore);
        updateProgressSafely(data.confidenceScore);
      }

      setIsLoadingQuestions(false);
      return questions;
    } catch (error) {
      console.error('Error fetching questions:', error);

      // Clear loading state
      setIsLoadingQuestions(false);

      // Show actual error to the user - no masking
      if (!error) {
        setError('Failed to fetch questions. Please try again.');
      } else if (error instanceof Error) {
        setError(`Failed to fetch questions: ${error.message}`);
      } else {
        setError(`Failed to fetch questions: ${String(error)}`);
      }

      // Always show the real error and allow completion if there are answers
      if (Object.keys(answers).length > 0) {
        setIsComplete(true);
      }

      // Increment fetch attempts counter
      setQuestionFetchAttempts((prev) => prev + 1);

      return null;
    }
  };

  // Use a single function for initialization that can be called directly
  const initializeQuestionnaire = useCallback(async () => {
    // Avoid multiple initialization attempts
    if (hasInitializedRef.current || initInProgressRef.current || !birthDetails) {
      return;
    }

    // Set initialization in progress
    initInProgressRef.current = true;

    try {
      // Handle initialization with initial data
      if (initialData) {
        // Create a local batch of updates to apply them all at once
        let updatedQuestions: DynamicQuestion[] | undefined = undefined;
        let updatedConfidenceScore: number | undefined = undefined;
        let updatedSessionId: string | undefined = undefined;
        let updatedAnswers: Record<string, QuestionAnswer> | undefined = undefined;

        if (initialData.hasOwnProperty('questions')) {
          updatedQuestions = (initialData as any).questions;
        }

        if (initialData.confidenceScore) {
          updatedConfidenceScore = initialData.confidenceScore;
        }

        if (initialData.sessionId) {
          updatedSessionId = initialData.sessionId;
        }

        if (initialData.answers) {
          // Convert answers object to Record<string, QuestionAnswer>
          const answersMap: Record<string, QuestionAnswer> = {};
          initialData.answers.forEach((answer: QuestionAnswer) => {
            answersMap[answer.questionId] = answer;
          });
          updatedAnswers = answersMap;
        }

        // Apply all updates at once
        if (updatedQuestions) setQuestions(updatedQuestions);
        if (updatedConfidenceScore) {
          setConfidenceScore(updatedConfidenceScore);
          setProgress(updatedConfidenceScore);
        }
        if (updatedSessionId) setSessionId(updatedSessionId);
        if (updatedAnswers) setAnswers(updatedAnswers);

        // Mark initialization as complete
        hasInitializedRef.current = true;
        initInProgressRef.current = false;
        return;
      }

      // Otherwise, fetch initial chart and questions
      setIsLoadingQuestions(true);

      try {
        const chartData = await fetchInitialChart();
        if (chartData) {
          await fetchQuestions();
        }
      } catch (error) {
        console.error('Error initializing questionnaire:', error);
        setError(`Failed to initialize questionnaire: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsLoadingQuestions(false);
        // Mark initialization as complete
        hasInitializedRef.current = true;
        initInProgressRef.current = false;
      }
    } catch (e) {
      console.error("Error during initialization:", e);
      setError(`Initialization error: ${e instanceof Error ? e.message : String(e)}`);
      // Reset initialization flags in case of error
      initInProgressRef.current = false;
    }
  }, [birthDetails, initialData]);

  // Run initialization once when component mounts or when dependencies change
  useEffect(() => {
    if (!hasInitializedRef.current && !initInProgressRef.current && birthDetails) {
      initializeQuestionnaire();
    }
  }, [birthDetails, initializeQuestionnaire]);

  // Separate useEffect for progress updates to avoid circular dependencies
  const updateProgressSafely = useCallback((score: number) => {
    // This function only updates the progress locally without calling onProgress
    // to avoid the circular dependency
    const progressValue = Math.min(Math.round(score), 100);
    setProgress(progressValue);
  }, []);

  // A separate effect that calls onProgress only when relevant state has changed
  // and initialization is complete
  useEffect(() => {
    if (hasInitializedRef.current && onProgress && questions.length > 0) {
      const progressValue = Math.min(
        Math.round((Object.keys(answers).length / questions.length) * 100),
        100
      );

      // Store current progress data to avoid unnecessary updates
      const progressData = {
        answeredQuestions: Object.keys(answers).length,
        totalQuestions: questions.length,
        confidence: progressValue
      };

      // Compare with previous progress data using ref to avoid dependency on state
      const previousProgressJSON = progressDataRef.current ?
        JSON.stringify(progressDataRef.current) : '';
      const currentProgressJSON = JSON.stringify(progressData);

      if (previousProgressJSON !== currentProgressJSON) {
        // Only call onProgress if data has actually changed
        progressDataRef.current = progressData;
        onProgress(progressData);
      }
    }
  }, [answers, questions, onProgress]);

  // Update the process answer function to use updateProgressSafely
  const processAnswer = async (
    question: DynamicQuestion,
    answer: string,
    updatedAnswers: Record<string, QuestionAnswer>
  ) => {
    try {
      // Update the answer history
      const updatedAnswerHistory = [...answerHistory, { questionId: question.id, answer }];
      setAnswerHistory(updatedAnswerHistory as any);

      // Update the question history
      const updatedQuestionHistory = [...questionHistory, question];
      setQuestionHistory(updatedQuestionHistory);

      // Calculate new confidence score
      // For simplicity, we'll increase confidence by a fixed amount per question
      // In a real implementation, this would be more sophisticated
      const questionWeight = question.weight || 1;
      const newConfidenceScore = Math.min(100, confidenceScore + (20 * questionWeight));
      setConfidenceScore(newConfidenceScore);
      updateProgressSafely(newConfidenceScore);

      // Check if we've reached the confidence threshold
      if (newConfidenceScore >= CONFIDENCE_THRESHOLD) {
        setIsComplete(true);
        return;
      }

      // If we have more questions in the current batch, move to the next one
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        return;
      }

      // If we've reached the end of the current questions but haven't reached the threshold,
      // we need to fetch more questions
      try {
        const newQuestions = await fetchQuestions();
        if (newQuestions && newQuestions.length > 0) {
          setCurrentQuestionIndex(0);
        } else {
          // If no more questions are available but we haven't reached the threshold,
          // we'll still allow the user to submit what they have with whatever confidence level they've reached
          setIsComplete(true);
        }
      } catch (error) {
        console.error('Error fetching more questions:', error);
        // If we can't fetch more questions, allow the user to submit with current confidence level
        setIsComplete(true);

      // Set the error message for all API errors without masking
      const errorMessage = error instanceof Error ? error.message : String(error);
      setError(`Couldn't fetch more questions: ${errorMessage}`);
      }
    } catch (error) {
      console.error('Error processing answer:', error);

      // Set error message for all errors without special handling for test errors
      const errorMessage = error instanceof Error ? error.message : String(error);
      setError(`Failed to process your answer: ${errorMessage}`);
      // Still allow the user to complete if they've answered some questions
      if (Object.keys(answers).length > 0) {
        setIsComplete(true);
      }
    }
  };

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
              fetchQuestions();
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
            onClick={() => fetchQuestions()}
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

  // Replace or add the rendering of the loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] w-full">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Processing your answers and rectifying birth time...</p>
        </div>
      </div>
    );
  }

  // If there are no questions, show a loading or error state
  if (questions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] w-full">
        {isLoading || isLoadingQuestions ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-4"></div>
            <p className="text-gray-600">Loading questionnaire...</p>
          </div>
        ) : error ? (
          <div className="error-container bg-red-50 border border-red-200 rounded-md p-4 max-w-3xl w-full">
            <p className="text-red-700" data-testid="error-message">Error fetching questions: {error}</p>
            <button
              onClick={() => {
                setError('');
                fetchQuestions();
              }}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              Retry
            </button>
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
                data-testid="start-questionnaire-button"
                onClick={() => {
                  setHasStarted(true);
                  fetchQuestions();
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
            data-testid="start-questionnaire-button"
            onClick={() => {
              setHasStarted(true);
              fetchQuestions();
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
                  data-testid="submit-questionnaire-button"
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
    case 'boolean':
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
