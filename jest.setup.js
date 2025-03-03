// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Disable actual network requests during tests
beforeAll(() => {
  // Store original implementations
  const realFetch = global.fetch;
  const realXHR = global.XMLHttpRequest;
  
  // Mock XMLHttpRequest for CORS issues
  const MockXHR = function() {
    return {
      open: jest.fn(),
      send: jest.fn(),
      setRequestHeader: jest.fn(),
      readyState: 4,
      status: 200,
      response: '{}',
      responseText: '{}',
      onreadystatechange: null,
      addEventListener: jest.fn((event, callback) => {
        if (event === 'load') {
          callback();
        }
      }),
      removeEventListener: jest.fn()
    };
  };
  
  // Replace XMLHttpRequest to prevent CORS errors
  global.XMLHttpRequest = MockXHR;
  
  // Mock Fetch API with a version that doesn't make real network requests
  global.fetch = jest.fn(() => Promise.resolve({
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    ok: true,
    status: 200,
    headers: new Headers(),
  }));
});

afterAll(() => {
  // Restore all mocks
  jest.restoreAllMocks();
});

// Mock AbortSignal.timeout
if (!AbortSignal.timeout) {
  AbortSignal.timeout = jest.fn((ms) => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), ms);
    return controller.signal;
  });
}

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    reload: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
    events: {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn(),
    },
  }),
}));

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:3001';
process.env.NEXT_PUBLIC_AI_SERVICE_URL = 'http://localhost:8080';

// Console error override to not show unnecessary errors during testing
const originalConsoleError = console.error;
console.error = (...args) => {
  // Filter out specific React errors that are noisy or irrelevant during testing
  const errorMessage = args[0] && typeof args[0] === 'string' ? args[0] : '';
  
  const ignoredErrors = [
    'Error: Uncaught [Error: ResizeObserver loop limit exceeded]',
    // Add React's useLayoutEffect SSR warning
    'Warning: useLayoutEffect does nothing on the server',
    // Filter out Act() warnings as they're mostly false positives with async code
    'Warning: An update to',
    'was not wrapped in act',
    // Filter out CORS and network errors that are expected in tests
    'Cross origin',
    'Network Error',
    'Failed to geocode',
    'Geocoding error',
    'Geocoding failed',
    // Add other errors to ignore as needed
  ];
  
  const shouldIgnore = ignoredErrors.some(ignored => 
    typeof errorMessage === 'string' && errorMessage.includes(ignored)
  );
  
  if (!shouldIgnore) {
    originalConsoleError(...args);
  }
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.scrollTo
window.scrollTo = jest.fn();

// Mock IntersectionObserver
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback;
  }
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

window.IntersectionObserver = MockIntersectionObserver;

