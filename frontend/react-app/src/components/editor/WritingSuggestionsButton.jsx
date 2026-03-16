/**
 * 写作建议触发按钮，右对齐
 */
export default function WritingSuggestionsButton({ onClick, loading }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="ml-auto text-xs px-2 py-1 rounded border border-border text-muted hover:bg-white/10 hover:text-fg disabled:opacity-50"
    >
      写作建议
    </button>
  )
}
