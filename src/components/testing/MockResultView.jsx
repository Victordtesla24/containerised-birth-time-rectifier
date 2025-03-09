import React from 'react';

/**
 * Mock result view for testing purposes
 * Displays a simple success message with the rectified birth time
 */
const MockResultView = ({ originalTime, suggestedTime, confidence }) => {
  return (
    <div className="bg-green-50 p-6 rounded-lg shadow-md border border-green-200 my-4">
      <h3 className="text-xl font-semibold text-green-800 mb-2">Birth Time Analysis Complete</h3>

      <div className="mb-4">
        <p className="text-gray-700">
          <span className="font-medium">Original Time:</span> {originalTime}
        </p>
        <p className="text-gray-700">
          <span className="font-medium">Suggested Time:</span> {suggestedTime}
        </p>
      </div>

      <div className="flex items-center">
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-green-600 h-2.5 rounded-full"
            style={{ width: `${confidence}%` }}
            data-testid="confidence-score"
          >
            {confidence}
          </div>
        </div>
        <span className="ml-2 text-sm text-gray-600">{confidence}%</span>
      </div>

      <div className="mt-6 flex justify-between">
        <button
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          data-testid="continue-to-questionnaire"
        >
          Continue to Questionnaire
        </button>

        <button
          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
          data-testid="export-pdf"
        >
          Export Results
        </button>
      </div>

      <div className="export-success hidden mt-4 p-3 bg-green-100 text-green-800 rounded">
        Results exported successfully!
      </div>

      <div
        className="chart-visualization mt-6 border border-gray-200 rounded p-4"
        data-testid="chart-visualization"
      >
        <svg
          width="300"
          height="300"
          viewBox="0 0 300 300"
          data-testid="chart-svg"
        >
          <circle cx="150" cy="150" r="100" fill="#f3f4f6" stroke="#d1d5db" />
          <circle
            cx="150"
            cy="80"
            r="15"
            fill="#fde68a"
            data-testid="planet-sun"
          />
          <circle
            cx="220"
            cy="150"
            r="10"
            fill="#93c5fd"
            data-testid="planet-moon"
          />
        </svg>
        <div className="entity-details hidden absolute bg-white p-2 shadow-md text-sm">
          Planet info will appear here on hover
        </div>
      </div>

      <div className="chart-comparison mt-6">
        <div className="view-toggle mb-2 text-blue-600 cursor-pointer">
          Toggle View
        </div>
        <div className="table-container hidden border border-gray-200 rounded p-4">
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-left p-2">Planet</th>
                <th className="text-left p-2">Original</th>
                <th className="text-left p-2">Rectified</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-2">Sun</td>
                <td className="p-2">15° Taurus</td>
                <td className="p-2">15° Taurus</td>
              </tr>
              <tr>
                <td className="p-2">Moon</td>
                <td className="p-2">28° Cancer</td>
                <td className="p-2">2° Leo</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="processing-indicator hidden">
        <div className="spinner"></div>
        <p>Processing your data...</p>
      </div>

      <div className="rectified-chart hidden">
        Rectified chart content
      </div>

      <div className="question hidden">
        <h4>Did you experience any significant changes in your career around age 30?</h4>
        <div className="options mt-2">
          <label className="block mb-2">
            <input type="radio" name="q1" value="yes" /> Yes, I changed jobs or got promoted
          </label>
          <label className="block mb-2">
            <input type="radio" name="q1" value="no" /> No, my career was stable
          </label>
        </div>
        <button className="next-question mt-2 px-3 py-1 bg-blue-500 text-white rounded">
          Next
        </button>
      </div>
    </div>
  );
};

export default MockResultView;
