# Notion2JIRA 连接工具

这个工具用于将 Notion 数据迁移到 JIRA，同时提供了与 JIRA 服务器的连接测试和基本操作功能。

## 特性

- 连接 JIRA 服务器并验证认证
- 创建 JIRA Issue
- 读取 JIRA Issue 信息
- 搜索 JIRA Issues
- 更新 JIRA Issue
- （待实现）添加评论和附件

## 环境设置

1. 安装依赖：
   ```
   pip install requests python-dotenv
   ```

2. 配置环境变量：
   - 复制 `.env_example` 文件并重命名为 `.env`
   - 编辑 `.env` 文件，填入您的实际配置信息：
     ```
     JIRA_BASE_URL=http://your-jira-server.com
     JIRA_USER_EMAIL=your.email@company.com
     JIRA_USER_PASSWORD=your_password_here
     ```

3. 环境变量说明：

   | 变量 | 说明 | 默认值 |
   |------|------|--------|
   | JIRA_BASE_URL | JIRA服务器的基础URL | http://rdjira.tp-link.com |
   | JIRA_USER_EMAIL | JIRA账号邮箱 | (空) |
   | JIRA_USER_PASSWORD | JIRA账号密码 | (空) |
   | VERIFY_SSL | 是否验证SSL证书 | False |
   | TRY_LEGACY_TLS_ADAPTER | 是否尝试使用旧版TLS适配器 | False |
   | USE_HTTP_1 | 是否使用HTTP/1.1协议 | True |
   | TEST_PROJECT_KEY | 测试用项目Key | SMBNET |
   | TEST_ISSUE_TYPE_NAME | 测试用Issue类型 | Story |

## 使用方法

直接运行脚本进行JIRA连接测试：

```
python test.py
```

脚本将执行以下操作：
1. 测试与JIRA服务器的连接和认证
2. 创建一个测试Issue
3. 读取创建的Issue信息
4. 尝试更新Issue
5. 测试搜索功能
6. 获取字段和Issue类型信息

## 安全注意事项

- 所有敏感信息（如用户名和密码）都应存储在 `.env` 文件中
- `.env` 文件已被添加到 `.gitignore` 中，确保不会被提交到版本控制系统
- 生产环境中应将 `VERIFY_SSL` 设置为 `True` 