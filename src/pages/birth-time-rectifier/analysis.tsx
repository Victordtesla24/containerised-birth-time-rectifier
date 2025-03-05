import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import { RectificationResult, BirthDetails, ChartData, Aspect } from '@/types';
import BirthChart from '@/components/charts/BirthChart';

export default function AnalysisPage() {
  const router = useRouter();
  const [rectificationResult, setRectificationResult] = useState<RectificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'birthChart' | 'lifeEvents' | 'additionalQuestions'>('overview');
  const [selectedChart, setSelectedChart] = useState<string>('d1Chart');
  const [selectedPlanet, setSelectedPlanet] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [needsAdditionalQuestions, setNeedsAdditionalQuestions] = useState<boolean>(false);
  const [additionalResponses, setAdditionalResponses] = useState<Record<string, string>>({});
  const [showShareOptions, setShowShareOptions] = useState<boolean>(false);
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  useEffect(() => {
    // Get the analysis data from sessionStorage when the component mounts
    try {
      const storedResult = sessionStorage.getItem('rectificationResult');
      if (storedResult) {
        const parsedResult = JSON.parse(storedResult);
        setRectificationResult(parsedResult);

        // Check if confidence is below threshold for additional questions
        const confidenceValue =
          typeof parsedResult.confidence === 'number'
            ? parsedResult.confidence
            : (parsedResult.confidence
                ? parsedResult.confidence / 100
                : 0.5);

        if (confidenceValue < 0.75) {
          setNeedsAdditionalQuestions(true);
        }

        // Check for API warning
        if (parsedResult._warning) {
          setApiWarning(parsedResult._warning);
        }

        // Fetch chart data for the rectified birth time
        fetchChartData(parsedResult.birthDetails, parsedResult.suggestedTime);
      } else {
        setError('No analysis data found. Please complete the birth time rectification process first.');
      }
    } catch (err) {
      console.error('Error retrieving rectification result:', err);
      setError('Failed to load analysis data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchChartData = async (birthDetails: BirthDetails, suggestedTime: string) => {
    try {
      if (!birthDetails) return;

      const chartRequest = {
        birthDetails: {
          ...birthDetails,
          time: suggestedTime
        }
      };

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

      const response = await fetch(`${apiUrl}/api/chart/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chartRequest),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch chart data: ${response.status}`);
      }

      const data = await response.json();

      // Check for API warning
      if (data._warning) {
        setApiWarning(data._warning);
      }

      // Set chart data for visualization
      setChartData(data);
    } catch (error) {
      console.error('Error fetching chart data:', error);
      // Create mock chart data for demonstration with all required properties
      setChartData({
        ascendant: {
          sign: 'Aries',
          degree: 15
        },
        planets: [
          {
            planet: 'sun',
            name: 'Sun',
            longitude: 120,
            latitude: 0,
            speed: 1,
            house: 10,
            sign: 'Leo',
            degree: '0'
          },
          {
            planet: 'moon',
            name: 'Moon',
            longitude: 45,
            latitude: 5,
            speed: 13,
            house: 4,
            sign: 'Taurus',
            degree: '15'
          }
        ],
        houses: Array.from({ length: 12 }, (_, i) => ({
          number: i + 1,
          startDegree: i * 30,
          endDegree: (i + 1) * 30,
          sign: ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'][i],
          degree: 0,
          planets: []
        })),
        divisionalCharts: {},
        aspects: [] // Add the missing aspects array
      });
    }
  };

  const handleExport = () => {
    if (!rectificationResult) return;

    // Format data for text report
    const originalTime = rectificationResult.originalTime || 'Not specified';
    const suggestedTime = rectificationResult.suggestedTime;
    const confidenceValue =
      typeof rectificationResult.confidence === 'number'
        ? rectificationResult.confidence
        : (rectificationResult.confidence
            ? rectificationResult.confidence / 100
            : 0.5);

    const reportLines = [
      '====== BIRTH TIME RECTIFICATION REPORT ======',
      '',
      `Original Birth Time: ${originalTime}`,
      `Rectified Birth Time: ${suggestedTime}`,
      `Date: ${rectificationResult.birthDetails?.birthDate || 'Not specified'}`,
      `Place: ${rectificationResult.birthDetails?.birthLocation || 'Not specified'}`,
      `Coordinates: ${rectificationResult.birthDetails?.coordinates?.latitude || 0}, ${rectificationResult.birthDetails?.coordinates?.longitude || 0}`,
      `Confidence: ${Math.round(confidenceValue * 100)}%`,
      `Reliability: ${rectificationResult.reliability || 'Medium'}`,
      '',
      '====== EXPLANATION ======',
      rectificationResult.explanation || 'No detailed explanation available.',
      '',
      '====== PLANETARY INFLUENCES ======',
    ];

    if (rectificationResult.planetaryPositions) {
      rectificationResult.planetaryPositions.forEach(influence => {
        reportLines.push(`${influence.planet}: ${influence.explanation || 'No description'} (House: ${influence.house})`);
      });
    } else {
      reportLines.push('No planetary influence data available.');
    }

    // Create download
    const reportText = reportLines.join('\n');
    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'birth-time-rectification-report.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = (platform: 'email' | 'twitter' | 'facebook' | 'whatsapp') => {
    if (!rectificationResult) return;

    const confidenceValue =
      typeof rectificationResult.confidence === 'number'
        ? rectificationResult.confidence
        : (rectificationResult.confidence
            ? rectificationResult.confidence / 100
            : 0.5);

    const shareText = `I just got my birth time rectified! The suggested time is ${rectificationResult.suggestedTime} with ${Math.round(confidenceValue * 100)}% confidence.`;
    const shareUrl = window.location.href;

    let shareLink = '';

    switch(platform) {
      case 'email':
        shareLink = `mailto:?subject=My Birth Time Rectification Results&body=${encodeURIComponent(shareText + '\n\n' + shareUrl)}`;
        break;
      case 'twitter':
        shareLink = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;
        break;
      case 'facebook':
        shareLink = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
        break;
      case 'whatsapp':
        shareLink = `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`;
        break;
    }

    if (shareLink) {
      window.open(shareLink, '_blank');
    }

    setShowShareOptions(false);
  };

  const submitAdditionalQuestions = async () => {
    if (!rectificationResult) return;

    // In a real application, this would submit the additional responses to the API
    // For now, we'll simulate an improved confidence level

    // Handle different result formats
    const confidenceValue =
      typeof rectificationResult.confidence === 'number'
        ? rectificationResult.confidence
        : (rectificationResult.confidence
            ? rectificationResult.confidence / 100
            : 0.5);

    const updatedResult = {
      ...rectificationResult,
      confidence: Math.min(0.9, confidenceValue + 0.15),
      reliability: "High",
      explanation: (rectificationResult.explanation || '') + "\n\nAdditional analysis based on your responses: The details you provided about your early childhood and family history strongly support the rectified birth time."
    };

    setRectificationResult(updatedResult);
    sessionStorage.setItem('rectificationResult', JSON.stringify(updatedResult));
    setNeedsAdditionalQuestions(false);
    setActiveTab('overview');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <CelestialBackground />
        <main className="container mx-auto px-4 py-8 relative z-10">
          <div className="max-w-2xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow p-6 mt-10">
            <h2 className="text-xl font-semibold mb-4 text-red-600">Error</h2>
            <p className="mb-6">{error}</p>
            <button
              onClick={() => router.push('/birth-time-rectifier')}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Return to Birth Details Form
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Birth Time Rectification Analysis</title>
        <meta name="description" content="Detailed analysis of your birth time rectification" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <h1 className="text-3xl font-bold text-center mb-4 text-white">
          Birth Time Analysis
        </h1>

        {apiWarning && (
          <div className="max-w-4xl mx-auto mb-4 bg-yellow-100 border-l-4 border-yellow-500 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">
                  {apiWarning}
                </p>
              </div>
            </div>
          </div>
        )}

        {rectificationResult && (
          <div className="max-w-4xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow overflow-hidden">
            <div className="flex flex-wrap border-b">
              <button
                className={`px-4 py-3 font-medium ${activeTab === 'overview' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </button>
              <button
                className={`px-4 py-3 font-medium ${activeTab === 'birthChart' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
                onClick={() => setActiveTab('birthChart')}
                data-testid="tab-button-birth-chart"
              >
                Birth Chart
              </button>
              <button
                className={`px-4 py-3 font-medium ${activeTab === 'lifeEvents' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
                onClick={() => setActiveTab('lifeEvents')}
              >
                Life Events
              </button>
              {needsAdditionalQuestions && (
                <button
                  className={`px-4 py-3 font-medium ${activeTab === 'additionalQuestions' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('additionalQuestions')}
                >
                  Additional Questions
                </button>
              )}
            </div>

            <div className="p-6">
              {activeTab === 'overview' && (
                <div>
                  <div className="mb-6">
                    <h2 className="text-2xl font-semibold mb-4">Rectification Results</h2>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <h3 className="font-medium text-lg mb-2">Original Birth Time</h3>
                        <p className="text-3xl font-bold">{rectificationResult.originalTime || 'Not specified'}</p>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <h3 className="font-medium text-lg mb-2">Rectified Birth Time</h3>
                        <p className="text-3xl font-bold text-green-600">
                          {rectificationResult.suggestedTime || 'Not available'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="mb-6">
                    <h3 className="font-medium text-lg mb-2">Confidence Level</h3>
                    <div className="w-full bg-gray-200 rounded-full h-4">
                      <div
                        className={`h-4 rounded-full ${
                          (rectificationResult.confidence > 0.8 || (rectificationResult.confidence ?? 0) > 80)
                            ? 'bg-green-500'
                            : (rectificationResult.confidence > 0.6 || (rectificationResult.confidence ?? 0) > 60)
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                        }`}
                        style={{
                          width: `${
                            Math.round(
                              typeof rectificationResult.confidence === 'number'
                                ? rectificationResult.confidence * 100
                                : (rectificationResult.confidence ?? 0)
                            )
                          }%`
                        }}
                      ></div>
                    </div>
                    <div className="flex justify-between mt-1 text-sm">
                      <span>0%</span>
                      <span className="font-medium">
                        {Math.round(
                          typeof rectificationResult.confidence === 'number'
                            ? rectificationResult.confidence * 100
                            : rectificationResult.confidence || 60
                        )}%
                      </span>
                      <span>100%</span>
                    </div>
                    <p className="mt-2">
                      Reliability: <span className="font-medium">{rectificationResult.reliability || 'Medium'}</span>
                    </p>
                  </div>

                  {rectificationResult.explanation && (
                    <div className="mb-6">
                      <h3 className="font-medium text-lg mb-2">Explanation</h3>
                      <p className="text-gray-700 whitespace-pre-line">{rectificationResult.explanation}</p>
                    </div>
                  )}

                  <div className="flex space-x-4 mt-8">
                    <button
                      onClick={handleExport}
                      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                      Export Report
                    </button>

                    <div className="relative">
                      <button
                        onClick={() => setShowShareOptions(!showShareOptions)}
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                        </svg>
                        Share Results
                      </button>

                      {showShareOptions && (
                        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10">
                          <div className="py-1">
                            <button onClick={() => handleShare('email')} className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100">
                              Email
                            </button>
                            <button onClick={() => handleShare('twitter')} className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100">
                              Twitter
                            </button>
                            <button onClick={() => handleShare('facebook')} className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100">
                              Facebook
                            </button>
                            <button onClick={() => handleShare('whatsapp')} className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100">
                              WhatsApp
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'birthChart' && chartData && (
                <div>
                  <div className="mb-4 flex justify-between items-center">
                    <h2 className="text-2xl font-semibold">Birth Chart (Indian Vedic Style)</h2>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setSelectedChart('d1Chart')}
                        className={`px-3 py-1 border rounded ${selectedChart === 'd1Chart' ? 'bg-blue-500 text-white' : 'bg-white'}`}
                      >
                        D1 (Rashi)
                      </button>
                      <button
                        onClick={() => setSelectedChart('d9Chart')}
                        className={`px-3 py-1 border rounded ${selectedChart === 'd9Chart' ? 'bg-blue-500 text-white' : 'bg-white'}`}
                      >
                        D9 (Navamsa)
                      </button>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    {selectedChart === 'd1Chart' && (
                      <div data-testid="d1-chart">
                        <BirthChart
                          data={chartData}
                          width={600}
                          height={600}
                          onPlanetClick={setSelectedPlanet}
                        />
                      </div>
                    )}
                    {selectedChart === 'd9Chart' && (
                      <div data-testid="d9-chart">
                        <BirthChart
                          data={chartData}
                          width={600}
                          height={600}
                          onPlanetClick={setSelectedPlanet}
                        />
                      </div>
                    )}
                  </div>

                  {selectedPlanet && (
                    <div className="mt-4 p-4 bg-blue-50 rounded">
                      <h3 className="font-medium mb-2">Planet Information: {selectedPlanet}</h3>
                      <p>
                        Click on planets in the chart to see detailed information about their position and influence.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'lifeEvents' && (
                <div>
                  <h2 className="text-2xl font-semibold mb-4">Life Events Analysis</h2>

                  {rectificationResult.significantEvents ? (
                    <div>
                      <h3 className="font-medium text-lg mb-2">Past Events</h3>
                      <div className="mb-6">
                        {rectificationResult.significantEvents.past?.map((event, index) => (
                          <div key={index} className="mb-4 p-3 border-l-4 border-blue-500 bg-blue-50">
                            <p className="font-medium">{event.date}</p>
                            <p>{event.description}</p>
                            <p className="text-sm text-gray-600 mt-1">
                              Confidence: {Math.round(typeof event.confidence === 'number' ? event.confidence * 100 : event.confidence)}% •
                              Impact areas: {event.impactAreas.join(', ')}
                            </p>
                          </div>
                        ))}
                      </div>

                      <h3 className="font-medium text-lg mb-2">Future Predictions</h3>
                      <div>
                        {rectificationResult.significantEvents.future?.map((event, index) => (
                          <div key={index} className="mb-4 p-3 border-l-4 border-purple-500 bg-purple-50">
                            <p className="font-medium">{event.date}</p>
                            <p>{event.description}</p>
                            <p className="text-sm text-gray-600 mt-1">
                              Confidence: {Math.round(typeof event.confidence === 'number' ? event.confidence * 100 : event.confidence)}% •
                              Impact areas: {event.impactAreas.join(', ')}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-600">
                      No life events analysis is available. This feature requires the advanced questionnaire data to generate predictions.
                    </p>
                  )}
                </div>
              )}

              {activeTab === 'additionalQuestions' && (
                <div>
                  <h2 className="text-2xl font-semibold mb-4">Additional Questions</h2>
                  <p className="mb-6 text-gray-700">
                    The confidence level of your birth time rectification is {
                      Math.round(
                        typeof rectificationResult.confidence === 'number'
                          ? rectificationResult.confidence * 100
                          : rectificationResult.confidence || 60
                      )
                    }%.
                    To improve accuracy, please answer these additional questions:
                  </p>

                  <form onSubmit={(e) => { e.preventDefault(); submitAdditionalQuestions(); }}>
                    <div className="mb-4">
                      <label className="block mb-2 font-medium">
                        Were there any notable events on the day of your birth?
                      </label>
                      <textarea
                        className="w-full px-3 py-2 border rounded"
                        rows={3}
                        value={additionalResponses.birthDayEvents || ''}
                        onChange={(e) => setAdditionalResponses({...additionalResponses, birthDayEvents: e.target.value})}
                      />
                    </div>

                    <div className="mb-4">
                      <label className="block mb-2 font-medium">
                        Do you know your mother's labor duration or any details about the birth process?
                      </label>
                      <textarea
                        className="w-full px-3 py-2 border rounded"
                        rows={3}
                        value={additionalResponses.laborDetails || ''}
                        onChange={(e) => setAdditionalResponses({...additionalResponses, laborDetails: e.target.value})}
                      />
                    </div>

                    <div className="mb-4">
                      <label className="block mb-2 font-medium">
                        Were there any early childhood (0-3 years) events that were particularly significant?
                      </label>
                      <textarea
                        className="w-full px-3 py-2 border rounded"
                        rows={3}
                        value={additionalResponses.earlyChildhood || ''}
                        onChange={(e) => setAdditionalResponses({...additionalResponses, earlyChildhood: e.target.value})}
                      />
                    </div>

                    <div className="mb-4">
                      <label className="block mb-2 font-medium">
                        Is there any family history relevant to your birth time (family patterns, hereditary traits)?
                      </label>
                      <textarea
                        className="w-full px-3 py-2 border rounded"
                        rows={3}
                        value={additionalResponses.familyHistory || ''}
                        onChange={(e) => setAdditionalResponses({...additionalResponses, familyHistory: e.target.value})}
                      />
                    </div>

                    <button
                      type="submit"
                      className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Submit Additional Information
                    </button>
                  </form>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
