# 文档整理计划

## 文档分类建议

### 📁 保留在根目录（当前活跃文档）

#### 核心架构和设计文档
- ✅ `architecture-issues-analysis.md` - **保留**，架构分析仍有参考价值
- ✅ `services-vs-tools-clarification.md` - **保留**，核心概念说明
- ✅ `implementation-design-gap-analysis.md` - **保留**，设计差距分析
- ✅ `externals-wrapping-strategy.md` - **保留**，外部依赖包装策略

#### 开发和测试指南（需要更新）
- ✅ `dev-notes.md` - **保留但需更新**，开发日志，建议移到 `dev-dairy/` 或定期归档
- ✅ `how-to-test-tools.md` - **保留并更新**，工具测试指南
- ✅ `testing-guide.md` - **保留并更新**，统一测试指南
- ✅ `TESTING_QUICK_START.md` - **保留并更新**，快速开始指南
- ✅ `tool-description-llm-test-guide.md` - **保留**，LLM 测试指南

#### 发布和打包文档
- ✅ `RELEASE.md` - **保留**，发布流程
- ✅ `PACKAGING.md` - **保留**，打包主文档
- ✅ `packaging-quickstart.md` - **保留**，快速打包指南
- ✅ `packaging-summary.md` - **保留**，打包总结

#### 工具和功能设置文档
- ✅ `google-search-api-setup.md` - **保留**，API 设置指南
- ✅ `llm-tool-calling-mechanism.md` - **保留**，LLM 工具调用机制

---

### 📦 移动到 `docs/archived/`（历史记录和已完成任务）

#### 测试相关历史文档
- 📦 `TESTING_FINAL.md` - **归档**，最终测试报告（历史）
- 📦 `TESTING_SUMMARY.md` - **归档**，测试总结（历史）
- 📦 `TEST_RESULTS_FINAL.md` - **归档**，测试结果（历史）
- 📦 `test-cleanup-summary.md` - **归档**，测试清理总结（已完成）
- 📦 `test-directory-reorganization-plan.md` - **归档**，重组计划（已完成）
- 📦 `test-directory-reorganization-summary.md` - **归档**，重组总结（已完成）
- 📦 `test-fixes-summary.md` - **归档**，测试修复总结（已完成）
- 📦 `skipped-tests-summary.md` - **归档**，跳过测试总结（历史）
- 📦 `skipped-tests-update.md` - **归档**，跳过测试更新（历史）
- 📦 `tools-test-coverage-summary.md` - **归档**，测试覆盖率总结（历史）
- 📦 `warnings-fixes-summary.md` - **归档**，警告修复总结（已完成）

#### 打包相关历史文档
- 📦 `BUILD_DEB_TEST.md` - **归档**，DEB 构建测试（历史）
- 📦 `BUILD_TEST_REPORT.md` - **归档**，构建测试报告（历史）
- 📦 `DEB_PACKAGING_VENV.md` - **归档**，DEB 打包 venv（历史，已合并到主文档）
- 📦 `DEB_PACKAGING.md` - **归档**，DEB 打包（历史，已合并到主文档）
- 📦 `INSTALL_DEB.md` - **归档**，DEB 安装（历史，已合并到主文档）
- 📦 `PORTABLE_PACKAGING.md` - **归档**，便携打包（历史，已合并到主文档）

#### 工具清理和问题文档
- 📦 `tool-cleanup-summary.md` - **归档**，工具清理总结（已完成）
- 📦 `tool-description-issues.md` - **归档**，工具描述问题（已修复）

#### 浏览器工具相关（部分归档）
- 📦 `browser-auto-install.md` - **归档**，自动安装（可能已过时）
- 📦 `browser-tool-quick-install.md` - **归档**，快速安装（可能已过时）
- 📦 `browser-tool-setup.md` - **归档**，设置指南（可能已过时）
- 📦 `browser-use-async-waiting.md` - **归档**，异步等待（技术细节，已解决）
- 📦 `browser-use-management.md` - **归档**，管理文档（技术细节）
- 📦 `browser-use-sync.md` - **归档**，同步文档（技术细节）

#### 其他历史文档
- 📦 `PROGRESS_DISPLAY_COMPARISON.md` - **归档**，进度显示比较（设计文档，已完成）
- 📦 `WHISPER_PROGRESS_DESIGN.md` - **归档**，Whisper 进度设计（设计文档，已完成）
- 📦 `TASK_PROCESSING_DEBUG.md` - **归档**，任务处理调试（调试文档，已完成）
- 📦 `type-safety-improvements.md` - **归档**，类型安全改进（已完成）

---

### 🔄 需要更新的文档

#### 高优先级更新
1. **`testing-guide.md`** - 统一所有测试相关文档，整合：
   - `TESTING_QUICK_START.md` 的内容
   - `how-to-test-tools.md` 的内容
   - 移除过时信息

2. **`how-to-test-tools.md`** - 更新工具测试流程，确保与当前代码一致

3. **`dev-notes.md`** - 考虑：
   - 移到 `dev-dairy/` 目录
   - 或定期归档到 `archived/`
   - 或改为当前开发状态文档

#### 中优先级更新
4. **`RELEASE.md`** - 检查发布流程是否最新
5. **`PACKAGING.md`** - 检查打包流程是否最新
6. **`architecture-issues-analysis.md`** - 更新已解决的问题状态

---

## 执行计划

### 第一步：创建归档目录
```bash
mkdir -p docs/archived/{tests,packaging,tools,browser,design}
```

### 第二步：移动归档文档
```bash
# 测试相关
mv docs/TESTING_FINAL.md docs/archived/tests/
mv docs/TESTING_SUMMARY.md docs/archived/tests/
mv docs/TEST_RESULTS_FINAL.md docs/archived/tests/
mv docs/test-*.md docs/archived/tests/
mv docs/skipped-tests-*.md docs/archived/tests/
mv docs/tools-test-coverage-summary.md docs/archived/tests/
mv docs/warnings-fixes-summary.md docs/archived/tests/

# 打包相关
mv docs/BUILD_*.md docs/archived/packaging/
mv docs/DEB_*.md docs/archived/packaging/
mv docs/INSTALL_DEB.md docs/archived/packaging/
mv docs/PORTABLE_PACKAGING.md docs/archived/packaging/

# 工具相关
mv docs/tool-cleanup-summary.md docs/archived/tools/
mv docs/tool-description-issues.md docs/archived/tools/

# 浏览器相关
mv docs/browser-*.md docs/archived/browser/
mv docs/browser-use-*.md docs/archived/browser/

# 设计相关
mv docs/PROGRESS_DISPLAY_COMPARISON.md docs/archived/design/
mv docs/WHISPER_PROGRESS_DESIGN.md docs/archived/design/
mv docs/TASK_PROCESSING_DEBUG.md docs/archived/design/
mv docs/type-safety-improvements.md docs/archived/design/
```

### 第三步：更新保留文档
1. 更新 `testing-guide.md`，整合所有测试文档
2. 更新 `RELEASE.md` 和 `PACKAGING.md`
3. 更新 `architecture-issues-analysis.md`

### 第四步：创建文档索引
在 `docs/README.md` 中创建文档索引，说明：
- 当前活跃文档的位置
- 归档文档的位置
- 如何查找特定文档

---

## 文档分类统计

- **保留文档**: ~15 个
- **归档文档**: ~25 个
- **需要更新**: ~6 个

---

## 注意事项

1. **不要删除文档**，只移动到归档目录
2. **保留 Git 历史**，使用 `git mv` 移动文件
3. **更新引用**，检查其他文档中对这些文件的引用
4. **创建索引**，帮助开发者找到文档

