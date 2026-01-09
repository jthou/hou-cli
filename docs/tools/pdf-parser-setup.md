# PDF 解析工具安装指南

## 概述

PDF 解析工具支持多种后端，可以解析PDF文件，提取文本、表格、公式、图片等结构化内容。工具会自动选择最合适的后端，也可以手动指定。

## 支持的后端

### 1. MinerU（推荐，完全本地化）

**特点：**
- ✅ 完全本地化，无需远程模型
- ✅ 免费使用
- ✅ 基于 LayoutLMv3 和 UniMERNet 公式识别
- ✅ 适合学术文献、RAG知识库构建

**安装：**
```bash
pip install mineru
```

**使用场景：**
- 学术论文解析
- 技术文档转换
- RAG 知识库构建
- 需要离线处理的场景

### 2. Camelot（专业表格提取）

**特点：**
- ✅ 纯本地规则引擎
- ✅ 免费使用
- ✅ 特别擅长复杂表格（跨页、合并单元格）
- ✅ 精度优于 Tabula

**安装：**
```bash
pip install camelot-py[cv]
```

**使用场景：**
- 金融年报表格提取
- 财务报表解析
- 数据表格导出（Excel/CSV）

### 3. Logics-Parsing（阿里API，高质量）

**特点：**
- ✅ 使用阿里 Qwen2.5-VL 大模型
- ✅ 高质量解析效果
- ✅ 30天内100万免费Tokens
- ⚠️ 需要API密钥
- ⚠️ 依赖远程服务

**安装：**
```bash
pip install logics-parsing
```

**配置API密钥：**
```bash
export DASHSCOPE_API_KEY="your-api-key"
# 或
export ALIBABA_CLOUD_API_KEY="your-api-key"
```

**成本：**
- 免费额度：30天内100万Tokens
- 超出后：Qwen-Long 模型约 0.0005元/千Tokens
- 1元可处理约200万Tokens（相当于5本《新华字典》文字量）

**使用场景：**
- 需要高质量解析的场景
- 复杂文档结构识别
- 公式和图表提取

## 安装方式

### 方式1：安装单个后端（推荐）

根据需求选择安装：

```bash
# 推荐：安装 MinerU（完全本地化，免费）
pip install mineru

# 或安装 Camelot（表格提取）
pip install camelot-py[cv]

# 或安装 Logics-Parsing（需要API密钥）
pip install logics-parsing
export DASHSCOPE_API_KEY="your-api-key"
```

### 方式2：安装所有后端

```bash
pip install mineru camelot-py[cv] logics-parsing
```

## 工具自动选择逻辑

工具会根据以下规则自动选择后端：

1. **如果指定了后端**：使用指定的后端（如果可用）
2. **如果提取模式是表格**：优先使用 Camelot
3. **否则**：优先使用 MinerU（本地免费）
4. **如果 MinerU 不可用**：尝试 Logics-Parsing（如果有API密钥）
5. **最后**：尝试 Camelot

## 使用示例

### 基本使用

```
用户：解析这个PDF文件：/path/to/document.pdf
AI：会使用 pdf_parser 工具，自动选择最合适的后端
```

### 提取表格

```
用户：提取这个PDF中的表格：/path/to/report.pdf
AI：会使用 pdf_parser，extract_mode='table'，自动选择 Camelot
```

### 指定后端

```
用户：使用 MinerU 解析这个PDF：/path/to/paper.pdf
AI：会使用 pdf_parser，backend='mineru'
```

## 工具参数

- `file_path`（必需）：PDF文件路径
- `output_format`（可选）：输出格式，`markdown`、`json`、`excel`、`text`，默认 `markdown`
- `extract_mode`（可选）：提取模式，`full`（完整）、`text`（仅文本）、`table`（仅表格）、`formula`（仅公式），默认 `full`
- `backend`（可选）：指定后端，`auto`（自动）、`mineru`、`logics`、`camelot`，默认 `auto`
- `output_path`（可选）：输出文件路径，默认在PDF同目录下生成

## 输出格式

### Markdown（默认）
- 适合：文档阅读、RAG知识库
- 格式：标准Markdown，包含标题、段落、表格、代码块等

### JSON
- 适合：程序处理、数据提取
- 格式：结构化JSON，包含文本、表格、元数据等

### Excel
- 适合：表格数据
- 格式：Excel文件，每个表格一个工作表

### Text
- 适合：纯文本提取
- 格式：纯文本，无格式

## 故障排查

### 问题1：没有可用的后端

**症状**：工具返回 "没有可用的PDF解析后端"

**解决方案**：
1. 至少安装一个后端：`pip install mineru` 或 `pip install camelot-py[cv]`
2. 检查安装是否成功：`mineru --version` 或 `python -c "import camelot"`

### 问题2：Logics-Parsing 需要API密钥

**症状**：使用 Logics-Parsing 时提示需要API密钥

**解决方案**：
1. 在阿里云控制台申请API密钥
2. 设置环境变量：`export DASHSCOPE_API_KEY="your-api-key"`
3. 或使用其他后端（MinerU 或 Camelot）

### 问题3：Camelot 提取表格失败

**症状**：Camelot 无法提取表格或精度低

**解决方案**：
1. 确保安装了 `camelot-py[cv]`（包含 OpenCV 依赖）
2. 尝试使用其他后端（MinerU 或 Logics-Parsing）
3. 检查PDF是否包含可提取的表格（非图片表格）

### 问题4：MinerU 转换超时

**症状**：MinerU 解析超过5分钟

**解决方案**：
1. 检查PDF文件大小，大文件可能需要更长时间
2. 尝试使用 Logics-Parsing（API处理可能更快）
3. 或使用 `extract_mode='text'` 仅提取文本

## 性能对比

| 后端 | 速度 | 精度 | 成本 | 适用场景 |
|------|------|------|------|----------|
| MinerU | 中等 | 高 | 免费 | 学术文献、RAG |
| Camelot | 快 | 表格高 | 免费 | 表格提取 |
| Logics-Parsing | 快 | 很高 | 有免费额度 | 高质量解析 |

## 参考链接

- MinerU: https://github.com/opendatalab/MinerU
- Camelot: https://github.com/camelot-dev/camelot
- Logics-Parsing: https://github.com/alibaba/logics-parsing
- 阿里云 DashScope: https://dashscope.aliyun.com/

