import React, { useRef, useState, useEffect } from 'react';
import * as d3 from 'd3';
import { ChartData, PlanetPosition } from '@/types';

interface ChartVisualizationProps {
  chartData: ChartData;
  width?: number;
  height?: number;
  onPlanetClick?: (planetId: string) => void;
}

const ChartVisualization: React.FC<ChartVisualizationProps> = ({
  chartData,
  width = 600,
  height = 600,
  onPlanetClick
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [activeEntity, setActiveEntity] = useState<{
    type: 'planet' | 'house';
    data: any;
  } | null>(null);
  const [viewMode, setViewMode] = useState<'circle' | 'table'>('circle');

  // Calculate chart dimensions
  const centerX = width / 2;
  const centerY = height / 2;
  const chartRadius = Math.min(width, height) / 2 - 40;

  // Draw chart when data changes
  useEffect(() => {
    if (!chartData || !svgRef.current) return;

    // Clear the SVG
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (viewMode === 'circle') {
      drawCircularChart(svg, chartData);
    }
  }, [chartData, viewMode, width, height]);

  // Draw circular chart using D3
  const drawCircularChart = (svg: d3.Selection<SVGSVGElement, unknown, null, undefined>, data: ChartData) => {
    // Draw chart background
    svg.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', chartRadius)
      .attr('fill', '#f8f8ff')
      .attr('stroke', '#333')
      .attr('stroke-width', 1);

    // Draw zodiac wheel (12 equal segments)
    for (let i = 0; i < 12; i++) {
      const startAngle = (i * 30 * Math.PI) / 180;
      const endAngle = ((i + 1) * 30 * Math.PI) / 180;

      // Draw zodiac segment
      const arcGenerator = d3.arc<any, any>()
        .innerRadius(chartRadius * 0.8)
        .outerRadius(chartRadius)
        .startAngle(startAngle)
        .endAngle(endAngle);

      const path = arcGenerator({});

      svg.append('path')
        .attr('d', path)
        .attr('transform', `translate(${centerX}, ${centerY})`)
        .attr('fill', i % 2 === 0 ? '#f0f0f8' : '#e8e8f0')
        .attr('stroke', '#666')
        .attr('stroke-width', 0.5);

      // Add zodiac sign
      const angle = (startAngle + endAngle) / 2;
      const labelRadius = chartRadius * 0.9;
      const x = centerX + labelRadius * Math.cos(angle);
      const y = centerY + labelRadius * Math.sin(angle);

      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '12px')
        .text(getZodiacSign(i));
    }

    // Draw houses if available
    const houses = Array.isArray(data.houses) ? data.houses : [];
    houses.forEach((house, i) => {
      // Get house number and sign
      const houseNumber = 'number' in house ? house.number : i + 1;

      // Add house number inside the chart
      const angle = ((i * 30 + 15) * Math.PI) / 180; // Center of each house
      const labelRadius = chartRadius * 0.7;
      const x = centerX + labelRadius * Math.cos(angle);
      const y = centerY + labelRadius * Math.sin(angle);

      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '14px')
        .attr('font-weight', 'bold')
        .text(houseNumber.toString())
        .on('mouseover', () => setActiveEntity({ type: 'house', data: house }))
        .on('mouseout', () => setActiveEntity(null));
    });

    // Draw planets
    const planets = data.planets || [];
    planets.forEach((planet, index) => {
      // Calculate planet position
      const longitude = planet.longitude || 0;
      const angle = ((longitude) * Math.PI) / 180;

      // Distribute planets at different distances to avoid overlap
      const distanceFromCenter = chartRadius * (0.4 + (index % 3) * 0.1);
      const x = centerX + distanceFromCenter * Math.cos(angle);
      const y = centerY + distanceFromCenter * Math.sin(angle);

      // Draw planet symbol
      svg.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 12)
        .attr('fill', getPlanetColor(planet.planet))
        .attr('stroke', '#333')
        .attr('stroke-width', 1)
        .attr('data-testid', `planet-${planet.planet}`)
        .on('mouseover', () => setActiveEntity({ type: 'planet', data: planet }))
        .on('mouseout', () => setActiveEntity(null))
        .on('click', () => {
          if (onPlanetClick) {
            onPlanetClick(planet.planet);
          }
        });

      // Add planet symbol or abbreviation
      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '10px')
        .attr('fill', '#fff')
        .text(getPlanetSymbol(planet.planet));
    });

    // Draw ascendant line
    let ascendantLongitude = 0;

    if (typeof data.ascendant === 'number') {
      ascendantLongitude = data.ascendant;
    } else if (typeof data.ascendant === 'object') {
      // If ascendant is an object, try to get the degree
      if (typeof data.ascendant.degree === 'number') {
        // Calculate approximate longitude based on sign and degree
        const signIndex = getSignIndex(data.ascendant.sign || '');
        ascendantLongitude = (signIndex * 30) + data.ascendant.degree;
      }
    }

    const ascAngle = (ascendantLongitude * Math.PI) / 180;
    svg.append('line')
      .attr('x1', centerX)
      .attr('y1', centerY)
      .attr('x2', centerX + chartRadius * Math.cos(ascAngle))
      .attr('y2', centerY + chartRadius * Math.sin(ascAngle))
      .attr('stroke', '#f00')
      .attr('stroke-width', 2)
      .attr('data-testid', 'ascendant');
  };

  // Helper functions
  const getZodiacSign = (index: number): string => {
    const signs = [
      "Aries", "Taurus", "Gemini", "Cancer",
      "Leo", "Virgo", "Libra", "Scorpio",
      "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ];
    return signs[index % 12];
  };

  const getSignIndex = (signName: string): number => {
    const signs = [
      "Aries", "Taurus", "Gemini", "Cancer",
      "Leo", "Virgo", "Libra", "Scorpio",
      "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ];
    return signs.findIndex(sign => sign === signName) !== -1
      ? signs.findIndex(sign => sign === signName)
      : 0;
  };

  const getPlanetColor = (planetName: string): string => {
    const colors: Record<string, string> = {
      'Sun': '#e6b800',
      'Moon': '#c0c0c0',
      'Mercury': '#9966ff',
      'Venus': '#ff66cc',
      'Mars': '#ff0000',
      'Jupiter': '#ff9900',
      'Saturn': '#663300',
      'Uranus': '#66ccff',
      'Neptune': '#3366ff',
      'Pluto': '#800080',
      'Rahu': '#000033',
      'Ketu': '#330000'
    };
    return colors[planetName] || '#333';
  };

  const getPlanetSymbol = (planetName: string): string => {
    // Return abbreviation or symbol
    const symbols: Record<string, string> = {
      'Sun': '☉',
      'Moon': '☽',
      'Mercury': '☿',
      'Venus': '♀',
      'Mars': '♂',
      'Jupiter': '♃',
      'Saturn': '♄',
      'Uranus': '♅',
      'Neptune': '♆',
      'Pluto': '♇',
      'Rahu': 'R',
      'Ketu': 'K'
    };
    return symbols[planetName] || planetName.charAt(0);
  };

  // Helper function to safely format numbers
  const formatDegree = (degree: number | string | undefined): string => {
    if (typeof degree === 'number') {
      return degree.toFixed(2);
    } else if (typeof degree === 'string') {
      return degree;
    }
    return '0.00';
  };

  return (
    <div className="chart-visualization">
      <div className="view-toggle mb-4 flex space-x-2">
        <button
          className={`px-4 py-2 rounded-md ${viewMode === 'circle'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-200 text-gray-800'}`}
          onClick={() => setViewMode('circle')}
        >
          Circle View
        </button>
        <button
          className={`px-4 py-2 rounded-md ${viewMode === 'table'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-200 text-gray-800'}`}
          onClick={() => setViewMode('table')}
        >
          Table View
        </button>
      </div>

      {viewMode === 'circle' ? (
        <div className="chart-container relative">
          <svg
            ref={svgRef}
            width={width}
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            className="mx-auto"
          />

          {activeEntity && (
            <div className="entity-details absolute top-4 left-4 bg-white p-4 rounded-md shadow-md">
              {activeEntity.type === 'planet' && (
                <div>
                  <h3 className="text-lg font-bold">{activeEntity.data.planet}</h3>
                  <p>Sign: {activeEntity.data.sign}</p>
                  <p>Degree: {formatDegree(activeEntity.data.degree)}°</p>
                  <p>House: {activeEntity.data.house}</p>
                  {activeEntity.data.retrograde && <p className="text-red-500">Retrograde</p>}
                  {activeEntity.data.description && (
                    <p className="mt-2 text-sm">{activeEntity.data.description}</p>
                  )}
                </div>
              )}

              {activeEntity.type === 'house' && (
                <div>
                  <h3 className="text-lg font-bold">House {
                    'number' in activeEntity.data
                      ? activeEntity.data.number
                      : '?'
                  }</h3>
                  <p>Sign: {'sign' in activeEntity.data ? activeEntity.data.sign : '?'}</p>
                  {activeEntity.data.planets && activeEntity.data.planets.length > 0 && (
                    <>
                      <p className="mt-2">Planets:</p>
                      <ul className="list-disc pl-5">
                        {activeEntity.data.planets.map((planet: any, idx: number) => (
                          <li key={idx}>{typeof planet === 'string' ? planet : planet.planet}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="table-container">
          <div className="ascendant-info mb-6 p-4 bg-blue-50 rounded-md">
            <h3 className="text-lg font-bold mb-2">Ascendant</h3>
            {typeof chartData.ascendant === 'number' ? (
              <p>Longitude: {chartData.ascendant.toFixed(2)}°</p>
            ) : (
              <>
                <p>Sign: {chartData.ascendant.sign || '?'}</p>
                <p>Degree: {formatDegree(chartData.ascendant.degree)}°</p>
                {chartData.ascendant.description && (
                  <p className="mt-2 text-sm">{chartData.ascendant.description}</p>
                )}
              </>
            )}
          </div>

          <h3 className="text-lg font-bold mb-2">Planets</h3>
          <div className="overflow-x-auto mb-6">
            <table className="planets-table min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Planet</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sign</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Degree</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">House</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {chartData.planets.map((planet, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">{planet.planet}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{planet.sign}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {formatDegree(planet.degree)}°
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{planet.house}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {planet.retrograde ? (
                        <span className="text-red-500">Retrograde</span>
                      ) : (
                        <span className="text-green-500">Direct</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="text-lg font-bold mb-2">Houses</h3>
          <div className="overflow-x-auto">
            <table className="houses-table min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">House</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sign</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Planets</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Array.isArray(chartData.houses) && chartData.houses.map((house, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {'number' in house ? house.number : idx + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {'sign' in house ? house.sign : '?'}
                    </td>
                    <td className="px-6 py-4">
                      {house.planets && house.planets.length > 0
                        ? house.planets.map((p: any) =>
                            typeof p === 'string' ? p : p.planet
                          ).join(', ')
                        : 'None'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartVisualization;
