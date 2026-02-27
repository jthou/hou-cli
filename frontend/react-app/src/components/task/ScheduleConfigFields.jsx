/**
 * 定时任务调度配置字段：任务名称、调度类型、间隔/cron
 */
import { formStyles } from './taskFormUtils'

export default function ScheduleConfigFields({
  taskName,
  onTaskNameChange,
  scheduleType,
  onScheduleTypeChange,
  intervalSeconds,
  onIntervalSecondsChange,
  cronExpr,
  onCronExprChange,
  cronTz,
  onCronTzChange,
}) {
  const { inputCls, labelCls } = formStyles
  return (
    <>
      <div>
        <label className={labelCls}>任务名称</label>
        <input
          type="text"
          value={taskName}
          onChange={e => onTaskNameChange(e.target.value)}
          placeholder="留空自动生成"
          className={inputCls}
        />
      </div>
      <div>
        <label className={labelCls}>调度类型 *</label>
        <select value={scheduleType} onChange={e => onScheduleTypeChange(e.target.value)} className={inputCls}>
          <option value="interval">按间隔（interval）</option>
          <option value="cron">Cron 表达式</option>
        </select>
      </div>
      {scheduleType === 'interval' && (
        <div>
          <label className={labelCls}>间隔秒数 *（≥ 60）</label>
          <input
            type="number"
            min={60}
            value={intervalSeconds}
            onChange={e => onIntervalSecondsChange(Number(e.target.value) || 60)}
            className={inputCls}
          />
        </div>
      )}
      {scheduleType === 'cron' && (
        <>
          <div>
            <label className={labelCls}>Cron 表达式 *（分 时 日 月 周）</label>
            <input
              type="text"
              value={cronExpr}
              onChange={e => onCronExprChange(e.target.value)}
              placeholder="0 2 * * *"
              className={inputCls}
            />
          </div>
          <div>
            <label className={labelCls}>时区（可选）</label>
            <input
              type="text"
              value={cronTz}
              onChange={e => onCronTzChange(e.target.value)}
              placeholder="Asia/Shanghai"
              className={inputCls}
            />
          </div>
        </>
      )}
    </>
  )
}
