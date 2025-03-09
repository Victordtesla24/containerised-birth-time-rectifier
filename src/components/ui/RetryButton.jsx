import React from 'react';

/**
 * RetryButton component for error recovery and retrying operations
 *
 * Features:
 * - Visual feedback when clicked
 * - Customizable text and styling
 * - Optional loading state
 */
const RetryButton = ({
  onClick,
  text = 'Retry',
  loading = false,
  variant = 'primary',
  size = 'medium',
  icon = true
}) => {
  // Size presets
  const sizeClasses = {
    small: { padding: '6px 12px', fontSize: '0.875rem' },
    medium: { padding: '10px 20px', fontSize: '1rem' },
    large: { padding: '12px 24px', fontSize: '1.125rem' }
  };

  // Get size values
  const sizeStyle = sizeClasses[size] || sizeClasses.medium;

  // Variant styles
  const getVariantStyle = () => {
    switch (variant) {
      case 'outline':
        return {
          background: 'transparent',
          color: '#3b82f6',
          border: '1px solid #3b82f6',
          boxShadow: 'none'
        };
      case 'text':
        return {
          background: 'transparent',
          color: '#3b82f6',
          border: 'none',
          boxShadow: 'none'
        };
      case 'secondary':
        return {
          background: '#1e293b',
          color: '#e2e8f0',
          border: '1px solid rgba(148, 163, 184, 0.2)',
          boxShadow: '0 2px 5px rgba(0, 0, 0, 0.1)'
        };
      case 'primary':
      default:
        return {
          background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
          color: 'white',
          border: 'none',
          boxShadow: '0 4px 15px rgba(59, 130, 246, 0.3)'
        };
    }
  };

  // Combined styles
  const buttonStyle = {
    ...sizeStyle,
    ...getVariantStyle(),
    borderRadius: '8px',
    fontWeight: 'bold',
    cursor: loading ? 'wait' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'all 0.2s ease',
    opacity: loading ? 0.8 : 1
  };

  // Hover styles handled with CSS in the style tag

  return (
    <button
      className={`retry-button ${variant} ${size}`}
      onClick={loading ? null : onClick}
      style={buttonStyle}
      disabled={loading}
    >
      {icon && (
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`retry-icon ${loading ? 'spinning' : ''}`}
        >
          <path
            d="M13.65 2.35C12.2 0.9 10.21 0 8 0C3.58 0 0.01 3.58 0.01 8C0.01 12.42 3.58 16 8 16C11.73 16 14.84 13.45 15.73 10H13.65C12.83 12.33 10.61 14 8 14C4.69 14 2 11.31 2 8C2 4.69 4.69 2 8 2C9.66 2 11.14 2.69 12.22 3.78L9 7H16V0L13.65 2.35Z"
            fill={buttonStyle.color}
          />
        </svg>
      )}
      {text}

      <style jsx>{`
        .retry-button:hover:not(:disabled) {
          transform: translateY(-2px);
        }

        .retry-button.primary:hover:not(:disabled) {
          box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
        }

        .retry-button.secondary:hover:not(:disabled) {
          background: #293548;
        }

        .retry-button.outline:hover:not(:disabled),
        .retry-button.text:hover:not(:disabled) {
          background: rgba(59, 130, 246, 0.1);
        }

        .retry-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .retry-icon {
          transition: transform 0.2s ease;
        }

        .retry-button:hover .retry-icon:not(.spinning) {
          transform: rotate(45deg);
        }

        .spinning {
          animation: spin 1.5s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  );
};

export default RetryButton;
