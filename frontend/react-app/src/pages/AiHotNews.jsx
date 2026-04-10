import TaskTypePage from '../components/task/TaskTypePage'

export default function AiHotNews() {
  return (
    <TaskTypePage
      taskType="ai_hot_news_digest"
      title="今日 AI 热点"
      description="由后台自动执行 5 轮网页检索（AI 资讯 / 模型发布 / 融资 / 监管 / 中文大模型），再调用 LLM 生成中文深度摘要。配置 TAVILY_API_KEY 时优先 Tavily，否则使用 DuckDuckGo。提交后可在"
      submitLabel="生成热点摘要"
      listTitle="今日 AI 热点任务"
      emptyText="暂无今日 AI 热点任务"
      topContent={
        <div className="mb-4 p-3 bg-white/5 border border-border rounded-lg text-sm text-muted space-y-2">
          <p>
            可选调整每轮检索条数（5～20）与语言代码；模型留空则使用环境默认对话模型。与 Cursor Skill{' '}
            <code className="text-cyan-300/90">ai-hot-news-summary</code> 口径一致。
          </p>
        </div>
      }
    />
  )
}
