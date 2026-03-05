# Hou CLI 网页阅读助手

Chrome 扩展，配合 Hou CLI 使用：
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
4. 扩展会在后台打开隐藏标签页、提取正文、关闭标签页，并将内容返回展示

### 视频下载（YouTube/Bilibili 需登录时）
1. 在浏览器中登录 YouTube 或 Bilibili
2. 在 Hou CLI「视频下载」页面，勾选「使用扩展获取 cookies」
3. 填写视频 URL，提交下载任务
4. 扩展会导出当前域名的 cookies 并传给后端，提高下载成功率

## 生产环境

若 Hou CLI 部署在非 localhost 的域名，需修改 `manifest.json` 中 `content_scripts.matches`，添加你的域名，例如：

```json
"matches": [
  "http://localhost:*/*",
  "http://127.0.0.1:*/*",
  "https://your-domain.com/*"
]
```
