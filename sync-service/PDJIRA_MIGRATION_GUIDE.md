# JIRA迁移指南：从rdjira到pdjira

## 📋 迁移概述

本文档记录了JIRA从`rdjira.tp-link.com`迁移到`pdjira.tp-link.com`的详细过程和所需的代码调整。

### 🔄 迁移信息
- **源环境**: http://rdjira.tp-link.com (旧版本)
- **目标环境**: https://pdjira.tp-link.com (JIRA 9.14.0)
- **项目空间**: SMBNET (保持不变)
- **迁移日期**: 2025-09-08

## 🚨 主要影响和变更

### 1. API兼容性问题

#### 用户搜索API参数变更
**问题**: JIRA 9.14版本中用户搜索API参数要求发生变化
```bash
# 错误信息
{"errorMessages":["没有提供用户查询所需参数"],"errors":{}}
```

**原因**: JIRA 9.x系列为了符合GDPR规定，修改了用户搜索API参数
- 弃用了`query`参数用于搜索邮箱
- 要求使用`username`参数进行用户搜索

**解决方案**: 
- 修改`services/jira_client.py`中的`search_users()`方法
- 从`query`参数改为`username`参数
- 自动提取邮箱中的用户名部分

#### Issue创建API项目字段格式变更
**问题**: 创建Issue时项目字段验证更严格
```bash
# 错误信息
{"errorMessages":[],"errors":{"project":"project is required"}}
```

**解决方案**:
- 将项目字段从`{'id': 'project_id'}`改为`{'key': 'project_key'}`
- 更新`services/field_mapper.py`和`services/jira_client.py`中的默认字段配置

### 2. 版本ID完全变更

**问题**: 新JIRA环境中所有版本ID都发生了变化
- 旧环境版本ID范围: 14577-14671
- 新环境版本ID范围: 10871-10918

**影响的文件**:
- `config/version_mapping.json` - 版本映射配置
- `config/settings.py` - 默认版本ID配置

**解决方案**:
- 重新生成版本映射配置文件
- 更新默认版本ID从`14577`到`10871`
- 保持版本名称映射关系

## 🛠️ 具体修改内容

### 1. 环境配置更新

**文件**: `scripts/init_config.py`
```python
# 修改前
JIRA_BASE_URL=http://rdjira.tp-link.com

# 修改后  
JIRA_BASE_URL=https://pdjira.tp-link.com
```

**文件**: `services/sync_service.py` (注释更新)
```python
# 修改前
jira_url: JIRA链接，如 "http://rdjira.tp-link.com/browse/SMBNET-123"

# 修改后
jira_url: JIRA链接，如 "https://pdjira.tp-link.com/browse/SMBNET-123"
```

### 2. 用户搜索API修复

**文件**: `services/jira_client.py`
```python
# 修改前
params = {
    'query': query,
    'maxResults': 10
}

# 修改后
params = {
    'username': query if '@' not in query else query.split('@')[0],
    'maxResults': 10
}
```

### 3. Issue创建字段修复

**文件**: `services/field_mapper.py` & `services/jira_client.py`
```python
# 修改前
def get_default_fields(self) -> Dict[str, Any]:
    return {
        'project': {'id': self.settings.jira.project_id},
        'issuetype': {'id': self.settings.jira.default_issue_type_id},
        'fixVersions': [{'id': self.settings.jira.default_version_id}]
    }

# 修改后
def get_default_fields(self) -> Dict[str, Any]:
    return {
        'project': {'key': self.settings.jira.project_key},
        'issuetype': {'id': self.settings.jira.default_issue_type_id},
        'fixVersions': [{'id': str(self.settings.jira.default_version_id)}]
    }
```

### 4. 版本配置更新

**文件**: `config/settings.py`
```python
# 修改前
default_version_id: str = "14577"

# 修改后
default_version_id: str = "10871"
```

**文件**: `config/version_mapping.json`
- 完全重新生成，包含新环境的48个版本
- 更新默认版本ID到"10871"
- 保留"待评估版本"的Notion名称映射

## 🔍 验证步骤

### 1. 环境验证脚本

创建了专门的验证脚本: `scripts/test_pdjira_migration.py`

运行验证:
```bash
python scripts/test_pdjira_migration.py
```

**验证内容**:
- ✅ JIRA连接测试
- ✅ 用户搜索API测试  
- ✅ 项目信息获取
- ✅ 版本信息获取 (48个版本)
- ✅ Issue创建字段验证

### 2. 版本映射重新生成

```bash
python scripts/generate_version_config.py
```

**结果**:
- 新环境发现48个版本 (vs 旧环境19个版本)
- 版本ID完全重新编号
- "待评估版本"从ID 14577 → 10871

## 📊 版本映射对比

| 版本名称 | 旧环境ID | 新环境ID | 状态 |
|---------|----------|----------|------|
| 待评估版本 | 14577 | 10871 | ✅ 已映射 |
| Controller 6.0 | 14605 | 10905 | 需要映射 |
| Design Center 1.2 | 14610 | 10874 | 需要映射 |
| Network 6.2 | 14614 | 10878 | 需要映射 |
| ... | ... | ... | ... |

## 🚀 部署建议

### 1. 部署前检查

```bash
# 1. 验证新环境连通性
python scripts/test_pdjira_migration.py

# 2. 检查配置文件
python scripts/init_config.py validate

# 3. 测试版本映射
python scripts/generate_version_config.py
```

### 2. 渐进式部署

1. **Phase 1**: 仅更新URL和基础API修复
2. **Phase 2**: 验证用户搜索功能  
3. **Phase 3**: 验证Issue创建功能
4. **Phase 4**: 完整同步功能测试

### 3. 回滚方案

如遇问题可快速回滚到旧环境:
```bash
# 恢复旧URL
JIRA_BASE_URL=http://rdjira.tp-link.com

# 恢复旧版本ID  
default_version_id: str = "14577"

# 使用旧版本映射配置的备份
```

## 🔧 故障排除

### 常见问题

1. **用户搜索返回空结果**
   - 检查用户名是否存在于新环境
   - 确认搜索参数格式正确

2. **版本映射失效**
   - 重新生成版本映射配置
   - 检查Notion版本名称是否需要调整

3. **Issue创建失败**
   - 验证项目Key是否正确
   - 检查字段格式是否符合新版本要求

### 调试工具

```bash
# API连通性测试
curl -u "username:password" "https://pdjira.tp-link.com/rest/api/2/myself"

# 用户搜索测试
curl -u "username:password" "https://pdjira.tp-link.com/rest/api/2/user/search?username=lucien.chen"

# 项目信息获取
curl -u "username:password" "https://pdjira.tp-link.com/rest/api/2/project/SMBNET"
```

## 📈 监控要点

迁移后需要重点监控:
- 同步成功率
- 用户搜索成功率  
- Issue创建成功率
- 版本映射准确性

## 💡 后续优化

1. **完善版本映射**: 根据实际使用情况补充Notion版本名称映射
2. **用户权限验证**: 确认所有用户在新环境中的权限正确
3. **性能监控**: 比较新旧环境的API响应性能
4. **数据一致性**: 定期检查同步数据的一致性

---

**迁移完成标志**: 所有测试用例通过，生产环境同步功能正常运行7天无异常。