import React, { Component, ErrorInfo, ReactNode } from 'react';
import RetryButton from './ui/RetryButton';

// Add type declaration for Google Analytics
declare global {
  interface Window {
    gtag?: (command: string, action: string, params?: any) => void;
  }
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Global Error Boundary component to catch and handle errors in the React component tree
 *
 * Features:
 * - Prevents app crashes by catching JavaScript errors anywhere in the component tree
 * - Provides custom fallback UI
 * - Reports errors to error monitoring service
 * - Offers retry options for recovery
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to an error reporting service
    console.error('Error caught by ErrorBoundary:', error, errorInfo);

    // Update state with error info
    this.setState({
      errorInfo
    });

    // Call onError handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Optional: Send error to monitoring service
    // If analytics is set up, we could add that logic here
    if (window.gtag) {
      try {
        window.gtag('event', 'error', {
          'event_category': 'error_boundary',
          'event_label': error.toString(),
          'value': 1
        });
      } catch (e) {
        console.error('Failed to report error to analytics', e);
      }
    }
  }

  handleRetry = (): void => {
    // Reset the error state
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReload = (): void => {
    // Force page reload
    window.location.reload();
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Use custom fallback if provided, otherwise show default error UI
      if (fallback) {
        return fallback;
      }

      // Default error UI with recovery options
      return (
        <div
          style={{
            padding: '20px',
            margin: '20px',
            borderRadius: '8px',
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            color: 'white',
            textAlign: 'center',
            maxWidth: '600px',
            marginLeft: 'auto',
            marginRight: 'auto',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(96, 165, 250, 0.2)'
          }}
        >
          <h2 style={{ color: '#f87171', marginBottom: '20px' }}>
            Something went wrong
          </h2>

          <p style={{ marginBottom: '15px', color: '#e2e8f0' }}>
            We've encountered an unexpected error.
          </p>

          {error && (
            <div
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                padding: '10px',
                borderRadius: '4px',
                marginBottom: '20px',
                fontFamily: 'monospace',
                textAlign: 'left',
                overflowX: 'auto'
              }}
            >
              <p style={{ color: '#f87171' }}>{error.toString()}</p>
            </div>
          )}

          <div
            style={{
              display: 'flex',
              gap: '16px',
              justifyContent: 'center',
              marginTop: '20px'
            }}
          >
            <RetryButton
              onClick={this.handleRetry}
              text="Try Recovery"
              variant="primary"
              icon={true}
            />

            <RetryButton
              onClick={this.handleReload}
              text="Refresh Page"
              variant="secondary"
              icon={false}
            />
          </div>
        </div>
      );
    }

    // When there's no error, render children normally
    return children;
  }
}

export default ErrorBoundary;
