import TaskTypePage from '../components/task/TaskTypePage'

export default function PdfToWiki() {
  return (
    <TaskTypePage
      taskType="pdf_to_wiki"
      title="PDF转Wiki"
      description="从 PDF URL 或本地路径读取，按页拆分、翻译后写入 MediaWiki。可选文本层（快）或页图识别 vision（扫描件/公式）。可单页汇总或目录页+多子页。"
      submitLabel="提交任务"
      listTitle="PDF 转 Wiki 任务"
      emptyText="暂无 PDF 转 Wiki 任务"
    />
  )
}
