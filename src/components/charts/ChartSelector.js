import React, { useState } from 'react';
import NorthIndianChart from './NorthIndianChart';

/**
 * ChartSelector - Component to switch between different chart types (D1, D9, etc.)
 * 
 * @param {Object} props
 * @param {Object} props.chartData - The chart data from API
 * @param {Object} props.d9ChartData - The D9 (Navamsa) chart data
 * @returns {JSX.Element}
 */
const ChartSelector = ({ chartData, d9ChartData }) => {
  const [selectedChart, setSelectedChart] = useState('d1');
  
  // Chart data to display based on selection
  const displayChartData = selectedChart === 'd1' ? chartData : d9ChartData;
  
  return (
    <div className="chart-selector">
      {/* Chart type tabs */}
      <div className="flex mb-4 border-b border-indigo-300 border-opacity-30">
        <button
          className={`py-2 px-4 text-sm font-medium ${
            selectedChart === 'd1' 
              ? 'text-white border-b-2 border-indigo-400' 
              : 'text-indigo-200 hover:text-white'
          }`}
          onClick={() => setSelectedChart('d1')}
        >
          Birth Chart (D1)
        </button>
        <button
          className={`py-2 px-4 text-sm font-medium ${
            selectedChart === 'd9' 
              ? 'text-white border-b-2 border-indigo-400' 
              : 'text-indigo-200 hover:text-white'
          }`}
          onClick={() => setSelectedChart('d9')}
          disabled={!d9ChartData}
        >
          Navamsa Chart (D9)
        </button>
      </div>
      
      {/* Selected chart visualization */}
      <div className="chart-display">
        {displayChartData ? (
          <NorthIndianChart 
            chartData={displayChartData} 
            className="w-full"
          />
        ) : (
          <div className="bg-indigo-800 bg-opacity-50 rounded-lg p-6 text-center border border-indigo-300 border-opacity-30">
            <p className="text-indigo-200">
              {selectedChart === 'd9' 
                ? 'Navamsa chart data not available' 
                : 'Chart data not available'}
            </p>
          </div>
        )}
      </div>
      
      {/* Chart description */}
      <div className="mt-4 p-4 bg-indigo-900 bg-opacity-40 rounded-lg text-sm">
        {selectedChart === 'd1' ? (
          <div>
            <h3 className="font-medium text-white mb-2">Birth Chart (Rashi / D1)</h3>
            <p className="text-indigo-200">
              The birth chart shows planetary positions at the time of birth and forms 
              the foundation of your astrological profile. It reveals your core personality,
              life path, and major life themes.
            </p>
          </div>
        ) : (
          <div>
            <h3 className="font-medium text-white mb-2">Navamsa Chart (D9)</h3>
            <p className="text-indigo-200">
              The Navamsa chart is the 9th divisional chart that reveals deeper aspects of your
              life, especially related to marriage, partnerships, and spiritual growth. It provides
              additional insights into how the energies of your birth chart will manifest.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChartSelector; 