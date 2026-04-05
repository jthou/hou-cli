/**
 * 流式 SSE 正文过滤：后端控制帧不得进入用户可见 Markdown。
 *
 * 时间：2026-03-13；理由：ENABLE_EVALUATION 等会经流式下发 __EVALUATION__，拼进正文会像「多答一份」；多段 done 在 GeneralChat 曾重复追加助手气泡；方法：与 backend/api/stream_sender.py StreamMessageBuilder 前缀对齐。
 */

/** @param {string} raw */
export function isOrchestratorControlChunk(raw) {
  if (raw == null || typeof raw !== 'string') return true
  return (
    raw.startsWith('__DEBUG__:') ||
    raw.startsWith('__STATUS__:') ||
    raw.startsWith('__ORCH_TRACE__:') ||
    raw.startsWith('__TOOL__:') ||
    raw.startsWith('__CTX_META__:') ||
    raw.startsWith('__EVALUATION__:') ||
    raw.startsWith('__REASONING__:')
  )
}
