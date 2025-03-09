import React, { useState, useEffect } from 'react';

/**
 * Enhanced error message component with better visibility and user interaction
 *
 * Features:
 * - Auto-dismissal option
 * - Different severity levels (error, warning, info)
 * - Custom action buttons
 * - Animated entry/exit
 */
const ErrorMessage = ({
  message,
  severity = 'error',
  onDismiss,
  autoDismiss = false,
  dismissTimeout = 5000,
  actions = []
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  // Auto-dismiss functionality
  useEffect(() => {
    if (autoDismiss && onDismiss) {
      const timer = setTimeout(() => {
        setIsExiting(true);
        setTimeout(() => {
          setIsVisible(false);
          onDismiss();
        }, 300); // Animation duration
      }, dismissTimeout);

      return () => clearTimeout(timer);
    }
  }, [autoDismiss, dismissTimeout, onDismiss]);

  // Handle manual dismissal
  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      setIsVisible(false);
      if (onDismiss) onDismiss();
    }, 300); // Animation duration
  };

  // Only render if visible
  if (!isVisible) return null;

  // Determine background and icon based on severity
  let backgroundColor, icon, borderColor;

  switch (severity) {
    case 'warning':
      backgroundColor = 'rgba(255, 193, 7, 0.1)';
      borderColor = '#ffc107';
      icon = '⚠️';
      break;
    case 'info':
      backgroundColor = 'rgba(33, 150, 243, 0.1)';
      borderColor = '#2196f3';
      icon = 'ℹ️';
      break;
    case 'success':
      backgroundColor = 'rgba(76, 175, 80, 0.1)';
      borderColor = '#4caf50';
      icon = '✅';
      break;
    case 'error':
    default:
      backgroundColor = 'rgba(244, 67, 54, 0.1)';
      borderColor = '#f44336';
      icon = '❌';
      break;
  }

  return (
    <div
      className={`error-message ${severity} ${isExiting ? 'exiting' : ''}`}
      style={{
        backgroundColor,
        border: `1px solid ${borderColor}`,
        padding: '12px 16px',
        borderRadius: '4px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'flex-start',
        opacity: isExiting ? 0 : 1,
        transform: isExiting ? 'translateY(-10px)' : 'translateY(0)',
        transition: 'opacity 0.3s, transform 0.3s',
        position: 'relative',
        maxWidth: '100%',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
      }}
    >
      <div
        className="error-icon"
        style={{
          marginRight: '12px',
          fontSize: '18px',
          lineHeight: '24px'
        }}
      >
        {icon}
      </div>
      <div
        className="error-content"
        style={{
          flex: 1,
          margin: '0 16px 0 0'
        }}
      >
        <div
          className="error-message-text"
          style={{
            color: '#ffffff',
            marginBottom: actions.length > 0 ? '8px' : '0'
          }}
        >
          {message}
        </div>

        {actions.length > 0 && (
          <div
            className="error-actions"
            style={{
              display: 'flex',
              marginTop: '8px',
              gap: '8px'
            }}
          >
            {actions.map((action, index) => (
              <button
                key={index}
                onClick={action.onClick}
                style={{
                  backgroundColor: action.primary ? borderColor : 'transparent',
                  color: action.primary ? '#ffffff' : borderColor,
                  border: action.primary ? 'none' : `1px solid ${borderColor}`,
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 500
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {onDismiss && (
        <button
          className="dismiss-button"
          onClick={handleDismiss}
          aria-label="Dismiss"
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            position: 'absolute',
            top: '8px',
            right: '8px',
            padding: '4px',
            color: '#ffffff',
            opacity: 0.7,
            fontSize: '18px',
            lineHeight: 1
          }}
        >
          ×
        </button>
      )}

      <style jsx>{`
        .error-message {
          animation: slideIn 0.3s forwards;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .dismiss-button:hover {
          opacity: 1;
        }
      `}</style>
    </div>
  );
};

export default ErrorMessage;
