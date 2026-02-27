import TaskFormPage from '../components/task/TaskFormPage'

export default function VideoExtractAudio() {
  return (
    <TaskFormPage
      taskType="video_extract_audio"
      title="视频提取音频"
      description="从本地视频文件中提取音频轨并保存为音频文件。提交后任务将加入队列，可在"
      submitLabel="提交任务"
    />
  )
}
