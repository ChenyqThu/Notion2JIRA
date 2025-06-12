# 新链接功能更新说明

本次更新重构了Notion页面中的链接处理逻辑，将不同类型的链接分别使用JIRA的Remote Link和Issue Link功能来处理，提供更好的链接管理体验。

## 主要改进

### 1. 原需求链接和PRD文档库链接 → Remote Link

**变更说明**：原来在JIRA Issue描述中直接添加的原需求链接和PRD文档库链接，现在改为使用JIRA的Remote Link功能。

**优势**：
- 在JIRA Issue页面的"链接"部分显示，更加清晰
- 支持链接类型标识和状态管理
- 不会让描述变得冗长
- 可以设置不同的链接关系类型

**处理的链接类型**：
- **原需求链接**：Notion页面本身的URL
- **PRD文档库链接**：通过"PRD 文档库"字段关联的文档页面

**Remote Link结构**：
```json
{
  "globalId": "notion-link-{hash}",
  "application": {
    "type": "com.notion.pages",
    "name": "Notion"
  },
  "relationship": "documented by",
  "object": {
    "url": "https://www.notion.so/page-id",
    "title": "原需求页面",
    "summary": "来自{issue_summary}的原始需求页面",
    "icon": {
      "url16x16": "https://www.notion.so/images/favicon.ico",
      "title": "Notion Page"
    }
  }
}
```

### 2. Relation字段中的JIRA Issue链接 → Issue Link

**变更说明**：Relation字段中包含的JIRA Issue Key（如SMBNET-123），现在使用JIRA的Issue Link功能直接建立Issue之间的关联关系。

**优势**：
- 在JIRA中建立真正的Issue关联关系
- 支持JIRA的链接类型（Blocks、Relates、Clones、Duplicate）
- 可以在JIRA中追踪Issue之间的依赖关系
- 支持双向导航

**处理逻辑**：
1. 从Relation字段（formula类型）中解析内容
2. 使用正则表达式提取JIRA Issue Keys：`\b([A-Z]+)-(\d+)\b`
3. 为每个Issue Key创建"Relates"类型的链接
4. 非JIRA格式的链接仍然作为Remote Link处理

**支持的Link Types**：
- **Relates** (ID: 10003)：默认使用，表示相关关系
- **Blocks** (ID: 10000)：阻塞关系
- **Clones** (ID: 10001)：克隆关系  
- **Duplicate** (ID: 10002)：重复关系

## 技术实现

### 字段映射器更新

**新增方法**：
- `_build_description_without_links()`: 构建不包含链接的描述
- `_extract_original_links()`: 提取原始需求链接
- `_extract_prd_links_for_remote()`: 提取PRD链接用于Remote Link
- `_is_jira_issue_link()`: 判断是否为JIRA Issue链接
- `_extract_jira_issue_keys_from_text()`: 从文本提取JIRA Issue Keys
- `build_remote_links_from_data()`: 构建多种类型的Remote Link对象

**映射流程**：
```
Notion Data
    ↓
解析并分类链接
    ↓
┌─────────────────┬─────────────────┐
│   Remote Links  │   Issue Links   │
│                 │                 │
│ • 原需求链接    │ • SMBNET-123    │
│ • PRD文档库链接 │ • SMBNET-456    │
│ • 其他关联链接  │ • ABC-789       │
└─────────────────┴─────────────────┘
    ↓                     ↓
JIRA Remote Link    JIRA Issue Link
```

### JIRA客户端更新

**新增方法**：
- `get_issue_link_types()`: 获取JIRA支持的Issue Link类型
- `create_issue_link()`: 创建单个Issue链接
- `create_issue_links()`: 批量创建Issue链接
- `extract_jira_issue_keys()`: 从文本提取JIRA Issue Keys

**Issue Link API**：
```http
POST /rest/api/2/issueLink
{
  "type": {"id": "10003"},
  "inwardIssue": {"key": "SMBNET-456"},
  "outwardIssue": {"key": "SMBNET-123"}
}
```

### 同步服务更新

**处理流程**：
1. 字段映射时分离`_remote_links`和`_issue_links`
2. 创建JIRA Issue后处理链接：
   - 使用`create_remote_issue_links()`处理Remote Links
   - 使用`create_issue_links()`处理Issue Links
3. 错误处理：链接创建失败不影响主同步流程

## 使用示例

### Notion页面示例

```yaml
功能 Name: "支付功能优化"
功能说明 Desc: "优化支付流程，提升用户体验"
PRD 文档库: 
  - page-id-1 (PRD文档1)
  - page-id-2 (PRD文档2)  
Relation: "SMBNET-123, SMBNET-456, https://www.notion.so/related-page"
```

### 处理结果

**JIRA Issue创建**：
- Summary: "支付功能优化"
- Description: "## 需求说明\n优化支付流程，提升用户体验"

**Remote Links创建**：
1. 原需求页面 → `https://www.notion.so/page-id`
2. PRD文档1 → `https://www.notion.so/page-id-1`  
3. PRD文档2 → `https://www.notion.so/page-id-2`
4. 关联页面 → `https://www.notion.so/related-page`

**Issue Links创建**：
1. 当前Issue ↔ SMBNET-123 (Relates)
2. 当前Issue ↔ SMBNET-456 (Relates)

## 配置说明

### 支持的字段名

**PRD文档库字段**：
- `PRD 文档库`
- `PRD文档库`  
- `PRD Documents`
- `prd_docs`

**关联字段**：
- `Relation`
- `relation`
- `关联`
- `关系`
- `关联链接`
- `Related Links`

### JIRA Issue Key格式

支持标准的JIRA Issue Key格式：
- 项目前缀：大写字母组合
- 连接符：`-`
- 数字：任意位数

**示例**：`SMBNET-123`、`ABC-456`、`PROJECT-1`

## 测试

运行测试脚本验证功能：

```bash
cd /path/to/Notion2JIRA
python test_new_link_features.py
```

测试覆盖：
1. 字段映射逻辑
2. JIRA Issue Key提取
3. Remote Link对象构建
4. Issue Link类型获取
5. 完整同步流程

## 注意事项

1. **向后兼容**：现有功能不受影响，只是改进了链接处理方式
2. **错误处理**：链接创建失败不会影响主要的Issue创建流程
3. **性能考虑**：批量处理链接以提高效率
4. **日志记录**：所有操作都有详细的日志记录便于调试

## 未来扩展

1. **更多Link Types**：支持配置不同类型的Issue关联关系
2. **智能链接识别**：根据内容自动判断链接类型和关系
3. **双向同步**：支持从JIRA反向同步链接变更到Notion
4. **链接验证**：验证链接的有效性和可访问性 