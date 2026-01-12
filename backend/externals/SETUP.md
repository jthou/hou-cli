# 外部依赖环境准备指南

本文档说明如何在新的开发机器上准备和同步外部依赖（externals）环境。

## 目录

- [系统依赖](#系统依赖)
- [Submodule 初始化](#submodule-初始化)
- [FFmpeg 编译](#ffmpeg-编译)
- [Whisper 安装](#whisper-安装)
- [其他依赖](#其他依赖)
- [验证安装](#验证安装)
- [常见问题](#常见问题)

---

## 系统依赖

在开始之前，确保系统已安装以下基础工具：

### macOS

```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装基础编译工具
xcode-select --install

# 安装必要的依赖
brew install git make pkg-config nasm
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    git \
    make \
    pkg-config \
    nasm \
    yasm \
    libtool \
    autoconf \
    automake \
    cmake
```

### Linux (CentOS/RHEL)

```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    git \
    pkgconfig \
    nasm \
    yasm \
    libtool \
    autoconf \
    automake \
    cmake
```

---

## Submodule 初始化

### 首次克隆仓库

如果是从零开始克隆仓库，使用 `--recursive` 参数自动初始化所有 submodule：

```bash
git clone --recursive <repository-url>
cd hou-cli
```

### 已有仓库初始化

如果已经克隆了仓库但没有初始化 submodule：

```bash
# 进入项目根目录
cd /path/to/hou-cli

# 初始化并更新所有 submodule
git submodule update --init --recursive
```

### 检查 Submodule 状态

```bash
# 查看所有 submodule 的状态
git submodule status

# 查看 submodule 的详细信息
git submodule foreach 'echo "=== $name ===" && git log -1 --oneline'
```

### 更新 Submodule

```bash
# 更新所有 submodule 到最新版本
git submodule update --remote

# 更新特定 submodule
git submodule update --remote backend/externals/ffmpeg
```

---

## FFmpeg 编译

FFmpeg 需要从源码编译，编译后的二进制文件位于 `backend/externals/ffmpeg/build/bin/`。

### 编译步骤

#### 1. 进入 FFmpeg 目录

```bash
cd backend/externals/ffmpeg
```

#### 2. 配置编译选项

```bash
# 基础配置（最小依赖，快速编译）
./configure \
    --prefix=$(pwd)/build \
    --enable-shared \
    --disable-static \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree

# 完整配置（包含更多编解码器，编译时间较长）
# 注意：需要先安装额外的依赖库（如 libx264, libvpx 等）
./configure \
    --prefix=$(pwd)/build \
    --enable-shared \
    --disable-static \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis
```

**推荐使用基础配置**，除非需要特定的编解码器支持。

#### 3. 编译

```bash
# 使用多核编译（推荐，加快编译速度）
make -j$(nproc)  # Linux
make -j$(sysctl -n hw.ncpu)  # macOS

# 或使用单核编译（如果遇到问题）
make
```

编译时间取决于机器性能，通常需要 10-30 分钟。

#### 4. 安装到 build 目录

```bash
make install
```

编译完成后，二进制文件将位于：
- `backend/externals/ffmpeg/build/bin/ffmpeg`
- `backend/externals/ffmpeg/build/bin/ffprobe`
- `backend/externals/ffmpeg/build/bin/ffplay`

### 验证 FFmpeg 编译

```bash
# 检查二进制文件是否存在
ls -lh backend/externals/ffmpeg/build/bin/

# 测试 FFmpeg 是否正常工作
backend/externals/ffmpeg/build/bin/ffmpeg -version
backend/externals/ffmpeg/build/bin/ffprobe -version
```

### 清理编译文件

如果需要重新编译：

```bash
cd backend/externals/ffmpeg
make clean
make distclean  # 完全清理，包括配置文件
```

### 平台特定说明

#### macOS

- 如果遇到 `nasm` 相关错误，确保已安装：`brew install nasm`
- 如果遇到权限问题，确保 `build` 目录可写

#### Linux

- 如果遇到缺少库的错误，查看 configure 输出的错误信息，安装相应的开发包
- 例如：`sudo apt install libx264-dev libvpx-dev` 等

---

## Whisper 安装

Whisper 是 Python 包，需要安装 Python 依赖。

### 前置要求

1. **Python 3.8-3.11**（推荐 3.9+）
2. **pip**（Python 包管理器）
3. **Rust**（可选，如果 tiktoken 需要编译）

### 安装 Rust（如果需要）

```bash
# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 或使用包管理器
# macOS
brew install rust

# Ubuntu/Debian
sudo apt install rustc cargo
```

### 安装 Whisper

```bash
# 进入项目根目录
cd /path/to/hou-cli

# 从本地源码安装（推荐，使用项目中的版本）
pip install -e backend/externals/whisper
```

这将自动安装所有依赖：
- PyTorch（深度学习框架）
- tiktoken（OpenAI 的快速分词器）
- numpy, numba, tqdm, more-itertools 等

### 验证 Whisper 安装

```bash
python -c "import whisper; print('Whisper installed successfully')"
python -c "import whisper; model = whisper.load_model('base'); print('Model loaded successfully')"
```

### 安装特定版本的 PyTorch（可选）

如果需要特定版本的 PyTorch（例如支持 CUDA）：

```bash
# 先安装 PyTorch
pip install torch torchvision torchaudio

# 然后安装 Whisper
pip install -e backend/externals/whisper
```

---

## 其他依赖

### Python 依赖（you-get, yt-dlp, bili23-downloader）

这些工具是纯 Python 实现，通常不需要额外编译。它们会在首次使用时自动安装依赖，或可以通过以下方式安装：

```bash
# you-get
pip install -e backend/externals/you-get

# yt-dlp
pip install -e backend/externals/yt-dlp

# bili23-downloader（如果有 requirements.txt）
cd backend/externals/bili23-downloader
pip install -r requirements.txt
```

### browser-use

```bash
pip install -e backend/externals/browser-use
```

---

## 验证安装

### 完整验证脚本

创建并运行以下脚本验证所有依赖：

```bash
#!/bin/bash
# verify_setup.sh

echo "=== 验证 Submodule ==="
git submodule status

echo ""
echo "=== 验证 FFmpeg ==="
if [ -f "backend/externals/ffmpeg/build/bin/ffmpeg" ]; then
    backend/externals/ffmpeg/build/bin/ffmpeg -version | head -1
else
    echo "❌ FFmpeg 未编译"
fi

echo ""
echo "=== 验证 Whisper ==="
python -c "import whisper; print('✅ Whisper 已安装')" 2>/dev/null || echo "❌ Whisper 未安装"

echo ""
echo "=== 验证其他工具 ==="
python -c "import you_get; print('✅ you-get 可用')" 2>/dev/null || echo "⚠️  you-get 未安装（可选）"
python -c "import yt_dlp; print('✅ yt-dlp 可用')" 2>/dev/null || echo "⚠️  yt-dlp 未安装（可选）"
```

运行验证：

```bash
chmod +x verify_setup.sh
./verify_setup.sh
```

---

## 常见问题

### 1. Submodule 显示为未初始化

**问题**：`git submodule status` 显示某些 submodule 前面有 `-` 号

**解决**：
```bash
git submodule update --init --recursive
```

### 2. FFmpeg 编译失败

**问题**：configure 或 make 失败

**解决**：
- 检查是否安装了所有系统依赖（见[系统依赖](#系统依赖)）
- 查看错误信息，安装缺失的库
- 尝试使用基础配置（不包含额外编解码器）
- 清理后重新编译：`make distclean && ./configure ... && make`

### 3. Whisper 安装失败（tiktoken 相关）

**问题**：安装时提示需要 Rust 或 setuptools_rust

**解决**：
```bash
# 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 安装 setuptools_rust
pip install setuptools-rust

# 重新安装 Whisper
pip install -e backend/externals/whisper
```

### 4. FFmpeg 二进制文件找不到

**问题**：运行时提示找不到 FFmpeg

**解决**：
- 确认已编译：`ls backend/externals/ffmpeg/build/bin/`
- 如果不存在，按照[FFmpeg 编译](#ffmpeg-编译)步骤重新编译
- 检查路径是否正确：工具会优先使用项目中的 FFmpeg，其次查找系统 PATH

### 5. 权限问题

**问题**：无法写入 build 目录

**解决**：
```bash
# 确保 build 目录存在且可写
mkdir -p backend/externals/ffmpeg/build
chmod -R u+w backend/externals/ffmpeg/build
```

### 6. 在不同机器间同步

**问题**：如何在多台机器上保持环境一致

**解决**：
1. **Submodule 版本**：通过 git 提交记录 submodule 的版本，其他机器拉取后执行 `git submodule update`
2. **编译产物**：FFmpeg 的 `build/` 目录通常不提交到 git（在 .gitignore 中），需要在每台机器上重新编译
3. **Python 依赖**：建议使用虚拟环境，并维护 `requirements.txt`

---

## 快速开始（完整流程）

对于新机器，按以下顺序执行：

```bash
# 1. 克隆仓库（包含 submodule）
git clone --recursive <repository-url>
cd hou-cli

# 2. 安装系统依赖（根据系统选择）
# macOS:
xcode-select --install
brew install git make pkg-config nasm

# Ubuntu/Debian:
sudo apt update && sudo apt install -y build-essential git make pkg-config nasm yasm

# 3. 编译 FFmpeg
cd backend/externals/ffmpeg
./configure --prefix=$(pwd)/build --enable-shared --disable-static --enable-gpl --enable-version3
make -j$(nproc)  # 或 make -j$(sysctl -n hw.ncpu) for macOS
make install
cd ../../..

# 4. 安装 Whisper
pip install -e backend/externals/whisper

# 5. 验证安装
backend/externals/ffmpeg/build/bin/ffmpeg -version
python -c "import whisper; print('Whisper OK')"
```

---

## 维护和更新

### 更新 Submodule

```bash
# 更新所有 submodule 到最新版本
git submodule update --remote

# 提交更新
git add backend/externals/
git commit -m "chore: update submodules"
```

### 重新编译 FFmpeg

如果更新了 FFmpeg submodule 或需要重新编译：

```bash
cd backend/externals/ffmpeg
make distclean
./configure --prefix=$(pwd)/build --enable-shared --disable-static --enable-gpl --enable-version3
make -j$(nproc)
make install
```

### 更新 Whisper

```bash
# 更新 submodule
git submodule update --remote backend/externals/whisper

# 重新安装
pip install -e backend/externals/whisper --upgrade
```

---

## 相关文档

- [README.md](./README.md) - 外部依赖的详细说明和使用指南
- [FFmpeg INSTALL.md](./ffmpeg/INSTALL.md) - FFmpeg 官方安装文档
- [Whisper README.md](./whisper/README.md) - Whisper 官方文档

