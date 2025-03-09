import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { ChartDimensions, ChartRendererProps } from './types';
import {
  calculateChartDimensions,
  calculatePlanetPosition,
  calculateHousePosition,
  calculateAspects,
  getPlanetSymbol,
  degreesToRadians,
  signAndDegreeToLongitude,
} from './calculations';
import { exportChart, ExportOptions } from './exporters';
import { motion, AnimatePresence } from 'framer-motion';

const ChartRenderer: React.FC<ChartRendererProps> = ({
  data,
  width = 600,
  height = 600,
  showLabels = true,
  onPlanetClick,
  selectedDivisionalChart,
  showCelestialLayers = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  // Get the active chart data
  const activeChart = selectedDivisionalChart
    ? data.divisionalCharts[selectedDivisionalChart]
    : data;

  // Detect rendering capabilities and set appropriate flags
  const renderCapabilities = useMemo(() => {
    // Default to assuming basic capabilities
    const capabilities = {
      supportsCanvas2D: true,
      hasReducedMotion: false,
    };

    // Check for reduced motion preference
    if (typeof window !== 'undefined' && window.matchMedia) {
      capabilities.hasReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    return capabilities;
  }, []);

  // Error state tracking
  const [renderError, setRenderError] = useState<string | null>(null);

  // Progressive loading
  const [isLoading, setIsLoading] = useState(true);

  // Rendering queue to prevent overwhelming the browser
  const renderQueueRef = useRef<number | null>(null);

  // Set loading complete after a short delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 200);

    return () => clearTimeout(timer);
  }, []);

  const drawChart = useCallback(() => {
    try {
      // Clear any previous render errors
      setRenderError(null);

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) {
        setRenderError("Could not get 2D context");
        return;
      }

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Apply transformations
      ctx.save();
      ctx.translate(pan.x, pan.y);
      ctx.scale(scale, scale);

    // Calculate dimensions
    const dimensions = calculateChartDimensions(width, height);
    const { radius, centerX, centerY } = dimensions;

    // Draw celestial layers if enabled
    if (showCelestialLayers && data.visualization?.celestialLayers) {
      try {
        data.visualization.celestialLayers.forEach(layer => {
          try {
            const gradient = ctx.createRadialGradient(
              centerX, centerY, 0,
              centerX, centerY, radius * (1 + layer.depth)
            );

            gradient.addColorStop(0, 'rgba(255, 255, 255, 0)');
            gradient.addColorStop(0.5, `rgba(255, 255, 255, ${0.1 * layer.parallaxFactor})`);
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius * (1 + layer.depth), 0, 2 * Math.PI);
            ctx.fill();
          } catch (layerError) {
            console.warn("Error rendering celestial layer:", layerError);
            // Continue with other layers rather than failing completely
          }
        });
      } catch (layersError) {
        console.warn("Error rendering celestial layers:", layersError);
        // Continue with chart rendering even if celestial layers fail
      }
    }

    // Draw main chart circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw zodiac signs on outer ring
    drawZodiacRing(ctx, dimensions);

    // Draw houses
    activeChart.houses.forEach(house => {
      const housePos = calculateHousePosition(house, dimensions);

      // Draw house lines
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(housePos.endX, housePos.endY);
      ctx.strokeStyle = '#666';
      ctx.lineWidth = 1;
      ctx.stroke();

      if (showLabels) {
        // Draw house numbers
        ctx.font = '12px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(
          house.number.toString(),
          housePos.midpointX,
          housePos.midpointY
        );
      }
    });

    // Calculate and draw aspects if they exist
    try {
      const aspects = calculateAspects(activeChart.planets);
      aspects.forEach(aspect => {
        const planet1 = activeChart.planets.find(p => p.name === aspect.planet1);
        const planet2 = activeChart.planets.find(p => p.name === aspect.planet2);

        if (planet1 && planet2) {
          const pos1 = calculatePlanetPosition(planet1, dimensions);
          const pos2 = calculatePlanetPosition(planet2, dimensions);

          ctx.beginPath();
          ctx.moveTo(pos1.x, pos1.y);
          ctx.lineTo(pos2.x, pos2.y);
          ctx.strokeStyle = getAspectColor(aspect.aspect);
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      });
    } catch (error) {
      console.warn('Error calculating or drawing aspects:', error);
    }

    // Draw planets - with multi-stage rendering pipeline to prevent memory spikes
    // First pass - draw background circles only
    activeChart.planets.forEach(planet => {
      try {
        const planetPos = calculatePlanetPosition(planet, dimensions);

        // Draw planet background circle
        ctx.beginPath();
        ctx.arc(planetPos.x, planetPos.y, 12, 0, 2 * Math.PI);
        ctx.fillStyle = 'white';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.stroke();
      } catch (error) {
        console.warn(`Error rendering planet ${planet.name} background:`, error);
      }
    });

    // Second pass - draw symbols
    activeChart.planets.forEach(planet => {
      try {
        const planetPos = calculatePlanetPosition(planet, dimensions);

        // Draw planet symbol
        ctx.font = '16px Arial';
        ctx.fillStyle = '#000';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(getPlanetSymbol(planet.name || ''), planetPos.x, planetPos.y);
      } catch (error) {
        console.warn(`Error rendering planet ${planet.name} symbol:`, error);
      }
    });

    // Third pass - draw labels (only if enabled)
    if (showLabels) {
      activeChart.planets.forEach(planet => {
        try {
          const planetPos = calculatePlanetPosition(planet, dimensions);

          // Determine retrograde status
          const isRetrograde = planet.retrograde || (planet.speed !== undefined && planet.speed < 0);

          // Draw degree and retrograde status
          ctx.font = '10px Arial';
          ctx.fillStyle = '#666';
          const degree = typeof planet.degree === 'number'
            ? planet.degree
            : (planetPos.degree || 0);
          ctx.fillText(
            `${degree.toFixed(1)}° ${isRetrograde ? 'R' : ''}`,
            planetPos.x,
            planetPos.y + 20
          );
        } catch (error) {
          console.warn(`Error rendering planet ${planet.name} labels:`, error);
        }
      });
    }

    // Draw ascendant line or mark
    try {
      // Handle both ascendant formats
      let ascendantDegree = 0;
      if (typeof activeChart.ascendant === 'number') {
        ascendantDegree = activeChart.ascendant;
      } else if (activeChart.ascendant && typeof activeChart.ascendant === 'object') {
        if (activeChart.ascendant.degree !== undefined) {
          // If sign is provided, convert to absolute degrees
          if (activeChart.ascendant.sign) {
            ascendantDegree = signAndDegreeToLongitude(
              activeChart.ascendant.sign,
              activeChart.ascendant.degree
            );
          } else {
            ascendantDegree = activeChart.ascendant.degree;
          }
        }
      }

      // Draw ascendant line (add 90 degrees to start from the top)
      const ascendantAngle = degreesToRadians(ascendantDegree + 90);
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(
        centerX + radius * Math.cos(ascendantAngle),
        centerY + radius * Math.sin(ascendantAngle)
      );
      ctx.strokeStyle = '#e74c3c';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw Ascendant label
      if (showLabels) {
        ctx.font = 'bold 14px Arial';
        ctx.fillStyle = '#e74c3c';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const labelDistance = radius * 1.1;
        ctx.fillText(
          'ASC',
          centerX + labelDistance * Math.cos(ascendantAngle),
          centerY + labelDistance * Math.sin(ascendantAngle)
        );
      }
    } catch (error) {
      console.warn('Error drawing ascendant:', error);
    }

    // Restore the canvas
    ctx.restore();
    } catch (error) {
      console.error("Critical render error:", error);
      setRenderError("Error rendering chart. Please try refreshing the page.");
    }
  }, [data, width, height, showLabels, scale, pan, activeChart, showCelestialLayers]);

  useEffect(() => {
    // Use requestAnimationFrame for smoother rendering and to prevent texture loading errors
    if (renderQueueRef.current) {
      cancelAnimationFrame(renderQueueRef.current);
    }

    renderQueueRef.current = requestAnimationFrame(() => {
      drawChart();
      renderQueueRef.current = null;
    });

    return () => {
      if (renderQueueRef.current) {
        cancelAnimationFrame(renderQueueRef.current);
        renderQueueRef.current = null;
      }
    };
  }, [drawChart]);

  const handleWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    const delta = event.deltaY > 0 ? 0.9 : 1.1;
    setScale(prev => Math.max(0.5, Math.min(3, prev * delta)));
  };

  const handleMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: event.clientX - pan.x, y: event.clientY - pan.y });
  };

  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    setPan({
      x: event.clientX - dragStart.x,
      y: event.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onPlanetClick || !canvasRef.current || isDragging) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left - pan.x) / scale;
    const y = (event.clientY - rect.top - pan.y) / scale;
    const dimensions = calculateChartDimensions(width, height);

    // Check if click is near any planet
    activeChart.planets.forEach(planet => {
      const planetPos = calculatePlanetPosition(planet, dimensions);
      const distance = Math.sqrt(
        Math.pow(x - planetPos.x, 2) + Math.pow(y - planetPos.y, 2)
      );

      if (distance < 15) {
        onPlanetClick(planetPos.id);
      }
    });
  };

  const handleExport = async (format: 'png' | 'svg' | 'pdf') => {
    if (!canvasRef.current) return;

    const options: ExportOptions = {
      width,
      height,
      format,
      quality: 1,
    };

    await exportChart(canvasRef.current, data, options);
    setShowExportMenu(false);
  };

  const renderLegend = () => (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="absolute left-2 top-2 bg-white p-4 rounded shadow-lg"
    >
      <h3 className="text-lg font-medium mb-2">Legend</h3>
      <div className="space-y-2">
        <div className="flex items-center">
          <div className="w-4 h-4 bg-red-500 rounded-full mr-2" />
          <span>Conjunction/Opposition/Square</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-green-500 rounded-full mr-2" />
          <span>Sextile</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-blue-500 rounded-full mr-2" />
          <span>Trine</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-red-600 rounded-full mr-2" />
          <span>Ascendant</span>
        </div>
        <div className="space-y-1 mt-2">
          <h4 className="font-medium">Planets</h4>
          {Object.entries(getPlanetSymbol).map(([name, symbol]) => (
            <div key={name} className="flex items-center">
              <span className="w-6 text-center mr-2">{symbol}</span>
              <span>{name}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="relative h-full w-full">
      {/* Progressive loading indicator */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 z-10">
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mb-2"></div>
            <p className="text-gray-700">Loading chart...</p>
          </div>
        </div>
      )}

      {/* Error message banner */}
      {renderError && (
        <div className="absolute top-0 left-0 right-0 bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mx-2 mt-2 z-20">
          <p className="flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {renderError}
          </p>
          <button
            onClick={() => {
              setRenderError(null);
              drawChart();
            }}
            className="text-sm text-red-600 hover:text-red-800 underline mt-1"
          >
            Try again
          </button>
        </div>
      )}

      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onClick={handleCanvasClick}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          maxWidth: '100%',
          maxHeight: '100%',
          width: 'auto',
          height: 'auto',
          display: 'block',
          margin: '0 auto',
          cursor: isDragging ? 'grabbing' : 'grab',
          opacity: isLoading ? 0 : 1,
          transition: 'opacity 0.3s ease-in-out'
        }}
        aria-hidden={!!renderError}
      />
      <div className="absolute top-2 right-2 space-x-2">
        <button
          onClick={() => setShowLegend(!showLegend)}
          className="px-2 py-1 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50"
        >
          Legend
        </button>
        <button
          onClick={() => setScale(1)}
          className="px-2 py-1 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50"
        >
          Reset
        </button>
        <div className="relative inline-block">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="px-2 py-1 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50"
          >
            Export
          </button>
          <AnimatePresence>
            {showExportMenu && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute right-0 mt-1 w-32 bg-white border border-gray-200 rounded shadow-lg"
              >
                <button
                  onClick={() => handleExport('png')}
                  className="block w-full px-4 py-2 text-left hover:bg-gray-100"
                >
                  PNG
                </button>
                <button
                  onClick={() => handleExport('svg')}
                  className="block w-full px-4 py-2 text-left hover:bg-gray-100"
                >
                  SVG
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  className="block w-full px-4 py-2 text-left hover:bg-gray-100"
                >
                  PDF
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <AnimatePresence>
        {showLegend && renderLegend()}
      </AnimatePresence>
    </div>
  );
};

