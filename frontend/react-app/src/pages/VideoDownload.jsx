import TaskTypePage from '../components/task/TaskTypePage'

export default function VideoDownload() {
  return (
    <TaskTypePage
      taskType="video_download"
      title="视频下载"
      description="支持 Bilibili、YouTube 等平台。输入视频链接后提交，下载任务将加入队列，可在"
      submitLabel="提交下载任务"
      listTitle="视频下载任务"
      emptyText="暂无视频下载任务"
    />
  )
}
