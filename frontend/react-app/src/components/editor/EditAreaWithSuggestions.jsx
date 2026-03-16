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
 */
export default function EditAreaWithSuggestions({
  textareaRef,
  value,
  onChange,
  placeholder,
  writingSuggestions,
}) {
  return (
    <div className="flex-1 min-h-[280px] flex flex-col gap-2 relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={TEXTAREA_CLS}
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
