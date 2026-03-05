import TaskTypePage from '../components/task/TaskTypePage'

export default function ImageGeneration() {
  return (
    <TaskTypePage
      taskType="image_generation"
      title="图片生成"
      description="根据文本描述生成图片。请输入简短描述（50–200 字）。支持万相、通义等模型。"
      submitLabel="提交生成"
      listTitle="图片生成任务"
      emptyText="暂无图片生成任务"
    />
  )
}
