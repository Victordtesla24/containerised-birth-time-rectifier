import React, { useRef, useEffect, useState } from 'react';
import * as React from 'react';
import d3 from '../utils/d3Shim';
import PropTypes from 'prop-types';

/**
 * Chart Visualization Component
 *
 * This component renders astrological charts with proper visualization
 * of all elements including Ketu and Ascendant as specified in the
 * implementation plan.
 *
 * @deprecated Use /components/charts/ChartVisualization.tsx instead.
 * This file is kept for backward compatibility but will be removed in future versions.
 * Consolidating with charts/ChartVisualization.tsx for better organization.
 */
function ChartVisualization({ chartData, isRectified = false, originalChart = null }) {
  const svgRef = useRef(null);
  const [activeEntity, setActiveEntity] = useState(null);
  const [viewMode, setViewMode] = useState('circle'); // 'circle' or 'table'
  const [comparisonMode, setComparisonMode] = useState(!!originalChart);

  // Calculate chart dimensions
  const width = 600;
  const height = 600;
  const centerX = width / 2;
  const centerY = height / 2;
  const chartRadius = Math.min(width, height) / 2 - 40;

  // Add debug info to help with testing
  useEffect(() => {
    if (chartData) {
      console.log('ChartVisualization received data:', {
        hasAscendant: !!chartData.ascendant,
        planetCount: chartData.planets?.length || 0,
        hasKetu: chartData.planets?.some(p => p.name === 'Ketu') || false
      });
    }
  }, [chartData]);

  // Draw chart when data changes
  useEffect(() => {
    if (!chartData || !svgRef.current) {
      console.log('Cannot render chart: missing data or SVG reference');
      return;
    }

    // Clear the SVG
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Add a class to help with test detection
    svg.attr('class', 'chart-svg-rendered');

    if (viewMode === 'circle') {
      if (comparisonMode && originalChart) {
        // Draw comparison view with two charts side by side
        drawComparisonCharts(svg, originalChart, chartData);
      } else {
        // Draw single chart
        drawCircularChart(svg, chartData, isRectified);
      }
    }
    // Table view is rendered in JSX
  }, [chartData, originalChart, viewMode, comparisonMode, isRectified]);

  // Draw circular chart using D3
  const drawCircularChart = (svg, data, isRectified = false) => {
    // Set class for the entire chart container for testing
    svg.attr('class', isRectified ? 'rectified-chart' : 'original-chart')
       .attr('data-testid', isRectified ? 'rectified-chart' : 'original-chart');

    // Draw chart background
    svg.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', chartRadius)
      .attr('fill', '#f8f8ff')
      .attr('stroke', '#333')
      .attr('stroke-width', 1);

    // Draw houses
    const houses = data.houses || [];
    houses.forEach((house, i) => {
      // Calculate angles for house cusps
      const startAngle = (house.cusp * Math.PI) / 180;
      const nextHouse = houses[(i + 1) % 12];
      const endAngle = (nextHouse.cusp * Math.PI) / 180;

      // Draw house segment
      const path = d3.arc()
        .innerRadius(0)
        .outerRadius(chartRadius)
        .startAngle(startAngle)
        .endAngle(endAngle);

      svg.append('path')
        .attr('d', path)
        .attr('transform', `translate(${centerX}, ${centerY})`)
        .attr('fill', i % 2 === 0 ? '#f0f0f8' : '#e8e8f0')
        .attr('stroke', '#666')
        .attr('stroke-width', 0.5)
        .attr('data-testid', `house-${house.number}`)
        .on('mouseover', () => setActiveEntity({ type: 'house', data: house }))
        .on('mouseout', () => setActiveEntity(null));

      // Add house number
      const angle = (startAngle + endAngle) / 2;
      const labelRadius = chartRadius * 0.85;
      const x = centerX + labelRadius * Math.cos(angle);
      const y = centerY + labelRadius * Math.sin(angle);

      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '12px')
        .text(house.number);
    });

    // Draw planets
    const planets = data.planets || [];
    planets.forEach(planet => {
      // Calculate planet position
      const angle = (planet.longitude * Math.PI) / 180;
      const distanceFromCenter = chartRadius * 0.6;
      const x = centerX + distanceFromCenter * Math.cos(angle);
      const y = centerY + distanceFromCenter * Math.sin(angle);

      // Draw planet symbol - making it larger and more distinctive
      const isKetu = planet.name === 'Ketu';
      const radius = isKetu ? 12 : 10; // Make Ketu slightly larger

      // Create planet group for better test detection
      const planetGroup = svg.append('g')
        .attr('class', `planet ${planet.name.toLowerCase()}`)
        .attr('data-testid', `planet-${planet.name}`);

      // Draw the circle
      planetGroup.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', radius)
        .attr('fill', getPlanetColor(planet.name))
        .attr('stroke', isKetu ? '#ff0000' : '#333') // Red outline for Ketu
        .attr('stroke-width', isKetu ? 2 : 1)
        .on('mouseover', () => setActiveEntity({ type: 'planet', data: planet }))
        .on('mouseout', () => setActiveEntity(null));

      // Add planet symbol or abbreviation
      planetGroup.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', isKetu ? '12px' : '10px')
        .attr('fill', '#fff')
        .text(getPlanetSymbol(planet.name));
    });

    // Draw ascendant line
    if (data.ascendant) {
      const ascAngle = (data.ascendant.longitude * Math.PI) / 180;
      svg.append('line')
        .attr('x1', centerX)
        .attr('y1', centerY)
        .attr('x2', centerX + chartRadius * Math.cos(ascAngle))
        .attr('y2', centerY + chartRadius * Math.sin(ascAngle))
        .attr('stroke', '#f00')
        .attr('stroke-width', 2)
        .attr('data-testid', 'ascendant');
    }

    // Draw zodiac signs on the outer ring
    const zodiacSigns = [
      'Aries', 'Taurus', 'Gemini', 'Cancer',
      'Leo', 'Virgo', 'Libra', 'Scorpio',
      'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ];

    zodiacSigns.forEach((sign, i) => {
      const angle = (i * 30 * Math.PI) / 180;
      const outerRadius = chartRadius * 1.1;
      const x = centerX + outerRadius * Math.cos(angle + Math.PI / 12);
      const y = centerY + outerRadius * Math.sin(angle + Math.PI / 12);

      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '10px')
        .attr('fill', '#333')
        .text(getZodiacSymbol(sign));
    });

    // Add a label for rectified chart
    if (isRectified) {
      svg.append('text')
        .attr('x', centerX)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#4a4a9c')
        .text('Rectified Chart');
    }
  };

  // Draw comparison view with original and rectified charts
  const drawComparisonCharts = (svg, originalData, rectifiedData) => {
    // Set class for the comparison container
    svg.attr('class', 'chart-comparison')
       .attr('data-testid', 'chart-comparison');

    // Draw original chart on the left side
    const originalG = svg.append('g')
      .attr('transform', `translate(${width / 4}, ${height / 2}) scale(0.45)`);

    originalG.append('text')
      .attr('x', 0)
      .attr('y', -chartRadius - 20)
      .attr('text-anchor', 'middle')
      .attr('font-size', '16px')
      .attr('font-weight', 'bold')
      .text('Original Chart');

    drawCircularChart(originalG, originalData);

    // Draw rectified chart on the right side
    const rectifiedG = svg.append('g')
      .attr('transform', `translate(${3 * width / 4}, ${height / 2}) scale(0.45)`);

    rectifiedG.append('text')
      .attr('x', 0)
      .attr('y', -chartRadius - 20)
      .attr('text-anchor', 'middle')
      .attr('font-size', '16px')
      .attr('font-weight', 'bold')
      .text('Rectified Chart');

    drawCircularChart(rectifiedG, rectifiedData, true);

    // Add connectors/arrows between charts to show change
    if (rectifiedData.birthTime && originalData.birthTime) {
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2 - 50)
        .attr('text-anchor', 'middle')
        .attr('font-size', '14px')
        .text(`Birth Time: ${originalData.birthTime} → ${rectifiedData.birthTime}`);
    }
  };

  // Helper functions
  const getPlanetColor = (planetName) => {
    const colors = {
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

  const getPlanetSymbol = (planetName) => {
    // Return abbreviation or symbol
    const symbols = {
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

  const getZodiacSymbol = (signName) => {
    const symbols = {
      'Aries': '♈',
      'Taurus': '♉',
      'Gemini': '♊',
      'Cancer': '♋',
      'Leo': '♌',
      'Virgo': '♍',
      'Libra': '♎',
      'Scorpio': '♏',
      'Sagittarius': '♐',
      'Capricorn': '♑',
      'Aquarius': '♒',
      'Pisces': '♓'
    };
    return symbols[signName] || signName.charAt(0);
  };

  return (
    <div className="chart-visualization" data-testid="chart-visualization">
      <div className="view-toggle">
        <button
          className={viewMode === 'circle' ? 'active' : ''}
          onClick={() => setViewMode('circle')}
          data-testid="circle-view"
        >
          Circle View
        </button>
        <button
          className={viewMode === 'table' ? 'active' : ''}
          onClick={() => setViewMode('table')}
          data-testid="table-view"
        >
          Table View
        </button>

        {originalChart && (
          <button
            className={comparisonMode ? 'active' : ''}
            onClick={() => setComparisonMode(!comparisonMode)}
            data-testid="comparison-toggle"
          >
            {comparisonMode ? 'Single Chart' : 'Compare Charts'}
          </button>
        )}
      </div>

      {viewMode === 'circle' ? (
        <div className="chart-container" data-testid="chart-container">
          <svg
            ref={svgRef}
            width={width}
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            data-testid="chart-svg"
          />

          {activeEntity && (
            <div className="entity-details" data-testid="entity-details">
              {activeEntity.type === 'planet' && (
                <div>
                  <h3>{activeEntity.data.name}</h3>
                  <p>Sign: {activeEntity.data.sign}</p>
                  <p>Degree: {activeEntity.data.degree.toFixed(2)}°</p>
                  <p>House: {activeEntity.data.house}</p>
                  {activeEntity.data.retrograde && <p>Retrograde</p>}
                </div>
              )}

              {activeEntity.type === 'house' && (
                <div>
                  <h3>House {activeEntity.data.number}</h3>
                  <p>Sign: {activeEntity.data.sign}</p>
                  <p>Cusp: {activeEntity.data.degree.toFixed(2)}°</p>
                  {activeEntity.data.planets && activeEntity.data.planets.length > 0 && (
                    <>
                      <p>Planets:</p>
                      <ul>
                        {activeEntity.data.planets.map(planet => (
                          <li key={planet}>{planet}</li>
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
        <div className="table-container" data-testid="table-container">
          <div className="ascendant-info" data-testid="ascendant-info">
            <h3>Ascendant</h3>
            <p>Sign: {chartData.ascendant.sign}</p>
            <p>Degree: {chartData.ascendant.degree.toFixed(2)}°</p>
          </div>

          <h3>Planets</h3>
          <table className="planets-table" data-testid="planets-table">
            <thead>
              <tr>
                <th>Planet</th>
                <th>Sign</th>
                <th>Degree</th>
                <th>House</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {chartData.planets.map(planet => (
                <tr key={planet.name}>
                  <td>{planet.name}</td>
                  <td>{planet.sign}</td>
                  <td>{planet.degree.toFixed(2)}°</td>
                  <td>{planet.house}</td>
                  <td>{planet.retrograde ? 'Retrograde' : 'Direct'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Houses</h3>
          <table className="houses-table" data-testid="houses-table">
            <thead>
              <tr>
                <th>House</th>
                <th>Sign</th>
                <th>Degree</th>
                <th>Planets</th>
              </tr>
            </thead>
            <tbody>
              {chartData.houses.map(house => (
                <tr key={house.number}>
                  <td>{house.number}</td>
                  <td>{house.sign}</td>
                  <td>{house.degree.toFixed(2)}°</td>
                  <td>{house.planets ? house.planets.join(', ') : 'None'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Define prop types for better TypeScript integration and for components that consume this
ChartVisualization.propTypes = {
  chartData: PropTypes.object.isRequired,
  isRectified: PropTypes.bool,
  originalChart: PropTypes.object
};

export default ChartVisualization;
