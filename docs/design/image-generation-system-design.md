# 图片生成系统设计文档（修订版）

## 概述

基于前期讨论与设计审查，设计一套图片生成能力：文生图工具、长文本转提示词 Tool、任务型前端页面。**首期仅用 Tool**，不使用 Skill；长文本场景通过 `text_to_image_prompt` Tool 在对话流中完成。任务型与 Chat 共用 `ImageGenService` 服务层。

## 设计目标

1. **文生图**：支持根据文本描述生成图片，接入百炼 multimodal-generation API
2. **长文本支持**：Chat 场景下，长文本经 `text_to_image_prompt` 提炼后再生成图片；**任务型不做长文本提炼**，用户输入短 prompt
3. **模型可选**：支持用户或 LLM 选择模型，不指定时默认 wan2.6-t2i
4. **任务型 UI**：与视频下载一致，左表单 + 右任务列表，复用 output-file API
5. **Chat 图片展示**：Tool 返回 base64，便于 chat 消息直接渲染

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户入口                                         │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  任务型页面                    │  Chat 对话                                    │
│  /image-generation            │  Home / 流式对话                              │
└──────────────┬───────────────┴──────────────────────┬───────────────────────┘
               │                                       │
               ▼                                       ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────────┐
│  任务队列                     │    │  Orchestrator (chat agent)                 │
│  process_image_generation    │    │  ├── text_to_image_prompt (Tool, async)    │
│  _task                       │    │  └── image_generation (Tool)               │
└──────────────┬───────────────┘    └──────────────────────┬───────────────────┘
               │                                             │
               └──────────────────┬──────────────────────────┘
                                  ▼
               ┌──────────────────────────────────────────────┐
               │  ImageGenService                             │
               │  封装百炼 multimodal-generation API          │
               │  - parse_model_name 解析模型                 │
               │  - 处理 base64/URL 返回，保存到本地           │
               └──────────────────────────────────────────────┘
```

## 模块设计

### 1. ImageGenService

**位置**: `backend/services/llm/image_gen_service.py`

**职责**: 封装百炼/网关图像生成 API，与 chat completion 分离。handler 与 Tool 均直接调用本服务。

**接口**:

```python
class ImageGenService:
    def __init__(self, model: Optional[str] = None):
        """model 支持 provider-model 格式，内部用 parse_model_name 解析"""

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024*1024",
        n: int = 1,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        返回: {
            "images": List[str],      # base64 或 URL 列表（API 原始返回）
            "output_file": str,       # 保存到本地后的首图路径（若指定 output_dir）
            "output_dir": str,
            "prompt": str,
        }
        """
```

**实现要点**:
- 使用 `model_registry.parse_model_name(model)` 解析出实际 model 名（如 `wan2.6-t2i`）
- 百炼 API 返回 base64 或临时 URL，需写入 `output_dir` 得到本地路径
- 复用 `model_config` 获取 API Key、Base URL
- 首期 **n 固定为 1**，多图后续扩展

---

### 2. ImageGenerationTool

**位置**: `backend/core/agent/tools/builtin/image_generation_tool.py`

**职责**: 供 chat agent 调用的文生图工具，内部调用 ImageGenService。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 图片描述 |
| model | string | 否 | 模型，默认 wan2.6-t2i |
| size | string | 否 | 尺寸，默认 1024*1024 |
| output_dir | string | 否 | 保存目录（Chat 场景可不填） |

**返回**:
- **任务型 / 指定 output_dir**：`data` 含 `output_file`、`output_dir`、`prompt`
- **Chat 场景（未指定 output_dir）**：`data` 含 `image_base64`（便于前端 `<img src="data:image/png;base64,...">`）、`prompt`；可选写入临时目录并返回 `output_file`

---

### 3. TextToImagePromptTool

**位置**: `backend/core/agent/tools/builtin/text_to_image_prompt_tool.py`

**职责**: 将长文本提炼为适合文生图的短提示词，供主 agent 在 Chat 中调用。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要提炼的长文本 |
| max_length | integer | 否 | 提示词最大字数，默认 150 |
| style_hint | string | 否 | 风格提示，如写实、动漫、水彩 |

**实现要点**:
- 实现 `_execute_async`，由 `ToolRegistry.execute_async` 调用（orchestrator 的 tool 调用为 async）
- 参考 `persistent_browser_tool`：在 `__init__` 中 `self.llm_service = LLMService()`
- 内部调用 `await self.llm_service.chat(system_prompt=..., user_prompt=text)` 得到提炼后的 prompt

**系统提示**:

```
你是图片提示词专家。将用户提供的长文本提炼成适合文生图模型的短提示词。
要求：
- 输出 50–200 字，描述画面主体、风格、氛围
- 只输出提示词本身，不要解释
- 保留关键视觉元素（人物、场景、物体、光线等）
- 适合 DALL-E、Stable Diffusion、通义万相等模型
```

**返回**: `ToolResult(success=True, data={"prompt": "提炼后的短提示词"})`

---

### 4. 任务队列集成

#### 4.1 任务类型定义

```python
"image_generation": {
    "name": "图片生成",
    "description": "根据文本描述生成图片。请输入简短描述（50–200 字），长文本请使用 Chat 的「根据文章生成配图」功能。",
    "metadata_schema": {
        "prompt": {
            "type": "string",
            "required": True,
            "description": "图片描述（建议 50–200 字）",
            "placeholder": "如：一只橘猫在阳光下打盹，写实风格",
        },
        "model": {
            "type": "string",
            "required": False,
            "default": "wan2.6-t2i",
            "enum": [
                {"value": "wan2.6-t2i", "label": "万相文生图"},
                {"value": "qwen-image-max-2025-12-30", "label": "通义 Image Max"},
                {"value": "qwen-image-plus-2026-01-09", "label": "通义 Image Plus"},
            ],
        },
        "size": {
            "type": "string",
            "required": False,
            "default": "1024*1024",
            "enum": [
                {"value": "1024*1024", "label": "1024×1024"},
                {"value": "1280*720", "label": "1280×720"},
                {"value": "720*1280", "label": "720×1280"},
            ],
        },
        "output_dir": {
            "type": "string",
            "required": False,
            "description": "保存目录，须在用户主目录下",
            "placeholder": "留空使用 ~/hou-cli/outputs/images",
        },
    },
}
```

**说明**: 首期不暴露 `n` 参数，固定为 1。

#### 4.2 任务处理器

```python
async def process_image_generation_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    - 直接调用 ImageGenService.generate()
    - output_dir 使用 normalize_output_dir(..., restrict_to_home=True)
    - 写入路径做 _validate_path_in_home 校验
    - 返回: { status, summary, data: { output_file, output_dir, prompt } }
    """
