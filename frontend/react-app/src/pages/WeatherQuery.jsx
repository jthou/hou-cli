import TaskTypePage from '../components/task/TaskTypePage'

export default function WeatherQuery() {
  return (
    <TaskTypePage
      taskType="weather_query"
      title="天气查询"
      description="查询指定地点的实时天气、预报、预警或空气质量。提交后任务将加入队列，可在"
      submitLabel="提交查询"
      listTitle="天气查询任务"
      emptyText="暂无天气查询任务"
    />
  )
}
