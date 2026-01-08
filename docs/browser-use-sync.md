# browser-use 团队成员同步指南

## 问题

browser-use 的修改没有推送到远程，团队成员如何同步？

## 解决方案：使用补丁文件

### 1. 生成补丁文件（维护者操作）

```bash
cd backend/externals/browser-use
git format-patch origin/main..HEAD -o ../../patches/browser-use
cd ../..
git add patches/
git commit -m "添加 browser-use 补丁文件"
```

### 2. 团队成员同步（新成员或更新时）

```bash
# 克隆项目
git clone <repo-url>
cd <project-dir>

# 初始化 submodule（获取官方版本）
git submodule update --init --recursive

# 应用补丁
./scripts/apply-browser-use-patches.sh
```

### 3. 更新补丁（当 browser-use 有新的修改时）

维护者：
```bash
# 生成新的补丁
cd backend/externals/browser-use
git format-patch origin/main..HEAD -o ../../patches/browser-use

# 提交补丁文件
cd ../..
git add patches/
git commit -m "更新 browser-use 补丁"
```

团队成员：
```bash
# 更新主项目
git pull

# 重新应用补丁
cd backend/externals/browser-use
git checkout main  # 或重置到官方版本
git clean -fd
cd ../..
./scripts/apply-browser-use-patches.sh
```

## 工作原理

1. **补丁文件保存在主项目中**（`patches/browser-use/`）
2. **团队成员克隆主项目时获取补丁**
3. **初始化 submodule 获取官方版本**
4. **应用补丁得到修改后的版本**

这样就不需要推送到远程，团队成员也能同步修改！

