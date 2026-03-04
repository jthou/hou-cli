# Hou CLI 网页阅读助手

Chrome 扩展，配合 Hou CLI「网页阅读」功能使用。通过创建隐藏标签页加载目标 URL，复用当前浏览器的登录态（Cookie），提取正文后返回给网页展示。

## 安装

1. 打开 Chrome，访问 `chrome://extensions`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目的 `extension` 目录

## 使用

1. 确保扩展已安装并启用
2. 在 Hou CLI 中打开「网页阅读」页面
3. 输入要读取的 URL，点击「读取网页」
4. 扩展会在后台打开隐藏标签页、提取正文、关闭标签页，并将内容返回展示

## 生产环境

若 Hou CLI 部署在非 localhost 的域名，需修改 `manifest.json` 中 `content_scripts.matches`，添加你的域名，例如：

```json
"matches": [
  "http://localhost:*/*",
  "http://127.0.0.1:*/*",
  "https://your-domain.com/*"
]
```
