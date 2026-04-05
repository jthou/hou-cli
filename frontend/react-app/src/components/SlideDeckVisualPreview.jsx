/**
 * slide_deck JSON → 预览（企业 PPT 模板风）
 * - 顶栏：经典演示蓝 + 白字标题（对齐参考里的色块标题栏 + 白底正文）
 * - 正文：白/近白底 + 深色正文；右侧浅蓝区作「图示/配图」占位
 * - 讲述区仍在画框下方
 * - 幻灯片外框与片内块均为直角（与 PowerPoint 幻灯片一致，无圆角）
 *
 * .ppt-slide-canvas：保证顶栏上的 text-white 在浅色站点主题下不被全局规则覆盖
 */
function sortSlides(slides) {
  const valid = (slides || []).filter(s => s && typeof s === 'object')
  return [...valid].sort((a, b) => {
    const ai = Number.isFinite(Number(a.index)) ? Number(a.index) : 1e9
    const bi = Number.isFinite(Number(b.index)) ? Number(b.index) : 1e9
    return ai - bi
  })
}

function bulletParts(b) {
  if (b && typeof b === 'object' && ('text' in b || 'point' in b)) {
    const t = String(b.text ?? b.point ?? '').trim()
    const e = String(b.speaker_elaboration ?? b.elaboration ?? '').trim()
    const hint = String(b.slide_hint ?? b.hint ?? b.short_prompt ?? '').trim()
    return { t, e, hint }
  }
  return { t: String(b ?? '').trim(), e: '', hint: '' }
}

const KIND_LABEL = {
  title: '封面',
  content: '内容',
  transition: '过渡',
  closing: '结尾',
}

const TEXT_SCHEME = {
  BULLETS: 'bullets',
  TITLE_ONLY: 'title_only',
  LONG_PROSE: 'long_prose',
  TITLE_LEAD: 'title_lead',
  TITLE_SUBTITLE_LEAD: 'title_subtitle_lead',
}

function slideLeadText(s) {
  return String(s?.lead ?? s?.body_summary ?? '').trim()
}

function slideSubtitleText(s) {
  return String(s?.subtitle ?? '').trim()
}

function slideBodyLongText(s) {
  const bt = String(s?.body_text ?? '').trim()
  if (bt) return bt
  const bullets = Array.isArray(s?.bullets) ? s.bullets : []
  if (bullets.length !== 1) return ''
  const { t, e, hint } = bulletParts(bullets[0])
  return [t, hint, e].filter(Boolean).join('\n\n').trim()
}

