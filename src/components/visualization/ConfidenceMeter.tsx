import React, { useEffect, useRef } from 'react';

interface ConfidenceMeterProps {
  value: number;
  maxValue?: number;
  threshold?: number;
  animate?: boolean;
  color?: string;
  className?: string;
}

/**
 * ConfidenceMeter - An animated progress meter for displaying confidence score
 *
 * @param {Object} props Component props
 * @param {number} props.value Current confidence value (0-100)
 * @param {number} props.maxValue Maximum value (default: 100)
 * @param {number} props.threshold Threshold value for completion (default: 80)
 * @param {boolean} props.animate Whether to animate the meter (default: true)
 * @param {string} props.color Primary color (default: indigo)
 * @param {string} props.className Additional CSS classes
 */
const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  value,
  maxValue = 100,
  threshold = 80,
  animate = true,
  color = 'indigo',
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const requestRef = useRef<number>();
  const currentValueRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  // Convert color string to tailwind classes
  const getColorClasses = (colorName: string) => {
    const colorMap: Record<string, {bg: string, text: string, border: string}> = {
      indigo: {
        bg: 'bg-indigo-600',
        text: 'text-indigo-200',
        border: 'border-indigo-300'
      },
      blue: {
        bg: 'bg-blue-600',
        text: 'text-blue-200',
        border: 'border-blue-300'
      },
      green: {
        bg: 'bg-green-600',
        text: 'text-green-200',
        border: 'border-green-300'
      },
      red: {
        bg: 'bg-red-600',
        text: 'text-red-200',
        border: 'border-red-300'
      },
      yellow: {
        bg: 'bg-yellow-600',
        text: 'text-yellow-200',
        border: 'border-yellow-300'
      },
      purple: {
        bg: 'bg-purple-600',
        text: 'text-purple-200',
        border: 'border-purple-300'
      }
    };

    return colorMap[colorName] || colorMap.indigo;
  };

  const colorClasses = getColorClasses(color);

  // Calculate normalized percentage
  const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
  const thresholdPercentage = (threshold / maxValue) * 100;

  // Animation logic
  useEffect(() => {
    if (!animate) {
      currentValueRef.current = percentage;
      renderMeter();
      return;
    }

    startTimeRef.current = performance.now();
    currentValueRef.current = currentValueRef.current || 0;

    const animateToValue = (timestamp: number) => {
      // Calculate progress based on time elapsed
      const elapsed = timestamp - startTimeRef.current;
      const duration = 1000; // 1 second animation
      const progress = Math.min(1, elapsed / duration);

      // Ease out cubic: progress = 1 - Math.pow(1 - progress, 3)
      const easedProgress = 1 - Math.pow(1 - progress, 3);

      // Calculate new value
      const oldValue = currentValueRef.current;
      const newValue = oldValue + (percentage - oldValue) * easedProgress;
      currentValueRef.current = newValue;

      // Render meter
      renderMeter();

      // Continue animation if not complete
      if (progress < 1) {
        requestRef.current = requestAnimationFrame(animateToValue);
      }
    };

    // Start animation
    requestRef.current = requestAnimationFrame(animateToValue);

    // Cleanup
    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, [percentage, animate]);

  // Canvas rendering function
  const renderMeter = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw background
    ctx.fillStyle = '#1E293B'; // Slate-800
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, width * 0.45, 0, Math.PI * 2);
    ctx.fill();

    // Draw threshold marker
    const thresholdAngle = (thresholdPercentage / 100) * Math.PI * 2 - Math.PI / 2;
    ctx.strokeStyle = '#FBBF24'; // Amber-400
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, width * 0.42, -Math.PI / 2, thresholdAngle);
    ctx.stroke();

    // Draw progress arc
    const angle = (currentValueRef.current / 100) * Math.PI * 2 - Math.PI / 2;

    // Determine color based on progress
    let progressColor;
    if (currentValueRef.current < 30) {
      progressColor = '#EF4444'; // Red-500
    } else if (currentValueRef.current < thresholdPercentage) {
      progressColor = '#F59E0B'; // Amber-500
    } else {
      progressColor = '#10B981'; // Emerald-500
    }

    ctx.strokeStyle = progressColor;
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, width * 0.35, -Math.PI / 2, angle);
    ctx.stroke();

    // Draw center text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 24px Inter, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${Math.round(currentValueRef.current)}%`, width / 2, height / 2);

    // Draw label
    ctx.font = '14px Inter, Arial, sans-serif';
    ctx.fillText('Confidence', width / 2, height / 2 + 24);
  };

  return (
    <div className={`confidence-meter relative ${className}`}>
      <div className="meter-container flex flex-col items-center">
        <canvas
          ref={canvasRef}
          width={200}
          height={200}
          className="meter-canvas"
        />
        <div className="meter-status text-sm mt-1">
          {percentage < 30 && (
            <span className="text-red-400">Low Confidence</span>
          )}
          {percentage >= 30 && percentage < thresholdPercentage && (
            <span className="text-yellow-400">Building Confidence</span>
          )}
          {percentage >= thresholdPercentage && (
            <span className="text-green-400">Sufficient Confidence</span>
          )}
        </div>
        <div className="meter-help text-xs text-gray-400 mt-1">
          {percentage < thresholdPercentage ? (
            `${Math.ceil(threshold - value)} more points needed for rectification`
          ) : (
            'Ready for rectification'
          )}
        </div>
      </div>
    </div>
  );
};

export default ConfidenceMeter;
