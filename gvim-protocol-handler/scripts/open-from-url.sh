#!/usr/bin/env bash
# 供自定义协议处理器或手动调试：解析 hou-gvim://... 并调用 GvimService。
set -euo pipefail
url="${1:-}"
if [[ -z "${url}" ]]; then
  echo "用法: open-from-url.sh 'hou-gvim://mediawiki?title=...'" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 与 macos/build-app.sh 写入的 hou_cli_root.txt 对齐（.app 内脚本不在仓库目录树下）
ROOT_FILE="${SCRIPT_DIR}/hou_cli_root.txt"
if [[ -f "${ROOT_FILE}" ]]; then
  REPO_ROOT="$(tr -d '\r\n' < "${ROOT_FILE}")"
elif [[ -n "${HOU_CLI_ROOT:-}" ]]; then
  REPO_ROOT="${HOU_CLI_ROOT}"
else
  # gvim-protocol-handler/scripts -> gvim-protocol-handler -> hou-cli 仓库根
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
fi
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
PY="python3"
if [[ -x "${REPO_ROOT}/venv/bin/python" ]]; then
  PY="${REPO_ROOT}/venv/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PY="${REPO_ROOT}/.venv/bin/python"
fi
exec "${PY}" "${SCRIPT_DIR}/open_mediawiki_gvim.py" --url "${url}"
