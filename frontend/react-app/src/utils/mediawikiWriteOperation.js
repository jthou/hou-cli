/**
 * 写入 MediaWiki 弹窗三态 → API metadata.operation（与 task_handlers mediawiki_write 一致）。
 * 时间：2026-03-13；理由：区分新建 / 更新覆盖 / 追加；方法：create | edit | append。
 *
 * @param {'create'|'edit'|'append'} mode
 * @returns {'create'|'edit'|'append'}
 */
export function operationFromMwDialogMode(mode) {
  if (mode === 'append') return 'append'
  if (mode === 'create') return 'create'
  return 'edit'
}
