import React from 'react';
import { motion } from 'framer-motion';

interface ConfidenceMeterProps {
  value: number;
  label?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
}

const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  value,
  label,
  description,
  size = 'md',
  showValue = true
}) => {
  // Ensure value is between 0 and 100
  const safeValue = Math.min(100, Math.max(0, value));
  
  // Map confidence level to color
  const getColor = (val: number) => {
    if (val >= 90) return 'text-emerald-400';
    if (val >= 75) return 'text-blue-400';
    if (val >= 60) return 'text-yellow-400';
    if (val >= 40) return 'text-orange-400';
    return 'text-red-400';
  };
  
  // Size classes
  const sizeClasses = {
    sm: 'w-20 h-20',
    md: 'w-28 h-28',
    lg: 'w-36 h-36'
  };
  
  // Font size classes
  const fontSizeClasses = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl'
  };
  
  return (
    <div className="flex flex-col items-center">
      <motion.div 
        className={`relative ${sizeClasses[size]} rounded-full bg-blue-950/70 border-4 border-blue-900/50 flex items-center justify-center`}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Background circle */}
        <svg className="absolute inset-0 w-full h-full">
          <circle
            cx="50%"
            cy="50%"
            r="45%"
            fill="none"
            stroke="rgba(30, 58, 138, 0.4)"
            strokeWidth="8%"
            strokeLinecap="round"
          />
        </svg>
        
        {/* Foreground progress circle */}
        <svg className="absolute inset-0 w-full h-full -rotate-90">
          <motion.circle
            cx="50%"
            cy="50%"
            r="45%"
            fill="none"
            stroke="url(#confidence-gradient)"
            strokeWidth="8%"
            strokeLinecap="round"
            initial={{ strokeDasharray: '100 100' }}
            animate={{ 
              strokeDasharray: `${safeValue} 100`,
              transition: { duration: 1.5, ease: 'easeOut' }
            }}
          />
          
          {/* Gradient definition */}
          <defs>
            <linearGradient id="confidence-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
          </defs>
        </svg>
        
        {/* Value text */}
        {showValue && (
          <motion.div 
            className="text-center z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            <span className={`${fontSizeClasses[size]} font-bold ${getColor(safeValue)}`}>
              {Math.round(safeValue)}%
            </span>
          </motion.div>
        )}
      </motion.div>
      
      {/* Label below */}
      {label && (
        <motion.div 
          className="mt-2 text-center"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <p className="text-blue-200 font-medium">{label}</p>
          {description && <p className="text-blue-300 text-sm mt-1">{description}</p>}
        </motion.div>
      )}
    </div>
  );
};

export default ConfidenceMeter; 