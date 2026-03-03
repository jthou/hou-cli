/**
 * 定时任务调度配置字段：任务名称、调度类型、间隔/cron
 * 间隔：前端按时/分/秒输入，内部仍用秒与父组件及后端通信。
 */
import { formStyles } from './taskFormUtils'

function secondsToHMS(total) {
  const sec = Math.max(0, Math.floor(Number(total) || 0))
  const hours = Math.floor(sec / 3600)
  const remainder = sec % 3600
  const minutes = Math.floor(remainder / 60)
  const seconds = remainder % 60
  return { hours, minutes, seconds }
}

function hmsToSeconds(h, m, s) {
  return (parseInt(h, 10) || 0) * 3600 + (parseInt(m, 10) || 0) * 60 + (parseInt(s, 10) || 0)
}

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
  const { hours, minutes, seconds } = secondsToHMS(intervalSeconds)

  const handleIntervalChange = (field, value) => {
    const str = String(value).trim()
    const num = str === '' ? 0 : Math.max(0, parseInt(str, 10) || 0)
    const h = field === 'hours' ? num : hours
    const m = field === 'minutes' ? num : minutes
    const s = field === 'seconds' ? num : seconds
    onIntervalSecondsChange(hmsToSeconds(h, m, s))
  }

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
          <label className={labelCls}>执行间隔 *（至少 1 分钟）</label>
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="number"
              min={0}
              value={hours}
              onChange={e => handleIntervalChange('hours', e.target.value)}
              className={inputCls}
              style={{ width: '4rem' }}
              aria-label="小时"
            />
            <span className="text-muted">时</span>
            <input
              type="number"
              min={0}
              value={minutes}
              onChange={e => handleIntervalChange('minutes', e.target.value)}
              className={inputCls}
              style={{ width: '4rem' }}
              aria-label="分钟"
            />
            <span className="text-muted">分</span>
            <input
              type="number"
              min={0}
              value={seconds}
              onChange={e => handleIntervalChange('seconds', e.target.value)}
              className={inputCls}
              style={{ width: '4rem' }}
              aria-label="秒"
            />
            <span className="text-muted">秒</span>
          </div>
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
