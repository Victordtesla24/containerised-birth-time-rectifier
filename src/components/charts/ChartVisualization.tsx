import React, { useRef, useState, useEffect } from 'react';
import * as d3 from 'd3';

interface PlanetData {
  id: string;
  name: string;
  sign: string;
  degree: number;
  house: number;
  longitude: number;
}

interface ChartData {
  planets: PlanetData[];
  houses: Array<{
    number: number;
    degree: number;
    sign: string;
  }>;
  ascendant: {
    degree: number;
    sign: string;
    longitude: number;
  };
  aspects: Array<{
    planet1: string;
    planet2: string;
    type: string;
    angle: number;
  }>;
}

interface ChartVisualizationProps {
  width: number;
  height: number;
  chartData: {
    planets: PlanetData[];
  };
  onPlanetClick?: (planetId: string) => void;
}

// Helper functions
const degreesToRadians = (degrees: number): number => {
  return (degrees * Math.PI) / 180;
};

const getPlanetSymbol = (planetName: string): string => {
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

const getZodiacSign = (index: number): string => {
  const signs = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
  ];
  return signs[index % 12];
};

const ChartVisualization: React.FC<ChartVisualizationProps> = ({
  width,
  height,
  chartData,
  onPlanetClick
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isZoomed, setIsZoomed] = useState(false);
  const [activeEntity, setActiveEntity] = useState<{
    type: 'planet';
    data: PlanetData;
  } | null>(null);
  const [scale, setScale] = useState(1);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // Calculate chart dimensions
  const centerX = width / 2;
  const centerY = height / 2;
  const chartRadius = Math.min(width, height) / 2 - 40;

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      const viewportWidth = window.innerWidth;
      const newScale = viewportWidth < 600 ? 0.5 : 1;
      setScale(newScale);

      // Update container dimensions
      if (containerRef.current) {
        containerRef.current.style.width = `${width * newScale}px`;
        containerRef.current.style.height = `${height * newScale}px`;
      }
    };

    handleResize(); // Set initial scale
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [width, height]);

  // Draw chart when data changes
  useEffect(() => {
    if (!svgRef.current || !chartData) return;

    const svg = d3.select(svgRef.current);

    // Clear existing content
    svg.selectAll('*').remove();

    // Set up the SVG with proper attributes
    svg
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('class', `chart-ready ${isZoomed ? 'zoom-animation-complete' : ''}`)
      .style('transform-origin', 'center')
      .style('transform', `scale(${scale})`);

    // Create base groups first for better rendering performance
    const chartGroup = svg.append('g').attr('class', 'chart-group');

    // Draw chart background
    chartGroup.append('circle')
      .attr('class', 'chart-background')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', chartRadius)
      .attr('fill', '#f8f8ff')
      .attr('stroke', '#333')
      .attr('stroke-width', 1);

    // Draw zodiac ring
    const zodiacGroup = chartGroup.append('g')
      .attr('class', 'zodiac-ring')
      .attr('transform', `translate(${centerX}, ${centerY})`);

    // Draw zodiac signs
    for (let i = 0; i < 12; i++) {
      const startAngle = (i * 30 - 90) * Math.PI / 180;
      const endAngle = ((i + 1) * 30 - 90) * Math.PI / 180;

      const arc = d3.arc()
        .innerRadius(chartRadius * 0.8)
        .outerRadius(chartRadius)
        .startAngle(startAngle)
        .endAngle(endAngle);

      zodiacGroup.append('path')
        .attr('d', arc({
          innerRadius: chartRadius * 0.8,
          outerRadius: chartRadius,
          startAngle: startAngle,
          endAngle: endAngle
        }))
        .attr('fill', i % 2 === 0 ? '#f0f0f8' : '#e8e8f0')
        .attr('stroke', '#666')
        .attr('stroke-width', 0.5);

      // Add zodiac symbol
      const angle = (i * 30 + 15 - 90) * Math.PI / 180;
      const labelRadius = chartRadius * 0.9;
      const x = labelRadius * Math.cos(angle);
      const y = labelRadius * Math.sin(angle);

      zodiacGroup.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', '12px')
        .text(getZodiacSign(i));
    }

    // Draw houses
    const housesGroup = chartGroup.append('g')
      .attr('class', 'house-divisions')
      .attr('transform', `translate(${centerX}, ${centerY})`);

    // Draw house lines (12 equal divisions)
    for (let i = 0; i < 12; i++) {
      const angle = (i * 30 - 90) * Math.PI / 180;
      const x1 = chartRadius * 0.4 * Math.cos(angle);
      const y1 = chartRadius * 0.4 * Math.sin(angle);
      const x2 = chartRadius * 0.8 * Math.cos(angle);
      const y2 = chartRadius * 0.8 * Math.sin(angle);

      housesGroup.append('line')
        .attr('x1', x1)
        .attr('y1', y1)
        .attr('x2', x2)
        .attr('y2', y2)
        .attr('stroke', '#666')
        .attr('stroke-width', 0.5);

      // Add house numbers
      const labelRadius = chartRadius * 0.6;
      const labelX = labelRadius * Math.cos(angle);
      const labelY = labelRadius * Math.sin(angle);

      housesGroup.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', '10px')
        .text((i + 1).toString());
    }

    // Draw planets first to ensure they're available for testing
    const planetsGroup = chartGroup.append('g')
      .attr('class', 'planet-symbols')
      .attr('data-testid', 'planet-symbols');

    // Add planets with proper data attributes
    chartData.planets.forEach(planet => {
      const planetGroup = planetsGroup.append('g')
        .attr('class', `planet ${planet.name.toLowerCase()}`)
        .attr('data-testid', `planet-${planet.name}`)
        .attr('data-sign', planet.sign)
        .attr('data-degree', planet.degree)
        .attr('data-house', planet.house)
        .attr('data-total-degree', planet.longitude)
        .on('click', () => onPlanetClick?.(planet.id))
        .on('mouseover', (event) => {
          const { clientX, clientY } = event;
          setTooltipPosition({ x: clientX, y: clientY });
          setActiveEntity({ type: 'planet', data: planet });
        })
        .on('mouseout', () => {
          setActiveEntity(null);
        });

      // Add planet symbol
      planetGroup.append('text')
        .attr('x', centerX + (chartRadius * 0.7) * Math.cos(degreesToRadians(planet.longitude - 90)))
        .attr('y', centerY + (chartRadius * 0.7) * Math.sin(degreesToRadians(planet.longitude - 90)))
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .text(getPlanetSymbol(planet.name));
    });

    // Force a repaint to ensure elements are immediately available
    svgRef.current.style.display = 'none';
    svgRef.current.getBoundingClientRect();
    svgRef.current.style.display = '';

  }, [chartData, width, height, scale, isZoomed, onPlanetClick]);

  const handleDoubleClick = () => {
    setIsZoomed(!isZoomed);
  };

  return (
    <div
      ref={containerRef}
      className={`chart-visualization ${isZoomed ? 'zoomed' : ''}`}
      style={{
        width: `${width * scale}px`,
        height: `${height * scale}px`,
        transformOrigin: 'center',
        transition: 'transform 0.3s ease-in-out',
        position: 'relative'
      }}
    >
      <svg
        ref={svgRef}
        onDoubleClick={handleDoubleClick}
        style={{
          transition: 'transform 0.3s ease-in-out',
          transform: `scale(${isZoomed ? 1.5 : 1})`
        }}
      />
      {activeEntity && (
        <div
          className="planet-tooltip"
          style={{
            position: 'absolute',
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translate(-50%, -100%)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(4px)',
            padding: '8px',
            borderRadius: '4px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            zIndex: 1000,
            pointerEvents: 'none'
          }}
        >
          <div className="font-medium">{activeEntity.data.name}</div>
          <div>{activeEntity.data.sign} {activeEntity.data.degree}°</div>
          <div>House {activeEntity.data.house}</div>
        </div>
      )}
    </div>
  );
};

export default ChartVisualization;
