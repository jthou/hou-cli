import TaskFormPage from '../components/task/TaskFormPage'

export default function UrlToWiki() {
  return (
    <TaskFormPage
      taskType="url_to_wiki"
      title="网文抓取"
      description="抓取指定 URL 正文，翻译成中文后写入 MediaWiki。可在"
      submitLabel="提交任务"
    />
  )
}
