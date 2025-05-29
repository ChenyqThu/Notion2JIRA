# 版本映射配置指南

## 📋 概述

版本映射功能允许您将Notion中的版本名称映射到JIRA中的具体版本ID。这样当从Notion同步需求到JIRA时，系统可以自动设置正确的修复版本。

## 🚀 快速开始

### 1. 生成配置文件

```bash
# 从JIRA获取所有版本并生成配置文件
python scripts/generate_version_config.py
```

### 2. 编辑配置文件

配置文件位置：`config/version_mapping.json`

### 3. 查看映射状态

```bash
# 查看当前映射状态
python scripts/manage_version_mapping.py status
```

## 📝 配置文件格式

配置文件采用人性化的JSON格式：

```json
{
  "_metadata": {
    "description": "JIRA版本到Notion版本名称的映射配置",
    "instructions": {
      "如何配置": [
        "1. 在每个JIRA版本的notion_names数组中添加对应的Notion版本名称",
        "2. 如果某个JIRA版本没有对应的Notion版本，保持notion_names为空数组[]",
        "3. 可以在comment字段添加备注说明",
        "4. 修改后保存文件，系统会自动加载新配置"
      ]
    }
  },
  "default_version_id": "14577",
  "version_mappings": {
    "14577": {
      "jira_name": "待评估版本",
      "notion_names": ["待评估版本", "未分配", "TBD"],
      "released": false,
      "archived": false,
      "description": "",
      "comment": "默认版本，用于未明确指定版本的需求"
    },
    "14613": {
      "jira_name": "Omada v6.1",
      "notion_names": ["Omada v6.1", "v6.1", "6.1版本"],
      "released": false,
      "archived": false,
      "description": "",
      "comment": "Omada控制器6.1版本"
    }
  }
}
```

## 🔧 配置说明

### 字段说明

- **jira_name**: JIRA中的版本名称（自动从JIRA获取，不要修改）
- **notion_names**: 对应的Notion版本名称数组（您需要配置的部分）
- **released**: 版本是否已发布（自动从JIRA获取）
- **archived**: 版本是否已归档（自动从JIRA获取）
- **description**: JIRA版本描述（自动从JIRA获取）
- **comment**: 您的备注说明（可选）

### 配置原则

1. **一对多映射**: 一个JIRA版本可以对应多个Notion版本名称
2. **空值处理**: 如果notion_names为空，表示该JIRA版本没有对应的Notion版本
3. **默认版本**: 当找不到匹配的版本时，使用default_version_id指定的版本
4. **大小写敏感**: 版本名称匹配时会进行模糊匹配（忽略大小写和空格）

## 📊 管理工具

### 查看状态

```bash
python scripts/manage_version_mapping.py status
```

显示：
- 配置文件信息
- 映射统计
- 详细的版本映射表

### 交互式管理

```bash
python scripts/manage_version_mapping.py interactive
```

支持的命令：
- `status` - 显示状态
- `sync` - 从JIRA同步版本列表
- `add` - 添加版本映射
- `remove` - 移除版本映射
- `quit` - 退出

### 从JIRA同步版本

```bash
python scripts/manage_version_mapping.py sync
```

这会：
- 从JIRA获取最新的版本列表
- 更新配置文件中的JIRA版本信息
- 保留现有的Notion映射配置

## 🧪 测试映射

```bash
python test_version_mapping.py
```

测试各种版本名称的映射结果，确保配置正确。

## 💡 配置示例

### 示例1：基本映射

```json
"14613": {
  "jira_name": "Omada v6.1",
  "notion_names": ["Omada v6.1", "v6.1"],
  "comment": "Omada控制器6.1版本"
}
```

### 示例2：多种别名

```json
"14577": {
  "jira_name": "待评估版本",
  "notion_names": ["待评估版本", "未分配", "TBD", "待定"],
  "comment": "默认版本，用于未明确指定版本的需求"
}
```

### 示例3：未映射版本

```json
"14640": {
  "jira_name": "Cloud Portal v5.2",
  "notion_names": [],
  "comment": "暂时不需要映射"
}
```

## ⚠️ 注意事项

1. **备份配置**: 修改配置前建议备份原文件
2. **JSON格式**: 确保JSON格式正确，注意逗号和引号
3. **重新加载**: 修改配置后系统会自动重新加载，无需重启
4. **版本同步**: 定期运行sync命令获取JIRA的最新版本
5. **空值索引**: 空的notion_names不会影响查找性能，系统会自动跳过

## 🔍 故障排除

### 问题1：找不到版本映射

**现象**: 日志显示"未找到版本映射，使用默认版本"

**解决**: 
1. 检查Notion中的版本名称是否正确
2. 确认配置文件中是否有对应的映射
3. 检查大小写和空格

### 问题2：配置文件格式错误

**现象**: 系统无法加载配置文件

**解决**:
1. 使用JSON验证工具检查格式
2. 重新生成配置文件
3. 检查逗号和引号是否正确

### 问题3：JIRA版本不存在

**现象**: 配置的版本ID在JIRA中不存在

**解决**:
1. 运行sync命令更新版本列表
2. 检查JIRA项目配置
3. 确认版本ID是否正确

## 📈 最佳实践

1. **定期同步**: 每周运行一次sync命令
2. **统一命名**: 在Notion中使用统一的版本命名规范
3. **及时更新**: JIRA中新增版本后及时更新映射
4. **文档记录**: 在comment字段记录版本用途
5. **测试验证**: 配置后运行测试脚本验证

## 🔄 工作流程

1. **初始设置**:
   ```bash
   python scripts/generate_version_config.py
   ```

2. **配置映射**:
   编辑 `config/version_mapping.json`

3. **验证配置**:
   ```bash
   python test_version_mapping.py
   ```

4. **定期维护**:
   ```bash
   python scripts/manage_version_mapping.py sync
   ```

通过这个版本映射系统，您可以灵活地管理Notion和JIRA之间的版本对应关系，确保同步过程中版本信息的准确性。 