const getAspectColor = (aspect: number): string => {
  const colors: Record<number, string> = {
    0: '#ff0000',   // Conjunction - Red
    60: '#00ff00',  // Sextile - Green
    90: '#ff0000',  // Square - Red
    120: '#0000ff', // Trine - Blue
    180: '#ff0000', // Opposition - Red
  };

  return colors[aspect] || '#000000';
};

// Helper function to draw the zodiac ring
function drawZodiacRing(ctx: CanvasRenderingContext2D, dimensions: ChartDimensions) {
  const { radius, centerX, centerY } = dimensions;
  const outerRadius = radius * 1.1;
  const zodiacWidth = radius * 0.12;

  const zodiacSigns = [
    { symbol: '♈', name: 'Aries', element: 'fire' },
    { symbol: '♉', name: 'Taurus', element: 'earth' },
    { symbol: '♊', name: 'Gemini', element: 'air' },
    { symbol: '♋', name: 'Cancer', element: 'water' },
    { symbol: '♌', name: 'Leo', element: 'fire' },
    { symbol: '♍', name: 'Virgo', element: 'earth' },
    { symbol: '♎', name: 'Libra', element: 'air' },
    { symbol: '♏', name: 'Scorpio', element: 'water' },
    { symbol: '♐', name: 'Sagittarius', element: 'fire' },
    { symbol: '♑', name: 'Capricorn', element: 'earth' },
    { symbol: '♒', name: 'Aquarius', element: 'air' },
    { symbol: '♓', name: 'Pisces', element: 'water' }
  ];

  // Draw the outer ring
  ctx.beginPath();
  ctx.arc(centerX, centerY, outerRadius, 0, 2 * Math.PI);
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw the inner ring
  ctx.beginPath();
  ctx.arc(centerX, centerY, outerRadius - zodiacWidth, 0, 2 * Math.PI);
  ctx.stroke();

  // Draw zodiac segments and symbols
  zodiacSigns.forEach((sign, index) => {
    const startAngle = degreesToRadians(index * 30 + 90); // Start from the top (add 90)
    const endAngle = degreesToRadians((index + 1) * 30 + 90);

    // Draw segment
    ctx.beginPath();
    ctx.arc(centerX, centerY, outerRadius, startAngle, endAngle);
    ctx.arc(centerX, centerY, outerRadius - zodiacWidth, endAngle, startAngle, true);
    ctx.closePath();

    // Fill with alternating colors
    ctx.fillStyle = index % 2 === 0 ? 'rgba(240, 240, 240, 0.5)' : 'rgba(220, 220, 220, 0.5)';
    ctx.fill();
    ctx.stroke();

    // Draw symbol
    const symbolAngle = degreesToRadians(index * 30 + 15 + 90); // Middle of segment
    const symbolRadius = outerRadius - (zodiacWidth / 2);

    ctx.font = '14px Arial';
    ctx.fillStyle = '#333';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(
      sign.symbol,
      centerX + symbolRadius * Math.cos(symbolAngle),
      centerY + symbolRadius * Math.sin(symbolAngle)
    );
  });
}

export default ChartRenderer;
