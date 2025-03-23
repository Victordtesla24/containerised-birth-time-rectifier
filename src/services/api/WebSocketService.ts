import { EventEmitter } from 'events';
import { getBaseWebSocketUrl } from '@/services/api/config';

interface WebSocketMessage {
  type: string;
  message?: string;
  data?: any;
  timestamp?: number;
  message_id?: string;
  session_id?: string;
  original_message_id?: string;
}

interface ReconnectionState {
  token?: string;
  queue: WebSocketMessage[];
  lastEventTimestamp: number;
  clientInfo?: Record<string, any>;
  subscriptions: string[];
}

interface WebSocketConfig {
  url: string;
  sessionId: string;
  token?: string;
  clientId?: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  debug?: boolean;
  pingInterval?: number;
}

interface ConnectionStatus {
  connected: boolean;
  connecting: boolean;
  reconnecting: boolean;
  reconnectAttempt: number;
  lastError?: string;
  wasConnected: boolean;
  connectionStartTime?: number;
  lastMessageTime?: number;
}

export class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private pingIntervalId: number | null = null;
  private reconnectTimeoutId: number | null = null;
  private connectionStatus: ConnectionStatus = {
    connected: false,
    connecting: false,
    reconnecting: false,
    reconnectAttempt: 0,
    wasConnected: false
  };
  private messageQueue: any[] = [];
  private reconnectTimer: number | null = null;
  private connectionCheckerTimer: number | null = null;
  private sessionId: string;
  private eventEmitter = new EventEmitter();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10; // Increased max attempts
  private reconnectDelay = 1000; // Start with 1s delay
  private heartbeatInterval: any = null;
  private pingTimeoutTimer: any = null;
  private lastHeartbeatResponse = 0;
  private connectionActive = false;
  private baseUrl: string;
  private reconnectionState: ReconnectionState = {
    token: undefined,
    queue: [],
    lastEventTimestamp: 0,
    subscriptions: []
  };
  private connectionTimeout: number = 15000; // 15 seconds
  private connectionTimer: any = null;
  private pendingMessages = new Map<string, { message: WebSocketMessage, timestamp: number }>();
  private messageCounter = 0;

  constructor(sessionId: string, options: { autoConnect?: boolean, maxReconnectAttempts?: number } = {}) {
    super();
    this.sessionId = sessionId;
    this.baseUrl = getBaseWebSocketUrl();

    // Apply options
    if (options.maxReconnectAttempts) {
      this.maxReconnectAttempts = options.maxReconnectAttempts;
    }

    // Auto-connect by default unless explicitly disabled
    if (options.autoConnect !== false) {
      this.connect();
    }

    // Add unload handler to properly close connection
    window.addEventListener('beforeunload', () => this.disconnect());

    // Set default values
    this.config = {
      url: this.baseUrl,
      sessionId: this.sessionId,
      token: options.token || '',
      clientId: options.clientId || `client_${Date.now().toString(36)}`,
      autoReconnect: options.autoConnect !== false,
      reconnectInterval: options.reconnectInterval || 2000,
      maxReconnectAttempts: options.maxReconnectAttempts || 10,
      debug: options.debug || false,
      pingInterval: options.pingInterval || 30000
    };
  }

  /**
   * Establish WebSocket connection with reconnection logic
   */
  public connect(): Promise<boolean> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      this.log('WebSocket already connected or connecting');
      return Promise.resolve(this.connectionStatus.connected);
    }

    this.connectionStatus.connecting = true;
    this.connectionStatus.reconnecting = false;

    // Build the WebSocket URL with query parameters
    const wsUrl = this.buildWebSocketUrl();
    this.log(`Connecting to ${wsUrl}`);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);

        // Record connection start time
        this.connectionStatus.connectionStartTime = Date.now();

        // Connection opened
        this.ws.onopen = (event) => {
          this.connectionStatus.connected = true;
          this.connectionStatus.connecting = false;
          this.connectionStatus.reconnectAttempt = 0;
          this.connectionStatus.wasConnected = true;
          this.connectionStatus.lastMessageTime = Date.now();

          this.log('WebSocket connection established');
          this.emit('connected', { timestamp: Date.now() });

          // Process any queued messages
          this.processQueue();

          // Start ping interval
          this.startPingInterval();

          // Start connection checker
          this.startConnectionChecker();

          resolve(true);
        };

        // Listen for messages
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.connectionStatus.lastMessageTime = Date.now();

            // Special handling for system messages
            if (data.type === 'connection_status') {
              this.handleConnectionStatusMessage(data);
            } else if (data.type === 'ping') {
              this.handlePingMessage(data);
            } else if (data.type === 'error') {
              this.handleErrorMessage(data);
            } else {
              // Forward all other messages
              this.emit('message', data);

              // Also emit a specific event for the message type
              if (data.type) {
                this.emit(data.type, data);
              }

              // Special handling for event types
              if (data.type === 'event' && data.event_type) {
                this.emit(`event:${data.event_type}`, data);
              }
            }
          } catch (err) {
            this.log('Error parsing message', err);
            this.emit('error', {
              type: 'parse_error',
              message: 'Failed to parse message',
              original: event.data,
              error: err
            });
          }
        };

        // Connection closed
        this.ws.onclose = (event) => {
          const wasConnected = this.connectionStatus.connected;
          this.connectionStatus.connected = false;
          this.connectionStatus.connecting = false;

          this.log(`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}, wasClean: ${event.wasClean}`);

          // Stop ping interval
          this.stopPingInterval();

          // Emit close event
          this.emit('disconnected', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
            timestamp: Date.now()
          });

          // Attempt reconnection if configured and if we were connected before
          if (this.config.autoReconnect && (wasConnected || this.connectionStatus.wasConnected)) {
            this.attemptReconnect();
          } else if (!wasConnected) {
            // If we were never connected, report failure
            reject(new Error(`Connection closed: ${event.reason || 'Unknown reason'}`));
          }
        };

        // Handle errors
        this.ws.onerror = (event) => {
          this.log('WebSocket error occurred', event);
          this.connectionStatus.lastError = 'WebSocket error occurred';

          this.emit('error', {
            type: 'connection_error',
            message: 'WebSocket error occurred',
            timestamp: Date.now()
          });

          // If we're still connecting, reject the promise
          if (this.connectionStatus.connecting && !this.connectionStatus.connected) {
            this.connectionStatus.connecting = false;
            reject(new Error('WebSocket connection error'));
          }
        };
      } catch (err) {
        this.connectionStatus.connecting = false;
        this.log('Error creating WebSocket', err);
        reject(err);
      }
    });
  }

  /**
   * Initialize connection after successful connection
   */
  private initializeConnection() {
    // Send client info
    this.sendClientInfo();

    // Request progress history if applicable
    if (this.reconnectionState.lastEventTimestamp > 0) {
      this.send('request_progress_history', {});
    }

    // Resubscribe to channels
    this.reconnectionState.subscriptions.forEach(channel => {
      this.subscribe(channel);
    });

    // Send any queued messages
    this.sendQueuedMessages();
  }

  /**
   * Send client information to the server
   */
  private sendClientInfo() {
    const clientInfo = {
      user_agent: navigator.userAgent,
      screen_size: `${window.innerWidth}x${window.innerHeight}`,
      app_version: process.env.REACT_APP_VERSION || '1.0.0',
      platform: navigator.platform,
      language: navigator.language
    };

    // Store for reconnection
    this.reconnectionState.clientInfo = clientInfo;

    // Send to server
    this.send('client_info', { ...clientInfo });
  }

  /**
   * Send any queued messages after reconnection
   */
  private sendQueuedMessages() {
    if (this.messageQueue.length === 0) return;

    console.log(`Sending ${this.messageQueue.length} queued messages`);

    // Create a copy of the queue and reset the original
    const queueCopy = [...this.messageQueue];
    this.messageQueue = [];

    // Process messages sequentially to maintain order
    const processMessages = async () => {
      for (const message of queueCopy) {
        try {
          // Wait a small amount of time between messages to avoid flooding
          await new Promise(resolve => setTimeout(resolve, 50));

          // Send the message and track result
          const success = this.sendRaw(message);

          // If sending failed, put message back in queue for next reconnection
          if (!success) {
            this.messageQueue.push(message);
          }
        } catch (error) {
          console.error('Error sending queued message:', error);
          // Re-queue the message on error
          this.messageQueue.push(message);
        }
      }

      // Log remaining messages
      if (this.messageQueue.length > 0) {
        console.warn(`${this.messageQueue.length} messages remain in queue after retry`);
      }
    };

    // Start processing messages asynchronously
    processMessages();
  }

  /**
   * Save any pending messages to queue when disconnected
   */
  private saveMessagesToQueue() {
    this.pendingMessages.forEach(({message}) => {
      this.messageQueue.push(message);
    });
    this.pendingMessages.clear();
  }

  /**
   * Attempt to reconnect with exponential backoff and more robust error handling
   */
  private attemptReconnect(): void {
    // Clear any existing reconnection timers
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Update connection status
    this.connectionStatus.reconnecting = true;
    this.connectionStatus.reconnectAttempt++;

    // Check if we've exceeded the maximum reconnection attempts
    if (this.connectionStatus.reconnectAttempt > this.maxReconnectAttempts) {
      this.log(`Maximum reconnection attempts (${this.maxReconnectAttempts}) reached. Giving up.`);

      // Reset reconnection state
      this.connectionStatus.reconnecting = false;
      this.emit('reconnect_failed', {
        attempts: this.connectionStatus.reconnectAttempt,
        maxAttempts: this.maxReconnectAttempts,
        error: this.connectionStatus.lastError || 'Maximum reconnection attempts reached',
        timestamp: Date.now()
      });

      // Emit terminal connection failure event for application-level handling
      this.emit('connection_terminal_failure', {
        message: 'Failed to establish a stable connection after multiple attempts',
        reconnectAttempts: this.connectionStatus.reconnectAttempt,
        lastError: this.connectionStatus.lastError,
        timestamp: Date.now()
      });

      return;
    }

    // Calculate exponential backoff delay with jitter
    // Base: 2^reconnectAttempt * reconnectDelay
    // Jitter: Random value between 0 and 1000ms to prevent thundering herd
    const backoffFactor = Math.min(10, Math.pow(2, this.connectionStatus.reconnectAttempt - 1));
    const jitter = Math.random() * 1000;
    const delay = Math.min(30000, this.config.reconnectInterval * backoffFactor + jitter); // Cap at 30 seconds

    this.log(`Reconnection attempt ${this.connectionStatus.reconnectAttempt}/${this.maxReconnectAttempts} scheduled in ${Math.round(delay)}ms`);

    // Emit reconnecting event for UI feedback
    this.emit('reconnecting', {
      attempt: this.connectionStatus.reconnectAttempt,
      maxAttempts: this.maxReconnectAttempts,
      delay: delay,
      nextAttemptTime: new Date(Date.now() + delay).toISOString(),
      timestamp: Date.now()
    });

    // Schedule reconnection
    this.reconnectTimer = window.setTimeout(() => {
      this.log(`Attempting reconnection (${this.connectionStatus.reconnectAttempt}/${this.maxReconnectAttempts})...`);

      // Prepare for reconnection
      this.prepareForReconnection();

      // Attempt to reconnect
      this.connect()
        .then((connected) => {
          if (connected) {
            this.log('Reconnection successful');
            this.handleSuccessfulReconnection();
          } else {
            this.log('Reconnection failed - socket not connected after connect() returned');
            this.attemptReconnect(); // Try again
          }
        })
        .catch((error) => {
          this.log('Reconnection failed', error);
          this.connectionStatus.lastError = error?.message || 'Unknown error during reconnection';

          // Emit specific reconnection failure event
          this.emit('reconnect_attempt_failed', {
            attempt: this.connectionStatus.reconnectAttempt,
            error: this.connectionStatus.lastError,
            willRetry: this.connectionStatus.reconnectAttempt < this.maxReconnectAttempts,
            nextAttemptDelay: this.config.reconnectInterval * Math.pow(2, this.connectionStatus.reconnectAttempt),
            timestamp: Date.now()
          });

          // Schedule next attempt
          this.attemptReconnect();
        });
    }, delay);
  }

  /**
   * Prepare for reconnection by cleaning up and saving state
   */
  private prepareForReconnection(): void {
    // Clean up any existing connection
    if (this.ws) {
      try {
        // Only attempt to close if still open
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.close(1000, 'Closing before reconnection attempt');
        }
      } catch (e) {
        this.log('Error while closing socket before reconnection', e);
      }
      this.ws = null;
    }

    // Stop any existing intervals/timeouts
    this.stopPingInterval();
    this.stopConnectionChecker();

    // Save message queue for reconnection
    this.saveMessagesToQueue();

    // Update reconnection state with latest data
    this.reconnectionState.lastEventTimestamp = Date.now();

    // Record subscriptions for resubscribing after reconnection
    if (!this.reconnectionState.token) {
      // Generate reconnection token only on first disconnect
      this.reconnectionState.token = `reconn_${Date.now().toString(36)}_${Math.random().toString(36).substr(2, 9)}`;
    }
  }

  /**
   * Handle a successful reconnection
   */
  private handleSuccessfulReconnection(): void {
    // Reset reconnection attempt counter
    this.connectionStatus.reconnectAttempt = 0;
    this.connectionStatus.reconnecting = false;

    // Emit reconnected event
    this.emit('reconnected', {
      timestamp: Date.now(),
      reconnectionDuration: this.connectionStatus.connectionStartTime ?
        Date.now() - this.connectionStatus.connectionStartTime : 0,
      queuedMessages: this.messageQueue.length
    });

    // Restore session
    this.restoreSession();

    // Process queued messages
    this.processQueue();

    // Restart heartbeat and connection checker
    this.startPingInterval();
    this.startConnectionChecker();
  }

  /**
   * Restore session after reconnection
   */
  private restoreSession(): void {
    // Resubscribe to channels
    if (this.reconnectionState.subscriptions.length > 0) {
      this.log(`Resubscribing to ${this.reconnectionState.subscriptions.length} channels`);
      this.reconnectionState.subscriptions.forEach(channel => {
        this.subscribe(channel);
      });
    }

    // Send client info with reconnection token
    this.sendClientInfo();

    // Send a reconnection notification to the server
    this.send('reconnection_notification', {
      reconnection_token: this.reconnectionState.token,
      last_event_timestamp: this.reconnectionState.lastEventTimestamp,
      client_id: this.config.clientId,
      session_id: this.sessionId,
      previous_session_info: {
        wasConnected: this.connectionStatus.wasConnected,
        lastMessageTime: this.connectionStatus.lastMessageTime,
        queuedMessages: this.messageQueue.length,
        pendingMessages: this.pendingMessages.size
      }
    });
  }

  /**
   * Enhanced connection checker with more robust health monitoring
   */
  private startConnectionChecker(): void {
    // Clear any existing checker
    this.stopConnectionChecker();

    // Start a new connection checker
    this.connectionCheckerTimer = window.setInterval(() => {
      // Skip check if not connected
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        return;
      }

      const now = Date.now();
      const lastMessageAge = now - (this.connectionStatus.lastMessageTime || now);
      const maxSilentPeriod = this.config.pingInterval * 3; // Max time without messages

      if (lastMessageAge > maxSilentPeriod) {
        this.log(`Connection appears stale. No messages for ${lastMessageAge}ms. Forcing reconnection.`);

        // Emit stale connection event
        this.emit('connection_stale', {
          lastMessageAge,
          maxSilentPeriod,
          timestamp: now
        });

        // Force a reconnection
        this.forceReconnect();
        return;
      }

      // Check for unresponsive connection (ping sent but no response received)
      if (this.lastHeartbeatResponse > 0) {
        const timeSinceLastPingResponse = now - this.lastHeartbeatResponse;
        if (timeSinceLastPingResponse > this.config.pingInterval * 2) {
          this.log(`Ping response timeout. Last ping response was ${timeSinceLastPingResponse}ms ago.`);

          // Emit ping timeout event
          this.emit('ping_timeout', {
            timeSinceLastPingResponse,
            timestamp: now
          });

          // Force a reconnection
          this.forceReconnect();
          return;
        }
      }

      // Check for expired pending messages
      const messageTimeout = 30000; // 30 seconds
      let expiredMessages = 0;

      this.pendingMessages.forEach((data, messageId) => {
        const messageAge = now - data.timestamp;
        if (messageAge > messageTimeout) {
          // Message has timed out
          expiredMessages++;
          this.pendingMessages.delete(messageId);

          // Emit message timeout event
          this.emit('message_timeout', {
            messageId,
            message: data.message,
            messageAge,
            timestamp: now
          });

          // Requeue the message for retry
          this.queueMessage(data.message);
        }
      });

      if (expiredMessages > 0) {
        this.log(`${expiredMessages} pending messages timed out and were requeued`);
      }

    }, 5000); // Check every 5 seconds
  }

  /**
   * Enhanced ping interval with health check
   */
  private startPingInterval(): void {
    // Clear any existing ping interval
    this.stopPingInterval();

    // Start a new ping interval
    this.pingIntervalId = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          // Send ping with sequence number and timestamp
          const pingId = Date.now().toString();
          const pingMessage = {
            type: 'ping',
            id: pingId,
            timestamp: Date.now(),
            client_info: {
              url: window.location.href,
              userAgent: navigator.userAgent,
              screenWidth: window.innerWidth,
              screenHeight: window.innerHeight,
              connectionState: {
                lastMessageAge: Date.now() - (this.connectionStatus.lastMessageTime || Date.now()),
                reconnectAttempts: this.connectionStatus.reconnectAttempt,
                connected: this.connectionStatus.connected
              }
            }
          };

          this.ws.send(JSON.stringify(pingMessage));

          // Set timeout for ping response
          this.pingTimeoutTimer = window.setTimeout(() => {
            this.log('Ping timeout - no response received');

            // Emit ping timeout event
            this.emit('ping_timeout', {
              pingId,
              timestamp: Date.now()
            });

            // If this happens repeatedly, connection checker will force reconnect
          }, 10000); // 10 second timeout for ping response

        } catch (error) {
          this.log('Error sending ping', error);

          // Handle ping send failure
          this.emit('ping_error', {
            error: error?.message || 'Unknown error sending ping',
            timestamp: Date.now()
          });
        }
      }
    }, this.config.pingInterval);
  }

  /**
   * Enhanced error handling for messages
   */
  private handleErrorMessage(data: any): void {
    this.log('Received error message from server', data);

    // Emit the error event
    this.emit('server_error', data);

    // Check if this is a fatal error that requires reconnection
    if (data.fatal || data.requires_reconnect) {
      this.log('Server reported fatal error or requested reconnection', data);

      // Emit specific event for fatal errors
      this.emit('server_fatal_error', {
        ...data,
        timestamp: Date.now()
      });

      // Force reconnection
      this.forceReconnect();
      return;
    }

    // Check if this is related to a specific message
    if (data.original_message_id && this.pendingMessages.has(data.original_message_id)) {
      // Get the original message
      const originalMessage = this.pendingMessages.get(data.original_message_id);

      // Remove from pending
      this.pendingMessages.delete(data.original_message_id);

      // Check if we should retry
      if (data.retriable && originalMessage) {
        this.log('Retriable error for message', data.original_message_id);

        // Requeue the message for retry
        this.queueMessage(originalMessage.message);

        // Emit retry event
        this.emit('message_retry', {
          messageId: data.original_message_id,
          error: data,
          retryCount: (originalMessage.message.retryCount || 0) + 1,
          timestamp: Date.now()
        });
      }
    }
  }

  /**
   * Forcefully reconnect with enhanced diagnostics
   */
  public forceReconnect(): void {
    this.log('Forcing reconnection...');

    // Gather diagnostic information
    const diagnostics = {
      socketState: this.ws ? this.ws.readyState : 'null',
      connectionStatus: { ...this.connectionStatus },
      queueLength: this.messageQueue.length,
      pendingMessages: this.pendingMessages.size,
      timestamp: Date.now()
    };

    // Emit reconnect event with diagnostics
    this.emit('force_reconnect', diagnostics);

    // Prepare for reconnection
    this.prepareForReconnection();

    // Reset connection status but preserve some information
    const wasConnected = this.connectionStatus.wasConnected;
    const lastError = this.connectionStatus.lastError;

    this.connectionStatus = {
      connected: false,
      connecting: false,
      reconnecting: false,
      reconnectAttempt: 0,
      wasConnected,
      lastError
    };

    // Start reconnection process
    this.attemptReconnect();
  }

  /**
   * Get detailed connection health status
   */
  public getConnectionHealth(): Record<string, any> {
    const now = Date.now();
    const lastMessageAge = now - (this.connectionStatus.lastMessageTime || now);
    const connectionDuration = now - (this.connectionStatus.connectionStartTime || now);

    return {
      connected: this.connectionStatus.connected,
      connecting: this.connectionStatus.connecting,
      reconnecting: this.connectionStatus.reconnecting,
      reconnectAttempt: this.connectionStatus.reconnectAttempt,
      lastError: this.connectionStatus.lastError,
      lastMessageAge,
      connectionDuration,
      queuedMessages: this.messageQueue.length,
      pendingMessages: this.pendingMessages.size,
      websocketState: this.ws ? this.ws.readyState : 'null',
      healthScore: this.calculateConnectionHealthScore(lastMessageAge, connectionDuration),
      timestamp: now
    };
  }

  /**
   * Calculate a health score for the connection (0-100)
   */
  private calculateConnectionHealthScore(lastMessageAge: number, connectionDuration: number): number {
    // Not connected
    if (!this.connectionStatus.connected) {
      return 0;
    }

    // Base score for being connected
    let score = 80;

    // Reduce score for old messages (stale connection)
    if (lastMessageAge > this.config.pingInterval * 2) {
      score -= Math.min(40, Math.floor(lastMessageAge / (this.config.pingInterval / 2)));
    }

    // Reduce score for reconnection attempts
    score -= Math.min(20, this.connectionStatus.reconnectAttempt * 5);

    // Reduce score for message queue buildup
    score -= Math.min(20, this.messageQueue.length);

    // Increase score for long-lived connections (stability)
    if (connectionDuration > 60000) { // 1 minute
      score += Math.min(20, Math.floor(connectionDuration / 60000));
    }

    // Ensure score stays within 0-100
    return Math.max(0, Math.min(100, score));
  }

  /**
   * Register for connection health events
   */
  public onConnectionHealthChange(callback: (health: Record<string, any>) => void): () => void {
    const handler = () => {
      callback(this.getConnectionHealth());
    };

    // Set up an interval to update health
    const intervalId = window.setInterval(handler, 10000); // Every 10 seconds

    // Also listen for connection events
    this.on('connected', handler);
    this.on('disconnected', handler);
    this.on('reconnecting', handler);
    this.on('reconnected', handler);
    this.on('error', handler);

    // Return function to cancel interval
    return () => {
      window.clearInterval(intervalId);
      this.off('connected', handler);
      this.off('disconnected', handler);
      this.off('reconnecting', handler);
      this.off('reconnected', handler);
      this.off('error', handler);
    };
  }

  private queueMessage(message: any): void {
    // Add to queue with timestamp for potential expiration
    this.messageQueue.push({
      message,
      queuedAt: Date.now()
    });

    // Limit queue size to prevent memory issues
    if (this.messageQueue.length > 100) {
      this.messageQueue.shift();
    }

    this.emit('message_queued', {
      queueLength: this.messageQueue.length,
      message
    });
  }

  private processQueue(): void {
    if (this.messageQueue.length === 0) {
      return;
    }

    this.log(`Processing ${this.messageQueue.length} queued messages`);

    // Process messages in order
    const queue = [...this.messageQueue];
    this.messageQueue = [];

    for (const item of queue) {
      // Skip expired messages (older than 5 minutes)
      if (Date.now() - item.queuedAt > 5 * 60 * 1000) {
        this.log('Skipping expired message from queue');
        continue;
      }

      this.send(item.message);
    }

    this.emit('queue_processed', { processedCount: queue.length });
  }

  private buildWebSocketUrl(): string {
    const url = new URL(this.config.url);

    // Add query parameters
    url.searchParams.append('session_id', this.config.sessionId);

    if (this.config.token) {
      url.searchParams.append('token', this.config.token);
    }

    url.searchParams.append('client_id', this.config.clientId);
    url.searchParams.append('ping_interval', this.config.pingInterval.toString());

    return url.toString();
  }

  private stopPingInterval(): void {
    if (this.pingIntervalId !== null) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }

  private stopConnectionChecker(): void {
    if (this.connectionCheckerTimer !== null) {
      clearInterval(this.connectionCheckerTimer);
      this.connectionCheckerTimer = null;
    }
  }

  private handleConnectionStatusMessage(data: any): void {
    this.log('Received connection status message', data);

    // Update internal status based on server status
    if (data.status === 'connected') {
      this.connectionStatus.connected = true;
      this.connectionStatus.connecting = false;
      this.connectionStatus.reconnecting = false;
    } else if (data.status === 'reconnecting' || data.status === 'waiting_to_reconnect') {
      this.connectionStatus.reconnecting = true;
    } else if (data.status === 'failed') {
      this.connectionStatus.connected = false;
      this.connectionStatus.connecting = false;
      this.connectionStatus.reconnecting = false;
      this.connectionStatus.lastError = data.reason || 'Connection failed';
    }

    // Emit the status message
    this.emit('connection_status', data);
  }

  private handlePingMessage(data: any): void {
    // Respond with pong
    this.send({
      type: 'pong',
      ping_id: data.ping_id,
      timestamp: Date.now()
    });
  }

  private log(...args: any[]): void {
    if (this.config.debug) {
      console.log(`[WebSocketService]`, ...args);
    }
  }
}
