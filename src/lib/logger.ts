/**
 * Simple logger utility for consistent logging across the application
 */

// Log levels
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// Log entry with metadata
interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  data?: any;
}

// Environment-aware logging
const isDev = process.env.NODE_ENV !== 'production';

/**
 * Format log data for output
 */
const formatLogData = (data: any): string => {
  if (!data) return '';
  try {
    return JSON.stringify(data);
  } catch (e) {
    return `[Unstringifiable data: ${typeof data}]`;
  }
};

/**
 * Create a log entry
 */
const createLogEntry = (level: LogLevel, message: string, data?: any): LogEntry => ({
  level,
  message,
  timestamp: new Date().toISOString(),
  data
});

/**
 * Output a log entry to the console
 */
const outputLog = (entry: LogEntry): void => {
  const { level, message, timestamp, data } = entry;

  // In development, show all logs
  // In production, filter out debug logs
  if (!isDev && level === 'debug') return;

  const formattedData = data ? ` ${formatLogData(data)}` : '';
  const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}${formattedData}`;

  switch (level) {
    case 'debug':
      console.debug(logMessage);
      break;
    case 'info':
      console.info(logMessage);
      break;
    case 'warn':
      console.warn(logMessage);
      break;
    case 'error':
      console.error(logMessage);
      break;
  }
};

/**
 * Logger interface
 */
export const logger = {
  debug: (message: string, data?: any) => {
    outputLog(createLogEntry('debug', message, data));
  },

  info: (message: string, data?: any) => {
    outputLog(createLogEntry('info', message, data));
  },

  warn: (message: string, data?: any) => {
    outputLog(createLogEntry('warn', message, data));
  },

  error: (message: string, data?: any) => {
    outputLog(createLogEntry('error', message, data));
  }
};
