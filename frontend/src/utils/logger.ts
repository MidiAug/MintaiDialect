/**
 * 统一日志工具
 * 提供统一的日志输出格式，时间精确到毫秒（不包含日期）
 */

type LogLevel = 'log' | 'info' | 'warn' | 'error' | 'debug'

/**
 * 获取当前时间戳（格式：HH:mm:ss.SSS）
 */
function getTimestamp(): string {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  const milliseconds = String(now.getMilliseconds()).padStart(3, '0')
  return `${hours}:${minutes}:${seconds}.${milliseconds}`
}

/**
 * 格式化日志消息
 */
function formatMessage(level: LogLevel, message: string, tag?: string): string {
  const timestamp = getTimestamp()
  const levelUpper = level.toUpperCase().padEnd(5)
  const tagPart = tag ? `[${tag}]` : ''
  return `[${timestamp}] ${levelUpper} ${tagPart} ${message}`
}

/**
 * 日志工具类
 */
class Logger {
  private tag?: string

  constructor(tag?: string) {
    this.tag = tag
  }

  /**
   * 创建带标签的Logger实例
   */
  static create(tag: string): Logger {
    return new Logger(tag)
  }

  /**
   * 通用日志方法（内部方法）
   */
  private logInternal(level: LogLevel, message: string, ...args: any[]): void {
    const formattedMessage = formatMessage(level, message, this.tag)
    
    switch (level) {
      case 'error':
        console.error(formattedMessage, ...args)
        break
      case 'warn':
        console.warn(formattedMessage, ...args)
        break
      case 'info':
        console.info(formattedMessage, ...args)
        break
      case 'debug':
        console.debug(formattedMessage, ...args)
        break
      default:
        console.log(formattedMessage, ...args)
    }
  }

  /**
   * 普通日志
   */
  log(message: string, ...args: any[]): void {
    this.logInternal('log', message, ...args)
  }

  /**
   * 信息日志
   */
  info(message: string, ...args: any[]): void {
    this.logInternal('info', message, ...args)
  }

  /**
   * 警告日志
   */
  warn(message: string, ...args: any[]): void {
    this.logInternal('warn', message, ...args)
  }

  /**
   * 错误日志
   */
  error(message: string, ...args: any[]): void {
    this.logInternal('error', message, ...args)
  }

  /**
   * 调试日志
   */
  debug(message: string, ...args: any[]): void {
    this.logInternal('debug', message, ...args)
  }
}

/**
 * 默认Logger实例（无标签）
 */
const defaultLogger = new Logger()

/**
 * 导出默认Logger实例和Logger类
 */
export default defaultLogger

/**
 * 导出Logger类，用于创建带标签的Logger实例
 */
export { Logger }

/**
 * 便捷方法：直接使用默认Logger
 */
export const logger = {
  log: (message: string, ...args: any[]) => defaultLogger.log(message, ...args),
  info: (message: string, ...args: any[]) => defaultLogger.info(message, ...args),
  warn: (message: string, ...args: any[]) => defaultLogger.warn(message, ...args),
  error: (message: string, ...args: any[]) => defaultLogger.error(message, ...args),
  debug: (message: string, ...args: any[]) => defaultLogger.debug(message, ...args),
  /**
   * 创建带标签的Logger
   */
  create: (tag: string) => Logger.create(tag),
}

