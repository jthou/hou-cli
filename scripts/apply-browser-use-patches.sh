#!/bin/bash
# 应用 browser-use 补丁脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCHES_DIR="$PROJECT_ROOT/patches/browser-use"
SUBMODULE_DIR="$PROJECT_ROOT/backend/externals/browser-use"

echo "=========================================="
echo "应用 browser-use 补丁"
echo "=========================================="

# 检查 submodule 是否存在
if [ ! -d "$SUBMODULE_DIR" ]; then
    echo "❌ browser-use submodule 不存在，请先初始化："
    echo "   git submodule update --init --recursive"
    exit 1
fi

# 检查补丁文件是否存在
if [ ! -d "$PATCHES_DIR" ] || [ -z "$(ls -A $PATCHES_DIR/*.patch 2>/dev/null)" ]; then
    echo "⚠️  没有找到补丁文件，跳过"
    exit 0
fi

cd "$SUBMODULE_DIR"

# 确保在正确的分支
git checkout -b hou-cli-patched 2>/dev/null || git checkout hou-cli-patched

# 应用补丁
echo ""
echo "应用补丁文件..."
for patch in "$PATCHES_DIR"/*.patch; do
    if [ -f "$patch" ]; then
        echo "  应用: $(basename $patch)"
        git am "$patch" || {
            echo "⚠️  补丁应用失败，尝试使用 git apply..."
            git apply "$patch" || echo "❌ 无法应用补丁: $patch"
        }
    fi
done

echo ""
echo "✅ 补丁应用完成"
echo "当前 commit: $(git rev-parse --short HEAD)"
