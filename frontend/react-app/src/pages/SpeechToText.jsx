import TaskTypePage from '../components/task/TaskTypePage'

export default function SpeechToText() {
  return (
    <TaskTypePage
      taskType="speech_to_text"
      title="语音转文字"
      description="使用 Whisper 将音频文件转成文字或字幕（支持 mp3、wav、m4a、flac 等）。提交后任务将加入队列，可在"
      submitLabel="提交任务"
      listTitle="语音转文字任务"
      emptyText="暂无语音转文字任务"
    />
  )
}
