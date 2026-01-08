# browser-use 修改管理指南

## 当前状态

- browser-use 已配置为 Git Submodule
- 当前版本：97f9c9b6（包含 DeepSeek 集成等修改）
- 修改保存在本地，主项目记录 commit hash

## 工作流程

### 1. 修改 browser-use

```bash
cd backend/externals/browser-use
# 进行修改
git add .
git commit -m "修改说明"
```

### 2. 在主项目中记录新版本

```bash
cd ../..
git add backend/externals/browser-use
git commit -m "更新 browser-use 到新版本"
```

### 3. 团队成员同步

```bash
# 克隆项目
git clone <repo-url>
git submodule update --init --recursive

# 更新 submodule
git pull
git submodule update --recursive
```

## 如果需要推送到远程（可选）

### 方案 A：Fork 到自己的 GitHub（推荐）

1. Fork https://github.com/browser-use/browser-use 到你的账户
2. 添加 fork 作为远程仓库：
   ```bash
   cd backend/externals/browser-use
   git remote add fork https://github.com/YOUR_USERNAME/browser-use.git
   git push fork your-branch
   ```
3. 更新 .gitmodules 指向你的 fork：
   ```bash
   # 编辑 .gitmodules
   # url = https://github.com/YOUR_USERNAME/browser-use.git
   ```

### 方案 B：保持本地修改（当前方式）

- 修改只保存在本地
- 主项目记录 commit hash
- 团队成员通过主项目同步获取相同版本
- **不需要推送到远程也能正常工作**

## 同步上游更新

```bash
cd backend/externals/browser-use
git remote add upstream https://github.com/browser-use/browser-use.git
git fetch upstream
git merge upstream/main
# 解决冲突后
cd ../..
git add backend/externals/browser-use
git commit -m "合并 browser-use 上游更新"
```
