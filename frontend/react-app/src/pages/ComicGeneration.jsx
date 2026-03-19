import TaskTypePage from '../components/task/TaskTypePage'

export default function ComicGeneration() {
  return (
    <TaskTypePage
      taskType="comic"
      title="漫画生成"
      description="将文章或故事转化为知识漫画（基于 baoyu-comic）。支持 TheTurbo.ai、万相图生。需 ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY，及 .baoyu-skills/.env 中图生 API（DASHSCOPE 万相等）。"
      submitLabel="提交生成"
      listTitle="漫画生成任务"
      emptyText="暂无漫画生成任务"
    />
  )
}
