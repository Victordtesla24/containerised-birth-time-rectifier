import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import { useSession } from '@/services/session/SessionProvider';

interface QuestionnaireFormProps {
  initialQuestions?: Question[];
  onQuestionnaireComplete: (answers: Answer[], confidenceScore: number) => void;
  saveProgressToLocalStorage?: boolean;
  disableRetry?: boolean;
}

export interface Question {
  id: string;
  type: string;
  questionText: string;
  options?: Option[];
  subText?: string;
  conditionalNextQuestions?: { [key: string]: string };
  meta?: {
    category?: string;
    weight?: number;
    contradictionCheckWith?: string[];
  };
}

export interface Option {
  id: string;
  text: string;
  value: string | number;
}

export interface Answer {
  questionId: string;
  answerId?: string;
  answerValue: string | number | boolean;
  timestamp: number;
  questionType: string;
  questionText: string;
  meta?: any;
}

interface ConfirmationDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({ message, onConfirm, onCancel }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
    <div className="bg-white p-6 rounded-lg shadow-xl max-w-md">
      <h3 className="text-lg font-medium mb-4">Confirm Your Response</h3>
      <p className="mb-4">{message}</p>
      <div className="flex justify-end space-x-3">
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
        >
          Review
        </button>
        <button
          onClick={onConfirm}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
);