// Mock ResizeObserver
class MockResizeObserver {
  constructor(callback) {
    this.callback = callback;
  }
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

window.ResizeObserver = MockResizeObserver;

// Enhanced Canvas Mock with additional WebGL requirements
const mockWebGLRenderingContext = {
  ARRAY_BUFFER: 'ARRAY_BUFFER',
  ELEMENT_ARRAY_BUFFER: 'ELEMENT_ARRAY_BUFFER',
  STATIC_DRAW: 'STATIC_DRAW',
  DYNAMIC_DRAW: 'DYNAMIC_DRAW',
  FLOAT: 'FLOAT',
  UNSIGNED_SHORT: 'UNSIGNED_SHORT',
  TRIANGLES: 'TRIANGLES',
  TRIANGLE_STRIP: 'TRIANGLE_STRIP',
  TRIANGLE_FAN: 'TRIANGLE_FAN',
  FRAGMENT_SHADER: 'FRAGMENT_SHADER',
  VERTEX_SHADER: 'VERTEX_SHADER',
  COMPILE_STATUS: 'COMPILE_STATUS',
  LINK_STATUS: 'LINK_STATUS',
  COLOR_BUFFER_BIT: 'COLOR_BUFFER_BIT',
  DEPTH_BUFFER_BIT: 'DEPTH_BUFFER_BIT',
  DEPTH_TEST: 'DEPTH_TEST',
  TEXTURE_2D: 'TEXTURE_2D',
  TEXTURE0: 'TEXTURE0',
  RGBA: 'RGBA',
  UNSIGNED_BYTE: 'UNSIGNED_BYTE',
  LINEAR: 'LINEAR',
  NEAREST: 'NEAREST',
  TEXTURE_MAG_FILTER: 'TEXTURE_MAG_FILTER',
  TEXTURE_MIN_FILTER: 'TEXTURE_MIN_FILTER',
  TEXTURE_WRAP_S: 'TEXTURE_WRAP_S',
  TEXTURE_WRAP_T: 'TEXTURE_WRAP_T',
  CLAMP_TO_EDGE: 'CLAMP_TO_EDGE',
  REPEAT: 'REPEAT',
  
  clearColor: jest.fn(),
  clearDepth: jest.fn(),
  clear: jest.fn(),
  enable: jest.fn(),
  disable: jest.fn(),
  createBuffer: jest.fn(() => ({})),
  bindBuffer: jest.fn(),
  bufferData: jest.fn(),
  createVertexArray: jest.fn(() => ({})),
  bindVertexArray: jest.fn(),
  createTexture: jest.fn(() => ({})),
  bindTexture: jest.fn(),
  texImage2D: jest.fn(),
  texParameteri: jest.fn(),
  createShader: jest.fn(() => ({})),
  shaderSource: jest.fn(),
  compileShader: jest.fn(),
  getShaderParameter: jest.fn(() => true),
  getShaderInfoLog: jest.fn(() => ''),
  createProgram: jest.fn(() => ({})),
  attachShader: jest.fn(),
  linkProgram: jest.fn(),
  getProgramParameter: jest.fn(() => true),
  getProgramInfoLog: jest.fn(() => ''),
  useProgram: jest.fn(),
  getAttribLocation: jest.fn(() => 0),
  getUniformLocation: jest.fn(() => ({})),
  enableVertexAttribArray: jest.fn(),
  vertexAttribPointer: jest.fn(),
  uniform1i: jest.fn(),
  uniform1f: jest.fn(),
  uniform2f: jest.fn(),
  uniform3f: jest.fn(),
  uniform4f: jest.fn(),
  uniformMatrix2fv: jest.fn(),
  uniformMatrix3fv: jest.fn(),
  uniformMatrix4fv: jest.fn(),
  activeTexture: jest.fn(),
  drawArrays: jest.fn(),
  drawElements: jest.fn(),
  viewport: jest.fn(),
  scissor: jest.fn(),
};

// Enhanced Canvas Mock
HTMLCanvasElement.prototype.getContext = function(contextType) {
  if (contextType === 'webgl' || contextType === 'webgl2') {
    return {
      ...mockWebGLRenderingContext,
      canvas: this,
    };
  } else if (contextType === '2d') {
    return {
      fillRect: jest.fn(),
      clearRect: jest.fn(),
      getImageData: jest.fn(() => ({ data: new Array(4) })),
      putImageData: jest.fn(),
      createImageData: jest.fn(() => []),
      drawImage: jest.fn(),
      scale: jest.fn(),
      measureText: jest.fn(() => ({ width: 0 })),
      rect: jest.fn(),
      arc: jest.fn(),
      fill: jest.fn(),
      beginPath: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      closePath: jest.fn(),
      stroke: jest.fn(),
      translate: jest.fn(),
      strokeText: jest.fn(),
      fillText: jest.fn(),
      restore: jest.fn(),
      save: jest.fn(),
      rotate: jest.fn(),
      createLinearGradient: jest.fn(() => ({
        addColorStop: jest.fn()
      })),
      createRadialGradient: jest.fn(() => ({
        addColorStop: jest.fn()
      })),
      canvas: this,
    };
  }
  return null;
};

// Mock for OffscreenCanvas
global.OffscreenCanvas = class OffscreenCanvas {
  constructor(width, height) {
    this.width = width;
    this.height = height;
  }
  
  getContext(contextType) {
    if (contextType === 'webgl' || contextType === 'webgl2') {
      return { ...mockWebGLRenderingContext, canvas: this };
    } else if (contextType === '2d') {
      return {
        fillRect: jest.fn(),
        clearRect: jest.fn(),
        getImageData: jest.fn(() => ({ data: new Array(4) })),
        putImageData: jest.fn(),
        createImageData: jest.fn(() => []),
        drawImage: jest.fn(),
        canvas: this,
        // Additional 2D context methods
        scale: jest.fn(),
        measureText: jest.fn(() => ({ width: 0 })),
        rect: jest.fn(),
        arc: jest.fn(),
        fill: jest.fn(),
        beginPath: jest.fn(),
        moveTo: jest.fn(),
        lineTo: jest.fn(),
        closePath: jest.fn(),
        stroke: jest.fn(),
        translate: jest.fn(),
        strokeText: jest.fn(),
        fillText: jest.fn(),
        restore: jest.fn(),
        save: jest.fn(),
        rotate: jest.fn(),
        createLinearGradient: jest.fn(() => ({
          addColorStop: jest.fn()
        })),
        createRadialGradient: jest.fn(() => ({
          addColorStop: jest.fn()
        })),
      };
    }
    return null;
  }
  
  transferToImageBitmap() {
    return {};
  }
};

// Longer timeout for async tests
jest.setTimeout(10000);

// Auto-restore mocks after each test
afterEach(() => {
  jest.restoreAllMocks();
});

// Mock the geocoding service that's causing test failures
jest.mock('@/services/geocoding', () => ({
  geocodeBirthPlace: jest.fn().mockResolvedValue({
    latitude: 51.5074,
    longitude: -0.1278,
    timezone: 'Europe/London'
  })
}), { virtual: true });

// Mock the Docker AI Service that's causing test failures
jest.mock('@/services/docker/DockerAIService', () => ({
  __esModule: true,
  default: {
    initializeContainer: jest.fn().mockResolvedValue(true),
    stopContainer: jest.fn().mockResolvedValue(true),
    getContainerStatus: jest.fn().mockResolvedValue({ 
      status: 'running', 
      message: 'Container is running'
    }),
    executeSwissEphemeris: jest.fn().mockResolvedValue({
      data: {
        positions: [
          { planet: 'Sun', sign: 'Aries', degree: 10 },
          { planet: 'Moon', sign: 'Taurus', degree: 15 }
        ]
      }
    })
  }
}), { virtual: true });

// Mock modules with path aliases
jest.mock('@/lib/utils', () => ({
  cn: jest.fn((...args) => args.join(' ').trim()),
  formatDate: jest.fn((date) => date ? new Date(date).toLocaleDateString() : ''),
  formatTime: jest.fn((time) => time || '')
}), { virtual: true }); 