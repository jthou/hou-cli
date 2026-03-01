import TaskFormPage from '../components/task/TaskFormPage'
import TaskListByTypePanel from '../components/TaskListByTypePanel'

export default function WebSearch() {
  return (
    <TaskFormPage
      taskType="web_search"
      title="网页搜索"
      description="使用 DuckDuckGo 执行关键词搜索，支持定时执行。提交后任务将加入队列，可在"
      submitLabel="提交搜索"
      rightContent={
        <TaskListByTypePanel
          taskType="web_search"
          title="网页搜索任务"
          emptyText="暂无网页搜索任务"
        />
      }
    />
  )
}
