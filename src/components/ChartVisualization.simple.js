// Simplified ChartVisualization component for Vercel deployment
// This version doesn't import CSS directly to avoid Next.js global CSS import errors

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';

const ChartVisualization = ({ chartData, onComplete }) => {
  const [loading, setLoading] = useState(true);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartData && chartRef.current) {
      // Simulate chart rendering
      const timer = setTimeout(() => {
        setLoading(false);
        if (onComplete) onComplete();
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [chartData, onComplete]);

  // Inline styles instead of importing CSS
  const styles = {
    container: {
      position: 'relative',
      width: '100%',
      height: '500px',
      background: 'linear-gradient(to bottom, #000830 0%, #000010 100%)',
      borderRadius: '10px',
      overflow: 'hidden',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      margin: '20px 0',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    },
    loadingText: {
      color: '#ffffff',
      fontSize: '18px',
      textAlign: 'center',
    },
    chart: {
      width: '100%',
      height: '100%',
      display: loading ? 'none' : 'block',
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
      style={styles.container}
    >
      {loading ? (
        <div style={styles.loadingText}>
          Rendering celestial chart...
        </div>
      ) : (
        <div ref={chartRef} style={styles.chart}>
          {chartData && (
            <div className="chart-data">
              <h3>Birth Chart Ready</h3>
              <p>Your celestial chart has been successfully rendered.</p>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};

export default ChartVisualization;