function normTextScheme(raw) {
  const x = String(raw || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
  const aliases = {
    classic: 'bullets',
    bullets_classic: 'bullets',
    title_short: 'title_lead',
    title_subtitle_short: 'title_subtitle_lead',
  }
  return aliases[x] || x
}

/** 与 backend slide_text_layout.effective_text_scheme 对齐 */
function effectiveTextScheme(s) {
  if (!s || typeof s !== 'object') return TEXT_SCHEME.BULLETS
  const raw = normTextScheme(s.text_scheme)
  if (Object.values(TEXT_SCHEME).includes(raw)) return raw
  const subtitle = slideSubtitleText(s)
  const lead = slideLeadText(s)
  const bodyLong = slideBodyLongText(s)
  const bullets = Array.isArray(s.bullets) ? s.bullets : []
  const nBullets = bullets.filter(b => bulletParts(b).t).length
  if (subtitle && lead) return TEXT_SCHEME.TITLE_SUBTITLE_LEAD
  if (lead && nBullets === 0) return TEXT_SCHEME.TITLE_LEAD
  if (bodyLong && nBullets === 0) return TEXT_SCHEME.LONG_PROSE
  if (nBullets === 0 && !lead && !bodyLong && !subtitle) return TEXT_SCHEME.TITLE_ONLY
  return TEXT_SCHEME.BULLETS
}

function collectNarrative(s, bullets) {
  const notes = String(s.speaker_notes || '').trim()
  const elaborations = []
  if (Array.isArray(bullets)) {
    for (const b of bullets) {
      const { t, e } = bulletParts(b)
      if (t && e) elaborations.push({ t, e })
    }
  }
  if (!notes && elaborations.length === 0) return null
  return { notes, elaborations }
}

/** 与参考图一致的「演示蓝」梯队（近 PowerPoint / 企业模板） */
const PPT = {
  headerGradient: 'linear-gradient(180deg, #5B9BD5 0%, #4A8AC4 48%, #3E7AB8 100%)',
  coverGradient: 'linear-gradient(165deg, #4F85C9 0%, #5B9BD5 42%, #6FA8DC 100%)',
  bodyBg: '#ffffff',
  bodyAlt: '#f9fafb',
  rightPanel: '#E8F1FA',
  rightPanelEdge: '#B8D4EE',
  borderOuter: 'rgba(15, 23, 42, 0.12)',
  text: '#1e293b',
  textMuted: '#64748b',
  bullet: '#2E75B6',
}

const slideFont =
  'ui-sans-serif, system-ui, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif'

/** slideImageUrls: 页 index → 配图 URL（通常为 /api/ppt-assistant/slide-images/file/...） */
export default function SlideDeckVisualPreview({ deck, slideImageUrls = {}, className = '' }) {
  if (!deck || !Array.isArray(deck.slides) || deck.slides.length === 0) {
    return (
      <div
        className={`flex items-center justify-center min-h-[180px] text-muted text-sm px-4 text-center ${className}`}
      >
        尚无幻灯片数据：请使用「一键」或「生成页面」得到 slide_deck 后，此处将显示 16:9 版式预览。
      </div>
    )
  }

  const deckTitle = String(deck.deck_title || '演示').trim() || '演示'
  const slides = sortSlides(deck.slides)

  /* 与真实幻灯片一致：外框直角，无圆角 */
  const frameClass =
    'ppt-slide-canvas relative overflow-hidden rounded-none aspect-video flex flex-col shadow-[0_14px_40px_-12px_rgba(15,23,42,0.35)] ring-1 ring-slate-900/10'

  return (
    <div className={`flex flex-col gap-10 ${className}`}>
      {slides.map((s, i) => {
        const kind = String(s.kind || 'content').trim() || 'content'
        const idx = s.index != null && Number.isFinite(Number(s.index)) ? Number(s.index) : i + 1
        const stitle = String(s.title || '').trim() || `第 ${idx} 页`
        const isCover = i === 0 && kind === 'title'
        const bullets = Array.isArray(s.bullets) ? s.bullets : []
        const kindZh = KIND_LABEL[kind] || kind
        const isTransition = kind === 'transition'
        const narrative = collectNarrative(s, bullets)
        const genSrc = slideImageUrls[idx] || slideImageUrls[String(idx)]
        const bodyScheme = effectiveTextScheme(s)
        const leadVis = slideLeadText(s)
        const subVis = slideSubtitleText(s)
        const longVis = slideBodyLongText(s)

        return (
          <div key={`slide-${idx}-${i}`} className="flex flex-col gap-2 w-full max-w-4xl mx-auto">
            <div className="px-1 text-[11px] text-muted tabular-nums">
              第 {idx} 页 · {kindZh}
            </div>

            {genSrc ? (
              <div
                className={`${frameClass} border border-slate-200/90 bg-black`}
                aria-label="百炼整页配图预览（与导出 pptx 满幅一致）"
              >
                <img
                  src={genSrc}
                  alt=""
                  className="absolute inset-0 h-full w-full object-cover"
                />
                <div className="pointer-events-none absolute right-2 top-2 bg-black/60 px-2 py-0.5 text-[10px] font-medium text-white/95">
                  百炼配图
                </div>
              </div>
            ) : isCover ? (
              <div
                className={`${frameClass} border border-slate-200/90`}
                style={{ fontFamily: slideFont, background: PPT.coverGradient }}
                aria-label="幻灯片画面"
              >
                <div className="absolute inset-0 pointer-events-none opacity-[0.18] bg-[radial-gradient(ellipse_80%_60%_at_50%_20%,white,transparent)]" />
                <div className="relative flex flex-col flex-1 items-center justify-center text-center px-8 sm:px-14 py-10">
                  <p className="text-[10px] sm:text-[11px] uppercase tracking-[0.35em] text-white/85 mb-4 font-semibold">
                    Presentation
                  </p>
                  <h2 className="text-white text-2xl sm:text-[1.85rem] font-bold leading-[1.3] tracking-tight max-w-[95%] drop-shadow-sm">
                    {stitle}
                  </h2>
                  <div className="mt-8 max-w-xl w-full h-px bg-white/35" />
                  <p className="mt-6 text-base sm:text-lg text-white/95 font-normal leading-relaxed">{deckTitle}</p>
                </div>
                <div
                  className="shrink-0 h-1.5 bg-white/95 border-t border-white/40"
                  aria-hidden
                />
              </div>
            ) : isTransition ? (
              <div
                className={`${frameClass} border border-slate-200/90 bg-white`}
                style={{ fontFamily: slideFont }}
                aria-label="幻灯片画面"
              >
                <header
                  className="shrink-0 flex items-center min-h-[3.5rem] sm:min-h-[4rem] px-6 sm:px-9 py-3 sm:py-3.5 shadow-[inset_0_-2px_0_rgba(0,0,0,0.07)]"
                  style={{ background: PPT.headerGradient }}
                >
                  <h3 className="text-white text-base sm:text-lg font-bold leading-snug line-clamp-2">
                    {stitle}
                  </h3>
                </header>
                <div
                  className="flex-1 flex flex-col items-center justify-center px-8"
                  style={{ background: `linear-gradient(180deg, ${PPT.bodyAlt} 0%, ${PPT.bodyBg} 28%)` }}
                >
                  <p className="text-sm font-medium" style={{ color: PPT.textMuted }}>
                    章节过渡
                  </p>
                </div>
              </div>
            ) : (
              <div
                className={`${frameClass} border border-slate-200/90 bg-white`}
                style={{ fontFamily: slideFont }}
                aria-label="幻灯片画面"
              >
                {/* 顶栏：标题（与参考图一致） */}
                <header
                  className="shrink-0 flex items-center min-h-[3.5rem] sm:min-h-[4rem] px-6 sm:px-9 py-3 sm:py-3.5 shadow-[inset_0_-2px_0_rgba(0,0,0,0.07)]"
                  style={{ background: PPT.headerGradient }}
                >
                  <h3 className="text-white text-base sm:text-[1.05rem] font-bold leading-snug line-clamp-2">
                    {stitle}
                  </h3>
                </header>

                <div className="flex-1 min-h-0 flex flex-col sm:flex-row">
                  {/* 左侧：要点（白底） */}
                  <div
                    className="flex-1 min-h-0 min-w-0 sm:max-w-[58%] px-6 sm:px-9 py-5 sm:py-6 overflow-y-auto border-b sm:border-b-0 sm:border-r border-slate-200/90"
                    style={{
                      background: `linear-gradient(180deg, ${PPT.bodyBg} 0%, ${PPT.bodyAlt} 100%)`,
                    }}
                  >
                    {bodyScheme === TEXT_SCHEME.TITLE_ONLY ? (
                      <p className="text-sm italic" style={{ color: PPT.textMuted }}>
                        （本页仅有大标题）
                      </p>
                    ) : bodyScheme === TEXT_SCHEME.TITLE_LEAD ? (
                      <p className="text-[15px] sm:text-[16px] leading-relaxed font-medium" style={{ color: PPT.text }}>
                        {leadVis || '（无短说明）'}
                      </p>
                    ) : bodyScheme === TEXT_SCHEME.TITLE_SUBTITLE_LEAD ? (
                      <div className="space-y-3">
                        <h4
                          className="text-[13px] sm:text-sm font-bold tracking-wide uppercase"
                          style={{ color: PPT.bullet }}
                        >
                          {subVis || '（小标题）'}
                        </h4>
                        <p className="text-[15px] sm:text-[16px] leading-relaxed" style={{ color: PPT.text }}>
                          {leadVis || '（无短说明）'}
                        </p>
                      </div>
                    ) : bodyScheme === TEXT_SCHEME.LONG_PROSE ? (
                      <div
                        className="text-[13px] sm:text-[14px] leading-relaxed space-y-3 whitespace-pre-wrap"
                        style={{ color: PPT.text }}
                      >
                        {longVis || '（无长说明正文）'}
                      </div>
                    ) : (
                      <ul
                        className="space-y-2.5 sm:space-y-3 text-[14px] sm:text-[15px] leading-relaxed"
                        style={{ color: PPT.text }}
                      >
                        {bullets.length === 0 ? (
                          <li className="italic" style={{ color: PPT.textMuted }}>
                            （无要点）
                          </li>
                        ) : (
                          bullets.map((b, bi) => {
                            const { t, hint } = bulletParts(b)
                            if (!t) return null
                            return (
                              <li key={bi} className="flex gap-3 items-start">
                                <span
                                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
                                  style={{ backgroundColor: PPT.bullet }}
                                  aria-hidden
                                />
                                <div className="min-w-0 flex-1">
                                  <span className="font-medium text-[#2E75B6] block leading-snug">{t}</span>
                                  {hint ? (
                                    <p
                                      className="mt-1.5 text-[12px] sm:text-[13px] leading-relaxed"
                                      style={{ color: PPT.text }}
                                    >
                                      {hint}
                                    </p>
                                  ) : null}
                                </div>
                              </li>
                            )
                          })
                        )}
                      </ul>
                    )}
                  </div>

                  {/* 右侧：浅蓝天色块 + 配图占位（对应参考图右侧图示区） */}
                  <div
                    className="relative shrink-0 sm:flex-1 min-h-[6rem] sm:min-h-0 flex flex-col"
                    style={{
                      background: `linear-gradient(145deg, ${PPT.rightPanel} 0%, #dceaf7 50%, #d4e4f5 100%)`,
                      borderLeft: `1px solid ${PPT.rightPanelEdge}`,
                    }}
                  >
                    <div className="absolute inset-0 opacity-[0.35] pointer-events-none bg-[repeating-linear-gradient(-12deg,transparent,transparent_12px,rgba(255,255,255,0.35)_12px,rgba(255,255,255,0.35)_13px)]" />
                    <div className="relative flex-1 flex items-center justify-center p-4 sm:p-5">
                      <div
                        className="w-full max-w-[14rem] sm:max-w-none rounded-none border-2 border-dashed flex flex-col items-center justify-center gap-2 px-4 py-6 text-center shadow-inner bg-white/50"
                        style={{ borderColor: PPT.rightPanelEdge }}
                      >
                        <svg
                          width="36"
                          height="36"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke={PPT.bullet}
                          strokeWidth="1.25"
                          className="opacity-75"
                          aria-hidden
                        >
                          <rect x="3" y="3" width="18" height="18" rx="0" />
                          <circle cx="8.5" cy="8.5" r="1.5" fill={PPT.bullet} stroke="none" />
                          <path d="M21 15l-5-5L5 21" />
                        </svg>
                        <span className="text-[12px] font-semibold" style={{ color: PPT.text }}>
                          图示 / 配图区
                        </span>
                        <span className="text-[11px] leading-snug max-w-[12rem]" style={{ color: PPT.textMuted }}>
                          导出 .pptx 后可粘贴架构图、截图或图表
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {narrative ? (
              <section
                className="rounded-none border border-border bg-surface/90 px-4 py-3 space-y-3 text-fg border-l-[4px] border-l-[#5B9BD5]"
                aria-label="讲述与备注"
              >
                <div className="text-[10px] uppercase tracking-[0.12em] text-muted font-semibold">
                  讲述（讲者备注 / 要点阐述 · 不出现在幻灯片画面上）
                </div>
                <div className="h-px bg-border/80" />
                {narrative.notes ? (
                  <div>
                    <p className="text-[11px] text-muted mb-1.5 font-medium">本页备注</p>
                    <p className="text-sm text-fg/90 leading-relaxed whitespace-pre-wrap">{narrative.notes}</p>
                  </div>
                ) : null}
                {narrative.elaborations.length ? (
                  <ul className="space-y-3 pt-1">
                    {narrative.elaborations.map((item, j) => (
                      <li key={j} className="text-sm">
                        <span className="font-semibold text-[#2E75B6]">{item.t}</span>
                        <p className="mt-1.5 text-xs text-muted leading-relaxed pl-0 border-l-2 border-border pl-3">
                          {item.e}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </section>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
