# 测试执行指南

## 测试任务

下载视频并提取字幕：
```
下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。
```

## 启动步骤

### 1. 启动后端（端口 6080）

```bash
cd /System/Volumes/Data/justin/dev/hou-cli
source venv/bin/activate
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600
python -m backend.main
```

或者使用启动脚本：
```bash
bash scripts/start_and_test.sh
```

### 2. 监控后端日志（可选，在另一个终端）

```bash
# 方式1：监控临时日志文件
tail -f /tmp/hou-cli-backend.log

# 方式2：监控应用日志文件（推荐）
tail -f ~/Library/Application\ Support/hou-cli/logs/backend.log
```

### 3. 执行测试任务

```bash
cd /System/Volumes/Data/justin/dev/hou-cli
source venv/bin/activate
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600

# 使用测试脚本
bash scripts/run_test_task.sh

# 或直接执行
python -m frontend.main chat "下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。"
```

## 验证要点

### 1. 心跳机制验证

在监控后端日志时，应该看到：
- 每30秒左右有状态更新消息
- 格式类似：`{"type":"status","data":{"task":"处理中","progress":0,"message":"任务正在执行中...","elapsed_time":30.xx}}`

### 2. 进度输出验证

在前端输出中，应该看到：
- `[计划]` 开头的任务分析信息
- `[第 X 轮]` 开头的执行轮次信息
- `[工具调用]` 开头的工具执行信息
- `[工具结果]` 开头的工具执行结果
- `[状态]` 开头的状态更新（心跳）

### 3. 超时验证

- 前端不应该在任务执行过程中超时
- 即使后端处理时间较长（如视频下载、音频提取），前端应该保持连接

### 4. 工具执行验证

应该看到以下工具被调用：
1. `video_downloader` - 下载视频
2. `ffmpeg` - 提取音频（如果需要）
3. `whisper` - 生成字幕

## 预期输出示例

```
[计划] 任务分析完成，制定了 X 个执行步骤。
[计划] 计划内容：...

[第 1 轮] 开始执行...
[工具调用] 正在执行: video_downloader
[工具结果] video_downloader 执行成功

[第 2 轮] 开始执行...
[工具调用] 正在执行: ffmpeg
[工具结果] ffmpeg 执行成功

[第 3 轮] 开始执行...
[工具调用] 正在执行: whisper
[工具结果] whisper 执行成功

✅ 任务完成！
```

## 故障排查

### 后端未启动
- 检查端口 6080 是否被占用：`lsof -i:6080`
- 检查后端日志：`tail -100 /tmp/hou-cli-backend.log`

### 前端连接失败
- 确认 `BACKEND_PORT=6080` 环境变量已设置
- 检查 `.env` 文件中是否有 `BACKEND_PORT=6080`
- 确认后端健康检查：`curl http://127.0.0.1:6080/health`

### 任务执行超时
- 增加 `STREAM_TIMEOUT` 环境变量值（默认 600 秒）
- 检查网络连接和视频下载速度

### 工具执行失败
- 检查工具依赖是否已安装（ffmpeg, whisper 等）
- 查看后端日志中的详细错误信息

