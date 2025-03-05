// @ts-ignore - Ignoring module resolution issues
import React from 'react';
import ChartRenderer from '../ChartRenderer';
import { ChartData } from '@/types';
// @ts-ignore - Ignoring module resolution issues
import { motion, AnimatePresence } from 'framer-motion';

interface BirthChartProps {
  data: ChartData;
  width?: number;
  height?: number;
  onPlanetClick?: (planetId: string) => void;
}

const BirthChart: React.FC<BirthChartProps> = ({
  data,
  width = 800,
  height = 800,
  onPlanetClick
}: BirthChartProps) => {
  const [selectedDivisionalChart, setSelectedDivisionalChart] = React.useState<string>('');
  const [showCelestialLayers, setShowCelestialLayers] = React.useState(true);
  const [showLabels, setShowLabels] = React.useState(true);
  const [showControls, setShowControls] = React.useState(true);

  const handlePlanetClick = React.useCallback((planetId: string) => {
    if (onPlanetClick) {
      onPlanetClick(planetId);
    }
  }, [onPlanetClick]);

  const divisionalChartOptions = Object.keys(data.divisionalCharts || {});

  return (
    <div className="relative chart-ready">
      {/* Hidden div with chart data for testing */}
      <div data-testid="chart-data" style={{ display: 'none' }}>
        {JSON.stringify(data)}
      </div>

      {/* Chart Controls */}
      <div className="absolute top-4 right-4 z-10 space-y-2">
        <button
          onClick={() => setShowControls(!showControls)}
          className="w-full px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          {showControls ? 'Hide Controls' : 'Show Controls'}
        </button>

        <AnimatePresence>
          {showControls && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              {/* Divisional Chart Selector */}
              {divisionalChartOptions.length > 0 && (
                <select
                  value={selectedDivisionalChart}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedDivisionalChart(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="">Main Chart (D1)</option>
                  {divisionalChartOptions.map((chart) => (
                    <option key={chart} value={chart}>
                      {chart}
                    </option>
                  ))}
                </select>
              )}

              {/* Toggle Switches */}
              <div className="space-y-2">
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Show Celestial Background</span>
                  <input
                    type="checkbox"
                    checked={showCelestialLayers}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setShowCelestialLayers(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                </label>

                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Show Labels</span>
                  <input
                    type="checkbox"
                    checked={showLabels}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setShowLabels(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                </label>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Chart Renderer */}
      <div className="relative bg-white rounded-lg shadow-lg overflow-hidden">
        <ChartRenderer
          data={data}
          width={width}
          height={height}
          showLabels={showLabels}
          onPlanetClick={handlePlanetClick}
          selectedDivisionalChart={selectedDivisionalChart}
          showCelestialLayers={showCelestialLayers}
        />
      </div>

      {/* Chart Information */}
      <div className="mt-4 p-4 bg-white rounded-lg shadow-lg">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Chart Information</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">
              <span className="font-medium">Ascendant:</span>{' '}
              {typeof data.ascendant === 'number'
                ? data.ascendant.toFixed(2)
                : data.ascendant.degree.toFixed(2)}°
            </p>
            <p className="text-sm text-gray-600">
              <span className="font-medium">Chart Type:</span>{' '}
              {selectedDivisionalChart || 'Main Chart (D1)'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">
              <span className="font-medium">Total Planets:</span>{' '}
              {data.planets.length}
            </p>
            <p className="text-sm text-gray-600">
              <span className="font-medium">Houses:</span>{' '}
              {data.houses.length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BirthChart;
