# gvim-protocol-handler（`hou-gvim://`）

与仓库根目录下的 **`extension/` 平级** 的本机集成：用操作系统注册的自定义协议打开 MediaWiki 词条到 **gvim**，**不经过**浏览器扩展，也**不需要**本机 HTTP 后端。

业务逻辑与 `extension` → `POST /api/gvim/open-mediawiki-page` 一致：均调用 `GvimService.open_mediawiki_page`（见 `backend/services/gvim_service/gvim_service.py`）。请在 **hou-cli 仓库根** 配置好 `.env`（含 MediaWiki）并安装 `gvim`。

## 协议约定（与 extension 对齐词条标题）

| 项 | 约定 |
|----|------|
| Scheme | `hou-gvim` |
| 示例 | `hou-gvim://mediawiki?title=词条名`（`title` 须 URL 编码；亦支持查询键 `page_title`、`pageTitle`） |
| 词条解析 | 与 `extension/content.js` 中 `mediaWikiTitleFromLocation` 得到的字符串同一语义，链接里直接使用该标题的编码形式即可 |

## 目录结构

```
gvim-protocol-handler/
├── README.md                 # 本说明
├── scripts/
│   ├── open-from-url.sh      # 入口：bash + 虚拟环境 python
│   └── open_mediawiki_gvim.py
└── macos/
    ├── build-app.sh          # 生成 HouGvimURLHandler.app
    └── HouGvimURLHandler/
        ├── Info.plist        # 注册 CFBundleURLSchemes: hou-gvim
        └── main.swift        # 将 URL 转交给 open-from-url.sh
```

## 用法 A：命令行 / 自动化（无需 .app）

```bash
chmod +x scripts/open-from-url.sh
./gvim-protocol-handler/scripts/open-from-url.sh 'hou-gvim://mediawiki?title=My%20Page'

# 或直接
python gvim-protocol-handler/scripts/open_mediawiki_gvim.py --title "My Page"
```

`open-from-url.sh` 会优先使用仓库根下 `venv` / `.venv` 的 Python，否则 `python3`。

## 用法 B：macOS 注册 `hou-gvim://`

1. 安装 Xcode 命令行工具（含 `swiftc`）。
2. 在仓库内执行：

   ```bash
   chmod +x gvim-protocol-handler/macos/build-app.sh
   ./gvim-protocol-handler/macos/build-app.sh
   ```

3. 打开生成的 **`gvim-protocol-handler/macos/dist/HouGvimURLHandler.app`** 一次（或拷到 `/Applications`），系统会将 `hou-gvim://` 关联到该应用。
4. 在 Wiki 页面或扩展注入的链接中使用：

   ```html
   <a href="hou-gvim://mediawiki?title=ENCODED_TITLE">gvim 打开</a>
   ```

**注意**：`.app` 内嵌的脚本通过相对路径解析 **hou-cli 仓库根**（`gvim-protocol-handler/scripts` 的上两级）。若你移动了仅包含 `dist/*.app` 的目录而没有完整仓库，需自行改脚本中的 `REPO_ROOT` 或设置可写死的安装路径（可自行 fork 调整）。

## 与 `extension/` 协同

| 方式 | 依赖 |
|------|------|
| 扩展按钮 → 本机 API | 后端运行 + 端口探测 |
| `hou-gvim://` 链接 | 本目录脚本 + `.env` + `gvim`；可选 macOS `.app` 注册协议 |

可在同一 Wiki 上并存：扩展继续走 HTTP；希望免后端时在 UI 中增加 `hou-gvim://...` 链接（`encodeURIComponent(title)`）。

## Windows / Linux

当前仓库仅提供 **可复用的 shell + Python**；注册协议需在对应系统自行配置（例如 Windows 注册表 `URL Protocol`，Linux `xdg-mime` + `.desktop`），并指向 `open-from-url.sh` 的等价调用或 `python open_mediawiki_gvim.py --url ...`。