```

---

### 5. Agent 集成

#### 5.1 工具注册

**agent_tools_registry.py** - 在 `AGENT_TOOLS["chat"]` 的**列表字面量**中追加:

```python
AGENT_TOOLS = {
    "chat": [
        # ... 现有工具 ...
        "image_generation",
        "text_to_image_prompt",
    ],
    # ...
}
```

#### 5.2 系统提示规则

**system_prompt_templates.py** - CHAT_SYSTEM_PROMPT 增加:

```
9. **图像生成工具（image_generation）**：当用户要求生成图片、画图、文生图时，必须使用 image_generation 工具
   - 例如："画一只猫" → 必须调用 image_generation 工具
   - 例如："根据这段描述生成图片" → 必须调用 image_generation 工具

10. **长文本转图片提示词（text_to_image_prompt）**：当用户提供长文本（文章、摘要等）并要求生成配图时，必须先调用 text_to_image_prompt 将长文本提炼成短提示词，再调用 image_generation
    - 例如："根据这篇文章生成配图" + 长文 → 先 text_to_image_prompt(text=长文)，再用返回的 prompt 调用 image_generation
    - 不要直接把长文作为 image_generation 的 prompt，文生图模型需要简短描述
```

---

### 6. 前端设计

#### 6.1 页面结构

**路由**: `/image-generation`

```jsx
// pages/ImageGeneration.jsx
<TaskTypePage
  taskType="image_generation"
  title="图片生成"
  description="根据文本描述生成图片。请输入简短描述（50–200 字）。支持万相、通义等模型。"
  submitLabel="提交生成"
  listTitle="图片生成任务"
  emptyText="暂无图片生成任务"
