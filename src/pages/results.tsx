import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import { CelestialNavbar } from '@/components/common/CelestialNavbar';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import CelestialChart from '@/components/visualization/CelestialChart';
import { preloadImages } from '@/utils/imageLoader';
import { getAllPlanetImagePaths } from '@/utils/planetImages';
import ConfidenceMeter from '@/components/visualization/ConfidenceMeter';
import PlanetaryPositionsTable from '@/components/tables/PlanetaryPositionsTable';
import { questionnaireApi, chartApi, systemApi } from '@/services/apiService';
import { BirthDetails, RectificationResult, PlanetPosition } from '@/types';
import {
  getBirthDetails,
  getQuestionnaireData,
  getRectificationResult,
  saveRectificationResult,
  AnalysisResults
} from '@/utils/sessionStorage';

export default function ResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<RectificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if API is available
    const checkApiHealth = async () => {
      try {
        const isAvailable = await systemApi.isApiAvailable();
        setApiAvailable(isAvailable);
        console.log('API availability check:', isAvailable ? 'API is available' : 'API is not available');
      } catch (error) {
        console.error('API health check failed:', error);
        setApiAvailable(false);
      }
    };

    checkApiHealth();
  }, []);

  useEffect(() => {
    // Preload images for better user experience
    const backgroundImage = '/images/backgrounds-1/space-background-1.jpg';
    const planetImages = getAllPlanetImagePaths();

    preloadImages([backgroundImage, ...planetImages])
      .then(() => {
        console.log('Images preloaded successfully');
      })
      .catch(error => {
        console.error('Error preloading images:', error);
      });

    // Retrieve data from session storage using utilities
    const storedResult = getRectificationResult();
    const birthDetails = getBirthDetails();
    const questionnaireData = getQuestionnaireData();

    // If we have a stored result, convert it to RectificationResult format
    if (storedResult && birthDetails) {
      const rectificationResult: RectificationResult = {
        birthDetails,
        originalTime: birthDetails.approximateTime,
        suggestedTime: storedResult.rectifiedBirthTime,
        confidence: storedResult.confidenceScore,
        reliability: storedResult.confidenceScore > 85 ? 'High' : 'Medium',
        taskPredictions: {
          time: storedResult.confidenceScore,
          ascendant: storedResult.confidenceScore,
          houses: storedResult.confidenceScore
        },
        explanation: 'Based on your birth details and life events questionnaire, we have analyzed planetary positions to determine a more accurate birth time.',
        planetaryPositions: storedResult.interpretations.map(interp => ({
          planet: interp.planet,
          sign: '',
          degree: '',
          house: 0,
          explanation: interp.interpretation
        }))
      };
      setResult(rectificationResult);
      setIsLoading(false);
      return;
    }

    // If we have birth details and questionnaire data but no result, try to generate one from the API
    if (birthDetails && questionnaireData && apiAvailable) {
      // Get result from API
      fetchRectificationResult(birthDetails, questionnaireData);
      return;
    }

    // If we only have birth details but no questionnaire data, redirect to questionnaire
    if (birthDetails && !questionnaireData) {
      setError('You need to complete the questionnaire before viewing results.');
      setIsLoading(false);

      // Optional: redirect after delay
      setTimeout(() => router.push('/birth-time-rectifier/questionnaire'), 3000);
      return;
    }

    // If we have nothing, show error
    if (!storedResult && !birthDetails) {
      setError('No rectification result found. Please complete the birth details and questionnaire first.');
      setIsLoading(false);
    }
  }, [router, apiAvailable]);

  // Function to fetch rectification result from API
  const fetchRectificationResult = async (birthDetails: BirthDetails, questionnaireData: any) => {
    setIsLoading(true);
    setError(null);

    try {
      console.log('Fetching rectification result from API');
      const apiResult = await questionnaireApi.processRectification(birthDetails, questionnaireData);

      // Convert API result to AnalysisResults format for storage
      const analysisResult: AnalysisResults = {
        rectifiedBirthTime: apiResult.suggestedTime,
        confidenceScore: apiResult.confidence,
        chartData: apiResult.taskPredictions || {},
        interpretations: apiResult.planetaryPositions.map(pos => ({
          planet: pos.planet,
          interpretation: pos.explanation || ''
        }))
      };

      // Store the analysis result in session storage
      saveRectificationResult(analysisResult);

      // Set the rectification result in state
      setResult(apiResult);
    } catch (error) {
      console.error('Error fetching rectification result:', error);
      setError('Failed to fetch rectification result from the server. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Format birth date for display
  const formatBirthDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (e) {
      console.error('Error formatting date:', e);
      return dateString;
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-blue-300 text-lg font-light celestial-text">Loading your birth time analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="bg-red-900 bg-opacity-50 p-6 rounded-lg max-w-lg">
          <h2 className="text-red-300 text-xl font-semibold mb-4">Error</h2>
          <p className="text-white">{error}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="flex flex-col items-center max-w-md px-6 py-8 text-center">
          <div className="text-yellow-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-white text-2xl mb-4">No Data Available</h2>
          <p className="text-blue-300 mb-6">
            We couldn't find any birth time rectification results. Please complete the birth details form and questionnaire.
          </p>
          <button
            onClick={() => router.push('/birth-time-analysis')}
            className="celestial-button"
          >
            Start Birth Time Analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Birth Time Results | Birth Time Rectifier</title>
        <meta name="description" content="Your birth time rectification results" />
      </Head>

      {/* Canvas-based animated star background */}
      <CelestialBackground />

      {/* Image background with higher z-index than canvas background */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: -5,
        backgroundImage: 'url(/images/backgrounds-1/space-background-1.jpg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        opacity: 0.6,
        mixBlendMode: 'screen'
      }}></div>

      {/* Navbar */}
      <CelestialNavbar />

      <main className="min-h-screen py-12 pt-28">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-12 text-center"
          >
            <h1 className="text-4xl font-bold text-white mb-4 high-contrast-text">
              Birth Time Rectification Results
            </h1>
            <p className="text-blue-200 max-w-2xl mx-auto">
              Based on your birth details and life events, we've calculated your precise birth time
              with {Math.round(result.confidence)}% confidence.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
            {/* Personal Details Section */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="bg-blue-900/30 backdrop-blur-md rounded-xl p-6 border border-blue-800/30"
            >
              <h2 className="text-2xl font-semibold text-blue-200 mb-6">Your Details</h2>
              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Name</label>
                  <p className="text-white">{result.birthDetails.name}</p>
                </div>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Birth Date</label>
                  <p className="text-white">{formatBirthDate(result.birthDetails.birthDate)}</p>
                </div>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Birth Location</label>
                  <p className="text-white">{result.birthDetails.birthLocation}</p>
                </div>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Timezone</label>
                  <p className="text-white">{result.birthDetails.timezone || 'UTC'}</p>
                </div>

                <div className="pt-2 mt-4 border-t border-blue-800/30">
                  <div className="space-y-1">
                    <label className="text-blue-300 text-sm">Provided Birth Time</label>
                    <p className="text-white">{result.originalTime}</p>
                  </div>

                  <div className="space-y-1 mt-3">
                    <label className="text-blue-300 text-sm">Rectified Birth Time</label>
                    <p className="text-white text-xl font-bold">{result.suggestedTime}</p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Celestial Chart Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="bg-blue-900/30 backdrop-blur-md rounded-xl p-6 border border-blue-800/30 lg:col-span-2"
            >
              <h2 className="text-2xl font-semibold text-blue-200 mb-6">Birth Chart</h2>
              <div className="aspect-square max-w-lg mx-auto">
                <CelestialChart
                  planetPositions={result.planetaryPositions}
                  birthTime={result.suggestedTime}
                  birthDate={result.birthDetails.birthDate}
                />
              </div>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
            {/* Confidence Section */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="bg-blue-900/30 backdrop-blur-md rounded-xl p-6 border border-blue-800/30"
            >
              <h2 className="text-2xl font-semibold text-blue-200 mb-6">Confidence Level</h2>
              <ConfidenceMeter
                value={result.confidence}
                label={`${Math.round(result.confidence)}% Confidence`}
                description={`Reliability: ${result.reliability}`}
              />

              <div className="mt-6 space-y-4">
                <h3 className="text-lg font-medium text-blue-200">Prediction Details</h3>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Time Accuracy</label>
                  <div className="w-full bg-blue-950/50 rounded-full h-2">
                    <div
                      className="bg-blue-400 h-2 rounded-full"
                      style={{ width: `${result.taskPredictions.time}%` }}
                    ></div>
                  </div>
                  <p className="text-white text-sm">{result.taskPredictions.time}% confidence</p>
                </div>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Ascendant Accuracy</label>
                  <div className="w-full bg-blue-950/50 rounded-full h-2">
                    <div
                      className="bg-blue-400 h-2 rounded-full"
                      style={{ width: `${result.taskPredictions.ascendant}%` }}
                    ></div>
                  </div>
                  <p className="text-white text-sm">{result.taskPredictions.ascendant}% confidence</p>
                </div>

                <div className="space-y-1">
                  <label className="text-blue-300 text-sm">Houses Accuracy</label>
                  <div className="w-full bg-blue-950/50 rounded-full h-2">
                    <div
                      className="bg-blue-400 h-2 rounded-full"
                      style={{ width: `${result.taskPredictions.houses}%` }}
                    ></div>
                  </div>
                  <p className="text-white text-sm">{result.taskPredictions.houses}% confidence</p>
                </div>
              </div>
            </motion.div>

            {/* Explanation Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
              className="bg-blue-900/30 backdrop-blur-md rounded-xl p-6 border border-blue-800/30 lg:col-span-2"
            >
              <h2 className="text-2xl font-semibold text-blue-200 mb-6">Analysis Explanation</h2>
              <p className="text-white leading-relaxed mb-6">
                {result.explanation}
              </p>

              <div className="mt-6">
                <h3 className="text-lg font-medium text-blue-200 mb-4">Planetary Positions</h3>
                <PlanetaryPositionsTable positions={result.planetaryPositions} />
              </div>
            </motion.div>
          </div>

          {result.significantEvents && result.significantEvents.past && result.significantEvents.past.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              className="bg-blue-900/30 backdrop-blur-md rounded-xl p-6 border border-blue-800/30 mb-12"
            >
              <h2 className="text-2xl font-semibold text-blue-200 mb-6">Significant Life Events</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-medium text-blue-200 mb-4">Past Influences</h3>
                  <div className="space-y-4">
                    {result.significantEvents.past.map((event, index) => (
                      <div key={index} className="bg-blue-950/40 rounded-lg p-4 border border-blue-900/40">
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="text-blue-100 font-medium">{event.description}</h4>
                          <span className="bg-blue-600/30 text-blue-200 text-xs px-2 py-1 rounded">
                            {Math.round(event.confidence * 100)}%
                          </span>
                        </div>
                        <p className="text-blue-300 text-sm mb-2">
                          {new Date(event.date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {event.impactAreas.map((area, i) => (
                            <span
                              key={i}
                              className="bg-blue-800/30 text-blue-200 text-xs px-2 py-0.5 rounded"
                            >
                              {area}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {result.significantEvents.future && result.significantEvents.future.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-blue-200 mb-4">Future Potentials</h3>
                    <div className="space-y-4">
                      {result.significantEvents.future.map((event, index) => (
                        <div key={index} className="bg-blue-950/40 rounded-lg p-4 border border-blue-900/40">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="text-blue-100 font-medium">{event.description}</h4>
                            <span className="bg-blue-600/30 text-blue-200 text-xs px-2 py-1 rounded">
                              {Math.round(event.confidence * 100)}%
                            </span>
                          </div>
                          <p className="text-blue-300 text-sm mb-2">
                            {new Date(event.date).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric'
                            })}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {event.impactAreas.map((area, i) => (
                              <span
                                key={i}
                                className="bg-blue-800/30 text-blue-200 text-xs px-2 py-0.5 rounded"
                              >
                                {area}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.7 }}
            className="text-center"
          >
            <button
              onClick={() => router.push('/birth-time-analysis')}
              className="celestial-button text-lg"
            >
              Start New Analysis
            </button>
          </motion.div>
        </div>
      </main>
    </>
  );
}
