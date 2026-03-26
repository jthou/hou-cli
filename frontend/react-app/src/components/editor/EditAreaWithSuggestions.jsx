/**
 * 编辑区：textarea + 写作建议浮层
 * 供 MarkdownEditorPreview、WikitextEditorPreview 复用
 */
import WritingSuggestionsPopover from '../WritingSuggestionsPopover'
import { TEXTAREA_CLS } from './EditorConstants'

/**
 * @param {Object} props
 * @param {React.RefObject} props.textareaRef
 * @param {string} props.value
 * @param {(v: string) => void} props.onChange
 * @param {string} props.placeholder
 * @param {Object} props.writingSuggestions - useWritingSuggestions 返回值
 * @param {string} [props.rootClassName] - 外层容器 class（默认带 min-h-[280px]）
 * @param {string} [props.textareaClassName] - textarea class（默认 TEXTAREA_CLS）
 * @param {(e: { currentTarget: HTMLTextAreaElement }) => void} [props.onTextareaScroll] - 编辑区滚动（用于与预览联动）
 * @param {(e: { currentTarget: HTMLTextAreaElement }) => void} [props.onTextareaBlur] - 失焦时保存选区，供外部按钮在光标处插入
 * @param {(e: { currentTarget: HTMLTextAreaElement }) => void} [props.onTextareaSelect] - 选区变化（与 blur 配合）
 */
export default function EditAreaWithSuggestions({
  textareaRef,
  value,
  onChange,
  placeholder,
  writingSuggestions,
  rootClassName,
  textareaClassName,
  onTextareaScroll,
  onTextareaBlur,
  onTextareaSelect,
}) {
  const rootCls = rootClassName ?? 'flex-1 min-h-[280px] flex flex-col gap-2 relative'
  const taCls = textareaClassName ?? TEXTAREA_CLS
  return (
    <div className={rootCls}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={onTextareaScroll}
        onBlur={onTextareaBlur}
        onSelect={onTextareaSelect}
        placeholder={placeholder}
        className={taCls}
        spellCheck={false}
      />
      <WritingSuggestionsPopover
        visible={writingSuggestions.visible}
        suggestions={writingSuggestions.suggestions}
        loading={writingSuggestions.loading}
        position={writingSuggestions.position}
        selectedIndex={writingSuggestions.selectedIndex}
        onSelect={writingSuggestions.onSelect}
        onClose={writingSuggestions.onClose}
        onRefresh={writingSuggestions.fetchSuggestions}
      />
    </div>
  )
}
