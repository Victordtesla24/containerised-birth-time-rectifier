import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface SessionContextValue {
  sessionId: string;
  isInitialized: boolean;
  initializeSession: () => Promise<void>;
}

// Create context with default values
const SessionContext = createContext<SessionContextValue>({
  sessionId: '',
  isInitialized: false,
  initializeSession: async () => {},
});

// Custom hook for using the session context
export const useSession = () => useContext(SessionContext);

interface SessionProviderProps {
  children: ReactNode;
}

export const SessionProvider: React.FC<SessionProviderProps> = ({ children }) => {
  const [sessionId, setSessionId] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState<boolean>(false);

  // Load session from localStorage on initial render
  useEffect(() => {
    const storedSession = localStorage.getItem('birthTimeRectifierSession');
    if (storedSession) {
      try {
        const { sessionId, expiresAt } = JSON.parse(storedSession);

        // Check if session is still valid
        const now = Math.floor(Date.now() / 1000);
        if (expiresAt && expiresAt > now) {
          setSessionId(sessionId);
          setIsInitialized(true);
        } else {
          // Session expired, clear it
          localStorage.removeItem('birthTimeRectifierSession');
        }
      } catch (error) {
        console.error('Failed to parse stored session', error);
        localStorage.removeItem('birthTimeRectifierSession');
      }
    }
  }, []);

  // Initialize a new session
  const initializeSession = async () => {
    try {
      const response = await fetch('/api/v1/session/init', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to initialize session');
      }

      const data = await response.json();

      // Store session in localStorage with expiration
      localStorage.setItem(
        'birthTimeRectifierSession',
        JSON.stringify({
          sessionId: data.session_id,
          expiresAt: data.expires_at,
        })
      );

      setSessionId(data.session_id);
      setIsInitialized(true);
    } catch (error) {
      console.error('Error initializing session:', error);
    }
  };

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        isInitialized,
        initializeSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export default SessionProvider;
