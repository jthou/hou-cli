# browser-use 团队成员同步指南

## 概述

本项目对 `browser-use` 进行了定制修改（如 DeepSeek 集成、DOM 优化等），这些修改保存在补丁文件中。团队成员需要通过补丁文件来同步这些修改。

## 首次设置（新成员）

### 步骤 1：克隆项目

```bash
git clone <repo-url>
cd <project-dir>
```

### 步骤 2：初始化 submodule

获取官方的 browser-use 版本：

```bash
git submodule update --init --recursive
```

这会：
- 初始化 `backend/externals/browser-use` submodule
- 获取官方 browser-use 仓库的代码

### 步骤 3：应用补丁

应用我们的定制修改：

```bash
./scripts/apply-browser-use-patches.sh
```

脚本会自动：
- 检查 submodule 是否存在
- 创建 `hou-cli-patched` 分支
- 按顺序应用所有补丁文件
- 显示应用结果

### 步骤 4：验证

检查补丁是否成功应用：

```bash
cd backend/externals/browser-use
git log --oneline -5
```

应该能看到包含 "DeepSeek"、"Fix items" 等关键词的 commit。

## 更新同步（已有成员）

当主项目更新了 browser-use 补丁时：

### 步骤 1：更新主项目

```bash
git pull
```

### 步骤 2：更新 submodule 到官方版本

```bash
cd backend/externals/browser-use
git checkout main  # 切换到官方分支
git pull origin main  # 获取最新官方版本
cd ../..
```

### 步骤 3：重新应用补丁

```bash
./scripts/apply-browser-use-patches.sh
```

## 补丁文件说明

补丁文件保存在 `patches/browser-use/` 目录：

- `0001-Fix-items-operation-failure-*.patch` - 修复 items 操作失败问题
- `0002-Improve-DOM-extraction-retry-*.patch` - 改进 DOM 提取重试机制
- `0003-DeepSeek-LLM.patch` - DeepSeek LLM 集成

这些补丁按顺序应用，确保修改的正确性。

## 常见问题

### Q: 补丁应用失败怎么办？

如果补丁应用失败，可能是：
1. submodule 版本不匹配
2. 补丁文件已过期

解决方法：
```bash
cd backend/externals/browser-use
git reset --hard origin/main  # 重置到官方版本
git clean -fd  # 清理未跟踪文件
cd ../..
./scripts/apply-browser-use-patches.sh  # 重新应用
```

### Q: 如何检查当前使用的版本？

```bash
cd backend/externals/browser-use
git log --oneline -1
git branch  # 查看当前分支
```

### Q: 补丁应用后需要做什么？

补丁应用后，browser-use 就已经包含了所有定制修改，可以直接使用，无需额外操作。

### Q: 可以修改 browser-use 的代码吗？

可以，但修改后需要：
1. 在 submodule 中提交修改
2. 生成新的补丁文件
3. 在主项目中提交补丁文件

详细步骤请参考维护者文档。

## 维护者操作

### 生成补丁文件

当 browser-use 有新的修改时：

```bash
cd backend/externals/browser-use
git format-patch origin/main..HEAD -o ../../patches/browser-use
cd ../..
git add patches/
git commit -m "更新 browser-use 补丁"
```

### 更新补丁文件

如果补丁文件需要更新：

```bash
# 删除旧补丁
rm patches/browser-use/*.patch

# 生成新补丁
cd backend/externals/browser-use
git format-patch origin/main..HEAD -o ../../patches/browser-use

# 提交
cd ../..
git add patches/
git commit -m "更新 browser-use 补丁"
```

## 技术细节

### 工作原理

1. **Submodule**：使用 Git Submodule 管理 browser-use 的官方版本
2. **补丁文件**：将我们的修改保存为补丁文件（`.patch`）
3. **自动应用**：通过脚本自动应用补丁到官方版本
4. **版本控制**：补丁文件保存在主项目中，团队成员可以同步

### 为什么使用补丁？

- ✅ 不需要 Fork 或推送修改到远程
- ✅ 团队成员可以轻松同步
- ✅ 可以随时更新或回退
- ✅ 保持与官方版本的兼容性

## 相关文档

- [browser-use 管理文档](./browser-use-management.md) - 详细的管理说明
- [browser-use 架构文档](./design/browser-use-architecture.md) - 技术架构说明
