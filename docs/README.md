# 文档索引

欢迎来到 Hou CLI 项目文档中心。本文档提供了所有文档的索引和导航。

## 📚 快速导航

### 🏗️ 架构与设计

- **[架构问题分析](architecture-issues-analysis.md)** - 当前架构问题分析和改进建议
- **[Services vs Tools 澄清](services-vs-tools-clarification.md)** - Services 和 Tools 的核心区别和关系
- **[实现设计差距分析](implementation-design-gap-analysis.md)** - 实现与设计之间的差距分析
- **[外部依赖包装策略](externals-wrapping-strategy.md)** - 外部依赖的包装和管理策略
- **[LLM 工具调用机制](llm-tool-calling-mechanism.md)** - LLM 如何调用工具的详细机制

### 🧪 测试指南

- **[测试指南](testing-guide.md)** - 完整的测试指南（主文档）
- **[测试快速开始](TESTING_QUICK_START.md)** - 快速开始测试的指南
- **[如何测试 Tools](how-to-test-tools.md)** - 工具测试的详细说明
- **[工具描述 LLM 测试指南](tool-description-llm-test-guide.md)** - 使用 LLM 验证工具描述的测试方法

### 📦 发布与打包

- **[发布指南](RELEASE.md)** - 如何创建和发布新版本
- **[打包指南](PACKAGING.md)** - 完整的打包流程和说明
- **[打包快速开始](packaging-quickstart.md)** - 快速打包指南
- **[打包总结](packaging-summary.md)** - 打包相关总结

### 🔧 开发与配置

- **[开发笔记](dev-notes.md)** - 项目开发日志和重要进展
- **[Google Search API 设置](google-search-api-setup.md)** - Google Search API 配置指南
- **[Browser-Use 集成调试指南](BROWSER_USE_DEBUGGING_GUIDE.md)** - 如何在 browser-use 源码中设置断点和调试

### 📁 其他目录

- **[归档文档](archived/)** - 历史文档和已完成任务的文档
- **[设计文档](design/)** - 详细的设计文档
- **[分析文档](analysis/)** - 问题分析和解决方案
- **[开发日志](dev-dairy/)** - 按日期组织的开发日志
- **[工具文档](tools/)** - 各个工具的详细使用说明
- **[故障排除](troubleshooting/)** - 常见问题和解决方案
- **[重构文档](refactoring/)** - 重构计划和总结

---

## 📖 文档分类

### 按用途分类

#### 🎯 新手入门
1. [测试快速开始](TESTING_QUICK_START.md) - 开始测试
2. [打包快速开始](packaging-quickstart.md) - 开始打包
3. [Google Search API 设置](google-search-api-setup.md) - 配置 API

#### 🏛️ 架构理解
1. [架构问题分析](architecture-issues-analysis.md) - 了解当前架构
2. [Services vs Tools 澄清](services-vs-tools-clarification.md) - 理解核心概念
3. [LLM 工具调用机制](llm-tool-calling-mechanism.md) - 理解工具调用

#### 🔧 开发工作
1. [测试指南](testing-guide.md) - 编写和运行测试
2. [如何测试 Tools](how-to-test-tools.md) - 测试工具
3. [开发笔记](dev-notes.md) - 查看开发历史

#### 🚀 发布部署
1. [发布指南](RELEASE.md) - 发布新版本
2. [打包指南](PACKAGING.md) - 创建发布包

### 按主题分类

#### 测试相关
- [测试指南](testing-guide.md)
- [测试快速开始](TESTING_QUICK_START.md)
- [如何测试 Tools](how-to-test-tools.md)
- [工具描述 LLM 测试指南](tool-description-llm-test-guide.md)

#### 架构相关
- [架构问题分析](architecture-issues-analysis.md)
- [Services vs Tools 澄清](services-vs-tools-clarification.md)
- [实现设计差距分析](implementation-design-gap-analysis.md)
- [外部依赖包装策略](externals-wrapping-strategy.md)
- [LLM 工具调用机制](llm-tool-calling-mechanism.md)

#### 打包发布相关
- [发布指南](RELEASE.md)
- [打包指南](PACKAGING.md)
- [打包快速开始](packaging-quickstart.md)
- [打包总结](packaging-summary.md)

#### 配置相关
- [Google Search API 设置](google-search-api-setup.md)

---

## 🔍 查找文档

### 按任务查找

**我想...**
- **开始测试** → [测试快速开始](TESTING_QUICK_START.md)
- **理解架构** → [架构问题分析](architecture-issues-analysis.md)
- **发布版本** → [发布指南](RELEASE.md)
- **打包项目** → [打包指南](PACKAGING.md)
- **配置 API** → [Google Search API 设置](google-search-api-setup.md)
- **测试工具** → [如何测试 Tools](how-to-test-tools.md)
- **查看开发历史** → [开发笔记](dev-notes.md)

### 按角色查找

**我是...**
- **新贡献者** → 从 [测试快速开始](TESTING_QUICK_START.md) 和 [架构问题分析](architecture-issues-analysis.md) 开始
- **测试工程师** → 查看 [测试指南](testing-guide.md) 和 [如何测试 Tools](how-to-test-tools.md)
- **维护者** → 查看 [发布指南](RELEASE.md) 和 [打包指南](PACKAGING.md)
- **架构师** → 查看 [架构问题分析](architecture-issues-analysis.md) 和 [实现设计差距分析](implementation-design-gap-analysis.md)

---

## 📂 文档组织说明

### 根目录文档
根目录下的文档是**当前活跃的文档**，应该保持最新。

### 归档文档
`archived/` 目录包含历史文档和已完成任务的文档：
- `archived/phases/` - 阶段实施相关的历史文档
- `archived/tests/` - 测试相关的历史文档
- `archived/fixes/` - 问题修复相关的历史文档
- `archived/optimization/` - 优化相关的历史文档
- `archived/packaging/` - 打包相关的历史文档
- `archived/tools/` - 工具相关的历史文档
- `archived/browser/` - 浏览器相关的历史文档
- `archived/design/` - 设计相关的历史文档

详见 [归档文档索引](archived/ARCHIVE_INDEX.md)

### 子目录文档
- `design/` - 详细的设计文档
- `analysis/` - 问题分析和解决方案
- `dev-dairy/` - 按日期组织的开发日志
- `tools/` - 各个工具的详细使用说明
- `troubleshooting/` - 常见问题和解决方案
- `refactoring/` - 重构计划和总结
- `todo/` - TODO 任务和计划

---

## 🔄 文档维护

### 文档更新原则
1. **保持活跃文档最新** - 根目录下的文档应该反映当前状态
2. **及时归档** - 已完成的任务和过时的文档应移到 `archived/`
3. **更新索引** - 当文档结构变化时，更新本文档

### 文档整理计划
文档整理相关的计划文档已归档到 `archived/` 目录，可通过 Git 历史查看。

---

## 📝 贡献文档

### 添加新文档
1. 在合适的目录创建文档
2. 更新本文档索引
3. 遵循文档命名规范（使用小写字母和连字符）

### 文档命名规范
- 使用小写字母
- 使用连字符分隔单词（`-`）
- 使用描述性的名称
- 示例：`how-to-test-tools.md`, `architecture-issues-analysis.md`

---

## ❓ 需要帮助？

如果找不到需要的文档：
1. 检查本文档索引
2. 查看 `archived/` 目录（历史文档）
3. 查看 Git 历史（文档可能已被移动或重命名）
4. 查看 [文档整理计划](DOCUMENTATION_ORGANIZATION_PLAN.md) 了解文档组织方式

---

**最后更新**: 2026-01-18  
**维护者**: 项目团队

