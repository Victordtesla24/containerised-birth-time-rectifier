/**
 * Tests for WebSocketService
 */

import { WebSocketService } from '../WebSocketService';

// Mock WebSocket implementation
global.WebSocket = jest.fn().mockImplementation(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  send: jest.fn(),
  close: jest.fn(),
  readyState: 0, // CONNECTING
  onopen: null,
  onclose: null,
  onerror: null,
  onmessage: null,
}));

// Mock window
Object.defineProperty(global, 'window', {
  value: {
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    location: {
      protocol: 'http:',
      host: 'localhost:3000',
    },
  },
  writable: true,
});

describe('WebSocketService', () => {
  let service: WebSocketService;

  beforeEach(() => {
    jest.clearAllMocks();
    // Initialize with autoConnect disabled to prevent auto connection
    service = new WebSocketService('test-session', { autoConnect: false });
  });

  test('constructor should set expected default values', () => {
    expect(service).toBeDefined();
    // Access the private config property for testing
    const config = (service as any).config;

    expect(config.sessionId).toBe('test-session');
    expect(config.autoReconnect).toBe(false);
    expect(config.token).toBe('');
    expect(config.maxReconnectAttempts).toBe(10);
  });

  test('connect should create a new WebSocket', async () => {
    const connectPromise = service.connect();

    // Simulate successful connection
    const ws = (service as any).ws;
    if (ws && ws.onopen) {
      ws.onopen({});
    }

    await expect(connectPromise).resolves.toBe(true);
    expect(global.WebSocket).toHaveBeenCalled();
  });

  test('disconnect should clean up resources', () => {
    // Setup service with mocked WebSocket
    (service as any).ws = {
      readyState: WebSocket.OPEN,
      close: jest.fn(),
      send: jest.fn(),
    };

    service.disconnect();

    expect((service as any).ws.close).toHaveBeenCalled();
    expect((service as any).ws).toBeNull();
  });
});
