// Type declarations to fix TypeScript errors
// @ts-ignore
import React, { useState } from 'react';
// @ts-ignore
import { useRouter } from 'next/router';
// @ts-ignore
import Head from 'next/head';
import BirthDetailsForm from '@/components/forms/BirthDetailsForm';
import { BirthDetails } from '@/types';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';

// Type declaration for process.env
declare const process: {
  env: {
    NODE_ENV: 'development' | 'production' | 'test';
    NEXT_PUBLIC_API_URL?: string;
  }
};

export default function BirthTimeRectifierPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingChart, setIsGeneratingChart] = useState(false);

  const handleSubmit = async (data: BirthDetails) => {
    setIsLoading(true);
    setError(null);

    try {
      // Store birth details in session storage for the next pages
      sessionStorage.setItem('birthDetails', JSON.stringify(data));

      // Generate initial chart
      setIsGeneratingChart(true);

      try {
        // Transform data to expected API format
        const apiPayload = {
          birthDate: new Date(data.birthDate).toISOString(),
          birthTime: data.approximateTime,
          latitude: data.coordinates?.latitude,
          longitude: data.coordinates?.longitude,
          timezone: data.timezone,
          chartType: "ALL"
        };

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/charts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(apiPayload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          if (errorData?.detail) {
            // Format validation errors
            const errorMessage = typeof errorData.detail === 'object'
              ? (errorData.detail.message || JSON.stringify(errorData.detail))
              : errorData.detail;
            throw new Error(errorMessage);
          } else {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
        }

        const chartData = await response.json();
        sessionStorage.setItem('initialChart', JSON.stringify(chartData));
      } catch (chartError) {
        // Only log errors in development or use an error logging service in production
        if (process.env.NODE_ENV !== 'production') {
          console.error('Chart generation error:', chartError);
        }
        // Continue even if chart generation fails
      } finally {
        setIsGeneratingChart(false);
      }

      // Redirect to questionnaire
      router.push('/birth-time-rectifier/questionnaire');
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') {
        console.error('Form submission error:', err);
      }
      const errorMessage = err instanceof Error
        ? err.message
        : 'Failed to process birth details. Please try again.';
      setError(errorMessage);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Birth Time Rectifier - Enter Details</title>
        <meta name="description" content="Enter your birth details for birth time rectification" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <h1 className="text-3xl font-bold text-center mb-8 text-white">
          Birth Time Rectifier
        </h1>

        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded max-w-2xl mx-auto">
            <p className="font-medium">Error:</p>
            <p>{error}</p>
          </div>
        )}

        <div className="max-w-2xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Enter Your Birth Details</h2>
          <p className="mb-6 text-gray-600">
            Please provide accurate birth information for the most precise rectification.
          </p>
          <BirthDetailsForm
            onSubmit={handleSubmit}
            isLoading={isLoading || isGeneratingChart}
            onValidation={() => {}}
          />

          {isGeneratingChart && (
            <div className="mt-6 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-gray-700">Generating initial chart...</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
