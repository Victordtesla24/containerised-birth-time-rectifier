/**
 * Logger Utility
 *
 * Provides standardized logging functions for the Birth Time Rectifier application.
 * Handles different log levels and formats consistently.
 */

// Define log levels
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

// Logger options type
export type LoggerOptions = {
  level?: 'debug' | 'info' | 'warn' | 'error';
  timestamp?: boolean;
};

// Default log level in production is INFO, but in development it's DEBUG
const DEFAULT_LOG_LEVEL = process.env.NODE_ENV === 'production' ? LogLevel.INFO : LogLevel.DEBUG;
const DEFAULT_TIMESTAMP = process.env.NODE_ENV === 'production';

// Get current log level from environment or use default
const getCurrentLogLevel = (): LogLevel => {
  const envLogLevel = process.env.NEXT_PUBLIC_LOG_LEVEL;
  if (envLogLevel) {
    switch (envLogLevel.toLowerCase()) {
      case 'debug':
        return LogLevel.DEBUG;
      case 'info':
        return LogLevel.INFO;
      case 'warn':
        return LogLevel.WARN;
      case 'error':
        return LogLevel.ERROR;
      default:
        return DEFAULT_LOG_LEVEL;
    }
  }
  return DEFAULT_LOG_LEVEL;
};

// Current log level and timestamp setting
let currentLogLevel = getCurrentLogLevel();
let includeTimestamp = DEFAULT_TIMESTAMP;

// Convert string level to LogLevel enum
const stringToLogLevel = (level: string): LogLevel => {
  switch (level.toLowerCase()) {
    case 'debug':
      return LogLevel.DEBUG;
    case 'info':
      return LogLevel.INFO;
    case 'warn':
      return LogLevel.WARN;
    case 'error':
      return LogLevel.ERROR;
    default:
      return DEFAULT_LOG_LEVEL;
  }
};

// Format log message with optional timestamp
const formatMessage = (...args: any[]): string => {
  // Convert objects to string representation
  const formattedArgs = args.map(arg => {
    if (arg instanceof Error) {
      return `${arg.toString()}${arg.stack ? '\n' + arg.stack : ''}`;
    } else if (typeof arg === 'object') {
      return JSON.stringify(arg);
    }
    return String(arg);
  });

  return formattedArgs.join(' ') + ' ';
};

// Log to console with appropriate level
const log = (level: LogLevel, ...args: any[]): void => {
  if (level < currentLogLevel) {
    return;
  }

  let logMethod: (...args: any[]) => void;

  switch (level) {
    case LogLevel.DEBUG:
      logMethod = console.debug;
      break;
    case LogLevel.INFO:
      logMethod = console.info;
      break;
    case LogLevel.WARN:
      logMethod = console.warn;
      break;
    case LogLevel.ERROR:
      logMethod = console.error;
      break;
    default:
      logMethod = console.log;
  }

  let message = formatMessage(...args);

  // Add timestamp if enabled
  if (includeTimestamp) {
    const timestamp = new Date().toISOString();
    message = `[${timestamp}] ${message}`;
  }

  logMethod(message);
};

// Create logger object with level-specific methods
export const logger = {
  debug: (...args: any[]) => log(LogLevel.DEBUG, ...args),
  info: (...args: any[]) => log(LogLevel.INFO, ...args),
  warn: (...args: any[]) => log(LogLevel.WARN, ...args),
  error: (...args: any[]) => log(LogLevel.ERROR, ...args),
  setLogLevel: (level: LogLevel) => {
    currentLogLevel = level;
  },
  getLogLevel: (): LogLevel => currentLogLevel,
  setOptions: (options: LoggerOptions) => {
    if (options.level) {
      currentLogLevel = stringToLogLevel(options.level);
    }
    if (options.timestamp !== undefined) {
      includeTimestamp = options.timestamp;
    }
  }
};

export default logger;
