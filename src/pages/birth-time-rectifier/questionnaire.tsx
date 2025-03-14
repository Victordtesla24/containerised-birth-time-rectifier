import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import LifeEventsQuestionnaire from '@/components/forms/LifeEventsQuestionnaire';
import { BirthDetails, QuestionnaireResponse } from '@/types';
import { QuestionnaireProgressData, QuestionnaireSubmitData } from '@/components/forms/LifeEventsQuestionnaire/types';

const QuestionnairePage: React.FC = () => {
  const router = useRouter();
  const [birthDetails, setBirthDetails] = useState<BirthDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [chartData, setChartData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Add a ref to track if initialization has happened
  const hasInitializedRef = useRef(false);
  // Add a ref to track progress updates
  const progressRef = useRef<QuestionnaireProgressData | null>(null);

  useEffect(() => {
    // Skip if already initialized
    if (hasInitializedRef.current) return;

    // Get birth details from session storage
    try {
      const storedBirthDetails = sessionStorage.getItem('birthDetails');
      const storedChartData = sessionStorage.getItem('initialChart');

      if (storedBirthDetails) {
        const parsedBirthDetails = JSON.parse(storedBirthDetails);
        setBirthDetails(parsedBirthDetails);
        hasInitializedRef.current = true;
      } else {
        // No mock fallback - redirect to birth details form if no data
        setError('Birth details not found. Please fill out the birth details form first.');
        setTimeout(() => {
          router.push('/birth-time-rectifier/birth-details');
        }, 3000);
      }

      if (storedChartData) {
        setChartData(JSON.parse(storedChartData));
      }
    } catch (error) {
      console.error('Error loading birth details from session storage:', error);
      setError('Error loading birth details. Please try again.');
    }
  }, []); // Remove router from dependencies

  const handleSubmit = async (data: QuestionnaireSubmitData) => {
    setIsLoading(true);

    try {
      // Format the data for the API
      const questionnaireData: QuestionnaireResponse = {
        answers: Object.entries(data.answers).map(([questionId, answer]) => ({
          questionId,
          question: questionId,
          answer
        })),
        confidenceScore: data.confidence,
        chartId: chartData?.chartId
      };

      // Send the completed questionnaire data to generate rectified chart
      const response = await fetch('/api/chart/rectify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          questionnaire: questionnaireData,
          birthDetails
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to rectify chart');
      }

      const rectificationResult = await response.json();

      // Store the rectification result in session
      sessionStorage.setItem('rectificationResult', JSON.stringify(rectificationResult));

      // Navigate to analysis page
      router.push('/birth-time-rectifier/analysis');
    } catch (error) {
      console.error('Error during questionnaire submission:', error);
      setError(`Error: ${error instanceof Error ? error.message : 'Failed to process questionnaire'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProgress = useCallback((progressData: QuestionnaireProgressData) => {
    // Compare with previous progress data to avoid unnecessary state updates
    if (JSON.stringify(progressRef.current) === JSON.stringify(progressData)) {
      return; // Skip if the same as previous progress data
    }

    // Update progress ref
    progressRef.current = progressData;

    console.log('Questionnaire progress:', progressData);
    // Store progress for potential recovery in case of refresh
    try {
      sessionStorage.setItem('questionnaireProgress', JSON.stringify(progressData));
    } catch (error) {
      console.error('Error saving questionnaire progress:', error);
    }
  }, []); // Empty dependency array means this function reference will remain stable

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
        <div className="mt-4">
          <button
            onClick={() => router.push('/birth-time-rectifier/birth-details')}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Go to Birth Details Form
          </button>
        </div>
      </div>
    );
  }

  if (!birthDetails) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Birth Time Rectification Questionnaire</h1>
      <LifeEventsQuestionnaire
        birthDetails={birthDetails}
        initialData={{
          answers: [],
          confidenceScore: 0
        }}
        onSubmit={handleSubmit}
        onProgress={handleProgress}
        isLoading={isLoading}
      />
    </div>
  );
};

export default QuestionnairePage;
