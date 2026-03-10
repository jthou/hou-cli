import TaskTypePage from '../components/task/TaskTypePage'

export default function UrlToWiki() {
  return (
    <TaskTypePage
      taskType="url_to_wiki"
      title="网文抓取"
      description="抓取指定 URL 正文生成 Markdown 草稿；可选翻译后写入 MediaWiki。可在"
      submitLabel="提交任务"
      listTitle="网文抓取任务"
      emptyText="暂无网文抓取任务"
    />
  )
}
