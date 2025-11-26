const globalCrypto: Crypto | undefined =
  typeof window !== 'undefined' ? window.crypto : (globalThis as { crypto?: Crypto }).crypto

/**
 * 生成UUID，兼容不支持 crypto.randomUUID 的环境
 */
export function generateUUID(): string {
  try {
    if (globalCrypto?.randomUUID) {
      return globalCrypto.randomUUID()
    }
    if (globalCrypto?.getRandomValues) {
      const buffer = new Uint8Array(16)
      globalCrypto.getRandomValues(buffer)
      buffer[6] = (buffer[6] & 0x0f) | 0x40
      buffer[8] = (buffer[8] & 0x3f) | 0x80
      const hex = Array.from(buffer, (b) => b.toString(16).padStart(2, '0')).join('')
      return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
    }
  } catch {}
  // 最后兜底：使用 Math.random 生成（碰撞风险低，可接受）
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

