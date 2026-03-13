import { useState } from 'react'
import TaskTypePage from '../components/task/TaskTypePage'

export default function WebSearch() {
  const [mode, setMode] = useState('compare')

  const isCompare = mode === 'compare'
  // 表单始终用 web_search 的 schema（query/num_results/language），确保有输入框
  // 提交时根据模式选择 task_type
  return (
    <TaskTypePage
      taskType="web_search"
      submitTaskType={isCompare ? 'web_search_compare' : 'web_search'}
      taskTypes={['web_search', 'web_search_compare']}
      title="网页搜索"
      description={
        isCompare
          ? '用 Tavily 和 DuckDuckGo 同时搜索相同关键词，结果分列展示便于对比。支持定时执行。'
          : '使用 DuckDuckGo 或 Tavily（有 key 时）执行关键词搜索，支持定时执行。提交后任务将加入队列，可在'
      }
      submitLabel={isCompare ? '对比搜索' : '提交搜索'}
      listTitle="网页搜索任务"
      emptyText="暂无网页搜索任务"
      topContent={
        <div className="mb-4 p-3 bg-white/5 border border-border rounded-lg">
          <label className="block text-sm text-muted mb-2">搜索模式</label>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="searchMode"
                checked={mode === 'compare'}
                onChange={() => setMode('compare')}
                className="text-accent focus:ring-accent"
              />
              <span className="text-white">对比搜索</span>
              <span className="text-muted text-xs">Tavily + DuckDuckGo 同时搜，结果分列</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="searchMode"
                checked={mode === 'single'}
                onChange={() => setMode('single')}
                className="text-accent focus:ring-accent"
              />
              <span className="text-white">单次搜索</span>
              <span className="text-muted text-xs">有 TAVILY_API_KEY 用 Tavily，否则 DuckDuckGo</span>
            </label>
          </div>
        </div>
      }
    />
  )
}
