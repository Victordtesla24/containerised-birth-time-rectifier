/**
 * WebSocket Client
 *
 * This utility provides a WebSocket client for real-time communication with the backend.
 * It handles connection management, reconnection, and message handling.
 */

import { logger } from './logger';
import unifiedApiClient from './unifiedApiClient';
import pythonApiAdapter from './pythonApiAdapter';

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.messageHandlers = new Map();
    this.connectionInfo = null;
  }

  /**
   * Get WebSocket connection details from the backend
   * @returns {Promise<Object>} Connection details including URL and any auth tokens
   */
  async getConnectionInfo() {
    try {
      // Try to get connection info from the realtime service
      const response = await pythonApiAdapter.realtimeService.getWebSocketDetails();
      this.connectionInfo = response;
      return response;
    } catch (error) {
      logger.error('Failed to get WebSocket connection details:', error);
      // Fallback to default connection info
      this.connectionInfo = {
        url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
        protocols: ['birth-time-rectifier'],
      };
      return this.connectionInfo;
    }
  }

  /**
   * Connect to the WebSocket server
   * @returns {Promise<boolean>} True if connection was successful
   */
  async connect() {
    if (this.isConnected) {
      logger.info('WebSocket already connected');
      return true;
    }

    try {
      // Get connection info if we don't have it yet
      if (!this.connectionInfo) {
        await this.getConnectionInfo();
      }

      return new Promise((resolve, reject) => {
        // Create WebSocket connection
        this.socket = new WebSocket(
          this.connectionInfo.url,
          this.connectionInfo.protocols || []
        );

        // Setup event handlers
        this.socket.onopen = () => {
          logger.info('WebSocket connection established');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve(true);
        };

        this.socket.onclose = (event) => {
          logger.warn(`WebSocket connection closed: ${event.code} ${event.reason}`);
          this.isConnected = false;
          this._handleDisconnect();
        };

        this.socket.onerror = (error) => {
          logger.error('WebSocket error:', error);
          if (!this.isConnected) {
            reject(error);
          }
        };

        this.socket.onmessage = (event) => {
          this._handleMessage(event);
        };

        // Set connection timeout
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);
      });
    } catch (error) {
      logger.error('Error connecting to WebSocket:', error);
      return false;
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket && this.isConnected) {
      logger.info('Closing WebSocket connection');
      this.socket.close(1000, 'Client disconnecting');
      this.isConnected = false;
      this.socket = null;
    }
  }

  /**
   * Send a message to the WebSocket server
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @returns {boolean} True if message was sent
   */
  send(type, data) {
    if (!this.isConnected || !this.socket) {
      logger.warn('Cannot send message: WebSocket not connected');
      return false;
    }

    try {
      const message = JSON.stringify({
        type,
        data,
        timestamp: new Date().toISOString(),
      });

      this.socket.send(message);
      return true;
    } catch (error) {
      logger.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  /**
   * Register a handler for a specific message type
   * @param {string} type - Message type to handle
   * @param {Function} handler - Handler function that receives the message data
   */
  on(type, handler) {
    if (typeof handler !== 'function') {
      throw new Error('Handler must be a function');
    }

    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }

    this.messageHandlers.get(type).push(handler);
    logger.debug(`Registered handler for message type: ${type}`);
  }

  /**
   * Remove a handler for a specific message type
   * @param {string} type - Message type
   * @param {Function} handler - Handler function to remove
   */
  off(type, handler) {
    if (!this.messageHandlers.has(type)) {
      return;
    }

    const handlers = this.messageHandlers.get(type);
    const index = handlers.indexOf(handler);

    if (index !== -1) {
      handlers.splice(index, 1);
      logger.debug(`Removed handler for message type: ${type}`);
    }

    if (handlers.length === 0) {
      this.messageHandlers.delete(type);
    }
  }

  /**
   * Handle an incoming message
   * @private
   * @param {MessageEvent} event - WebSocket message event
   */
  _handleMessage(event) {
    try {
      const message = JSON.parse(event.data);

      logger.debug(`Received WebSocket message of type: ${message.type}`);

      // Call registered handlers for this message type
      if (this.messageHandlers.has(message.type)) {
        const handlers = this.messageHandlers.get(message.type);
        handlers.forEach(handler => {
          try {
            handler(message.data);
          } catch (error) {
            logger.error(`Error in WebSocket message handler for type ${message.type}:`, error);
          }
        });
      }

      // Call handlers for 'any' message type
      if (this.messageHandlers.has('any')) {
        const handlers = this.messageHandlers.get('any');
        handlers.forEach(handler => {
          try {
            handler(message);
          } catch (error) {
            logger.error('Error in WebSocket "any" message handler:', error);
          }
        });
      }
    } catch (error) {
      logger.error('Error processing WebSocket message:', error, event.data);
    }
  }

  /**
   * Handle disconnection and reconnection
   * @private
   */
  _handleDisconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;

      // Exponential backoff
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      logger.info(`Attempting to reconnect WebSocket in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connect().catch(error => {
          logger.error('WebSocket reconnection failed:', error);
        });
      }, delay);
    } else {
      logger.error(`WebSocket reconnection failed after ${this.maxReconnectAttempts} attempts`);
    }
  }
}

// Create a singleton instance
const websocketClient = new WebSocketClient();

export default websocketClient;
