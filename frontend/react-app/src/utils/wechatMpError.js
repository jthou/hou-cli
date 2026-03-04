/**
 * 微信公众号 API 错误格式化：40164 IP 白名单等错误时追加解决提示。
 */
export function formatWechatMpError(prefix, err) {
  const msg = err?.message || String(err)
  let display = prefix ? `${prefix}: ${msg}` : msg
  if (/40164|not in whitelist|invalid ip/i.test(msg)) {
    const ipMatch = msg.match(/(\d+\.\d+\.\d+\.\d+)/)
    const ip = ipMatch ? ipMatch[1] : ''
    const hint = ip
      ? `\n\n请将 IP ${ip} 添加到微信公众平台 IP 白名单：开发 → 基本配置 → IP 白名单`
      : '\n\n请将服务器出口 IP 添加到微信公众平台 IP 白名单：开发 → 基本配置 → IP 白名单'
    display += hint
  }
  return display
}
