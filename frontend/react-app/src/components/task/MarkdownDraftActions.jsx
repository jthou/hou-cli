/**
 * Markdown 草稿的预览与操作：复制、发送到写文章、添加到参考、写入 MediaWiki
 * 供 url_to_wiki、pdf_to_wiki 等产出 Markdown 草稿的任务结果复用。
 * 基于 DraftPreviewActions 的 Markdown 格式封装。
 */
import DraftPreviewActions from './DraftPreviewActions'

export default function MarkdownDraftActions({
  markdown,
  sourceUrl,
  suggestTitle,
  sourceType = 'url_to_wiki',
  summaryText = '查看 Markdown 草稿与后续操作',
  onWriteSuccess,
}) {
  return (
    <DraftPreviewActions
      content={markdown}
      format="markdown"
      copyLabel="复制 Markdown"
      suggestTitle={suggestTitle}
      sourceUrl={sourceUrl}
      sourceType={sourceType}
      summaryText={summaryText}
      onWriteSuccess={onWriteSuccess}
    />
  )
}
