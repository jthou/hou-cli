# 设计文档索引

本文档目录包含项目的所有设计文档，按功能分类编号。

## 文档编号规则

文档采用三级编号系统：`XX-文档名.md`

- **00X**: 核心架构和概述
- **01X**: 系统组件设计
- **02X**: 通信和集成
- **03X**: 开发和配置
- **04X**: 用户指南

## 文档列表

### 00X - 核心架构和概述

- **[00-architecture-design.md](./00-architecture-design.md)** - 架构设计文档
  - 说明 LLM Agent CLI 的整体架构设计
  - 前后端分离架构、进程模型、通信方式
  - 多 Agent 协作架构、SOP 流程编排架构

- **[00-architecture-diagram.md](./00-architecture-diagram.md)** - 架构图
  - 使用 Mermaid 图表展示系统整体架构
  - 模块说明、数据流说明、通讯关系说明

### 01X - 系统组件设计

- **[01-multi-agent-design.md](./01-multi-agent-design.md)** - 多 Agent 协作设计
  - Agent 编排器、协调器设计
  - 专门化 Agent 实现（Chat、PDF、Code、FileSystem、Research、Tool）

- **[01-sop-workflow-design.md](./01-sop-workflow-design.md)** - SOP 流程编排设计
  - 标准操作流程定义和执行
  - 流程识别器、流程执行引擎、流程状态管理

- **[01-code-execution-and-security.md](./01-code-execution-and-security.md)** - 代码执行和安全设计
  - 代码执行引擎、沙箱隔离
  - 权限管理、命令过滤、资源限制、审计日志

- **[01-knowledge-base-design.md](./01-knowledge-base-design.md)** - 知识库管理设计
  - 文件存储管理、知识提炼和处理
  - 向量化存储、向量搜索服务

- **[work-assistant-reference-design.md](./work-assistant-reference-design.md)** - 工作助手参考块设计
  - 工作助手无参考块时的设计考量
  - 可选方案：保持现状 / 增加参考块 / 替代性上下文来源

- **[01-code-and-memory-design.md](./01-code-and-memory-design.md)** - 代码能力和长记忆设计
  - 代码读取/编辑能力、文件系统操作
  - 长记忆系统、上下文管理

- **[01-context-storage-and-compression-design.md](./01-context-storage-and-compression-design.md)** - 上下文存储和整理机制设计
  - 持久化存储方案、上下文压缩策略
  - 上下文摘要生成

- **[01-three-level-memory-and-context-design.md](./01-three-level-memory-and-context-design.md)** - 三级记忆体系与上下文系统设计
  - 短期/近端/长期三层记忆架构
  - 记忆系统与记忆内容分离、统一记忆管理（MemoryManager）
  - 上下文系统与记忆系统职责划分与协作

### 02X - 通信和集成

- **[02-ipc-and-packaging.md](./02-ipc-and-packaging.md)** - IPC 通信和打包方案
  - TCP Localhost IPC 实现
  - 跨平台打包方案（PyInstaller、安装程序）

- **[02-streaming-response.md](./02-streaming-response.md)** - 流式响应设计
  - 流式输出实现、SSE 支持
  - 前端流式渲染

### 03X - 开发和配置

- **[03-implementation-guide.md](./03-implementation-guide.md)** - 实现指南
  - 前后端分离架构的具体实现步骤
  - 代码示例和最佳实践

- **[03-dependency-management.md](./03-dependency-management.md)** - 依赖管理指南
  - Python 依赖管理方案
  - requirements.txt、pyproject.toml 使用

- **[03-env-configuration.md](./03-env-configuration.md)** - 环境变量配置指南
  - `.env` 文件配置
  - API Key 管理、配置验证

### 04X - 用户指南

- **[04-getting-started.md](./04-getting-started.md)** - 快速开始指南
  - 项目启动方式
  - 首次使用说明

- **[04-setup-guide.md](./04-setup-guide.md)** - 设置指南
  - 环境设置、依赖安装
  - 配置说明

- **[04-quick-reference.md](./04-quick-reference.md)** - 快速参考
  - 核心概念速查
  - 常用功能索引

- **[04-rich-ui-guide.md](./04-rich-ui-guide.md)** - Rich UI 指南
  - Rich 库使用指南
  - UI 组件说明

### 功能设计

- **[image-generation-system-design.md](./image-generation-system-design.md)** - 图片生成系统设计
  - 文生图工具、长文本转提示词 subagent
  - 任务型前端、Agent 集成、实现顺序

- **[video-downloader-tool-design.md](./video-downloader-tool-design.md)** - 视频下载工具设计
  - 多平台下载、工具选择与降级策略

- **[work-assistant-agent-design.md](./work-assistant-agent-design.md)** - 工作助手 Agent 设计
  - 任务分解、做计划、会议纪要分析、项目笔记整理、公司知识库
  - MediaWiki 为唯一数据源（项目背景、团队架构）
  - 同步更新 MediaWiki 与看板

- **[model-selectable-at-use-time-design.md](./model-selectable-at-use-time-design.md)** - 模型使用时可选择设计
  - 运行时用户选择模型（chat/code/reasoning 或具体模型名）
  - ChatRequest 扩展、Orchestrator 模型覆盖逻辑
  - 后端测试验证方案（单元测试、集成测试、API 测试）

- **[model-availability-audit-design.md](./model-availability-audit-design.md)** - 模型可用性审计设计
  - 对每个模型主动发 "hello" 探测
  - 有回馈→可用，报错→显示错误信息
  - 应对配额耗尽（FreeTierOnly）、403、429 等场景

## 文档阅读顺序建议

### 新开发者
1. [04-getting-started.md](./04-getting-started.md) - 快速开始
2. [04-setup-guide.md](./04-setup-guide.md) - 环境设置
3. [00-architecture-design.md](./00-architecture-design.md) - 了解整体架构
4. [00-architecture-diagram.md](./00-architecture-diagram.md) - 查看架构图
5. [04-quick-reference.md](./04-quick-reference.md) - 快速参考

### 架构设计者
1. [00-architecture-design.md](./00-architecture-design.md) - 核心架构
2. [01-multi-agent-design.md](./01-multi-agent-design.md) - Agent 设计
3. [01-sop-workflow-design.md](./01-sop-workflow-design.md) - 流程编排
4. [02-ipc-and-packaging.md](./02-ipc-and-packaging.md) - 通信方案

### 功能开发者
1. [03-implementation-guide.md](./03-implementation-guide.md) - 实现指南
2. [01-code-execution-and-security.md](./01-code-execution-and-security.md) - 代码执行
3. [01-knowledge-base-design.md](./01-knowledge-base-design.md) - 知识库
4. [01-code-and-memory-design.md](./01-code-and-memory-design.md) - 代码能力

## 文档维护

- 新增文档时，请按照编号规则添加到相应分类
- 更新文档时，请同步更新本文档索引
- 文档重命名时，请使用 `git mv` 保留历史记录

