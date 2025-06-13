# 同步服务脚本说明

## 状态映射同步脚本 (sync_status_mapping.py)

### 功能说明
该脚本用于获取Notion和JIRA的当前状态，并分析、更新状态映射表。

### 主要功能
1. **获取JIRA状态**: 自动获取JIRA项目的所有工作流状态
2. **获取Notion状态**: 获取Notion数据库的状态字段选项
3. **映射分析**: 分析当前映射表的覆盖情况，识别新增或过时的状态
4. **生成建议**: 为新状态提供映射建议
5. **保存报告**: 生成详细的分析报告和更新后的映射表

### 使用方法

#### 1. 仅分析JIRA状态
```bash
cd sync-service/scripts
python sync_status_mapping.py
```

#### 2. 同时分析JIRA和Notion状态
```bash
cd sync-service/scripts
python sync_status_mapping.py --notion-db-id your-notion-database-id
```

#### 3. 显示帮助信息
```bash
python sync_status_mapping.py --show-help
```

### 输出文件
脚本会在 `sync-service/data/` 目录下生成以下文件：

1. **分析报告** (`status_mapping_analysis_YYYYMMDD_HHMMSS.json`)
   - 包含完整的分析结果
   - JIRA和Notion状态列表
   - 映射覆盖情况
   - 改进建议

2. **更新后的映射表** (`updated_status_mapping_YYYYMMDD_HHMMSS.py`)
   - Python格式的状态映射表
   - 可直接用于更新代码中的映射配置

### 示例输出
```json
{
  "jira_statuses": ["TODO", "开发中", "Testing（测试）", "完成"],
  "notion_statuses": ["待输入 WI", "JIRA Wait Review", "DEVING", "Testing"],
  "mapping_coverage": {
    "covered": 4,
    "total": 4,
    "percentage": 100.0
  },
  "suggestions": []
}
```

## JIRA用户缓存管理脚本 (manage_user_cache.py)

### 功能说明
该脚本用于管理JIRA用户缓存，提供邮箱到用户ID的映射，避免频繁查询JIRA API。

### 主要功能
1. **刷新缓存**: 获取所有JIRA用户并建立邮箱映射
2. **查看统计**: 显示缓存状态和统计信息
3. **搜索用户**: 根据邮箱搜索特定用户
4. **测试映射**: 测试产品线用户映射是否正确

### 使用方法

#### 1. 刷新用户缓存
```bash
cd sync-service/scripts
python manage_user_cache.py refresh
```

#### 2. 强制刷新缓存（忽略TTL）
```bash
python manage_user_cache.py refresh --force
```

#### 3. 查看缓存统计
```bash
python manage_user_cache.py stats
```

#### 4. 搜索特定用户
```bash
python manage_user_cache.py search --email harry.zhao@tp-link.com
```

#### 5. 测试产品线用户映射
```bash
python manage_user_cache.py test
```

### 缓存特性
- **自动过期**: 缓存默认24小时后过期
- **持久化**: 缓存保存在 `sync-service/data/jira_user_cache.json`
- **增量更新**: 支持实时搜索并更新缓存
- **性能优化**: 避免重复的JIRA API调用

### 示例输出

#### 缓存统计
```
=== JIRA用户缓存统计 ===
总用户数: 156
缓存时间: 2025-06-13T11:45:00.123456
缓存过期: 否
缓存文件: /path/to/sync-service/data/jira_user_cache.json
缓存TTL: 24.0 小时

示例用户 (前10个):
  harry.zhao@tp-link.com -> Harry (119d872b-594c-8133-a207-000293b6f173)
  ludingyang@tp-link.com.hk -> Luding Yang (account-id-123)
  ...
```

#### 用户搜索
```
=== 搜索用户: harry.zhao@tp-link.com ===
找到用户:
  姓名: Harry
  邮箱: harry.zhao@tp-link.com
  账户ID: 119d872b-594c-8133-a207-000293b6f173
  状态: 活跃
```

#### 产品线映射测试
```
=== 测试产品线用户映射 ===
检查产品线负责人邮箱:
  ✓ Controller: ludingyang@tp-link.com.hk -> Luding Yang
  ✓ Gateway: zhujiayin@tp-link.com.hk -> Zhu Jiayin
  ✗ Managed Switch: huangguangrun@tp-link.com.hk -> 未找到
  ...

检查Reporter邮箱:
  ✓ Reporter: harry.zhao@tp-link.com -> Harry
```

## 注意事项

1. **权限要求**: 确保JIRA账户有足够权限访问用户信息
2. **网络连接**: 脚本需要访问JIRA API，确保网络连接正常
3. **配置文件**: 确保 `.env` 文件中的JIRA配置正确
4. **缓存文件**: 用户缓存文件包含敏感信息，注意保护

## Reporter字段映射功能

### 新增功能说明
现在系统支持将Notion的"需求负责人"字段同时映射为JIRA Issue的Reporter字段。

### 工作原理
1. 从Notion的"需求负责人"字段提取用户邮箱
2. 在JIRA中查找对应的用户账户
3. 将找到的用户设置为JIRA Issue的Reporter
4. 如果找不到对应用户，会记录警告日志但不影响Issue创建

### 支持的字段名
- 需求负责人 (推荐)
- 需求录入 (向后兼容)
- reporter
- Reporter
- owner
- Owner

### 日志示例
```
从需求负责人字段提取到Reporter邮箱: user@tp-link.com.hk
找到Reporter对应的JIRA用户: 张三 (account-id-123)
字段映射转换完成 - has_reporter: True
``` 