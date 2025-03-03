interface LoggerOptions {
  level: 'debug' | 'info' | 'warn' | 'error';
  timestamp?: boolean;
}

class Logger {
  private static instance: Logger;
  private options: LoggerOptions;

  private constructor() {
    this.options = {
      level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
      timestamp: true
    };
  }

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private getTimestamp(): string {
    return this.options.timestamp ? `[${new Date().toISOString()}] ` : '';
  }

  private formatMessage(message: string, ...args: any[]): string {
    const timestamp = this.getTimestamp();
    const formattedArgs = args.map(arg => 
      arg instanceof Error ? arg.stack : 
      typeof arg === 'object' ? JSON.stringify(arg) : 
      String(arg)
    ).join(' ');
    return `${timestamp}${message}${formattedArgs ? ' ' + formattedArgs + ' ' : ' '}`;
  }

  public debug(message: string, ...args: any[]): void {
    if (this.options.level === 'debug') {
      console.debug(this.formatMessage(message, ...args));
    }
  }

  public info(message: string, ...args: any[]): void {
    if (['debug', 'info'].includes(this.options.level)) {
      console.info(this.formatMessage(message, ...args));
    }
  }

  public warn(message: string, ...args: any[]): void {
    if (['debug', 'info', 'warn'].includes(this.options.level)) {
      console.warn(this.formatMessage(message, ...args));
    }
  }

  public error(message: string, ...args: any[]): void {
    console.error(this.formatMessage(message, ...args));
  }

  public setOptions(options: Partial<LoggerOptions>): void {
    this.options = { ...this.options, ...options };
  }
}

export const logger = Logger.getInstance(); 