/**
 * Session Service
 *
 * Handles API calls related to session management. This service implements the
 * /api/session/init endpoint as described in the sequence diagram.
 */

import apiClient from '../client';
import endpoints from '../endpoints';

/**
 * Session service for creating, checking, and managing user sessions
 */
class SessionService {
  /**
   * Initialize a new session
   *
   * @returns {Promise<{session_id: string, created_at: number, expires_at: number, status: string}>}
   */
  async initSession() {
    try {
      // Attempt to initialize via API
      const response = await apiClient.get(endpoints.SESSION.INIT);

      // Store session ID in localStorage
      if (response && response.data && response.data.session_id) {
        localStorage.setItem('sessionId', response.data.session_id);
        return response.data;
      }

      throw new Error('Invalid session response format');
    } catch (error) {
      console.warn('Could not initialize session via API:', error);

      // Create a mock session if in development
      if (process.env.NODE_ENV !== 'production') {
        console.log('Creating mock session for development environment');
        const mockSession = this._createMockSession();
        localStorage.setItem('sessionId', mockSession.session_id);
        return mockSession;
      }

      throw error;
    }
  }

  /**
   * Check status of an existing session
   *
   * @param {string} sessionId - Optional session ID (will use stored one if not provided)
   * @returns {Promise<{active: boolean, expires_at: number}>}
   */
  async checkStatus(sessionId = null) {
    const sid = sessionId || this.getSessionId();

    if (!sid) {
      return { active: false, expires_at: 0 };
    }

    try {
      const response = await apiClient.get(endpoints.SESSION.STATUS, {
        params: { session_id: sid }
      });

      return response.data;
    } catch (error) {
      console.warn('Session status check failed:', error);

      // For development environment, create mock response
      if (process.env.NODE_ENV !== 'production') {
        // Simple check - if session ID exists in localStorage, consider it active
        return {
          active: true,
          expires_at: Math.floor(Date.now() / 1000) + 3600 // 1 hour from now
        };
      }

      return { active: false, expires_at: 0 };
    }
  }

  /**
   * Refresh an existing session
   *
   * @param {string} sessionId - Optional session ID (will use stored one if not provided)
   * @returns {Promise<{session_id: string, created_at: number, expires_at: number, status: string}>}
   */
  async refreshSession(sessionId = null) {
    const sid = sessionId || this.getSessionId();

    try {
      const response = await apiClient.post(endpoints.SESSION.REFRESH, {
        session_id: sid
      });

      // Update session ID in localStorage if it changed
      if (response && response.data && response.data.session_id) {
        localStorage.setItem('sessionId', response.data.session_id);
        return response.data;
      }

      throw new Error('Invalid session refresh response format');
    } catch (error) {
      console.warn('Session refresh failed:', error);

      // For development, just create a new session
      if (process.env.NODE_ENV !== 'production') {
        return this.initSession();
      }

      throw error;
    }
  }

  /**
   * End the current session
   *
   * @param {string} sessionId - Optional session ID (will use stored one if not provided)
   * @returns {Promise<{success: boolean}>}
   */
  async endSession(sessionId = null) {
    const sid = sessionId || this.getSessionId();

    if (!sid) {
      return { success: true };
    }

    try {
      const response = await apiClient.post(endpoints.SESSION.END, {
        session_id: sid
      });

      // Remove from localStorage
      localStorage.removeItem('sessionId');

      return response.data || { success: true };
    } catch (error) {
      console.warn('Session end failed:', error);

      // For development, just remove from localStorage
      if (process.env.NODE_ENV !== 'production') {
        localStorage.removeItem('sessionId');
        return { success: true };
      }

      throw error;
    }
  }

  /**
   * Get the session ID from localStorage
   *
   * @returns {string|null} The session ID or null if not found
   */
  getSessionId() {
    return localStorage.getItem('sessionId');
  }

  /**
   * Clear the session data from localStorage
   */
  clearSession() {
    localStorage.removeItem('sessionId');
  }

  /**
   * Create a mock session for development/testing
   *
   * @returns {{session_id: string, created_at: number, expires_at: number, status: string}}
   * @private
   */
  _createMockSession() {
    const now = Math.floor(Date.now() / 1000);
    return {
      session_id: `session_${now}`,
      created_at: now,
      expires_at: now + 3600, // 1 hour from now
      status: 'active'
    };
  }
}

// Create and export the service instance
export const sessionService = new SessionService();
