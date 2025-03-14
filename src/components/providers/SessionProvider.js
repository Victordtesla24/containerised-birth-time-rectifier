import React, { createContext, useContext, useState, useEffect } from 'react';
import sessionClient from '../../services/api/sessionClient';

// Create a context to manage session state
const SessionContext = createContext();

/**
 * SessionProvider component that initializes and manages the application session.
 * Provides session state to all child components.
 */
export function SessionProvider({ children }) {
  const [sessionState, setSessionState] = useState({
    initialized: false,
    initializing: true,
    error: null,
    sessionId: null,
    expiresAt: null,
  });

  // Function to initialize the session
  const initializeSession = async () => {
    try {
      console.log('Initializing session...');
      setSessionState(prev => ({ ...prev, initializing: true, error: null }));

      const sessionData = await sessionClient.initializeSession();
      console.log('Session initialized:', sessionData);

      setSessionState({
        initialized: true,
        initializing: false,
        error: null,
        sessionId: sessionData?.session_id || null,
        expiresAt: sessionData?.expires_at || null,
      });

      return true;
    } catch (error) {
      console.error('Session initialization error:', error);

      // Handle real errors
      setSessionState({
        initialized: false,
        initializing: false,
        error: error.message || 'Failed to initialize session',
        sessionId: null,
        expiresAt: null,
      });

      return false;
    }
  };

  // Initialize session on component mount
  useEffect(() => {
    initializeSession();

    // Clean up session on unmount
    return () => {
      // We don't actually clean up the session when component unmounts
      // as the session should persist across page navigations
    };
  }, []);

  // Create the value object with session state and functions
  const contextValue = {
    ...sessionState,
    initializeSession,
  };

  return (
    <SessionContext.Provider value={contextValue}>
      {sessionState.initializing ? (
        // You can add a loading indicator here if needed
        children
      ) : sessionState.error && !sessionState.initialized ? (
        <div className="session-error">
          <div className="error-container">
            <h3>Connection Error</h3>
            <p>We're having trouble connecting to our servers. Please try again later.</p>
            <p className="error-details">{sessionState.error}</p>
            <button onClick={initializeSession} className="retry-button">
              Retry Connection
            </button>
          </div>
          <style jsx>{`
            .session-error {
              position: fixed;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              display: flex;
              justify-content: center;
              align-items: center;
              background: rgba(0, 0, 0, 0.8);
              z-index: 1000;
            }
            .error-container {
              background: #1a1a2e;
              border: 1px solid #3a3a5a;
              border-radius: 8px;
              padding: 20px;
              max-width: 400px;
              text-align: center;
              color: white;
            }
            h3 {
              color: #ff6b6b;
              margin-top: 0;
            }
            .error-details {
              color: #aaa;
              font-size: 0.8rem;
              margin-top: 15px;
            }
            .retry-button {
              background: #4361ee;
              color: white;
              border: none;
              padding: 10px 20px;
              border-radius: 4px;
              margin-top: 15px;
              cursor: pointer;
              transition: background 0.3s;
            }
            .retry-button:hover {
              background: #3a56d4;
            }
          `}</style>
        </div>
      ) : (
        children
      )}
    </SessionContext.Provider>
  );
}

// Custom hook to use the session context
export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
