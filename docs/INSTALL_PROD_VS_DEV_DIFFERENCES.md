# install-prod vs install-dev 详细区别

## 概述

- **`make install`** (原 `install-dev`): 安装开发依赖，包含所有工具和测试框架
- **`make install-prod`**: 安装生产依赖，仅核心功能，用于生产部署

## 详细对比

### 1. Python 依赖包

| 项目 | install (dev) | install-prod |
|------|---------------|--------------|
| **依赖文件** | `requirements.txt` | `requirements.txt` |
| **包含内容** | 生产依赖 + 开发依赖 | 仅生产依赖 |

#### install (dev) 额外包含的开发依赖：

**测试框架**:
- `pytest>=7.4.0` - 测试框架
- `pytest-asyncio>=0.21.0` - 异步测试支持
- `pytest-cov>=4.1.0` - 测试覆盖率
- `pytest-mock>=3.11.0` - Mock 支持

**代码质量工具**:
- `black>=23.11.0` - 代码格式化
- `isort>=5.12.0` - import 排序
- `flake8>=6.1.0` - 代码检查
- `pylint>=3.0.0` - 代码分析
- `mypy>=1.7.0` - 类型检查
- `types-pyyaml>=6.0.12` - 类型定义
- `types-requests>=2.31.0` - 类型定义

**打包工具**:
- `pyinstaller>=6.0.0` - 打包工具

**开发工具**:
- `ipdb>=0.13.13` - 调试器
- `ipython>=8.17.0` - 交互式 Python
- `sphinx>=7.2.0` - 文档生成
- `sphinx-rtd-theme>=1.3.0` - 文档主题
- `pre-commit>=3.5.0` - Git 预提交钩子

**浏览器自动化依赖** (browser-use):
- `langchain>=0.3.25` (更高版本要求)
- `langchain-core>=0.3.64` (更高版本要求)
- `langchain-openai>=0.3.21`
- `langchain-ollama>=0.3.3`
- `playwright>=1.40.0` - 浏览器驱动
- `anyio>=4.9.0`

**Jupyter 工具**:
- `jupyter-client>=8.6.0`
- `ipykernel>=6.25.0`

**PDF 解析工具**:
- `mineru[all]>=2.7.0` (完整功能版本)
- `camelot-py[cv]>=1.0.0` (表格提取)

#### install-prod 仅包含：

- 所有生产依赖（约 20 个包）
- `mineru>=2.7.0` (基础版本，不含额外功能)

### 2. pip install 命令

| 项目 | install (dev) | install-prod |
|------|---------------|--------------|
| **requirements** | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| **项目安装** | `pip install -e ".[dev]"` | `pip install -e .` |

**区别**:
- dev: 安装项目时包含可选开发依赖（从 `pyproject.toml` 的 `[project.optional-dependencies.dev]`）
- prod: 只安装项目本身，不包含可选依赖

### 3. Whisper 模型下载

| 项目 | install (dev) | install-prod |
|------|---------------|--------------|
| **命令** | `install_whisper.sh --download-models` | `install_whisper.sh` |
| **行为** | ✅ 下载 Whisper 模型文件 | ❌ 不下载模型（按需下载） |

**影响**:
- dev: 预先下载模型，首次使用更快，但占用更多磁盘空间（约 1-3 GB）
- prod: 首次使用时才下载，节省空间，但首次使用较慢

### 4. Jupyter Kernel 注册

| 项目 | install (dev) | install-prod |
|------|---------------|--------------|
| **行为** | ✅ 自动注册 Jupyter kernel | ⚠️ 需要手动运行 `install_jupyter.sh` |

**dev 命令**:
```bash
python -m ipykernel install --user --name python3 --display-name "Python 3"
```

**prod 命令**:
```bash
bash scripts/install_jupyter.sh
```

**区别**:
- dev: 自动注册 kernel，可以直接在 Jupyter 中使用
- prod: 需要单独运行脚本注册 kernel

### 5. PDF 解析器安装

| 项目 | install (dev) | install-prod |
|------|---------------|--------------|
| **环境变量** | `PDF_PARSERS=all` | `PDF_PARSERS=mineru` |
| **安装内容** | 所有 PDF 解析器 | 仅 MinerU |

**dev 安装**:
- MinerU (完整版，包含所有功能)
- Camelot (表格提取)
- 其他可选解析器

**prod 安装**:
- 仅 MinerU (基础版)

**影响**:
- dev: 支持更多 PDF 解析功能，适合测试和开发
- prod: 只安装核心解析器，减少依赖和体积

### 6. 其他脚本执行

| 脚本 | install (dev) | install-prod |
|------|---------------|--------------|
| `update_externals.sh` | ✅ | ✅ |
| `install_ffmpeg.sh` | ✅ | ✅ |
| `check_browser_deps.sh` | ✅ | ✅ |
| `install_video_downloaders.sh` | ✅ | ✅ |
| `install_browser_use.sh` | ✅ | ✅ |

**相同部分**: 这些脚本在两个命令中执行相同

## 总结对比表

| 特性 | install (dev) | install-prod |
|------|---------------|--------------|
| **Python 包数量** | ~50+ | ~20 |
| **磁盘占用** | 更大（包含模型和工具） | 更小 |
| **安装时间** | 更长 | 更短 |
| **测试工具** | ✅ 包含 | ❌ 不包含 |
| **代码质量工具** | ✅ 包含 | ❌ 不包含 |
| **Whisper 模型** | ✅ 预下载 | ❌ 按需下载 |
| **Jupyter Kernel** | ✅ 自动注册 | ⚠️ 需手动 |
| **PDF 解析器** | ✅ 全部 | ✅ 仅 MinerU |
| **浏览器自动化** | ✅ 完整依赖 | ⚠️ 基础依赖 |
| **适用场景** | 开发、测试、调试 | 生产部署 |

## 使用建议

### 使用 `make install` (dev) 的场景：
- ✅ 日常开发
- ✅ 运行测试
- ✅ 代码审查和格式化
- ✅ 调试和开发新功能
- ✅ 需要完整功能测试

### 使用 `make install-prod` 的场景：
- ✅ 生产环境部署
- ✅ Docker 容器构建
- ✅ CI/CD 流水线（如果不需要测试工具）
- ✅ 最小化安装（节省空间和时间）
- ✅ 服务器部署

## 磁盘空间估算

**install (dev)**:
- Python 包: ~500 MB - 1 GB
- Whisper 模型: ~1-3 GB
- 其他工具: ~200-500 MB
- **总计**: ~2-5 GB

**install-prod**:
- Python 包: ~200-400 MB
- Whisper 模型: 0 GB (按需下载)
- 其他工具: ~100-200 MB
- **总计**: ~300-600 MB

## 安装时间估算

**install (dev)**:
- 依赖安装: 5-15 分钟
- 模型下载: 5-20 分钟（取决于网络）
- **总计**: 10-35 分钟

**install-prod**:
- 依赖安装: 3-8 分钟
- 模型下载: 0 分钟（按需）
- **总计**: 3-8 分钟

---

**最后更新**: 2026-01-26  
**维护者**: 项目团队



