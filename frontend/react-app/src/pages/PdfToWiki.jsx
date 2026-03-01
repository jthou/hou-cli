import TaskFormPage from '../components/task/TaskFormPage'
import TaskListByTypePanel from '../components/TaskListByTypePanel'

export default function PdfToWiki() {
  return (
    <TaskFormPage
      taskType="pdf_to_wiki"
      title="PDF 转 Wiki"
      description="从 PDF URL 或本地路径读取，按页拆分、转文字、翻译后写入 MediaWiki。可选单页汇总或目录页+多子页。"
      submitLabel="提交任务"
      rightContent={
        <TaskListByTypePanel
          taskType="pdf_to_wiki"
          title="PDF 转 Wiki 任务"
          emptyText="暂无 PDF 转 Wiki 任务"
        />
      }
    />
  )
}
