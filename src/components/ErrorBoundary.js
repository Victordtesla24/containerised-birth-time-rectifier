import React from 'react';

/**
 * ErrorBoundary component to catch JavaScript errors anywhere in the child component tree
 * and display a fallback UI instead of crashing the whole app
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to an error reporting service
    console.error('ErrorBoundary caught error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      // Render fallback UI
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p className="error-message">
            {this.state.error && this.state.error.toString()}
          </p>
          <button onClick={() => window.location.reload()} className="retry-button">
            Reload Page
          </button>

          <style jsx>{`
            .error-boundary {
              position: relative;
              padding: 20px;
              margin: 20px 0;
              text-align: center;
              background: rgba(15, 23, 42, 0.7);
              border-radius: 8px;
              color: white;
              max-width: 800px;
              margin: 0 auto;
            }

            h2 {
              color: #ef4444;
              margin-bottom: 15px;
            }

            .error-message {
              color: #f1f5f9;
              margin-bottom: 20px;
              font-family: monospace;
              overflow-wrap: break-word;
            }

            .retry-button {
              padding: 10px 20px;
              background: #3b82f6;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              transition: background 0.3s;
            }

            .retry-button:hover {
              background: #2563eb;
            }
          `}</style>
        </div>
      );
    }

    // Return children if there's no error
    return this.props.children;
  }
}

export default ErrorBoundary;
