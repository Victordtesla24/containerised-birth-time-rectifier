import { EventEmitter } from 'events';

// Define interface for websocket messages
interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
  message_id: string;
  session_id: string;
}

// Define websocket service options
interface WebSocketServiceOptions {
  token?: string;
  clientId?: string;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  debug?: boolean;
  pingInterval?: number;
}

// Define connection status interface
interface ConnectionStatus {
  connected: boolean;
  connecting: boolean;
  reconnecting: boolean;
  reconnectAttempts: number;
}

// Define reconnection state interface
interface ReconnectionState {
  lastEventTimestamp: number;
  subscriptions: string[];
}

// Define WebSocket configuration interface
interface WebSocketConfig {
  url: string;
  sessionId: string;
  token: string;
  clientId: string;
  autoReconnect: boolean;
  reconnectInterval: number;
  maxReconnectAttempts: number;
  debug: boolean;
  pingInterval: number;
}

/**
 * WebSocket service for real-time communication
 * Extends EventEmitter to support event-based communication
 */
export class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private sessionId: string;
  private messageQueue: WebSocketMessage[] = [];
  private messageCounter: number = 0;
  private pingInterval: any;
  private reconnectTimeout: any;
  private config!: WebSocketConfig;

  private connectionStatus: ConnectionStatus = {
    connected: false,
    connecting: false,
    reconnecting: false,
    reconnectAttempts: 0
  };

  private reconnectionState: ReconnectionState = {
    lastEventTimestamp: 0,
    subscriptions: []
  };

  /**
   * Construct a new WebSocketService instance
   * @param sessionId Session ID for this connection
   * @param options Connection options
   */
  constructor(sessionId: string, options: WebSocketServiceOptions = {}) {
    super(); // Initialize EventEmitter

    this.sessionId = sessionId;

    // Determine base URL from environment or defaults
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:9000';
    this.baseUrl = typeof process !== 'undefined' && process.env.NEXT_PUBLIC_WS_URL
      ? process.env.NEXT_PUBLIC_WS_URL
      : `${protocol}//${host}/ws`;

    // Auto-connect by default unless explicitly disabled
    if (options.autoConnect !== false) {
      this.connect();
    }

    // Add unload handler to properly close connection
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.disconnect());
    }

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
   * Connect to the WebSocket server
   * @returns Promise that resolves when connected
   */
  public connect(): Promise<boolean> {
    // Return existing connection if already connected
    if (this.connectionStatus.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve(true);
    }

    // Return existing connection attempt if already connecting
    if (this.connectionStatus.connecting) {
      return new Promise((resolve, reject) => {
        this.once('connected', () => resolve(true));
        this.once('connection_error', reject);
      });
    }

    this.connectionStatus.connecting = true;

    return new Promise((resolve, reject) => {
      try {
        // Configure the WebSocket URL with parameters
        const url = new URL(this.baseUrl);
        url.searchParams.append('session_id', this.config.sessionId);

        if (this.config.token) {
          url.searchParams.append('token', this.config.token);
        }

        url.searchParams.append('client_id', this.config.clientId);
        url.searchParams.append('timestamp', Date.now().toString());

        // Create the WebSocket connection
        this.ws = new WebSocket(url.toString());

        // Set up WebSocket event handlers
        if (this.ws) {
          // Handle connection open
          this.ws.onopen = () => {
            this.connectionStatus.connected = true;
            this.connectionStatus.connecting = false;
            this.connectionStatus.reconnecting = false;
            this.connectionStatus.reconnectAttempts = 0;

            this.log('WebSocket connected');
            this.emit('connected');

            // Initialize the connection
            this.initializeConnection();

            // Start ping interval
            this.startPing();

            // Process any queued messages
            this.processQueue();

            resolve(true);
          };

          // Handle incoming messages
          this.ws.onmessage = (event) => {
            this.handleMessage(event);
          };

          // Handle connection close
          this.ws.onclose = (event) => {
            const wasConnected = this.connectionStatus.connected;

            this.connectionStatus.connected = false;
            this.connectionStatus.connecting = false;

            this.log(`WebSocket closed: ${event.code} - ${event.reason}`);
            this.emit('disconnected', { code: event.code, reason: event.reason });

            // Stop ping interval
            this.stopPing();

            // Attempt reconnection if auto-reconnect is enabled
            if (wasConnected && this.config.autoReconnect) {
              this.scheduleReconnect();
            }

            // If still connecting (initial connection), reject the connection promise
            if (this.connectionStatus.connecting) {
              this.connectionStatus.connecting = false;
              reject(new Error(`WebSocket connection closed: ${event.code} - ${event.reason}`));
            }
          };

          // Handle connection error
          this.ws.onerror = (error) => {
            this.log('WebSocket error', error);
            this.emit('connection_error', error);

            if (this.connectionStatus.connecting) {
              this.connectionStatus.connecting = false;
              reject(new Error('WebSocket connection error'));
            }
          };
        }
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
  }

  /**
   * Send client info to the server
   */
  private sendClientInfo() {
    this.send('client_info', {
      client_id: this.config.clientId,
      session_id: this.config.sessionId,
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'node',
      device_type: this.getDeviceType(),
      last_event_timestamp: this.reconnectionState.lastEventTimestamp
    });
  }

  /**
   * Get device type based on user agent
   */
  private getDeviceType(): string {
    if (typeof navigator === 'undefined') return 'server';

    const ua = navigator.userAgent;
    if (/mobile|android|iphone|ipad|ipod/i.test(ua)) return 'mobile';
    if (/tablet|ipad/i.test(ua)) return 'tablet';
    return 'desktop';
  }

  /**
   * Start the ping interval
   */
  private startPing() {
    this.stopPing();
    this.pingInterval = setInterval(() => {
      this.send('ping', { timestamp: Date.now() });
    }, this.config.pingInterval);
  }

  /**
   * Stop the ping interval
   */
  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Schedule reconnection after connection loss
   */
  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.connectionStatus.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('Maximum reconnection attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    this.connectionStatus.reconnecting = true;
    this.connectionStatus.reconnectAttempts++;

    const delay = this.config.reconnectInterval;
    this.log(`Scheduling reconnect in ${delay}ms (attempt ${this.connectionStatus.reconnectAttempts}/${this.config.maxReconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.log(`Attempting to reconnect (${this.connectionStatus.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
      this.emit('reconnecting', { attempt: this.connectionStatus.reconnectAttempts });

      this.connect()
        .then(() => {
          this.log('Reconnected successfully');
          this.emit('reconnected');
        })
        .catch(err => {
          this.log('Reconnection failed', err);
          this.scheduleReconnect();
        });
    }, delay);
  }

  /**
   * Process queued messages after connection
   */
  private processQueue() {
    if (this.messageQueue.length === 0) return;

    this.log(`Processing ${this.messageQueue.length} queued messages`);

    // Create a copy of the queue and clear it
    const queue = [...this.messageQueue];
    this.messageQueue = [];

    // Send all queued messages
    queue.forEach(message => {
      try {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify(message));
          this.log(`Sent queued message (${message.type})`);
        } else {
          // If connection lost during processing, re-queue
          this.messageQueue.push(message);
        }
      } catch (err) {
        this.log(`Error sending queued message (${message.type})`, err);
        // Re-queue on error
        this.messageQueue.push(message);
      }
    });
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(event: MessageEvent) {
    try {
      const message = JSON.parse(event.data);

      // Update last event timestamp for reconnection history
      if (message.timestamp) {
        this.reconnectionState.lastEventTimestamp = Math.max(
          this.reconnectionState.lastEventTimestamp,
          message.timestamp
        );
      }

      // Handle system messages
      if (message.type === 'ping') {
        this.send('pong', { timestamp: Date.now() });
        return;
      }

      // Emit the message event
      this.emit('message', message);

      // Emit specific event for the message type
      this.emit(message.type, message.data);

    } catch (err) {
      this.log('Error parsing message', err);
      this.emit('error', err);
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  public disconnect() {
    this.stopPing();

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close();
      }
      this.ws = null;
    }

    this.connectionStatus.connected = false;
    this.connectionStatus.connecting = false;
    this.connectionStatus.reconnecting = false;

    this.log('WebSocket disconnected');
  }

  /**
   * Send a message to the WebSocket server
   * @param type Message type
   * @param data Message data (optional)
   * @returns Promise that resolves when message is sent or queued
   */
  public send(type: string, data: any = {}): Promise<boolean> {
    const message: WebSocketMessage = {
      type,
      data,
      timestamp: Date.now(),
      message_id: `msg_${Date.now()}_${this.messageCounter++}`,
      session_id: this.sessionId
    };

    // If not connected, queue the message
    if (!this.connectionStatus.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.messageQueue.push(message);
      this.log(`Message queued (${type}): not connected`);
      return Promise.resolve(false);
    }

    try {
      this.ws.send(JSON.stringify(message));
      this.log(`Message sent (${type})`);
      return Promise.resolve(true);
    } catch (err) {
      this.log(`Error sending message (${type})`, err);
      // Queue on error
      this.messageQueue.push(message);
      return Promise.resolve(false);
    }
  }

  /**
   * Subscribe to a channel
   * @param channel Channel name to subscribe to
   */
  public subscribe(channel: string): Promise<boolean> {
    // Track subscription for reconnection
    if (!this.reconnectionState.subscriptions.includes(channel)) {
      this.reconnectionState.subscriptions.push(channel);
    }

    return this.send('subscribe', { channel });
  }

  /**
   * Unsubscribe from a channel
   * @param channel Channel name to unsubscribe from
   */
  public unsubscribe(channel: string): Promise<boolean> {
    // Remove from subscriptions
    const index = this.reconnectionState.subscriptions.indexOf(channel);
    if (index !== -1) {
      this.reconnectionState.subscriptions.splice(index, 1);
    }

    return this.send('unsubscribe', { channel });
  }

  /**
   * Log a message with optional data if debug is enabled
   */
  private log(message: string, data?: any): void {
    if (this.config.debug) {
      if (data) {
        console.log(`[WebSocket] ${message}`, data);
      } else {
        console.log(`[WebSocket] ${message}`);
      }
    }
  }
}
