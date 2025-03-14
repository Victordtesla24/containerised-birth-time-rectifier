import React, { useRef, useState, useEffect } from 'react';
import d3 from '../../../src/utils/d3Shim';

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
    houses?: Array<{
      number: number;
      degree: number;
      sign: string;
    }>;
    ascendant?: {
      degree: number;
      sign: string;
      longitude: number;
    };
    aspects?: Array<{
      planet1: string;
      planet2: string;
      type: string;
      angle: number;
    }>;
  };
  onPlanetClick?: (planetId: string) => void;
  renderMode?: 'standard' | 'enhanced' | '3d'; // Added for production environment
  showEffects?: boolean; // For fancy visualizations in production
  originalChart?: any; // For comparison mode
  isRectified?: boolean; // To indicate if this is a rectified chart
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
  onPlanetClick,
  renderMode = 'standard',
  showEffects = false,
  originalChart = null,
  isRectified = false
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
      .attr('class', `chart-ready ${isZoomed ? 'zoom-animation-complete' : ''} ${renderMode}`)
      .attr('data-render-mode', renderMode) // Add data attribute for testing
      .attr('data-rectified', isRectified ? 'true' : 'false') // Add data attribute for testing
      .style('transform-origin', 'center')
      .style('transform', `scale(${scale})`);

    // Create base groups first for better rendering performance
    const chartGroup = svg.append('g').attr('class', 'chart-group');

    // Determine background style based on render mode
    const bgFill = renderMode === 'enhanced' ? 'url(#cosmic-gradient)' :
                  (renderMode === '3d' ? 'url(#space-gradient)' : '#f8f8ff');

    // For enhanced or 3D modes, create gradient definitions
    if (renderMode !== 'standard') {
      const defs = svg.append('defs');

      if (renderMode === 'enhanced') {
        // Create cosmic background gradient for enhanced mode
        const gradient = defs.append('radialGradient')
          .attr('id', 'cosmic-gradient')
          .attr('cx', '50%')
          .attr('cy', '50%')
          .attr('r', '50%');

        gradient.append('stop')
          .attr('offset', '0%')
          .attr('stop-color', '#1a1a2e');

        gradient.append('stop')
          .attr('offset', '100%')
          .attr('stop-color', '#0f0f1a');
      } else if (renderMode === '3d') {
        // Create space gradient for 3D mode
        const gradient = defs.append('radialGradient')
          .attr('id', 'space-gradient')
          .attr('cx', '50%')
          .attr('cy', '50%')
          .attr('r', '70%');

        gradient.append('stop')
          .attr('offset', '0%')
          .attr('stop-color', '#16213e');

        gradient.append('stop')
          .attr('offset', '80%')
          .attr('stop-color', '#0a0a1a');

        gradient.append('stop')
          .attr('offset', '100%')
          .attr('stop-color', '#050510');
      }
    }

    // Draw chart background
    chartGroup.append('circle')
      .attr('class', 'chart-background')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', chartRadius)
      .attr('fill', bgFill)
      .attr('stroke', renderMode === 'standard' ? '#333' : '#556')
      .attr('stroke-width', renderMode === '3d' ? 2 : 1);

    // Add advanced effects for production visualization if enabled
    if (showEffects) {
      // Stars backdrop for enhanced and 3D modes
      if (renderMode !== 'standard') {
        const starsGroup = chartGroup.append('g').attr('class', 'stars-backdrop');

        // Generate random stars
        for (let i = 0; i < 100; i++) {
          const x = Math.random() * width;
          const y = Math.random() * height;
          const r = Math.random() * 1.5;
          const opacity = Math.random() * 0.8 + 0.2;

          starsGroup.append('circle')
            .attr('cx', x)
            .attr('cy', y)
            .attr('r', r)
            .attr('fill', '#fff')
            .attr('opacity', opacity)
            .attr('class', 'star');
        }

        // Add subtle glow to chart background
        chartGroup.append('circle')
          .attr('cx', centerX)
          .attr('cy', centerY)
          .attr('r', chartRadius + 10)
          .attr('fill', 'none')
          .attr('stroke', isRectified ? '#5a89cc' : '#8866aa')
          .attr('stroke-width', 5)
          .attr('opacity', 0.3)
          .attr('filter', 'blur(10px)')
          .attr('class', 'chart-glow');
      }
    }

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

      // Determine zodiac segment fill color based on render mode
      let fill: string;
      if (renderMode === 'standard') {
        fill = i % 2 === 0 ? '#f0f0f8' : '#e8e8f0';
      } else if (renderMode === 'enhanced') {
        // Rich blues and purples for enhanced mode
        fill = i % 2 === 0 ? '#1a3366' : '#2a2a4a';
      } else {
        // Deep space colors for 3D mode
        fill = i % 2 === 0 ? '#192338' : '#141d30';
      }

      zodiacGroup.append('path')
        .attr('d', arc({
          innerRadius: chartRadius * 0.8,
          outerRadius: chartRadius,
          startAngle: startAngle,
          endAngle: endAngle
        }))
        .attr('fill', fill)
        .attr('stroke', renderMode === 'standard' ? '#666' : '#99a')
        .attr('stroke-width', 0.5)
        .attr('class', `zodiac-segment segment-${i}`);

      // Add zodiac symbol with appropriate styling based on render mode
      const angle = (i * 30 + 15 - 90) * Math.PI / 180;
      const labelRadius = chartRadius * 0.9;
      const x = labelRadius * Math.cos(angle);
      const y = labelRadius * Math.sin(angle);

      zodiacGroup.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', renderMode === '3d' ? '14px' : '12px')
        .attr('fill', renderMode === 'standard' ? '#333' : '#dde')
        .attr('class', 'zodiac-label')
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
        .attr('stroke', renderMode === 'standard' ? '#666' : '#99a')
        .attr('stroke-width', 0.5)
        .attr('class', 'house-line');

      // Add house numbers with appropriate styling
      const labelRadius = chartRadius * 0.6;
      const labelX = labelRadius * Math.cos(angle);
      const labelY = labelRadius * Math.sin(angle);

      housesGroup.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', '10px')
        .attr('fill', renderMode === 'standard' ? '#333' : '#ccd')
        .attr('class', 'house-number')
        .text((i + 1).toString());
    }

    // Draw planets with enhanced styling based on render mode
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
        .on('mouseover', (event: MouseEvent) => {
          const { clientX, clientY } = event;
          setTooltipPosition({ x: clientX, y: clientY });
          setActiveEntity({ type: 'planet', data: planet });
        })
        .on('mouseout', () => {
          setActiveEntity(null);
        });

      // Calculate planet position
      const planetX = centerX + (chartRadius * 0.7) * Math.cos(degreesToRadians(planet.longitude - 90));
      const planetY = centerY + (chartRadius * 0.7) * Math.sin(degreesToRadians(planet.longitude - 90));

      // For enhanced visuals in production, add orbit path and glow effects
      if (renderMode !== 'standard' && showEffects) {
        // Add orbit path for planets (subtle circular path)
        const orbitRadius = chartRadius * 0.7;
        planetGroup.append('circle')
          .attr('cx', centerX)
          .attr('cy', centerY)
          .attr('r', orbitRadius)
          .attr('fill', 'none')
          .attr('stroke', '#4466aa')
          .attr('stroke-width', 0.5)
          .attr('opacity', 0.3)
          .attr('stroke-dasharray', '2,2')
          .attr('class', 'planet-orbit');

        // Add glow effect for planets
        if (renderMode === '3d') {
          // Add a glow/halo effect for the planet in 3D mode
          planetGroup.append('circle')
            .attr('cx', planetX)
            .attr('cy', planetY)
            .attr('r', 12)
            .attr('fill', 'none')
            .attr('stroke', getPlanetColor(planet.name))
            .attr('stroke-width', 3)
            .attr('opacity', 0.4)
            .attr('filter', 'blur(3px)')
            .attr('class', 'planet-glow');
        }
      }

      // Enhanced planet display for production
      if (renderMode !== 'standard') {
        // Draw a circle for the planet with fancy styling
        planetGroup.append('circle')
          .attr('cx', planetX)
          .attr('cy', planetY)
          .attr('r', planet.name === 'Sun' ? 10 : 7)
          .attr('fill', getPlanetColor(planet.name))
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
          .attr('class', 'planet-body');
      }

      // Always add planet symbol text for testing compatibility
      planetGroup.append('text')
        .attr('x', planetX)
        .attr('y', planetY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', renderMode === 'standard' ? '12px' : '14px')
        .attr('fill', renderMode === 'standard' ? '#333' : '#fff')
        .attr('class', 'planet-symbol')
        .text(getPlanetSymbol(planet.name));
    });

    // Draw Ascendant line with appropriate styling
    if (chartData.ascendant) {
      const ascAngle = degreesToRadians(chartData.ascendant.longitude - 90);
      const lineColor = renderMode === 'standard' ? '#f00' : (isRectified ? '#ff66aa' : '#ffaa33');

      // Draw ascendant line
      chartGroup.append('line')
        .attr('x1', centerX)
        .attr('y1', centerY)
        .attr('x2', centerX + chartRadius * Math.cos(ascAngle))
        .attr('y2', centerY + chartRadius * Math.sin(ascAngle))
        .attr('stroke', lineColor)
        .attr('stroke-width', renderMode === '3d' ? 3 : 2)
        .attr('data-testid', 'ascendant')
        .attr('class', 'ascendant-line');

      // Add glow effect for ascendant line in enhanced modes
      if (renderMode !== 'standard' && showEffects) {
        chartGroup.append('line')
          .attr('x1', centerX)
          .attr('y1', centerY)
          .attr('x2', centerX + chartRadius * Math.cos(ascAngle))
          .attr('y2', centerY + chartRadius * Math.sin(ascAngle))
          .attr('stroke', lineColor)
          .attr('stroke-width', 6)
          .attr('opacity', 0.4)
          .attr('filter', 'blur(4px)')
          .attr('class', 'ascendant-glow');
      }
    }

    // Add label for rectified chart if applicable
    if (isRectified) {
      svg.append('text')
        .attr('x', centerX)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', renderMode === 'standard' ? '#4a4a9c' : '#88aaff')
        .attr('class', 'rectified-label')
        .text('Rectified Chart');
    }

    // Add comparison indicator if comparing charts
    if (originalChart) {
      svg.append('text')
        .attr('x', width - 20)
        .attr('y', 20)
        .attr('text-anchor', 'end')
        .attr('font-size', '14px')
        .attr('fill', renderMode === 'standard' ? '#4a4a9c' : '#88aaff')
        .attr('class', 'comparison-indicator')
        .text('Comparison Mode');
    }

    // Force a repaint to ensure elements are immediately available
    svgRef.current.style.display = 'none';
    svgRef.current.getBoundingClientRect();
    svgRef.current.style.display = '';

  }, [chartData, width, height, scale, isZoomed, onPlanetClick, renderMode, showEffects, isRectified, originalChart]);

  // Define planet color function based on render mode
  const getPlanetColor = (planetName: string): string => {
    // Enhanced colors for production
    const standardColors: Record<string, string> = {
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

    const enhancedColors: Record<string, string> = {
      'Sun': '#ffd700',
      'Moon': '#e6e6fa',
      'Mercury': '#9966ff',
      'Venus': '#ff55cc',
      'Mars': '#ff3333',
      'Jupiter': '#ffaa33',
      'Saturn': '#8b4513',
      'Uranus': '#33ccff',
      'Neptune': '#4169e1',
      'Pluto': '#9932cc',
      'Rahu': '#483d8b',
      'Ketu': '#8b0000'
    };

    return renderMode === 'standard' ?
      (standardColors[planetName] || '#333') :
      (enhancedColors[planetName] || '#4466aa');
  };

  const handleDoubleClick = () => {
    setIsZoomed(!isZoomed);
  };

  return (
    <div
      ref={containerRef}
      className={`chart-visualization ${isZoomed ? 'zoomed' : ''} ${renderMode}-mode`}
      data-testid="chart-visualization"
      data-render-mode={renderMode}
      style={{
        width: `${width * scale}px`,
        height: `${height * scale}px`,
        transformOrigin: 'center',
        transition: 'transform 0.3s ease-in-out',
        position: 'relative',
        overflow: 'hidden', // Prevent effects from overflowing
        borderRadius: renderMode !== 'standard' ? '8px' : '0', // Rounded corners for fancy modes
        boxShadow: renderMode !== 'standard' ? '0 4px 20px rgba(0,0,0,0.3)' : 'none' // Shadow for fancy modes
      }}
    >
      {/* Add production quality overlay effects if enabled */}
      {renderMode !== 'standard' && showEffects && (
        <div className="cosmic-effects-overlay" style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          zIndex: 1,
          background: 'radial-gradient(circle at center, transparent 30%, rgba(0,0,30,0.2) 100%)',
          opacity: 0.8
        }}>
          {/* Optional cosmic particles animation overlay for 3D mode */}
          {renderMode === '3d' && (
            <div className="cosmic-particles" style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px)',
              backgroundSize: '30px 30px',
              backgroundPosition: 'center',
              animation: 'float 60s infinite linear',
              opacity: 0.2
            }} />
          )}
        </div>
      )}

      {/* Chart visualization SVG */}
      <svg
        ref={svgRef}
        onDoubleClick={handleDoubleClick}
        style={{
          transition: 'transform 0.3s ease-in-out',
          transform: `scale(${isZoomed ? 1.5 : 1})`,
          position: 'relative',
          zIndex: 2 // Keep chart visualization above effects overlay
        }}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        data-testid="chart-svg"
      />

      {/* Controls for production environment */}
      {renderMode !== 'standard' && (
        <div className="chart-controls" style={{
          position: 'absolute',
          bottom: 10,
          right: 10,
          zIndex: 3,
          display: 'flex',
          gap: '8px'
        }}>
          <button
            className="chart-control-btn zoom-btn"
            onClick={handleDoubleClick}
            style={{
              background: 'rgba(30,30,60,0.7)',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 8px',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
              backdropFilter: 'blur(4px)'
            }}
            data-testid="zoom-toggle"
          >
            {isZoomed ? 'Zoom Out' : 'Zoom In'}
          </button>
        </div>
      )}

      {/* Enhanced tooltip for production environment */}
      {activeEntity && (
        <div
          className={`planet-tooltip ${renderMode}-tooltip`}
          style={{
            position: 'absolute',
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translate(-50%, -100%)',
            backgroundColor: renderMode === 'standard'
              ? 'rgba(255, 255, 255, 0.9)'
              : 'rgba(20, 30, 60, 0.85)',
            color: renderMode === 'standard' ? '#333' : '#fff',
            backdropFilter: 'blur(4px)',
            padding: '8px 12px',
            borderRadius: '6px',
            boxShadow: renderMode === 'standard'
              ? '0 2px 4px rgba(0,0,0,0.1)'
              : '0 4px 12px rgba(0,10,50,0.3), 0 0 0 1px rgba(255,255,255,0.1)',
            zIndex: 1000,
            pointerEvents: 'none',
            fontSize: '14px',
            lineHeight: '1.5',
            maxWidth: '200px'
          }}
          data-testid="planet-info"
        >
          <div className="tooltip-header" style={{
            fontWeight: 'bold',
            marginBottom: '4px',
            borderBottom: renderMode !== 'standard' ? '1px solid rgba(255,255,255,0.2)' : 'none',
            paddingBottom: renderMode !== 'standard' ? '4px' : '0'
          }}>
            {activeEntity.data.name}
          </div>
          <div className="tooltip-content">
            <div>{activeEntity.data.sign} {activeEntity.data.degree.toFixed(2)}°</div>
            <div>House {activeEntity.data.house}</div>
          </div>
        </div>
      )}

      {/* Render mode indicator for testing */}
      <div
        className="render-mode-indicator"
        data-testid="render-mode-indicator"
        style={{
          position: 'absolute',
          bottom: 5,
          left: 5,
          fontSize: '10px',
          color: 'rgba(100,100,100,0.5)',
          zIndex: 5,
          pointerEvents: 'none'
        }}>
        {renderMode}
      </div>
    </div>
  );
};

export default ChartVisualization;
