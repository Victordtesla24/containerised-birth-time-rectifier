import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { motion } from 'framer-motion';
import { CelestialNavbar } from '@/components/common/CelestialNavbar';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import LifeEventsQuestionnaire from '@/components/forms/LifeEventsQuestionnaire';
import { preloadImages } from '@/utils/imageLoader';
import { getAllPlanetImagePaths } from '@/utils/planetImages';
import { BirthDetails, QuestionnaireResponse } from '@/types';
import { getBirthDetails, saveQuestionnaireData } from '@/utils/sessionStorage';
import { QuestionnaireSubmitData, QuestionnaireProgressData } from '@/components/forms/LifeEventsQuestionnaire/types';

// Confidence threshold for birth time rectification
const CONFIDENCE_THRESHOLD = 80;

export default function QuestionnairePage() {
  const router = useRouter();
  const [birthDetails, setBirthDetails] = useState<BirthDetails | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Preload images for better user experience
    const backgroundImage = '/images/backgrounds-2/space-galaxy-1.jpg';
    const planetImages = getAllPlanetImagePaths();

    preloadImages([backgroundImage, ...planetImages])
      .then(() => {
        console.log('Images preloaded successfully');
      })
      .catch(error => {
        console.error('Error preloading images:', error);
      });

    // Retrieve birth details from session storage using the utility
    const storedDetails = getBirthDetails();

    if (storedDetails === undefined) {
      // Redirect back to birth details form if no data found
      router.push('/birth-time-analysis');
      return;
    }

    setBirthDetails(storedDetails);
    setIsLoading(false);
  }, [router]);

  // Function to handle questionnaire submission
  const handleSubmit = async (data: QuestionnaireSubmitData) => {
    try {
      setIsLoading(true);
      setError(null);

      if (!birthDetails) {
        throw new Error('Birth details not found');
      }

      // Convert QuestionnaireSubmitData to QuestionnaireResponse structure
      const questionnaireResponse: QuestionnaireResponse = {
        birthDetails: birthDetails,
        answers: Object.entries(data.answers).map(([questionId, answer]) => ({
          questionId,
          question: questionId, // We don't have the actual question text here
          answer: String(answer)
        })),
        confidenceScore: data.confidence,
      };

      // Check if confidence threshold is met
      if (!questionnaireResponse.confidenceScore || questionnaireResponse.confidenceScore < CONFIDENCE_THRESHOLD) {
        setError(`Confidence score (${questionnaireResponse.confidenceScore}%) is below the required threshold (${CONFIDENCE_THRESHOLD}%). Please continue answering questions.`);
        setIsLoading(false);
        return;
      }

      console.log('Questionnaire data:', questionnaireResponse);
      console.log('Birth details:', birthDetails);

      // Store the questionnaire data in session storage using the utility
      saveQuestionnaireData(questionnaireResponse);

      // In a real application, we might make an immediate API call here
      // or let the results page handle the API interaction

      // For now, we'll just redirect to the results page
      setTimeout(() => {
        router.push('/results');
      }, 1500);
    } catch (error) {
      console.error('Error submitting questionnaire:', error);
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // Function to handle progress updates
  const handleProgress = (data: QuestionnaireProgressData) => {
    setProgress(data.confidence);
  };

  // Default birth details to prevent null issues
  const defaultBirthDetails: BirthDetails = {
    name: '',
    gender: '',
    birthDate: '',
    approximateTime: '',
    birthLocation: '',
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-blue-300 text-lg font-light celestial-text">Preparing your questionnaire...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="flex flex-col items-center max-w-md px-6 py-8 text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-white text-2xl mb-4">Error</h2>
          <p className="text-blue-300 mb-6">{error}</p>
          <button
            onClick={() => router.push('/birth-time-analysis')}
            className="celestial-button"
          >
            Return to Birth Time Analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Birth Time Questionnaire | Birth Time Rectifier</title>
        <meta name="description" content="Complete this questionnaire to refine your birth time analysis" />
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
        backgroundImage: 'url(/images/backgrounds-2/space-galaxy-1.jpg)',
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
            className="max-w-3xl mx-auto"
          >
            <div className="text-center mb-10">
              <h1 className="text-4xl font-bold text-white mb-4 high-contrast-text">Life Events Questionnaire</h1>
              <p className="text-blue-200 max-w-2xl mx-auto">
                Your responses help us analyze how celestial patterns align with significant events in your life,
                enabling a more precise birth time calculation
              </p>
            </div>

            {/* Questionnaire Component */}
            <LifeEventsQuestionnaire
              birthDetails={birthDetails || defaultBirthDetails}
              onSubmit={handleSubmit}
              onProgress={handleProgress}
            />

            {/* Info Card */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="mt-8 bg-blue-900/20 backdrop-blur-sm rounded-lg p-4 border border-blue-800/20"
            >
              <h3 className="text-sm font-semibold text-blue-300 mb-2">Why we need this information:</h3>
              <ul className="text-sm text-blue-200 space-y-1 list-disc pl-5">
                <li>Significant life events are influenced by planetary transitions</li>
                <li>Your birth time determines the exact alignment of planets at birth</li>
                <li>By mapping life events to planetary positions, we can reverse-calculate your precise birth time</li>
                <li>More detailed information leads to higher confidence in our analysis</li>
              </ul>
            </motion.div>
          </motion.div>
        </div>
      </main>
    </>
  );
}
