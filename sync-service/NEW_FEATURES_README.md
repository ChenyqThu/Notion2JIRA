# 新功能更新说明

本次更新实现了三个重要的功能改进：

## 1. 内存利用率告警阈值提升

### 修改内容
- 将内存利用率告警阈值从 **80%** 提升到 **90%**
- Warning 级别：内存使用率 > 90%
- Critical 级别：内存使用率 > 95%
- 健康检查中的内存阈值也相应调整到 95%

### 修改文件
- `sync-service/services/monitor_service.py`

### 影响
- 减少不必要的内存告警
- 提高系统运行的稳定性阈值

## 2. 根据产品线字段映射JIRA Assignee

### 映射关系
根据 Notion Page 的 **产品线字段**，自动决定 JIRA 的 Assignee：

| 产品线 | 经办人 |
|--------|--------|
| Controller | ludingyang@tp-link.com.hk |
| Gateway | zhujiayin@tp-link.com.hk |
| Managed Switch | huangguangrun@tp-link.com.hk |
| Unmanaged Switch | huangguangrun@tp-link.com.hk |
| EAP | ouhuanrui@tp-link.com.hk |
| OLT | fancunlian@tp-link.com.hk |
| APP | xingxiaosong@tp-link.com.hk |
| **其他未命中的** | ludingyang@tp-link.com.hk（默认） |

### 字段名支持
系统会自动识别以下字段名：
- `产品线`
- `product_line`
- `Product Line`
- `Product`

### 修改文件
- `sync-service/services/field_mapper.py` 中的 `_extract_assignee` 方法

## 3. Relation 字段关联页面链接支持

### 功能说明
当 Notion Page 的 **relation 字段**（formula 类型）包含一个或多个关联页面的链接时，系统会：

1. **解析关联链接**：支持逗号分隔的多个链接
2. **创建远程链接**：通过 JIRA REST API 向 JIRA card 写入 relation 关系
3. **自动构建**：根据链接自动构建符合 JIRA 标准的远程链接对象

### API 接口
使用 JIRA REST API：
```
POST /rest/api/2/issue/{issueIdOrKey}/remotelink
```

### 支持的数据格式

#### Formula 类型（逗号分隔）
```json
{
  "properties": {
    "relation": {
      "value": "https://www.notion.so/page1,https://www.notion.so/page2",
      "type": "formula"
    }
  }
}
```

#### 直接 Relation 类型
```json
{
  "properties": {
    "relation": {
      "value": [
        {"id": "abc123def456"},
        {"id": "def456ghi789"}
      ],
      "type": "relation"
    }
  }
}
```

### 字段名支持
系统会自动识别以下字段名：
- `relation`
- `Relation`
- `关联`
- `关系`

### 远程链接对象结构
```json
{
  "globalId": "notion-relation-{hash}",
  "application": {
    "type": "com.notion.pages",
    "name": "Notion"
  },
  "relationship": "relates to",
  "object": {
    "url": "关联页面URL",
    "title": "关联页面标题",
    "summary": "来自{issue_summary}的关联页面",
    "icon": {
      "url16x16": "https://www.notion.so/images/favicon.ico",
      "title": "Notion Page"
    },
    "status": {
      "resolved": false,
      "icon": {
        "url16x16": "https://www.notion.so/images/favicon.ico",
        "title": "Active"
      }
    }
  }
}
```

### 修改文件
- `sync-service/services/field_mapper.py`：
  - 新增 `_extract_relations` 方法
  - 新增 `build_remote_issue_links` 方法
  - 修改 `map_notion_to_jira` 方法
- `sync-service/services/jira_client.py`：
  - 新增 `create_remote_issue_link` 方法
- `sync-service/services/sync_service.py`：
  - 修改 `_create_new_jira_issue` 方法，添加远程链接处理

## 测试

运行测试脚本验证新功能：

```bash
cd sync-service
python test_new_features.py
```

测试内容包括：
1. 内存告警阈值测试
2. 产品线映射测试
3. 关联字段提取测试
4. 远程链接构建测试

## 部署说明

1. **无需配置更改**：所有新功能都是基于现有配置
2. **向后兼容**：现有功能不受影响
3. **错误处理**：远程链接创建失败不会影响主同步流程
4. **日志记录**：所有操作都有详细的日志记录

## 注意事项

1. **远程链接创建**：仅在创建新 JIRA Issue 时处理，更新操作暂不支持
2. **链接格式**：目前支持 Notion 页面链接和一般 URL
3. **错误恢复**：远程链接创建失败时会记录错误但不中断主流程
4. **性能影响**：批量链接创建可能会增加处理时间

## 日志示例

```
2024-01-15 10:30:15 - field_mapper - INFO - 根据产品线 'Controller' 分配经办人: ludingyang@tp-link.com.hk
2024-01-15 10:30:16 - field_mapper - INFO - 提取到 2 个关联链接
2024-01-15 10:30:17 - field_mapper - INFO - 构建了 2 个远程链接对象
2024-01-15 10:30:18 - jira_client - INFO - 开始创建远程链接, issue_key=SMBNET-123, link_count=2
2024-01-15 10:30:19 - sync_service - INFO - 远程链接创建成功, page_id=abc123, jira_issue_key=SMBNET-123, link_count=2 