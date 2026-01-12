# 发布指南

本文档说明如何创建和发布 Hou CLI 的新版本。

## 发布前检查清单

- [ ] 更新版本号（`pyproject.toml`）
- [ ] 更新 CHANGELOG.md（如果存在）
- [ ] 运行所有测试
- [ ] 检查文档是否最新
- [ ] 确认所有依赖版本兼容

## 发布步骤

### 1. 更新版本号

编辑 `pyproject.toml`:

```toml
[project]
version = "0.1.1"  # 更新版本号
```

### 2. 提交更改

```bash
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
git push
```

### 3. 创建 Git 标签

```bash
# 创建带注释的标签
git tag -a v0.1.1 -m "Release v0.1.1"

# 推送标签（触发 CI/CD）
git push origin v0.1.1
```

### 4. 等待 CI/CD 完成

GitHub Actions 会自动：
1. 在 Windows、Linux、macOS 上构建
2. 创建发布包
3. 上传到 GitHub Releases

### 5. 编辑 GitHub Release

1. 访问 https://github.com/yourusername/hou-cli/releases
2. 找到刚创建的 release
3. 编辑说明，添加：
   - 版本亮点
   - 变更日志
   - 已知问题
   - 升级指南

## 手动发布（不使用 CI/CD）

如果不想使用 CI/CD，可以手动构建和发布：

### Windows

```cmd
build\build-windows.bat
```

输出: `dist\hou-cli-windows-amd64.zip`

### Linux

```bash
./build/build-linux.sh
cd dist/hou-cli-linux-release
tar -czf ../hou-cli-linux-amd64.tar.gz *
```

### macOS

```bash
./build/build-macos.sh
cd dist/hou-cli-macos-release
tar -czf ../hou-cli-macos-universal.tar.gz *
```

### 创建 Release

1. 在 GitHub 上创建新的 Release
2. 上传所有平台的发布包
3. 添加发布说明

## 版本号规范

遵循 [语义化版本](https://semver.org/)：

- **主版本号** (MAJOR): 不兼容的 API 修改
- **次版本号** (MINOR): 向下兼容的功能性新增
- **修订号** (PATCH): 向下兼容的问题修正

示例：
- `1.0.0` - 首次稳定发布
- `1.1.0` - 新增功能
- `1.1.1` - 修复 bug
- `2.0.0` - 重大更新（可能不兼容）

## 发布后

- [ ] 更新文档网站（如果有）
- [ ] 在社区/论坛发布公告
- [ ] 监控错误报告
- [ ] 准备热修复（如果需要）

## 回滚发布

如果发布有问题，可以：

1. **删除 Release**:
   ```bash
   git tag -d v0.1.1
   git push origin :refs/tags/v0.1.1
   ```

2. **创建修复版本**:
   - 修复问题
   - 发布新版本（如 `0.1.2`）

## 常见问题

### Q: 如何跳过 CI/CD 测试？

A: 在提交信息中添加 `[skip ci]`:
```bash
git commit -m "Update docs [skip ci]"
```

### Q: 如何只发布特定平台？

A: 编辑 `.github/workflows/release.yml`，注释掉不需要的平台。

### Q: 发布包太大怎么办？

A: 
1. 检查 `hou-cli.spec` 中的 `excludes` 列表
2. 使用 UPX 压缩
3. 考虑分平台发布（如 Linux 分 x86_64 和 ARM64）

### Q: macOS 代码签名失败？

A: 
1. 确保有有效的开发者证书
2. 在本地签名后再上传：
   ```bash
   codesign -s "Developer ID Application: Your Name" dist/hou-cli
   ```

## 参考

- [打包文档](docs/PACKAGING.md)
- [GitHub Releases API](https://docs.github.com/en/rest/releases/releases)

