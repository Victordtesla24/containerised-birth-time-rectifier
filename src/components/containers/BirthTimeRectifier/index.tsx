import React, { useState } from 'react';
import BirthDetailsForm from '@/components/forms/BirthDetailsForm';
import BirthChart from '@/components/charts/BirthChart';
import { ChartData } from '@/types';
import { DockerAIService } from '@/services/docker/DockerAIService';

interface BirthTimeRectifierProps {
  onSubmit?: (data: any) => Promise<void>;
  onBirthTimeCalculated?: (data: any) => void;
  onError?: (error: string) => void;
  isLoading?: boolean;
}

const BirthTimeRectifier: React.FC<BirthTimeRectifierProps> = ({
  onSubmit,
  onBirthTimeCalculated,
  onError,
  isLoading = false
}) => {
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [formValid, setFormValid] = useState(false);
  const [selectedPlanet, setSelectedPlanet] = useState<string | null>(null);

  const handleFormSubmit = async (data: any) => {
    try {
      // Call onSubmit if it exists
      if (onSubmit) {
        await onSubmit(data);
      }

      // Get the AI service and calculate birth time
      const aiService = DockerAIService.getInstance();
      const result = await aiService.calculateBirthTime({
        date: data.date,
        time: data.time,
        place: data.place,
        coordinates: data.coordinates,
        timezone: data.timezone,
        name: data.name
      });

      // Call onBirthTimeCalculated callback with the result
      if (onBirthTimeCalculated) {
        onBirthTimeCalculated(result);
      }

      // Assuming the API returns chart data
      // In a real implementation, this would come from the API response
      const mockChartData: ChartData = {
        ascendant: 0,
        planets: [
          {
            planet: 'Sun',
            sign: 'Aries',
            degree: '0',
            name: 'Sun',
            longitude: 0,
            latitude: 0,
            speed: 1,
            house: 1,
            explanation: 'test explanation',
          },
          {
            planet: 'Moon',
            sign: 'Cancer',
            degree: '0',
            name: 'Moon',
            longitude: 90,
            latitude: 0,
            speed: 13,
            house: 4,
            explanation: 'test explanation for moon',
          },
        ],
        houses: [
          {
            number: 1,
            startDegree: 0,
            endDegree: 30,
            planets: [],
          },
          {
            number: 4,
            startDegree: 90,
            endDegree: 120,
            planets: [],
          },
        ],
        divisionalCharts: {
          D9: {
            ascendant: 45,
            planets: [
              {
                planet: 'Sun',
                sign: 'Taurus',
                degree: '15',
                name: 'Sun',
                longitude: 45,
                latitude: 0,
                speed: 1,
                house: 2,
              },
            ],
            houses: [
              {
                number: 2,
                startDegree: 30,
                endDegree: 60,
                planets: [],
              },
            ],
            divisionalCharts: {},
            aspects: [],
          },
        },
        aspects: [],
      };
      setChartData(mockChartData);

      // Automatically select the first planet
      if (mockChartData.planets.length > 0) {
        setSelectedPlanet(mockChartData.planets[0].name || mockChartData.planets[0].planet);
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      // Call onError callback with the error message
      if (onError) {
        onError(error instanceof Error ? error.message : String(error));
      }
    }
  };

  const handlePlanetClick = (planetId: string) => {
    setSelectedPlanet(planetId);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Form Section */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Birth Time Rectification
          </h2>
          <BirthDetailsForm
            onSubmit={handleFormSubmit}
            onValidation={setFormValid}
            isLoading={isLoading}
          />
        </div>

        {/* Chart Section */}
        {chartData && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Birth Chart
            </h2>
            <BirthChart
              data={chartData}
              onPlanetClick={handlePlanetClick}
            />
            {selectedPlanet && (
              <div className="mt-4 p-4 bg-gray-50 rounded-md">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Selected Planet Information
                </h3>
                <div className="space-y-2">
                  {chartData.planets
                    .filter(planet => (planet.name || planet.planet) === selectedPlanet)
                    .map(planet => (
                      <div key={planet.name || planet.planet}>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Name:</span> {planet.name || planet.planet}
                        </p>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Position:</span>{' '}
                          {planet.longitude !== undefined ? planet.longitude.toFixed(2) : '0.00'}°
                        </p>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">House:</span> {planet.house}
                        </p>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Speed:</span>{' '}
                          {planet.speed !== undefined ? planet.speed.toFixed(4) : '0.0000'}°/day
                        </p>
                        {planet.explanation && (
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Analysis:</span>{' '}
                            {planet.explanation}
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default BirthTimeRectifier;
