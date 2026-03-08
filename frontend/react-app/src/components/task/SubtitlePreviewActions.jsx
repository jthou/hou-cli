/**
 * 字幕预览与操作：复制、发送到写作助手、添加到参考、写入 MediaWiki
 * 基于 DraftPreviewActions 的纯文本格式封装。
 */
import DraftPreviewActions from './DraftPreviewActions'

export default function SubtitlePreviewActions({
  content,
  suggestTitle,
  summaryText = '查看字幕与后续操作',
  onWriteSuccess,
}) {
  return (
    <DraftPreviewActions
      content={content}
      format="text"
      copyLabel="复制字幕"
      suggestTitle={suggestTitle}
      sourceType="speech_to_text"
      summaryText={summaryText}
      onWriteSuccess={onWriteSuccess}
    />
  )
}
