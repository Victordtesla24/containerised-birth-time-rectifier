import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import './ChartVisualization.css';

const ChartVisualization = ({ chartData }) => {
  const svgRef = useRef(null);
  const [activeEntity, setActiveEntity] = useState(null);
  const [viewMode, setViewMode] = useState('circle');

  // Planet colors for rendering
  const planetColors = {
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

  // Planet symbols
  const planetSymbols = {
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
    'Rahu': '☊',
    'Ketu': '☋'
  };

  // Draw the chart when data changes
  useEffect(() => {
    if (!chartData || !svgRef.current) return;

    drawChart();
  }, [chartData, viewMode]);

  // Main chart drawing function
  const drawChart = () => {
    // Clear the SVG
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (viewMode === 'circle') {
      drawCircularChart(svg);
    } else {
      // Table view is handled in the JSX below
    }
  };

  // Draw circular chart
  const drawCircularChart = (svg) => {
    if (!chartData) return;

    const width = 600;
    const height = 600;
    const centerX = width / 2;
    const centerY = height / 2;
    const chartRadius = Math.min(width, height) / 2 - 40;

    // Set SVG dimensions
    svg.attr('width', width)
       .attr('height', height)
       .attr('viewBox', `0 0 ${width} ${height}`)
       .attr('data-testid', 'chart');

    // Draw chart background
    svg.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', chartRadius)
      .attr('fill', '#f8f8ff')
      .attr('stroke', '#333')
      .attr('stroke-width', 1);

    // Draw zodiac ring
    const outerRadius = chartRadius;
    const innerRadius = chartRadius * 0.85;

    // Draw the 12 zodiac segments
    for (let i = 0; i < 12; i++) {
      const startAngle = (i * 30 * Math.PI) / 180;
      const endAngle = ((i + 1) * 30 * Math.PI) / 180;

      // Create zodiac segment path
      const path = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius)
        .startAngle(startAngle)
        .endAngle(endAngle);

      // Append the path to SVG
      svg.append('path')
        .attr('d', path)
        .attr('transform', `translate(${centerX}, ${centerY})`)
        .attr('fill', i % 2 === 0 ? '#f0f0f8' : '#e8e8f0')
        .attr('stroke', '#666')
        .attr('stroke-width', 0.5);

      // Add zodiac sign
      const angle = (startAngle + endAngle) / 2;
      const labelRadius = (innerRadius + outerRadius) / 2;
      const x = centerX + labelRadius * Math.cos(angle);
      const y = centerY + labelRadius * Math.sin(angle);

      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '12px')
        .attr('fill', '#333')
        .text(getZodiacSign(i));
    }

    // Draw houses if available
    if (chartData.houses && chartData.houses.length > 0) {
      drawHouses(svg, centerX, centerY, chartRadius);
    }

    // Draw Ascendant line
    if (chartData.ascendant) {
      drawAscendant(svg, centerX, centerY, chartRadius);
    }

    // Draw planets
    if (chartData.planets && chartData.planets.length > 0) {
      drawPlanets(svg, centerX, centerY, chartRadius * 0.7);
    }
  };

  // Draw houses
  const drawHouses = (svg, centerX, centerY, chartRadius) => {
    const houses = chartData.houses;

    houses.forEach((house, i) => {
      // Draw house cusp lines
      const angle = (house.cusp * Math.PI) / 180;
      const x2 = centerX + chartRadius * Math.cos(angle);
      const y2 = centerY + chartRadius * Math.sin(angle);

      svg.append('line')
        .attr('x1', centerX)
        .attr('y1', centerY)
        .attr('x2', x2)
        .attr('y2', y2)
        .attr('stroke', '#999')
        .attr('stroke-width', 0.5)
        .attr('stroke-dasharray', '3,3');

      // Add house number
      const labelRadius = chartRadius * 0.3;
      const labelX = centerX + labelRadius * Math.cos(angle + Math.PI / 24);
      const labelY = centerY + labelRadius * Math.sin(angle + Math.PI / 24);

      svg.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '10px')
        .attr('fill', '#666')
        .text(house.number);
    });
  };

  // Draw Ascendant
  const drawAscendant = (svg, centerX, centerY, chartRadius) => {
    const ascLongitude = chartData.ascendant.longitude;
    const ascAngle = (ascLongitude * Math.PI) / 180;

    // Draw a bold line for Ascendant
    svg.append('line')
      .attr('x1', centerX)
      .attr('y1', centerY)
      .attr('x2', centerX + chartRadius * Math.cos(ascAngle))
      .attr('y2', centerY + chartRadius * Math.sin(ascAngle))
      .attr('stroke', '#f00')
      .attr('stroke-width', 2)
      .attr('data-testid', 'ascendant');

    // Add Ascendant label
    const labelRadius = chartRadius * 1.05;
    const labelX = centerX + labelRadius * Math.cos(ascAngle);
    const labelY = centerY + labelRadius * Math.sin(ascAngle);

    svg.append('text')
      .attr('x', labelX)
      .attr('y', labelY)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('fill', '#f00')
      .text('ASC');
  };

  // Draw planets
  const drawPlanets = (svg, centerX, centerY, planetRadius) => {
    const planets = chartData.planets;

    // Keep track of planet positions to handle overlaps
    const positions = [];

    planets.forEach(planet => {
      // Calculate position based on longitude
      const longitude = planet.longitude;
      const angle = (longitude * Math.PI) / 180;

      // Base position
      let x = centerX + planetRadius * Math.cos(angle);
      let y = centerY + planetRadius * Math.sin(angle);

      // Check for overlaps and adjust
      const overlap = positions.find(pos => {
        const dx = pos.x - x;
        const dy = pos.y - y;
        return Math.sqrt(dx * dx + dy * dy) < 25; // 25 is minimum distance between planets
      });

      if (overlap) {
        // Adjust radius slightly to avoid overlap
        const adjustedRadius = planetRadius * (1 + 0.1 * Math.random());
        x = centerX + adjustedRadius * Math.cos(angle);
        y = centerY + adjustedRadius * Math.sin(angle);
      }

      // Store position
      positions.push({ x, y });

      // Draw planet circle
      svg.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 12)
        .attr('fill', planetColors[planet.name] || '#333')
        .attr('stroke', '#333')
        .attr('stroke-width', 1)
        .attr('data-testid', `planet-${planet.name}`)
        .on('mouseover', () => setActiveEntity({ type: 'planet', data: planet }))
        .on('mouseout', () => setActiveEntity(null))
        .attr('class', 'interactive');

      // Add planet symbol
      svg.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '12px')
        .attr('fill', '#fff')
        .attr('pointer-events', 'none')
        .text(planetSymbols[planet.name] || planet.name.charAt(0));

      // Add special indicator for retrograde planets
      if (planet.retrograde) {
        svg.append('text')
          .attr('x', x)
          .attr('y', y + 20)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10px')
          .attr('fill', '#f00')
          .text('R');
      }
    });
  };

  // Helper to get zodiac sign name
  const getZodiacSign = (index) => {
    const signs = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
    return signs[index];
  };

  // Toggle between circle and table view
  const toggleView = () => {
    setViewMode(viewMode === 'circle' ? 'table' : 'circle');
  };

  // Generate planets table for table view
  const renderPlanetsTable = () => {
    if (!chartData || !chartData.planets) return null;

    return (
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
    );
  };

  return (
    <div className="chart-visualization" data-testid="chart-visualization">
      <div className="view-toggle">
        <button
          className={viewMode === 'circle' ? 'active' : ''}
          onClick={() => setViewMode('circle')}
          data-testid="chart-view"
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
      </div>

      {viewMode === 'circle' ? (
        <div className="chart-container">
          <svg ref={svgRef} />

          {activeEntity && (
            <div className="entity-details">
              {activeEntity.type === 'planet' && (
                <div>
                  <h3>{activeEntity.data.name}</h3>
                  <p>Sign: {activeEntity.data.sign}</p>
                  <p>Degree: {activeEntity.data.degree.toFixed(2)}°</p>
                  <p>House: {activeEntity.data.house}</p>
                  {activeEntity.data.retrograde && <p>Retrograde</p>}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="table-container">
          <div className="ascendant-info">
            <h3>Ascendant</h3>
            <p>Sign: {chartData?.ascendant?.sign}</p>
            <p>Degree: {chartData?.ascendant?.degree.toFixed(2)}°</p>
          </div>

          <h3>Planets</h3>
          {renderPlanetsTable()}

          <h3>Houses</h3>
          <table className="houses-table">
            <thead>
              <tr>
                <th>House</th>
                <th>Sign</th>
                <th>Degree</th>
              </tr>
            </thead>
            <tbody>
              {chartData?.houses?.map(house => (
                <tr key={house.number}>
                  <td>{house.number}</td>
                  <td>{house.sign}</td>
                  <td>{house.degree.toFixed(2)}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ChartVisualization;
