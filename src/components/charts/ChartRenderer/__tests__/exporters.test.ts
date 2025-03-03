import { exportChart, ExportOptions } from '../exporters';
import { ChartData } from '@/types';

describe('Chart Exporters', () => {
  const mockCanvas = document.createElement('canvas');
  const mockData: ChartData = {
    ascendant: 0,
    planets: [],
    houses: [],
    divisionalCharts: {},
    aspects: []
  };

  beforeEach(() => {
    // Mock canvas methods with valid base64 PNG data
    const validBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
    mockCanvas.toDataURL = jest.fn(() => `data:image/png;base64,${validBase64}`);
    const mockContext = {
      canvas: mockCanvas,
      drawImage: jest.fn(),
      fillRect: jest.fn(),
      fillText: jest.fn(),
      beginPath: jest.fn(),
      arc: jest.fn(),
      stroke: jest.fn(),
      getContextAttributes: jest.fn(),
      globalAlpha: 1,
      globalCompositeOperation: 'source-over',
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high' as ImageSmoothingQuality,
      strokeStyle: '#000',
      fillStyle: '#000',
      shadowOffsetX: 0,
      shadowOffsetY: 0,
      shadowBlur: 0,
      shadowColor: 'rgba(0,0,0,0)',
      lineWidth: 1,
      lineCap: 'butt' as CanvasLineCap,
      lineJoin: 'miter' as CanvasLineJoin,
      miterLimit: 10,
      lineDashOffset: 0,
      font: '10px sans-serif',
      textAlign: 'start' as CanvasTextAlign,
      textBaseline: 'alphabetic' as CanvasTextBaseline,
      direction: 'ltr' as CanvasDirection,
      save: jest.fn(),
      restore: jest.fn(),
      scale: jest.fn(),
      rotate: jest.fn(),
      translate: jest.fn(),
      transform: jest.fn(),
      setTransform: jest.fn(),
      resetTransform: jest.fn(),
      createLinearGradient: jest.fn(),
      createRadialGradient: jest.fn(),
      createPattern: jest.fn(),
      clearRect: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      bezierCurveTo: jest.fn(),
      quadraticCurveTo: jest.fn(),
      closePath: jest.fn(),
      fill: jest.fn(),
      clip: jest.fn(),
      isPointInPath: jest.fn(),
      isPointInStroke: jest.fn(),
      measureText: jest.fn().mockReturnValue({ width: 10 }),
      setLineDash: jest.fn(),
      getLineDash: jest.fn().mockReturnValue([]),
      createImageData: jest.fn(),
      getImageData: jest.fn(),
      putImageData: jest.fn(),
      getTransform: jest.fn(),
      drawFocusIfNeeded: jest.fn(),
      scrollPathIntoView: jest.fn(),
    } as unknown as CanvasRenderingContext2D;

    mockCanvas.getContext = jest.fn().mockImplementation((contextId: string, _options?: any) => {
      switch (contextId) {
        case '2d':
          return mockContext;
        case 'bitmaprenderer':
          return {
            transferFromImageBitmap: jest.fn(),
            canvas: mockCanvas,
          } as unknown as ImageBitmapRenderingContext;
        case 'webgl':
        case 'webgl2':
          return {
            canvas: mockCanvas,
            drawingBufferWidth: 600,
            drawingBufferHeight: 600,
            getContextAttributes: jest.fn(),
            isContextLost: jest.fn(),
            getExtension: jest.fn(),
            getParameter: jest.fn(),
            getSupportedExtensions: jest.fn(),
          } as unknown as WebGLRenderingContext;
        default:
          return null;
      }
    });

    // Mock document methods with complete link element
    const mockLink = {
      click: jest.fn(),
      download: '',
      href: '',
      style: { display: 'none' },
    };
    document.createElement = jest.fn((tag: string) => {
      if (tag === 'a') return mockLink as any;
      if (tag === 'canvas') return mockCanvas;
      return document.createElement(tag);
    });

    // Mock URL methods
    global.URL.createObjectURL = jest.fn(() => 'blob:mock');
    global.URL.revokeObjectURL = jest.fn();
  });

  it('exports to PNG', async () => {
    const options: ExportOptions = {
      width: 600,
      height: 600,
      format: 'png',
      filename: 'test.png',
      quality: 1,
    };

    await exportChart(mockCanvas, mockData, options);

    expect(mockCanvas.toDataURL).toHaveBeenCalledWith('image/png', 1);
    expect(document.createElement).toHaveBeenCalledWith('a');
  });

  it('exports to SVG', async () => {
    const options: ExportOptions = {
      width: 600,
      height: 600,
      format: 'svg',
      filename: 'test.svg',
    };

    await exportChart(mockCanvas, mockData, options);

    expect(document.createElement).toHaveBeenCalledWith('a');
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it('exports to PDF', async () => {
    const options: ExportOptions = {
      width: 600,
      height: 600,
      format: 'pdf',
      filename: 'test.pdf',
    };

    await exportChart(mockCanvas, mockData, options);

    expect(mockCanvas.toDataURL).toHaveBeenCalledWith('image/png', 1.0);
  });

  it('uses default filename when not provided', async () => {
    const options: ExportOptions = {
      width: 600,
      height: 600,
      format: 'png',
    };

    await exportChart(mockCanvas, mockData, options);

    const link = document.createElement('a');
    expect(link.download).toBe('birth-chart.png');
  });

  it('handles export errors gracefully', async () => {
    const mockError = new Error('Export failed');
    mockCanvas.toDataURL = jest.fn(() => {
      throw mockError;
    });

    const options: ExportOptions = {
      width: 600,
      height: 600,
      format: 'png',
    };

    await expect(exportChart(mockCanvas, mockData, options)).rejects.toThrow(mockError);
  });
});