const ContradictionDialog: React.FC<{
  prevAnswer: Answer;
  currentAnswer: Answer;
  onResolve: (keepNew: boolean) => void;
}> = ({ prevAnswer, currentAnswer, onResolve }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
    <div className="bg-white p-6 rounded-lg shadow-xl max-w-md">
      <h3 className="text-lg font-medium mb-4">Your answers seem contradictory</h3>
      <p className="mb-4">
        You previously indicated: <strong>&quot;{prevAnswer.questionText}&quot;</strong> with answer <strong>&quot;{prevAnswer.answerValue.toString()}&quot;</strong>
      </p>
      <p className="mb-6">
        But now you've answered: <strong>&quot;{currentAnswer.questionText}&quot;</strong> with answer <strong>&quot;{currentAnswer.answerValue.toString()}&quot;</strong>
      </p>
      <p className="mb-4">Which answer feels more accurate to you?</p>
      <div className="flex justify-between space-x-3">
        <button
          onClick={() => onResolve(false)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
        >
          Keep Previous Answer
        </button>
        <button
          onClick={() => onResolve(true)}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Use New Answer
        </button>
      </div>
    </div>
  </div>
);

const QuestionnaireForm: React.FC<QuestionnaireFormProps> = ({
  initialQuestions = [],
  onQuestionnaireComplete,
  saveProgressToLocalStorage = true,
  disableRetry = false,
}) => {
  const router = useRouter();
  const { sessionId } = useSession();

  // State for questionnaire progress
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [questions] = useState<Question[]>(initialQuestions);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState<string | number | boolean>('');
  const [confidenceScore, setConfidenceScore] = useState(20); // Start with 20%
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showContradiction, setShowContradiction] = useState(false);
  const [contradictoryAnswer, setContradictoryAnswer] = useState<{
    prevAnswer: Answer,
    currentAnswer: Answer
  } | null>(null);

  // Reference to the latest answers for use in callbacks
  const answersRef = useRef(answers);
  const loadingRef = useRef(loading);

  // Local storage key for persisting progress
  const localStorageKey = `questionnaire_${sessionId}`;

  // Update ref when answers change
  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  // Update ref when loading changes
  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  // Load progress from local storage on initial render
  useEffect(() => {
    if (saveProgressToLocalStorage && sessionId) {
      const savedProgress = localStorage.getItem(localStorageKey);
      if (savedProgress) {
        try {
          const progress = JSON.parse(savedProgress);
          if (progress.answers && progress.answers.length > 0) {
            setAnswers(progress.answers);
            setCurrentQuestionIndex(progress.currentQuestionIndex || 0);
            setConfidenceScore(progress.confidenceScore || 20);
          }
        } catch (e) {
          console.error('Error loading saved progress:', e);
        }
      }
    }
  }, [sessionId, saveProgressToLocalStorage, localStorageKey]);

  // Save progress to local storage when answers change
  useEffect(() => {
    if (saveProgressToLocalStorage && sessionId && answers.length > 0) {
      localStorage.setItem(localStorageKey, JSON.stringify({
        answers,
        currentQuestionIndex,
        confidenceScore,
        sessionId,
        timestamp: Date.now()
      }));
    }
  }, [answers, currentQuestionIndex, confidenceScore, sessionId, saveProgressToLocalStorage, localStorageKey]);

  // Function to check for contradictions
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const checkForContradictions = useCallback((newAnswer: Answer): boolean => {
    // Simple contradiction check based on metadata
    const contradictions = answersRef.current.filter(prevAnswer => {
      const prevQuestion = questions.find(q => q.id === prevAnswer.questionId);
      const currentQuestion = questions.find(q => q.id === newAnswer.questionId);

      // Check if there's a defined contradiction relationship
      const hasContradictionCheck = prevQuestion?.meta?.contradictionCheckWith?.includes(currentQuestion?.id || '') ||
                                   currentQuestion?.meta?.contradictionCheckWith?.includes(prevQuestion?.id || '');

      if (!hasContradictionCheck) return false;

      // Simple contradiction logic (can be expanded with more complex rules)
      // For boolean/choice questions: check if answers are opposite
      if ((prevAnswer.questionType === 'boolean' || prevAnswer.questionType === 'choice') &&
          (newAnswer.questionType === 'boolean' || newAnswer.questionType === 'choice')) {
        // Consider answers contradictory if they represent opposite choices
        // This is a simplified example - real implementation would be more nuanced
        if (
          (prevAnswer.answerValue === true && newAnswer.answerValue === false) ||
          (prevAnswer.answerValue === false && newAnswer.answerValue === true) ||
          (prevAnswer.answerValue === 'yes' && newAnswer.answerValue === 'no') ||
          (prevAnswer.answerValue === 'no' && newAnswer.answerValue === 'yes')
        ) {
          return true;
        }
      }

      return false;
    });

    if (contradictions.length > 0) {
      setContradictoryAnswer({
        prevAnswer: contradictions[0], // Focus on the first contradiction found
        currentAnswer: newAnswer
      });
      setShowContradiction(true);
      return true;
    }

    return false;
  }, [questions]);

  // Function to handle contradiction resolution
  const handleContradictionResolution = useCallback((keepNew: boolean) => {
    if (!contradictoryAnswer) return;

    if (keepNew) {
      // Keep the new answer, update the old one
      setAnswers(prev => prev.map(a =>
        a.questionId === contradictoryAnswer.prevAnswer.questionId
          ? { ...a, meta: { ...a.meta, overridden: true } }
          : a
      ));
      handleAnswerSubmit(true);
    } else {
      // Keep the old answer, discard the new one
      setCurrentAnswer(''); // Reset the current answer
    }

    // Clear contradiction state
    setShowContradiction(false);
    setContradictoryAnswer(null);
  }, [contradictoryAnswer]);

  // Function to calculate confidence score based on answers
  const calculateConfidenceScore = useCallback((updatedAnswers: Answer[]): number => {
    if (updatedAnswers.length === 0) return 20; // Base confidence

    // Simple algorithm: each answer contributes to confidence based on weight
    // Starting with 20% base confidence
    let confidence = 20;
    const maxPossibleConfidence = 100;
    const remainingConfidence = maxPossibleConfidence - confidence;

    // Calculate confidence increment per question, weighted by question type/importance
    const totalAnswers = questions.length || 10; // Fallback to 10 if questions length is not available
    const baseIncrement = remainingConfidence / totalAnswers;

    updatedAnswers.forEach(answer => {
      const question = questions.find(q => q.id === answer.questionId);
      // Apply weight multiplier if available in question metadata
      const weight = question?.meta?.weight || 1;
      confidence += baseIncrement * weight;
    });

    // Cap at 99% - requiring final verification for 100%
    return Math.min(99, Math.round(confidence));
  }, [questions]);

  // Fetch the first question or next question
  const fetchNextQuestion = useCallback(async () => {
    if (loadingRef.current) return;

    setLoading(true);
    setError(null);

    try {
      // In a real implementation, this would call API to get next question
      // Mock implementation for now
      if (currentQuestionIndex < questions.length) {
        // Already have the question - just increment index
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      } else {
        // All questions answered
        setLoading(false);
        if (confidenceScore >= 90) {
          onQuestionnaireComplete(answers, confidenceScore);
        } else {
          setError("More questions needed to reach sufficient confidence.");
        }
      }

      // Reset retry count on successful fetch
      setRetryCount(0);
    } catch (error) {
      console.error("Error fetching question:", error);
      setError("Failed to load question. Please try again or refresh.");

      // Implement retry logic
      if (retryCount < 3) {
        setRetryCount(prev => prev + 1);
        console.log(`Retrying to fetch question (attempt ${retryCount + 1}/3)...`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        return fetchNextQuestion();
      }
    } finally {
      setLoading(false);
    }
  }, [currentQuestionIndex, questions.length, confidenceScore, answers, onQuestionnaireComplete, retryCount]);

  // Submit the current answer and move to the next question
  const handleAnswerSubmit = useCallback((skipContradictionCheck = false) => {
    if (loading || !currentAnswer) return;

    try {
      const currentQuestion = questions[currentQuestionIndex];

      // Create answer object
      const answer: Answer = {
        questionId: currentQuestion.id,
        answerId: typeof currentAnswer === 'string' ? currentAnswer : undefined,
        answerValue: currentAnswer,
        timestamp: Date.now(),
        questionType: currentQuestion.type,
        questionText: currentQuestion.questionText
      };

      // Check for contradictions unless we're skipping the check (coming from contradiction resolution)
      if (!skipContradictionCheck && checkForContradictions(answer)) {
        // If contradiction detected, don't proceed until resolved
        return;
      }

      // Update answers
      const updatedAnswers = [...answers, answer];
      setAnswers(updatedAnswers);

      // Update confidence score
      const newConfidenceScore = calculateConfidenceScore(updatedAnswers);
      setConfidenceScore(newConfidenceScore);

      // Reset current answer
      setCurrentAnswer('');

      // Fetch next question
      fetchNextQuestion();
    } catch (error) {
      console.error("Error submitting answer:", error);
      setError("Failed to submit answer. Please try again.");
    }
  }, [loading, currentAnswer, questions, currentQuestionIndex, answers, checkForContradictions, calculateConfidenceScore, fetchNextQuestion]);

  // Handle input change
  const handleInputChange = (value: string | number | boolean) => {
    setCurrentAnswer(value);
  };

  // Handle answer confirmation
  const handleConfirmAnswer = () => {
    setShowConfirmation(false);
    handleAnswerSubmit();
  };

  // Generate the current question component based on question type
  const renderCurrentQuestion = () => {
    if (currentQuestionIndex >= questions.length) {
      return (
        <div className="text-center p-6">
          <p className="mb-4">All questions completed!</p>
          {confidenceScore >= 90 ? (
            <button
              onClick={() => onQuestionnaireComplete(answers, confidenceScore)}
              className="px-6 py-3 bg-green-600 text-white rounded-lg shadow-md hover:bg-green-700"
            >
              Complete Questionnaire
            </button>
          ) : (
            <div>
              <p className="mb-4">We need a bit more information to reach sufficient confidence.</p>
              <p className="text-sm text-gray-500">Current confidence: {confidenceScore}%</p>
            </div>
          )}
        </div>
      );
    }

    const question = questions[currentQuestionIndex];

    // Render based on question type
    switch (question.type) {
      case 'choice':
        return (
          <div className="mb-6">
            <h3 className="text-xl font-medium mb-3">{question.questionText}</h3>
            {question.subText && <p className="text-gray-600 mb-4">{question.subText}</p>}
            <div className="space-y-3">
              {question.options?.map(option => (
                <div key={option.id} className="flex items-center">
                  <input
                    type="radio"
                    id={option.id}
                    name={question.id}
                    value={option.value.toString()}
                    checked={currentAnswer === option.value}
                    onChange={() => handleInputChange(option.value)}
                    className="mr-3"
                  />
                  <label htmlFor={option.id} className="text-gray-800">{option.text}</label>
                </div>
              ))}
            </div>
          </div>
        );

      case 'boolean':
        return (
          <div className="mb-6">
            <h3 className="text-xl font-medium mb-3">{question.questionText}</h3>
            {question.subText && <p className="text-gray-600 mb-4">{question.subText}</p>}
            <div className="flex space-x-4">
              <button
                onClick={() => handleInputChange(true)}
                className={`px-5 py-2 rounded-lg ${
                  currentAnswer === true
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                }`}
              >
                Yes
              </button>
              <button
                onClick={() => handleInputChange(false)}
                className={`px-5 py-2 rounded-lg ${
                  currentAnswer === false
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                }`}
              >
                No
              </button>
            </div>
          </div>
        );

      case 'text':
        return (
          <div className="mb-6">
            <h3 className="text-xl font-medium mb-3">{question.questionText}</h3>
            {question.subText && <p className="text-gray-600 mb-4">{question.subText}</p>}
            <textarea
              value={currentAnswer as string || ''}
              onChange={(e) => handleInputChange(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={4}
              placeholder="Enter your answer..."
            />
          </div>
        );

      default:
        return <div>Unsupported question type: {question.type}</div>;
    }
  };

  // Render the questionnaire progress bar
  const renderProgressBar = () => {
    const totalQuestions = questions.length;
    const answeredQuestions = answers.length;

    // Calculate progress percentage for the bar
    const progressPercent = totalQuestions > 0
      ? (answeredQuestions / totalQuestions) * 100
      : 0;

    return (
      <div className="mb-6">
        <div className="flex justify-between mb-1">
          <span className="text-sm text-gray-600">
            Question {currentQuestionIndex + 1} of {totalQuestions}
          </span>
          <span className="text-sm font-medium text-gray-700">
            Confidence: {confidenceScore}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full"
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Birth Time Rectification Questionnaire</h2>

      {renderProgressBar()}

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {error}
          {!disableRetry && (
            <button
              onClick={() => {
                setError(null);
                fetchNextQuestion();
              }}
              className="ml-auto text-sm underline"
            >
              Try Again
            </button>
          )}
        </div>
      )}

      {renderCurrentQuestion()}

      <div className="flex justify-between mt-6">
        <button
          onClick={() => router.back()}
          className="px-5 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
        >
          Back
        </button>

        <button
          onClick={() => {
            if (typeof currentAnswer !== 'undefined' && currentAnswer !== '') {
              // Show confirmation for significant or high-impact questions
              const question = questions[currentQuestionIndex];
              const isSignificant = question?.meta?.weight && question.meta.weight > 1;

              if (isSignificant) {
                setShowConfirmation(true);
              } else {
                handleAnswerSubmit();
              }
            }
          }}
          disabled={loading || currentAnswer === '' || currentAnswer === undefined}
          className={`px-5 py-2 rounded-lg ${
            loading || currentAnswer === '' || currentAnswer === undefined
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {loading ? 'Loading...' : 'Next'}
        </button>
      </div>

      {/* Question count and confidence indicator */}
      <div className="mt-6 text-sm text-gray-600">
        <div>Questions answered: {answers.length}</div>
        <div>Remaining to 90% confidence: {Math.max(0, Math.ceil((90 - confidenceScore) / 10))} questions (estimate)</div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <ConfirmationDialog
          message={`Please confirm your answer to "${questions[currentQuestionIndex].questionText}"`}
          onConfirm={handleConfirmAnswer}
          onCancel={() => setShowConfirmation(false)}
        />
      )}

      {/* Contradiction Dialog */}
      {showContradiction && contradictoryAnswer && (
        <ContradictionDialog
          prevAnswer={contradictoryAnswer.prevAnswer}
          currentAnswer={contradictoryAnswer.currentAnswer}
          onResolve={handleContradictionResolution}
        />
      )}
    </div>
  );
};

export default QuestionnaireForm;
