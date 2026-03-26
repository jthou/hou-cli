# Hou CLI 网页阅读助手

Chrome 扩展，配合 Hou CLI 使用：

- `background.js` - Service Worker，主流程
- `content.js` - Content Script，与页面通信
- `amazon.js` - Amazon 产品页专用逻辑：展开 productDetails、DOM 选择器、**指定位置截图**（主图、价格、产品详情等）
- **网页阅读**：通过创建隐藏标签页加载目标 URL，复用浏览器登录态，提取正文
- **视频下载**：导出 YouTube/Bilibili 等域名的 cookies（Netscape 格式），供 yt-dlp 使用，解决 403 下载失败

## 安装

1. 打开 Chrome，访问 `chrome://extensions`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目的 `extension` 目录

## 使用

### 网页阅读
1. 确保扩展已安装并启用
2. 在 Hou CLI 中打开「网页阅读」页面
3. 输入要读取的 URL，点击「读取网页」
4. 扩展会在后台打开隐藏标签页、**自动展开所有「See more」「展开更多」等折叠内容**、提取正文、关闭标签页，并将内容返回展示

#### 微信公众号配图（防盗链 / 跨域）

- **时间/背景**：`mp.weixin.qq.com` 正文内图片常依赖 Referer/Cookie，在 Markdown 预览或外链场景下无法直接加载。
- **方法**：在「网页阅读」抓取 **微信公众号文章 URL** 时，前端会请求扩展**附带拉取正文配图**（扩展内 `fetch` + 微信 Referer/Cookie）；图片以 data URL 回传后，由后端 `POST /api/web-reader/materialize-inline-images` 写入应用数据目录，Markdown 中替换为本站 ` /api/web-reader/inline-static/{uuid}.ext`。
- **占位图**：正文里常见 `src="data:image/svg+xml,..."` 懒加载占位，真图在 `data-src`；扩展在 `extractContent` 内会把此类 `src` 改写成绝对 `https://mmbiz.qpic.cn/...`，预览与 Markdown 替换才能对齐。
- **懒加载后**：浏览器常把 `src` 换成带 `tp=webp&wx_lazy=1` 等与 `data-src` 不同的 URL；拉图时用 **已加载的 `https` `src` 优先**，否则 `inlineImageMap` 键与 HTML 里 `src` 对不上。前端替换时同时匹配 `&` 与 `&amp;`（序列化差异）。

#### 微信读书 `weread.qq.com`

- **时间/背景**：与公众号类似，插图在 DOM 中且 CDN 可能校验 Referer。
- **方法**：在阅读器容器内抽取 `html` + 图片 URL → Service Worker 带 `Referer: https://weread.qq.com/` 与 Cookie `fetch` → 返回 `inlineImageMap`；前端 `materialize-inline-images` 后 `htmlToMd`。同时仍做分屏截图；**DOM 正文 ≥ 80 字** 时不自动跑 OCR，可手动「识别文字」。
- **插图 DOM**：常见 `img.wr_readerImage_opacity`，`src`/`data-src` 指向 `https://res.weread.qq.com/wrepub/...`；拉图时对 **每张图 URL** 使用 Referer `https://weread.qq.com/`（与页面 host 不同）。另对全书签内上述选择器再扫一遍，避免绝对定位图落在滚动根 `innerHTML` 外而漏 URL。
- **要求**：须在浏览器中已登录可打开该文的微信网页；扩展需有对应站点权限（默认 manifest 已含 `mp.weixin.qq.com`）。

### 视频下载（YouTube/Bilibili 需登录时）

用法与网页阅读类似：网页阅读用扩展抓取页面内容，视频下载用扩展导出 cookies。

1. 在浏览器中登录 YouTube 或 Bilibili
2. 在 Hou CLI「视频下载」页面，勾选「使用扩展获取 cookies」
3. 填写视频 URL，提交下载任务
4. 扩展会导出当前域名的 cookies 并传给后端，提高下载成功率

若遇到「Sign in to confirm you're not a bot」或 403 错误，详见 [docs/VIDEO_DOWNLOADER_FIXES.md](../docs/VIDEO_DOWNLOADER_FIXES.md)。

## 测试「Extension context invalidated」

扩展重新加载后，旧页面的 content script 可能报此错误。验证修复：

1. 打开 `http://127.0.0.1:8081/web-reader`（或 3000 端口）
2. 在 `chrome://extensions` 中点击扩展的「重新加载」
3. 回到 Web Reader 页面，点击「抓取」或输入 URL 读取
4. 控制台不应再出现未捕获的 "Extension context invalidated"；若出现，刷新页面即可

## 生产环境

若 Hou CLI 部署在非 localhost 的域名，需修改 `manifest.json` 中 `content_scripts.matches`，添加你的域名，例如：

```json
"matches": [
  "http://localhost:*/*",
  "http://127.0.0.1:*/*",
  "https://your-domain.com/*"
]
```
