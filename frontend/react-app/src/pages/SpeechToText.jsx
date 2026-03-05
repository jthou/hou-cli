import TaskTypePage from '../components/task/TaskTypePage'

export default function SpeechToText() {
  return (
    <TaskTypePage
      taskType="speech_to_text"
      title="字幕提取"
      description="使用 Whisper 将音频文件转成文字或字幕（支持 mp3、wav、m4a、flac 等）。提交后任务将加入队列，可在"
      submitLabel="提交任务"
      listTitle="字幕提取任务"
      emptyText="暂无字幕提取任务"
    />
  )
}
