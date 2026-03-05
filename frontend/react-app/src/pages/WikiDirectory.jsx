import TaskFormPage from '../components/task/TaskFormPage'

export default function WikiDirectory() {
  return (
    <TaskFormPage
      taskType="wiki_directory_refresh"
      title="Wiki 目录"
      description="根据任务记录（网文抓取、PDF 转 Wiki）生成并写入一个 Wiki 目录页，列出已写入的页面与来源。"
      submitLabel="刷新目录"
    />
  )
}
