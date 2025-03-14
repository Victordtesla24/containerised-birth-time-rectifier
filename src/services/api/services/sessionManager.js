/**
 * Session Manager Service
 *
 * This module provides advanced session management functionality beyond the basic
 * session API service. It handles session initialization, persistence, and validation
 * as specified in the sequence diagram.
 */

import apiClient from '../client';
import endpoints from '../endpoints';
import { sessionService } from './session';

/**
 * Time intervals for session operations in milliseconds
 */
const SESSION_INTERVALS = {
  CHECK_INTERVAL: 5 * 60 * 1000, // 5 minutes
  EXPIRATION_WARNING: 2 * 60 * 1000, // 2 minutes before expiration
  REFRESH_THRESHOLD: 15 * 60 * 1000, // 15 minutes before expiration
};

class SessionManager {
  constructor() {
    this.sessionId = null;
    this.sessionExpires = null;
    this.sessionCheckInterval = null;
    this.sessionListeners = [];
    this.initialized = false;
  }

  /**
   * Initialize the session manager
   * This will either create a new session or validate/refresh an existing one
   *
   * @returns {Promise<{initialized: boolean, session?: object, error?: Error}>}
   */
  async initialize() {
    try {
      // Check if we already have a session in localStorage
      const existingSessionId = sessionService.getSessionId();

      if (existingSessionId) {
        // Validate the existing session
        const status = await this.checkSessionStatus();
        if (status.active) {
          this.sessionId = existingSessionId;
          this.sessionExpires = new Date(status.expires_at * 1000);
          this.startSessionMonitoring();
          this.initialized = true;
          return { initialized: true, session: { id: this.sessionId, expires: this.sessionExpires } };
        }
      }

      // Create a new session if no valid session exists
      const sessionData = await sessionService.initSession();

      this.sessionId = sessionData.session_id;
      this.sessionExpires = new Date(sessionData.expires_at * 1000);
      this.startSessionMonitoring();
      this.initialized = true;

      return { initialized: true, session: { id: this.sessionId, expires: this.sessionExpires } };
    } catch (error) {
      console.error('Session initialization failed:', error);

      // Create a fallback local session if API fails
      if (process.env.NODE_ENV !== 'production') {
        const fallbackSession = this.createFallbackSession();
        return { initialized: true, session: fallbackSession, error };
      }

      return { initialized: false, error };
    }
  }

  /**
   * Check the current session status
   *
   * @returns {Promise<{active: boolean, expires_at: number}>}
   */
  async checkSessionStatus() {
    try {
      const status = await sessionService.checkStatus();
      return status;
    } catch (error) {
      console.warn('Session status check failed:', error);

      // Fall back to checking local expiration time
      if (this.sessionExpires) {
        return {
          active: new Date() < this.sessionExpires,
          expires_at: Math.floor(this.sessionExpires.getTime() / 1000)
        };
      }

      return { active: false, expires_at: 0 };
    }
  }

  /**
   * Start the session monitoring process
   * This will periodically check the session status and refresh if needed
   */
  startSessionMonitoring() {
    // Clear any existing interval
    if (this.sessionCheckInterval) {
      clearInterval(this.sessionCheckInterval);
    }

    // Set up periodic session check
    this.sessionCheckInterval = setInterval(async () => {
      try {
        const status = await this.checkSessionStatus();

        if (!status.active) {
          // Session expired, need to reinitialize
          this.handleSessionExpiration();
          return;
        }

        const currentTime = new Date();
        const expirationTime = new Date(status.expires_at * 1000);
        const timeUntilExpiration = expirationTime.getTime() - currentTime.getTime();

        // If session is close to expiring, refresh it
        if (timeUntilExpiration < SESSION_INTERVALS.REFRESH_THRESHOLD) {
          await this.refreshSession();
        }

        // If approaching expiration, notify listeners
        if (timeUntilExpiration < SESSION_INTERVALS.EXPIRATION_WARNING) {
          this.notifySessionExpiring(timeUntilExpiration);
        }
      } catch (error) {
        console.error('Session monitoring error:', error);
      }
    }, SESSION_INTERVALS.CHECK_INTERVAL);
  }

  /**
   * Refresh the current session
   *
   * @returns {Promise<boolean>} Success status
   */
  async refreshSession() {
    try {
      // Create a new session
      const sessionData = await sessionService.initSession();

      this.sessionId = sessionData.session_id;
      this.sessionExpires = new Date(sessionData.expires_at * 1000);

      this.notifySessionRefreshed();
      return true;
    } catch (error) {
      console.error('Session refresh failed:', error);
      return false;
    }
  }

  /**
   * Handle a session expiration event
   */
  handleSessionExpiration() {
    // Clear session data
    this.sessionId = null;
    this.sessionExpires = null;

    // Clear localStorage
    sessionService.clearSession();

    // Notify listeners
    this.notifySessionExpired();

    // Attempt to initialize a new session
    this.initialize().catch(console.error);
  }

  /**
   * Create a fallback local session when API is unavailable
   * Only used in development/test environments
   *
   * @returns {object} Fallback session data
   */
  createFallbackSession() {
    const sessionId = `local_${Date.now()}`;
    const expires = new Date(Date.now() + (3600 * 1000)); // 1 hour

    // Store in localStorage to persist across page reloads
    localStorage.setItem('sessionId', sessionId);

    this.sessionId = sessionId;
    this.sessionExpires = expires;

    return {
      id: sessionId,
      expires: expires
    };
  }

  /**
   * Add a session event listener
   *
   * @param {function} listener - Function to call on session events
   * @returns {function} Function to remove the listener
   */
  addSessionListener(listener) {
    this.sessionListeners.push(listener);

    // Return function to remove the listener
    return () => {
      this.sessionListeners = this.sessionListeners.filter(l => l !== listener);
    };
  }

  /**
   * Notify listeners that the session is expiring soon
   *
   * @param {number} timeRemaining - Time until expiration in milliseconds
   */
  notifySessionExpiring(timeRemaining) {
    const minutesRemaining = Math.floor(timeRemaining / 60000);
    this.sessionListeners.forEach(listener => {
      listener({
        type: 'expiring',
        timeRemaining,
        minutesRemaining
      });
    });
  }

  /**
   * Notify listeners that the session has expired
   */
  notifySessionExpired() {
    this.sessionListeners.forEach(listener => {
      listener({
        type: 'expired'
      });
    });
  }

  /**
   * Notify listeners that the session has been refreshed
   */
  notifySessionRefreshed() {
    this.sessionListeners.forEach(listener => {
      listener({
        type: 'refreshed',
        sessionId: this.sessionId,
        expiresAt: this.sessionExpires
      });
    });
  }

  /**
   * Get the current session ID
   *
   * @returns {string|null} Current session ID or null if no session
   */
  getSessionId() {
    return this.sessionId;
  }

  /**
   * Check if the session manager is initialized
   *
   * @returns {boolean} Whether the session manager is initialized
   */
  isInitialized() {
    return this.initialized;
  }

  /**
   * End the current session
   *
   * @returns {Promise<void>}
   */
  async endSession() {
    // Clear interval
    if (this.sessionCheckInterval) {
      clearInterval(this.sessionCheckInterval);
      this.sessionCheckInterval = null;
    }

    // Clear session data
    this.sessionId = null;
    this.sessionExpires = null;
    this.initialized = false;

    // Clear localStorage
    sessionService.clearSession();
  }
}

// Create and export a singleton instance
const sessionManager = new SessionManager();
export default sessionManager;
