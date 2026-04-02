#!/usr/bin/env bash
# 在 macOS 上生成 HouGvimURLHandler.app，注册 hou-gvim:// 到本机。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOU_CLI_ROOT="$(cd "${ROOT}/.." && pwd)"
SRC="${ROOT}/macos/HouGvimURLHandler"
OUT="${ROOT}/macos/dist/HouGvimURLHandler.app"
BIN="${OUT}/Contents/MacOS/HouGvimURLHandler"
RES="${OUT}/Contents/Resources"

rm -rf "${OUT}"
mkdir -p "${OUT}/Contents/MacOS" "${RES}"
cp "${SRC}/Info.plist" "${OUT}/Contents/Info.plist"
cp "${ROOT}/scripts/open-from-url.sh" "${RES}/"
cp "${ROOT}/scripts/open_mediawiki_gvim.py" "${RES}/"
printf '%s' "${HOU_CLI_ROOT}" > "${RES}/hou_cli_root.txt"
chmod +x "${RES}/open-from-url.sh"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "需要 Xcode 命令行工具: xcode-select --install" >&2
  exit 1
fi
swiftc -O -whole-module-optimization "${SRC}/main.swift" -o "${BIN}" -framework Cocoa
chmod +x "${BIN}"

echo "已生成: ${OUT}"
echo "首次使用：双击该 app 一次（或通过「打开」）以注册协议；或将 app 拖到 /Applications 后从浏览器点击 hou-gvim:// 链接测试。"
