import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

const AnalysisPage: React.FC = () => {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [analysisData, setAnalysisData] = useState<any>(null);

  useEffect(() => {
    // In a real implementation, we would fetch this data from the API
    const mockAnalysisData = {
      originalBirthTime: '12:00',
      rectifiedBirthTime: '12:15',
      confidence: 95,
      explanation: 'Based on your life events and personality traits, we have determined that your birth time is likely 12:15 rather than 12:00.',
      chartData: {
        // Chart data would go here
      }
    };

    // Simulate API call
    setTimeout(() => {
      setAnalysisData(mockAnalysisData);
      setIsLoading(false);
    }, 1000);
  }, []);

  const handleExport = () => {
    console.log('Exporting analysis data');
    // In a real implementation, we would export the data to PDF or other format
  };

  const handleShare = () => {
    console.log('Sharing analysis data');
    // In a real implementation, we would generate a shareable link
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
        <p className="ml-4 text-lg">Analyzing birth time data...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Birth Time Rectification Analysis</h1>

      {analysisData && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4">Results</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <p className="text-gray-600">Original Birth Time</p>
              <p className="text-xl font-medium">{analysisData.originalBirthTime}</p>
            </div>
            <div>
              <p className="text-gray-600">Rectified Birth Time</p>
              <p className="text-xl font-medium text-blue-600">{analysisData.rectifiedBirthTime}</p>
            </div>
          </div>

          <div className="mb-6">
            <p className="text-gray-600">Confidence</p>
            <div className="w-full bg-gray-200 rounded-full h-4 mt-2">
              <div
                className="bg-blue-600 h-4 rounded-full"
                style={{ width: `${analysisData.confidence}%` }}
              ></div>
            </div>
            <p className="text-right text-sm mt-1">{analysisData.confidence}%</p>
          </div>

          <div className="mb-6">
            <p className="text-gray-600">Explanation</p>
            <p className="mt-2">{analysisData.explanation}</p>
          </div>

          <div className="flex flex-wrap gap-4">
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Export PDF
            </button>
            <button
              onClick={handleShare}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Share Results
            </button>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Start New Analysis
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
