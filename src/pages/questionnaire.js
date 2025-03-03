import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/common/Layout';
import Link from 'next/link';
import { questionnaireApi } from '../services/apiService';
import sessionStorage from '../services/sessionStorage';
import NorthIndianChart from '../components/charts/NorthIndianChart';

// Celestial Background component with parallax effect
const CelestialBackground = ({ scrollPosition }) => {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden bg-indigo-900">
      {/* Stars layer (furthest) */}
      <div 
        className="absolute inset-0 bg-repeat"
        style={{
          backgroundImage: 'url(/images/stars-bg.png)',
          backgroundSize: '400px',
          transform: `translateY(${scrollPosition * 0.1}px)`
        }}
      ></div>
      
      {/* Nebula layer (middle) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-40"
        style={{
          backgroundImage: 'url(/images/nebula-bg.png)',
          backgroundPosition: 'center',
          transform: `translateY(${scrollPosition * 0.2}px)`
        }}
      ></div>
      
      {/* Galaxies layer (closest) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-20"
        style={{
          backgroundImage: 'url(/images/galaxies-bg.png)',
          backgroundPosition: '75% 50%',
          transform: `translateY(${scrollPosition * 0.3}px)`
        }}
      ></div>
      
      {/* Gradient overlay to improve text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-indigo-900 opacity-80"></div>
    </div>
  );
};

// Loading indicator with celestial animation
const LoadingIndicator = ({ message }) => (
  <div className="flex flex-col items-center justify-center p-4 text-white">
    <div className="celestial-spinner w-16 h-16 mb-3 relative">
      <div className="absolute inset-0 rounded-full border-4 border-indigo-200 border-opacity-20"></div>
      <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-indigo-400 animate-spin"></div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-2 h-2 bg-white rounded-full"></div>
      </div>
    </div>
    <div className="text-indigo-200">{message}</div>
  </div>
);

// Confidence Indicator Component
const ConfidenceIndicator = ({ value }) => {
  const percentage = Math.min(100, Math.max(0, value));
  const getColor = () => {
    if (percentage < 40) return 'from-red-500 to-red-600';
    if (percentage < 70) return 'from-yellow-500 to-yellow-600';
    return 'from-green-500 to-green-600';
  };
  
  return (
    <div className="confidence-indicator w-full mb-4">
      <div className="flex justify-between text-white text-sm mb-2">
        <span>Confidence Score</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="h-3 w-full bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full bg-gradient-to-r ${getColor()}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      <div className="mt-1 text-xs text-indigo-200">
        {percentage >= 90 ? (
          'High confidence - Analysis complete!'
        ) : percentage >= 70 ? (
          'Good confidence - Few more questions needed'
        ) : percentage >= 40 ? (
          'Moderate confidence - More details required'
        ) : (
          'Low confidence - Additional information needed'
        )}
      </div>
    </div>
  );
};

export default function Questionnaire() {
  const router = useRouter();
  const [scrollPosition, setScrollPosition] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionHistory, setQuestionHistory] = useState([]);
  const [userResponses, setUserResponses] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [confidence, setConfidence] = useState(30);
  const [chartData, setChartData] = useState(null);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const [loadingState, setLoadingState] = useState('initializing'); // 'initializing', 'submitting', 'idle'
  
  // Handle scroll for parallax effect
  useEffect(() => {
    const handleScroll = () => {
      setScrollPosition(window.pageYOffset);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  // Check for saved questionnaire session
  useEffect(() => {
    const savedSession = sessionStorage.getQuestionnaireSession();
    if (savedSession) {
      setSessionId(savedSession.sessionId);
      setQuestionHistory(savedSession.questionHistory);
      setUserResponses(savedSession.userResponses);
      setConfidence(savedSession.confidence);
    }
  }, []);
  
  // Initialize questionnaire session with birth details from router query
  useEffect(() => {
    if (!router.isReady) return;
    
    const initializeQuestionnaire = async () => {
      try {
        setIsLoading(true);
        setLoadingState('initializing');
        setError(null);
        
        // Check for existing session first
        if (sessionId) {
          // If we have a session ID, try to get the next question
          const nextQuestionResponse = await questionnaireApi.getNextQuestion(sessionId, {});
          setCurrentQuestion(nextQuestionResponse.question);
          setConfidence(nextQuestionResponse.confidence || confidence);
          setIsLoading(false);
          setLoadingState('idle');
          return;
        }
        
        // Get birth details from query params or session storage
        let birthDetails = {};
        
        if (router.query.birthDate && router.query.birthTime) {
          birthDetails = {
            birthDate: router.query.birthDate,
            birthTime: router.query.birthTime,
            birthPlace: router.query.birthPlace,
            latitude: router.query.latitude ? parseFloat(router.query.latitude) : null,
            longitude: router.query.longitude ? parseFloat(router.query.longitude) : null,
            timezone: router.query.timezone || null
          };
        } else {
          // Try to get from session storage
          const savedDetails = sessionStorage.getBirthDetails();
          
          if (!savedDetails) {
            // No birth details found, redirect to birth details page
            router.push('/birth-details');
            return;
          }
          
          birthDetails = savedDetails;
        }
        
        // Initialize questionnaire with birth details
        const response = await questionnaireApi.initialize(birthDetails);
        
        // Save session ID and initial question
        if (response && response.sessionId) {
          setSessionId(response.sessionId);
          setCurrentQuestion(response.firstQuestion);
          setConfidence(response.confidence || 30);
          
          // Save to session storage
          sessionStorage.saveQuestionnaireSession({
            sessionId: response.sessionId,
            questionHistory: [],
            userResponses: {},
            confidence: response.confidence || 30
          });
        } else {
          throw new Error('Failed to initialize questionnaire session');
        }
      } catch (error) {
        console.error('Failed to initialize questionnaire:', error);
        setError('Failed to start the questionnaire. Please try again.');
      } finally {
        setIsLoading(false);
        setLoadingState('idle');
      }
    };
    
    initializeQuestionnaire();
  }, [router.isReady, router.query, sessionId]);
  
  // Handle yes/no response
  const handleYesNoResponse = async (answer) => {
    if (isLoading || !sessionId || loadingState === 'submitting') return;
    
    try {
      setIsLoading(true);
      setLoadingState('submitting');
      
      // Add current question and response to history
      const updatedHistory = [...questionHistory, {
        question: currentQuestion,
        response: answer
      }];
      
      // Update responses
      const updatedResponses = {
        ...userResponses,
        [currentQuestion.id]: answer
      };
      
      setQuestionHistory(updatedHistory);
      setUserResponses(updatedResponses);
      
      // Send response to API and get next question
      const response = await questionnaireApi.getNextQuestion(sessionId, {
        [currentQuestion.id]: answer
      });
      
      // Update state with new question and confidence
      setCurrentQuestion(response.question);
      setConfidence(response.confidence || confidence);
      
      // Check if analysis is complete
      if (response.analysisComplete || response.confidence >= 90) {
        setAnalysisComplete(true);
        
        // If chart data is provided, save it
        if (response.chartData) {
          setChartData(response.chartData);
        }
        
        // Save to session storage
        sessionStorage.saveQuestionnaireSession({
          sessionId,
          questionHistory: updatedHistory,
          userResponses: updatedResponses,
          confidence: response.confidence || confidence
        });
        
        // Delay redirect to give user time to see completion message
        setTimeout(() => {
          router.push({
            pathname: '/analysis',
            query: { sessionId }
          });
        }, 2000);
      } else {
        // Save session progress
        sessionStorage.saveQuestionnaireSession({
          sessionId,
          questionHistory: updatedHistory,
          userResponses: updatedResponses,
          confidence: response.confidence || confidence
        });
      }
    } catch (error) {
      console.error('Error submitting response:', error);
      setError('Failed to submit your response. Please try again.');
    } finally {
      setIsLoading(false);
      setLoadingState('idle');
    }
  };
  
  // Handle multiple choice response
  const handleMultipleChoiceResponse = async (optionId) => {
    if (isLoading || !sessionId || loadingState === 'submitting') return;
    
    try {
      setIsLoading(true);
      setLoadingState('submitting');
      
      // Add current question and response to history
      const selectedOption = currentQuestion.options.find(option => option.id === optionId);
      const updatedHistory = [...questionHistory, {
        question: currentQuestion,
        response: selectedOption.text
      }];
      
      // Update responses
      const updatedResponses = {
        ...userResponses,
        [currentQuestion.id]: optionId
      };
      
      setQuestionHistory(updatedHistory);
      setUserResponses(updatedResponses);
      
      // Send response to API and get next question
      const response = await questionnaireApi.getNextQuestion(sessionId, {
        [currentQuestion.id]: optionId
      });
      
      // Update state with new question and confidence
      setCurrentQuestion(response.question);
      setConfidence(response.confidence || confidence);
      
      // Check if analysis is complete
      if (response.analysisComplete || response.confidence >= 90) {
        setAnalysisComplete(true);
        
        // If chart data is provided, save it
        if (response.chartData) {
          setChartData(response.chartData);
        }
        
        // Save to session storage
        sessionStorage.saveQuestionnaireSession({
          sessionId,
          questionHistory: updatedHistory,
          userResponses: updatedResponses,
          confidence: response.confidence || confidence
        });
        
        // Delay redirect to give user time to see completion message
        setTimeout(() => {
          router.push({
            pathname: '/analysis',
            query: { sessionId }
          });
        }, 2000);
      } else {
        // Save session progress
        sessionStorage.saveQuestionnaireSession({
          sessionId,
          questionHistory: updatedHistory,
          userResponses: updatedResponses,
          confidence: response.confidence || confidence
        });
      }
    } catch (error) {
      console.error('Error submitting response:', error);
      setError('Failed to submit your response. Please try again.');
    } finally {
      setIsLoading(false);
      setLoadingState('idle');
    }
  };
  
  // Render the current question
  const renderQuestion = () => {
    if (!currentQuestion) return null;
    
    switch (currentQuestion.type) {
      case 'yes_no':
        return (
          <div className="question-card bg-indigo-800 bg-opacity-50 p-6 rounded-xl shadow-lg">
            <h3 className="text-xl text-white mb-4">{currentQuestion.text}</h3>
            {currentQuestion.description && (
              <p className="mb-6 text-indigo-200">{currentQuestion.description}</p>
            )}
            <div className="flex gap-4 justify-center mt-6">
              <button 
                onClick={() => handleYesNoResponse(true)}
                disabled={isLoading}
                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow disabled:opacity-50"
              >
                Yes
              </button>
              <button 
                onClick={() => handleYesNoResponse(false)}
                disabled={isLoading}
                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow disabled:opacity-50"
              >
                No
              </button>
            </div>
          </div>
        );
        
      case 'multiple_choice':
        return (
          <div className="question-card bg-indigo-800 bg-opacity-50 p-6 rounded-xl shadow-lg">
            <h3 className="text-xl text-white mb-4">{currentQuestion.text}</h3>
            {currentQuestion.description && (
              <p className="mb-6 text-indigo-200">{currentQuestion.description}</p>
            )}
            <div className="mt-6 space-y-3">
              {currentQuestion.options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => handleMultipleChoiceResponse(option.id)}
                  disabled={isLoading}
                  className="w-full px-4 py-3 bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg shadow text-left flex items-center disabled:opacity-50"
                >
                  <span className="w-6 h-6 rounded-full border-2 border-indigo-400 flex items-center justify-center mr-3">
                    {option.id}
                  </span>
                  {option.text}
                </button>
              ))}
            </div>
          </div>
        );
        
      default:
        return <div className="text-white">Unsupported question type</div>;
    }
  };
  
  // Render completion message
  const renderCompletionMessage = () => (
    <div className="text-center">
      <div className="text-3xl text-white mb-4">Analysis Complete!</div>
      <div className="text-xl text-indigo-200 mb-8">
        Preparing your detailed birth time rectification results...
      </div>
      <div className="celestial-spinner w-20 h-20 mx-auto mb-6 relative">
        <div className="absolute inset-0 rounded-full border-4 border-indigo-200 border-opacity-20"></div>
        <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-indigo-400 animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 bg-white rounded-full"></div>
        </div>
      </div>
      <div className="text-lg text-indigo-300">
        You will be redirected to your results in a moment...
      </div>
    </div>
  );
  
  // Render error message
  const renderError = () => (
    <div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-6 text-center">
      <div className="text-xl text-red-300 mb-4">
        {error || 'An error occurred during the questionnaire.'}
      </div>
      <div className="flex justify-center gap-4 mt-6">
        <button 
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
        >
          Try Again
        </button>
        <Link href="/birth-details">
          <div className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg">
            Back to Birth Details
          </div>
        </Link>
      </div>
    </div>
  );
  
  // Render loading state
  const renderLoadingState = () => {
    let message = 'Loading...';
    
    if (loadingState === 'initializing') {
      message = 'Preparing your personalized questionnaire...';
    } else if (loadingState === 'submitting') {
      message = 'Processing your response...';
    }
    
    return <LoadingIndicator message={message} />;
  };
  
  return (
    <Layout pageTitle="Questionnaire">
      <CelestialBackground scrollPosition={scrollPosition} />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-6 text-center">Birth Time Rectification Questionnaire</h1>
          
          <div className="mb-6">
            <ConfidenceIndicator value={confidence} />
          </div>
          
          {error ? (
            renderError()
          ) : isLoading ? (
            <div className="flex justify-center my-12">
              {renderLoadingState()}
            </div>
          ) : analysisComplete ? (
            renderCompletionMessage()
          ) : (
            <>
              {renderQuestion()}
              
              <div className="mt-8 flex justify-between">
                <Link 
                  href="/birth-details"
                  className="text-indigo-300 hover:text-white transition"
                >
                  ← Back to Birth Details
                </Link>
                
                <div className="text-indigo-300">
                  Questions: {questionHistory.length + 1} / {confidence < 40 ? '10+' : confidence < 70 ? '5-8' : '1-3 more'}
                </div>
              </div>
              
              {questionHistory.length > 0 && (
                <div className="mt-8 p-4 bg-indigo-900 bg-opacity-30 rounded-lg">
                  <h3 className="text-lg text-white mb-3">Previous Questions</h3>
                  <div className="space-y-2">
                    {questionHistory.slice(-3).reverse().map((item, index) => (
                      <div key={index} className="text-sm">
                        <div className="text-indigo-300">{item.question.text}</div>
                        <div className="text-white">Your answer: {typeof item.response === 'boolean' 
                          ? (item.response ? 'Yes' : 'No') 
                          : item.response}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
} 