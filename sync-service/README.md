# Notion2JIRA 同步服务

## 概述

Notion2JIRA同步服务是一个自动化工具，用于实现Notion数据库与JIRA项目之间的双向同步。

## 核心功能

### 1. Notion → JIRA 同步
- 接收Notion webhook事件
- 解析Notion页面数据
- 创建对应的JIRA Issue
- 支持字段映射和数据转换

### 2. 版本映射系统
- 支持Notion关联项目字段到JIRA版本的映射
- 本地映射文件管理
- 命令行管理工具
- 自动缓存和fallback机制

### 3. 字段映射引擎
- 支持32种Notion字段类型
- 智能类型检测
- 双重存储策略（properties + raw_properties）
- 容错机制

## 版本映射系统

### 工作原理

1. **关联项目字段检测**: 系统检测Notion页面中的"关联项目"字段
2. **版本名称提取**: 从关联项目页面ID获取对应的版本名称
3. **JIRA版本映射**: 将版本名称映射到JIRA版本ID
4. **Fallback机制**: 关联项目 → 计划版本 → 默认版本

### 本地映射管理

版本映射关系存储在 `data/notion_version_mapping.json` 文件中：

```json
{
  "mappings": {
    "1a715375-830d-80ca-8c96-fb4758a39f0c": {
      "name": "Controller 6.1 ePOS",
      "description": "控制器6.1版本，支持ePOS功能",
      "created_at": "2025-12-26T10:00:00",
      "updated_at": "2025-12-26T10:00:00"
    }
  },
  "last_updated": "2025-12-26T10:00:00",
  "version": "1.0.0",
  "description": "Notion项目库ID到名称的映射关系"
}
```

### 管理命令

使用 `scripts/manage_notion_version_mapping.py` 脚本管理版本映射：

```bash
# 列出所有映射
python scripts/manage_notion_version_mapping.py list

# 添加新映射
python scripts/manage_notion_version_mapping.py add \
  "1a715375-830d-80ca-8c96-fb4758a39f0c" \
  "Controller 6.1 ePOS" \
  "控制器6.1版本"

# 更新映射
python scripts/manage_notion_version_mapping.py update \
  "1a715375-830d-80ca-8c96-fb4758a39f0c" \
  "Controller 6.1 ePOS Updated" \
  "更新的描述"

# 删除映射
python scripts/manage_notion_version_mapping.py remove \
  "1a715375-830d-80ca-8c96-fb4758a39f0c"

# 搜索映射
python scripts/manage_notion_version_mapping.py search "Controller"

# 从CSV导入
python scripts/manage_notion_version_mapping.py import mappings.csv

# 导出到CSV
python scripts/manage_notion_version_mapping.py export mappings.csv
```

### CSV格式

导入/导出的CSV文件格式：

```csv
notion_id,version_name,description,created_at
1a715375-830d-80ca-8c96-fb4758a39f0c,Controller 6.1 ePOS,控制器6.1版本,2025-12-26T10:00:00
```

## 配置管理

### 环境变量

在 `.env` 文件中配置以下变量：

```env
# JIRA配置
JIRA_BASE_URL=https://your-jira-instance.com
JIRA_USER_EMAIL=your-email@company.com
JIRA_USER_PASSWORD=your-api-token
JIRA_PROJECT_KEY=SMBNET
JIRA_PROJECT_ID=13904

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Notion配置（可选，用于反向同步）
NOTION_TOKEN=secret_your_notion_integration_token_here
NOTION_DATABASE_ID=your_notion_database_id_here
NOTION_VERSION_DATABASE_ID=1a015375830d8119ac6ff5e28ce889d6

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/sync_service.log
```

### 版本映射配置

版本映射配置文件位于 `config/version_mapping.json`：

```json
{
  "version_mappings": {
    "Controller 6.1 ePOS": 14605,
    "Controller 6.0": 14577,
    "v6.0": 14577,
    "v6.1": 14605
  },
  "default_version_id": 14577
}
```

## 服务模块

### 核心服务

- **NotionVersionCache** (`services/notion_version_cache.py`): 版本缓存管理器
- **VersionMapper** (`services/version_mapper.py`): 版本映射服务
- **FieldMapper** (`services/field_mapper.py`): 字段映射引擎
- **JiraClient** (`services/jira_client.py`): JIRA API客户端
- **NotionClient** (`services/notion_client.py`): Notion API客户端

### 管理脚本

- **manage_notion_version_mapping.py**: 版本映射管理工具
- **test_simple_mapping.py**: 版本映射功能测试

## 部署指南

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

```bash
# 复制环境变量模板
cp .env_example .env

# 编辑配置文件
vim .env
```

### 3. 初始化版本映射

```bash
# 添加版本映射
python scripts/manage_notion_version_mapping.py add \
  "notion-page-id" \
  "Version Name" \
  "Description"
```

### 4. 启动服务

```bash
# 启动同步服务
python main.py
```

## 测试

### 版本映射测试

```bash
# 运行版本映射测试
python test_simple_mapping.py
```

### 功能测试

```bash
# 测试JIRA连接
python test_jira_connection.py

# 测试字段映射
python test_field_mapping.py
```

## 监控和维护

### 日志查看

```bash
# 查看实时日志
tail -f logs/sync_service.log

# 查看错误日志
grep ERROR logs/sync_service.log
```

### 版本映射维护

```bash
# 定期检查映射状态
python scripts/manage_notion_version_mapping.py list

# 备份映射数据
python scripts/manage_notion_version_mapping.py export backup_$(date +%Y%m%d).csv
```

## 故障排除

### 常见问题

1. **版本映射失败**
   - 检查 `data/notion_version_mapping.json` 文件是否存在
   - 验证Notion页面ID格式是否正确
   - 确认版本名称在JIRA中存在

2. **JIRA连接失败**
   - 检查JIRA配置是否正确
   - 验证API token是否有效
   - 确认网络连接正常

3. **字段映射错误**
   - 查看详细日志信息
   - 检查字段类型是否支持
   - 验证数据格式是否正确

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python main.py
```

## 未来规划

### 监控看板

计划开发Web界面用于：
- 可视化管理版本映射
- 监控同步状态
- 查看同步历史
- 配置管理界面
- 错误日志查看

### 功能扩展

- 支持更多字段类型
- 增强错误处理机制
- 性能优化
- 批量操作支持

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

[MIT License](LICENSE) 