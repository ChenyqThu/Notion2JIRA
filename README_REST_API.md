# JIRA REST API 测试脚本

这个脚本使用纯 REST API 方式与 JIRA 进行交互，包括创建 issue 和添加评论等功能。

## 主要功能

- ✅ 使用 REST API 创建 Issue
- ✅ 使用 REST API 添加评论
- ✅ 使用 REST API 更新 Issue
- ✅ 读取 Issue 信息
- ✅ 搜索 Issues (JQL)
- ✅ 获取项目信息和元数据

## 与原版本的区别

| 功能 | 原版本 (test.py) | 新版本 (test_rest_api.py) |
|------|------------------|---------------------------|
| 创建 Issue | 使用 webform 表单提交 | 使用 REST API |
| 添加评论 | 使用 REST API (有XSRF问题) | 使用 REST API |
| 更新 Issue | 使用 REST API | 使用 REST API |
| 认证方式 | Basic Auth + XSRF Token | Basic Auth |
| 请求头 | 模拟浏览器 | 标准 API 客户端 |

## 环境配置

确保 `.env` 文件包含以下配置：

```bash
JIRA_BASE_URL=http://rdjira.tp-link.com
JIRA_USER_EMAIL=your.email@tp-link.com
JIRA_USER_PASSWORD=your_password
VERIFY_SSL=False
TEST_PROJECT_KEY=SMBNET
TEST_ISSUE_TYPE_NAME=Story
```

## 运行脚本

```bash
python test_rest_api.py
```

## 脚本执行流程

1. **设置认证** - 配置 Basic Authentication
2. **测试连接** - 验证与 JIRA 的连接和认证
3. **获取项目信息** - 获取项目 ID 和可用的 issue 类型
4. **获取创建元数据** - 获取创建 issue 所需的字段信息
5. **创建 Issue** - 使用 REST API 创建新的 issue
6. **读取 Issue** - 验证创建的 issue
7. **添加评论** - 使用 REST API 添加评论
8. **更新 Issue** - 使用 REST API 更新 issue 字段
9. **验证更新** - 再次读取 issue 确认更新成功
10. **测试已知 Issue** - 读取用户指定的已存在 issue
11. **搜索 Issues** - 使用 JQL 搜索相关 issues

## 主要函数说明

### `create_issue_rest_api(project_key, summary, description, issue_type_name)`
使用 REST API 创建 issue，自动获取项目 ID 和 issue 类型 ID。

### `add_comment_rest_api(issue_key, comment_text)`
使用 REST API 向指定 issue 添加评论。

### `update_issue_rest_api(issue_key, fields_to_update)`
使用 REST API 更新 issue 的字段。

### `get_project_info(project_key)`
获取项目的详细信息，包括可用的 issue 类型。

### `get_create_meta(project_key)`
获取创建 issue 的元数据，包括必填字段信息。

## 优势

1. **标准化** - 使用标准的 REST API，符合 JIRA 官方文档
2. **简洁** - 不需要处理 XSRF token 和复杂的表单数据
3. **可靠** - 避免了 webform 方式可能遇到的页面变化问题
4. **易维护** - 代码结构清晰，易于理解和维护
5. **兼容性** - 适用于不同版本的 JIRA

## 注意事项

- 确保用户账号有创建 issue 和添加评论的权限
- 如果遇到 SSL 证书问题，可以设置 `VERIFY_SSL=False`（仅限测试环境）
- 项目 Key 和 issue 类型名称需要与实际 JIRA 配置匹配

## 错误处理

脚本包含完整的错误处理机制：
- HTTP 错误会显示详细的错误信息
- JSON 解析错误会显示原始响应内容
- 网络连接问题会给出相应提示
- 认证失败会提供解决建议 