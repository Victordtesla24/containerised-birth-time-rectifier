import { logger } from '../logger';

describe('Logger', () => {
  const originalConsole = { ...console };
  const mockConsole = {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  };

  beforeEach(() => {
    // Mock console methods
    Object.assign(console, mockConsole);
    
    // Reset logger options to default
    logger.setOptions({
      level: 'debug',
      timestamp: false
    });
  });

  afterEach(() => {
    // Restore original console
    Object.assign(console, originalConsole);
    jest.clearAllMocks();
  });

  describe('Log Levels', () => {
    it('should log debug messages when level is debug', () => {
      logger.debug('test debug');
      expect(console.debug).toHaveBeenCalledWith('test debug ');
    });

    it('should log info messages when level is debug or info', () => {
      logger.info('test info');
      expect(console.info).toHaveBeenCalledWith('test info ');

      logger.setOptions({ level: 'info' });
      logger.info('test info 2');
      expect(console.info).toHaveBeenCalledWith('test info 2 ');
    });

    it('should not log debug messages when level is info', () => {
      logger.setOptions({ level: 'info' });
      logger.debug('test debug');
      expect(console.debug).not.toHaveBeenCalled();
    });

    it('should always log error messages regardless of level', () => {
      ['debug', 'info', 'warn', 'error'].forEach(level => {
        logger.setOptions({ level: level as 'debug' | 'info' | 'warn' | 'error' });
        logger.error('test error');
        expect(console.error).toHaveBeenCalledWith('test error ');
      });
    });
  });

  describe('Message Formatting', () => {
    it('should format error objects correctly', () => {
      const error = new Error('test error');
      logger.error('Error occurred:', error);
      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('Error occurred: Error: test error')
      );
    });

    it('should format objects using JSON.stringify', () => {
      const obj = { test: 'value' };
      logger.info('Object:', obj);
      expect(console.info).toHaveBeenCalledWith('Object: {"test":"value"} ');
    });

    it('should handle multiple arguments', () => {
      logger.info('Multiple', 'arguments', 123);
      expect(console.info).toHaveBeenCalledWith('Multiple arguments 123 ');
    });

    it('should include timestamp when enabled', () => {
      logger.setOptions({ timestamp: true });
      logger.info('test');
      expect(console.info).toHaveBeenCalledWith(
        expect.stringMatching(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] test /)
      );
    });
  });

  describe('Singleton Pattern', () => {
    it('should maintain the same instance', () => {
      const { logger: logger2 } = require('../logger');
      expect(logger2).toBe(logger);
    });

    it('should maintain options across imports', () => {
      logger.setOptions({ level: 'warn' });
      const { logger: logger2 } = require('../logger');
      
      logger2.debug('test debug');
      expect(console.debug).not.toHaveBeenCalled();
      
      logger2.warn('test warn');
      expect(console.warn).toHaveBeenCalled();
    });
  });
}); 