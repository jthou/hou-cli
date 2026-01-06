# Google Custom Search API 配置指南

本文档说明如何获取和配置 Google Custom Search API 密钥和搜索引擎 ID。

## 概述

Google Custom Search API 允许您通过编程方式访问 Google 的搜索结果。需要两个关键信息：
1. **API 密钥**：用于身份验证
2. **搜索引擎 ID (cx)**：标识您的自定义搜索引擎

## 获取步骤

### 第一步：创建 Google Cloud 项目

1. 访问 [Google Cloud 控制台](https://console.cloud.google.com/)
2. 使用您的 Google 账号登录
3. 点击左上角的项目选择器，选择"新建项目"
4. 输入项目名称（如 "hou-cli-search"），点击"创建"

### 第二步：启用 Custom Search API

1. 在 Google Cloud 控制台中，点击左侧导航菜单
2. 选择"**API 和服务**" > "**库**"
3. 在搜索栏中输入"**Custom Search API**"
4. 找到"**Custom Search API**"，点击进入
5. 点击"**启用**"按钮

### 第三步：创建 API 密钥

1. 在左侧导航栏中，选择"**凭据**"
2. 点击"**创建凭据**"按钮
3. 选择"**API 密钥**"
4. 系统将生成一个新的 API 密钥，格式类似：`AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
5. **重要**：复制并保存此密钥

### 第四步：设置 API 密钥限制（推荐）

为了安全，建议设置 API 密钥限制：

1. 在"凭据"页面，点击刚创建的 API 密钥
2. 在"API 限制"部分，选择"限制密钥"
3. 选择"Custom Search API"
4. 在"应用限制"部分，可以选择：
   - **HTTP 引用来源**：限制只能从特定网站调用
   - **IP 地址**：限制只能从特定 IP 调用
   - **无**：不限制（不推荐用于生产环境）
5. 点击"保存"

### 第五步：创建自定义搜索引擎

1. 访问 [Google 可编程搜索引擎控制台](https://programmablesearchengine.google.com/controlpanel/all)
2. 点击"**添加**"按钮
3. 填写搜索引擎配置：
   - **搜索引擎名称**：例如 "hou-cli-web-search"
   - **要搜索的网站**：
     - 选择"搜索整个网络"：可以搜索所有网站
     - 或输入特定网站：例如 `example.com`（只搜索该网站）
4. 点击"**创建**"
5. 创建完成后，在搜索引擎列表中点击您的搜索引擎
6. 在"控制面板"页面，找到"**搜索引擎 ID**"（格式类似：`012345678901234567890:abcdefghijk`）
7. **重要**：复制并保存此 ID

## 配置到项目中

将获取的密钥和 ID 配置到 `.env` 文件中：

```bash
# Google Custom Search API 密钥
GOOGLE_SEARCH_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Google Custom Search Engine ID
GOOGLE_SEARCH_ENGINE_ID=012345678901234567890:abcdefghijk
```

## 配额和限制

### 免费配额
- **每天 100 次查询**
- 适合个人使用和小规模应用

### 付费配额
如果需要更高配额：
1. 在 Google Cloud 控制台中设置计费账户
2. 在"API 和服务" > "配额"中查看和调整配额
3. 付费配额根据使用量计费

## 安全建议

1. **设置 API 密钥限制**：限制只能从特定来源调用
2. **不要将密钥提交到代码仓库**：确保 `.env` 文件在 `.gitignore` 中
3. **定期轮换密钥**：如果密钥泄露，及时在 Google Cloud 控制台中删除并创建新密钥
4. **监控使用情况**：定期检查 API 使用量，防止异常调用

## 测试 API

可以使用以下 curl 命令测试 API 是否配置正确：

```bash
curl "https://www.googleapis.com/customsearch/v1?key=YOUR_API_KEY&cx=YOUR_ENGINE_ID&q=test"
```

将 `YOUR_API_KEY` 和 `YOUR_ENGINE_ID` 替换为您的实际值。

## 常见问题

### Q: API 密钥和搜索引擎 ID 有什么区别？
A: 
- **API 密钥**：用于身份验证，证明您有权限使用 Google API
- **搜索引擎 ID**：标识您创建的自定义搜索引擎，决定搜索范围和配置

### Q: 可以创建多个搜索引擎吗？
A: 可以。每个搜索引擎都有唯一的 ID，可以用于不同的搜索场景（例如：一个搜索整个网络，一个只搜索特定网站）。

### Q: 免费配额用完了怎么办？
A: 
- 等待第二天配额重置
- 或者设置计费账户以获取更高配额

### Q: 如何查看 API 使用情况？
A: 在 Google Cloud 控制台的"API 和服务" > "仪表板"中查看使用统计。

## 参考链接

- [Google Custom Search API 文档](https://developers.google.com/custom-search/v1/overview)
- [Google Cloud 控制台](https://console.cloud.google.com/)
- [可编程搜索引擎控制台](https://programmablesearchengine.google.com/controlpanel/all)