/>
```

#### 6.2 结果展示

**TaskResultDisplay.jsx** - 新增 `image_generation` 分支，使用 `output_file` 单路径，复用 output-file API:

```jsx
if (taskType === 'image_generation' && result.data) {
  const d = result.data
  const hasImage = taskId && d.output_file
  const streamUrl = hasImage ? `/api/task-queue/tasks/${taskId}/output-file` : null
  return (
    <div className="space-y-2 text-muted">
      {result.summary && <p className="text-green-400">{result.summary}</p>}
      {streamUrl && (
        <div className="mt-3 rounded-lg overflow-hidden border border-border">
          <img src={streamUrl} alt="生成图" className="w-full object-contain max-h-[360px]" />
        </div>
      )}
      {d.output_dir && <p><span className="text-muted">保存位置 </span><code className="text-cyan-300 break-all">{d.output_dir}</code></p>}
      {d.output_file && <p><span className="text-muted">输出文件 </span><code className="text-cyan-300 break-all">{d.output_file}</code></p>}
      {d.prompt && <p className="text-muted text-xs">提示词: {d.prompt}</p>}
    </div>
  )
}
```

#### 6.3 Chat 消息中的图片展示

**已确认**：前端 chat 消息组件支持 `data:image/png;base64,...` 格式。Tool 返回 `image_base64` 后，orchestrator 注入 `![生成的图片]({base64})` 到流，前端 MarkdownPreview（marked）解析为 `<img src={base64}>` 渲染。

#### 6.4 侧边栏

```js
{ path: '/image-generation', icon: '🖼️', label: '图片生成', group: 'media' },
```

---

## 数据流

### 场景 1：任务型页面

```
用户填写 prompt、model、size、output_dir → 提交 → 创建 image_generation 任务
→ Worker 执行 process_image_generation_task
→ 直接调用 ImageGenService.generate(prompt, model, size, n=1, output_dir)
→ 百炼 API 返回 base64/URL → 保存到 output_dir → 得到 output_file
→ 返回 { status, summary, data: { output_file, output_dir, prompt } }
→ 前端 TaskResultDisplay 通过 /output-file 展示图片
```

### 场景 2：Chat 直接生成

```
用户：「画一只橘猫在阳光下打盹」
→ LLM 调用 image_generation(prompt="一只橘猫在阳光下打盹")
→ ImageGenerationTool 调用 ImageGenService（不指定 output_dir 或使用临时目录）
→ 返回 data 含 image_base64（及可选 output_file）
→ orchestrator 将 base64 嵌入 assistant 消息
→ 前端 chat 消息渲染 <img src="data:image/png;base64,...">
```

### 场景 3：Chat 长文本生成配图

```
用户：「根据这段文字生成配图」+ 粘贴长文
→ LLM 调用 text_to_image_prompt(text=长文)  [async]
→ 得到 data.prompt
→ LLM 调用 image_generation(prompt=data.prompt)
→ 同场景 2 展示
```

---

## 文件结构

```
backend/
├── services/llm/
│   └── image_gen_service.py              # 新建：图像 API 封装
├── core/agent/
│   ├── tools/builtin/
│   │   ├── image_generation_tool.py      # 新建
│   │   └── text_to_image_prompt_tool.py  # 新建
│   ├── agent_tools_registry.py           # 修改：chat 列表增加两工具
│   └── system_prompt_templates.py        # 修改：增加规则 9、10
├── infrastructure/execution/
│   └── task_handlers.py                  # 修改：新增 image_generation 类型与 handler

frontend/react-app/src/
├── pages/
│   └── ImageGeneration.jsx               # 新建
├── components/
│   ├── Sidebar.jsx                       # 修改：增加导航
│   └── TaskResultDisplay.jsx             # 修改：image_generation 分支
└── App.jsx                               # 修改：增加路由
```

**首期不实现**：`skills/image_generation/`（Skill）

---

## 实现顺序

| 阶段 | 内容 |
|------|------|
| 1 | ImageGenService：封装百炼 API，parse_model_name，处理 base64/URL，保存到本地 |
| 2 | 任务类型 image_generation + process_image_generation_task（含路径校验） |
| 3 | ImageGenerationTool：调用 ImageGenService，Chat 场景返回 base64 |
| 4 | 前端：ImageGeneration 页面、TaskResultDisplay、Sidebar、路由 |
| 5 | TextToImagePromptTool：实现 _execute_async，注入 LLMService，注册到 chat |
| 6 | 系统提示：增加 image_generation、text_to_image_prompt 规则 |
| 7 | 确认 chat 消息组件支持 base64 图片渲染（✅ 已确认：orchestrator 注入 Markdown，前端 marked 解析） |

---

## 依赖与配置

- **百炼 API Key**: `BAILIAN_API_KEY` 或 `DASHSCOPE_API_KEY`
- **模型**: `model_registry.parse_model_name()` 解析，API 请求用实际 model 名（如 `wan2.6-t2i`）
- **输出目录**: 默认 `~/hou-cli/outputs/images`，使用 `normalize_output_dir(..., restrict_to_home=True)`

---

## 后续扩展

- **多图 (n>1)**：扩展 output-file API 支持 `?index=i`，`result.data` 存 `output_files`
- **ImageGenerationSkill**：若需技能匹配优先，再实现，workflow 调用 image_generation tool
- **图生图**：支持 `reference_image` 参数，调用 qwen-image-edit-plus 等
