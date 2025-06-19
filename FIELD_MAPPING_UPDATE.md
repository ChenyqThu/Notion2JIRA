# Notion字段映射更新说明

## 更新日期
2025年1月19日

## 更新内容

根据Notion数据库字段的变化，对系统中的字段映射配置进行了以下调整：

### 字段名变更

| 原字段名 | 新字段名 | 用途说明 |
|---------|---------|---------|
| 需求负责人 | Owner | 需求责任人，用于映射JIRA的Assignee和Reporter字段 |
| 功能 Name | Function Name | 功能标题，用于映射JIRA的Summary字段 |
| 功能说明 Desc | Description | 功能描述，用于映射JIRA的Description字段 |

### 影响的文件

#### sync-service（同步服务）
- `services/field_mapper.py` - 字段映射逻辑的核心文件
- `scripts/debug_fields.py` - 调试脚本中的字段列表
- `scripts/README.md` - Reporter字段映射功能说明
- `NEW_LINK_FEATURES_README.md` - 示例数据更新

#### webhook-server（Webhook服务）
- `routes/webhook.js` - 标题字段提取逻辑
- `scripts/test-field-parsing.js` - 测试脚本中的示例数据
- `scripts/test-webhook.js` - Webhook测试数据
- `README.md` - 字段说明文档

#### 文档
- `PRD.md` - 项目需求文档中的字段映射表

### 向后兼容性

系统保持向后兼容，同时支持新旧字段名：

- **Owner字段**: 优先使用"Owner"，同时支持"需求负责人"等旧字段名
- **Function Name字段**: 优先使用"Function Name"，同时支持"功能 Name"等旧字段名  
- **Description字段**: 优先使用"Description"，同时支持"功能说明 Desc"等旧字段名

### 字段优先级顺序

#### 标题字段
1. Function Name (新)
2. 功能 Name (旧)
3. title, name, Title, Name, 需求名

#### Owner字段
1. Owner (新)
2. 需求负责人 (旧)
3. 需求录入, reporter, Reporter, owner

#### 描述字段
1. Description (新)
2. 功能说明 Desc (旧)
3. description

### 部署说明

本次更新无需重启服务，配置变更会在下次字段映射时自动生效。

建议用户：
1. 将Notion数据库中的字段名更新为新的命名
2. 旧字段名仍可正常工作，但建议逐步迁移
3. 如有问题可回退到旧字段名

### 测试确认

更新后请确认以下功能正常：
- [ ] 新字段名的页面能正常同步到JIRA
- [ ] 标题、描述、负责人字段映射正确
- [ ] 旧字段名仍可正常工作（向后兼容）
- [ ] Webhook服务能正确解析新字段 