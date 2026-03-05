/**
 * 管道模板配置（先选链路再填参数）
 * 供「任务管理」弹层与「管道编排」页共用。
 * - form.fields: 用户需填写的表单项
 * - createTasks(formValues, api): 异步创建多任务并返回 { task1Id, task2Id, ... }
 */
export const PIPELINE_TEMPLATES = [
  {
    id: 'video_extract_audio_to_speech',
    name: '音频提取 → 字幕提取',
    description: '从视频提取音频，再对音频做字幕提取，第二步自动使用第一步的输出。',
    steps: [
      { task_type: 'video_extract_audio', label: '步骤 1：音频提取' },
      { task_type: 'speech_to_text', label: '步骤 2：字幕提取', input_from_step: 1 },
    ],
    form: {
      fields: [
        { id: 'input_file', label: '视频文件路径（第一步输入）', required: true, type: 'file', accept: '.mp4,.mkv,.avi,.mov,.webm,video/*', placeholder: '本地路径或上传' },
        { id: 'name1', label: '第一步任务名称（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name2', label: '第二步任务名称（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
      ],
    },
    async createTasks(formValues, api) {
      const pipelineId = crypto.randomUUID()
      const path = (formValues.input_file || '').trim()
      if (!path) throw new Error('请填写或上传视频文件路径（第一步输入）')
      const res1 = await api.create({
        task_type: 'video_extract_audio',
        task_name: (formValues.name1 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: { input_file: path },
        pipeline_id: pipelineId,
      })
      if (!res1.success) throw new Error(res1.detail || res1.message || '创建第一步任务失败')
      const res2 = await api.create({
        task_type: 'speech_to_text',
        task_name: (formValues.name2 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: res1.task_id,
        input_bindings: { input_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res2.success) throw new Error(res2.detail || res2.message || '创建第二步任务失败')
      return { task1Id: res1.task_id, task2Id: res2.task_id }
    },
  },
  {
    id: 'video_download_audio_to_speech',
    name: '视频下载（仅音频）→ 字幕提取',
    description: '从 B 站/YouTube 等链接仅下载音频，再对音频做字幕提取，第二步自动使用第一步的输出。',
    steps: [
      { task_type: 'video_download', label: '步骤 1：视频下载（仅音频）' },
      { task_type: 'speech_to_text', label: '步骤 2：字幕提取', input_from_step: 1 },
    ],
    form: {
      fields: [
        { id: 'url', label: '视频链接（第一步输入）', required: true, type: 'text', placeholder: '如 https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx' },
        { id: 'output_dir', label: '保存目录（可选）', required: false, type: 'text', placeholder: '留空使用 ~/hou-cli/outputs' },
        { id: 'name1', label: '第一步任务名称（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name2', label: '第二步任务名称（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
      ],
    },
    async createTasks(formValues, api) {
      const pipelineId = crypto.randomUUID()
      const url = (formValues.url || '').trim()
      if (!url) throw new Error('请填写视频链接（第一步输入）')
      const metadata = { url, extract_audio_only: true }
      if ((formValues.output_dir || '').trim()) metadata.output_dir = formValues.output_dir.trim()
      const res1 = await api.create({
        task_type: 'video_download',
        task_name: (formValues.name1 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata,
        pipeline_id: pipelineId,
      })
      if (!res1.success) throw new Error(res1.detail || res1.message || '创建第一步任务失败')
      const res2 = await api.create({
        task_type: 'speech_to_text',
        task_name: (formValues.name2 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: res1.task_id,
        input_bindings: { input_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res2.success) throw new Error(res2.detail || res2.message || '创建第二步任务失败')
      return { task1Id: res1.task_id, task2Id: res2.task_id }
    },
  },
  {
    id: 'video_download_to_extract_to_speech_to_wiki',
    name: '视频下载 → 提取音频 → 转字幕 → 写入 MediaWiki',
    description: '完整链路：下载视频 → 提取音频轨 → 字幕提取 → 将字幕内容写入 MediaWiki 页面。',
    steps: [
      { task_type: 'video_download', label: '步骤 1：视频下载' },
      { task_type: 'video_extract_audio', label: '步骤 2：音频提取', input_from_step: 1 },
      { task_type: 'speech_to_text', label: '步骤 3：字幕提取', input_from_step: 2 },
      { task_type: 'mediawiki_write', label: '步骤 4：文字写入 MediaWiki', input_from_step: 3 },
    ],
    form: {
      fields: [
        { id: 'url', label: '视频链接', required: true, type: 'text', placeholder: '如 https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx' },
        { id: 'mediawiki_title', label: 'MediaWiki 页面标题', required: true, type: 'text', placeholder: '如：我的笔记/2025-02' },
        { id: 'output_dir', label: '保存目录（可选）', required: false, type: 'text', placeholder: '留空使用 ~/hou-cli/outputs' },
        { id: 'name1', label: '步骤 1 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name2', label: '步骤 2 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name3', label: '步骤 3 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name4', label: '步骤 4 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
      ],
    },
    async createTasks(formValues, api) {
      const pipelineId = crypto.randomUUID()
      const url = (formValues.url || '').trim()
      if (!url) throw new Error('请填写视频链接')
      const title = (formValues.mediawiki_title || '').trim()
      if (!title) throw new Error('请填写 MediaWiki 页面标题')
      const meta1 = { url }
      if ((formValues.output_dir || '').trim()) meta1.output_dir = formValues.output_dir.trim()
      const res1 = await api.create({
        task_type: 'video_download',
        task_name: (formValues.name1 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: meta1,
        pipeline_id: pipelineId,
      })
      if (!res1.success) throw new Error(res1.detail || res1.message || '创建步骤 1 失败')
      const res2 = await api.create({
        task_type: 'video_extract_audio',
        task_name: (formValues.name2 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: res1.task_id,
        input_bindings: { input_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res2.success) throw new Error(res2.detail || res2.message || '创建步骤 2 失败')
      const res3 = await api.create({
        task_type: 'speech_to_text',
        task_name: (formValues.name3 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: res2.task_id,
        input_bindings: { input_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res3.success) throw new Error(res3.detail || res3.message || '创建步骤 3 失败')
      const res4 = await api.create({
        task_type: 'mediawiki_write',
        task_name: (formValues.name4 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: { title },
        depends_on_task_id: res3.task_id,
        input_bindings: { content_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res4.success) throw new Error(res4.detail || res4.message || '创建步骤 4 失败')
      return { task1Id: res1.task_id, task2Id: res2.task_id, task3Id: res3.task_id, task4Id: res4.task_id }
    },
  },
  {
    id: 'video_download_audio_to_speech_to_wiki',
    name: '视频下载（仅音频）→ 转字幕 → 写入 MediaWiki',
    description: '从链接仅下载音频 → 字幕提取 → 将字幕内容写入 MediaWiki 页面。',
    steps: [
      { task_type: 'video_download', label: '步骤 1：视频下载（仅音频）' },
      { task_type: 'speech_to_text', label: '步骤 2：字幕提取', input_from_step: 1 },
      { task_type: 'mediawiki_write', label: '步骤 3：文字写入 MediaWiki', input_from_step: 2 },
    ],
    form: {
      fields: [
        { id: 'url', label: '视频链接', required: true, type: 'text', placeholder: '如 https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx' },
        { id: 'mediawiki_title', label: 'MediaWiki 页面标题', required: true, type: 'text', placeholder: '如：我的笔记/2025-02' },
        { id: 'output_dir', label: '保存目录（可选）', required: false, type: 'text', placeholder: '留空使用 ~/hou-cli/outputs' },
        { id: 'name1', label: '步骤 1 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name2', label: '步骤 2 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
        { id: 'name3', label: '步骤 3 任务名（可选）', required: false, type: 'text', placeholder: '留空自动生成' },
      ],
    },
    async createTasks(formValues, api) {
      const pipelineId = crypto.randomUUID()
      const url = (formValues.url || '').trim()
      if (!url) throw new Error('请填写视频链接')
      const title = (formValues.mediawiki_title || '').trim()
      if (!title) throw new Error('请填写 MediaWiki 页面标题')
      const metadata = { url, extract_audio_only: true }
      if ((formValues.output_dir || '').trim()) metadata.output_dir = formValues.output_dir.trim()
      const res1 = await api.create({
        task_type: 'video_download',
        task_name: (formValues.name1 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata,
        pipeline_id: pipelineId,
      })
      if (!res1.success) throw new Error(res1.detail || res1.message || '创建步骤 1 失败')
      const res2 = await api.create({
        task_type: 'speech_to_text',
        task_name: (formValues.name2 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: res1.task_id,
        input_bindings: { input_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res2.success) throw new Error(res2.detail || res2.message || '创建步骤 2 失败')
      const res3 = await api.create({
        task_type: 'mediawiki_write',
        task_name: (formValues.name3 || '').trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: { title },
        depends_on_task_id: res2.task_id,
        input_bindings: { content_file: 'result.data.output_file' },
        pipeline_id: pipelineId,
      })
      if (!res3.success) throw new Error(res3.detail || res3.message || '创建步骤 3 失败')
      return { task1Id: res1.task_id, task2Id: res2.task_id, task3Id: res3.task_id }
    },
  },
]
