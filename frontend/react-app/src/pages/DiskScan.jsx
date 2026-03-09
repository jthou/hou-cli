import TaskTypePage from '../components/task/TaskTypePage'

export default function DiskScan() {
  return (
    <TaskTypePage
      taskType="disk_scan"
      title="磁盘空间扫描"
      description="扫描磁盘占用，定位大目录。提交后任务在后台执行，可在任务列表查看进度与结果。"
      submitLabel="开始扫描"
      listTitle="磁盘扫描任务"
      emptyText="暂无磁盘扫描任务"
    />
  )
}
