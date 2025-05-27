# JIRA Issue创建功能测试指南

## 概述

本文档说明如何测试第2.4节任务：**JIRA Issue创建逻辑**的实现。

## 功能说明

已实现的功能包括：

1. **JiraClient类** - JIRA API客户端
   - 连接JIRA系统
   - 创建、获取、更新Issue
   - 用户搜索和项目元数据获取

2. **FieldMapper类** - 字段映射引擎
   - Notion到JIRA的字段映射转换
   - 支持标题、描述、优先级、分配人员等字段
   - 必填字段验证

3. **SyncService更新** - 集成JIRA创建逻辑
   - 消费Redis队列中的同步消息
   - 执行字段映射和JIRA Issue创建
   - 保存同步映射关系

## 测试前准备

### 1. 环境变量配置

创建 `.env` 文件（基于 `.env_example`）：

```bash
# JIRA 基本配置
JIRA_BASE_URL=http://rdjira.tp-link.com
JIRA_USER_EMAIL=your.email@tp-link.com
JIRA_USER_PASSWORD=your_password_here

# JIRA项目配置
JIRA_PROJECT_KEY=SMBNET
JIRA_PROJECT_ID=13904
JIRA_DEFAULT_ISSUE_TYPE_ID=10001
JIRA_DEFAULT_VERSION_ID=14577

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 日志配置
LOG_LEVEL=INFO
```

### 2. 安装依赖

```bash
cd sync-service
pip install -r requirements.txt
```

## 测试步骤

### 1. 独立测试JIRA功能

运行测试脚本：

```bash
cd sync-service
python test_jira_creation.py
```

这个测试会：
- 测试JIRA连接
- 获取项目元数据
- 模拟Notion数据进行字段映射
- 创建真实的JIRA Issue
- 验证创建结果

### 2. 集成测试（完整流程）

启动同步服务：

```bash
cd sync-service
python main.py
```

然后通过webhook-server发送测试消息到Redis队列，观察同步服务的处理结果。

## 预期结果

### 成功情况

1. **连接测试成功**：
   ```
   ✅ JIRA连接成功
   项目信息: SMBNET (ID: 13904)
   ```

2. **Issue创建成功**：
   ```
   ✅ JIRA Issue创建测试成功
   Issue Key: SMBNET-1234
   Issue ID: 116789
   ```

3. **字段映射正确**：
   - 标题：从Notion的"功能 Name"字段映射
   - 描述：组合"功能说明 Desc"、"需求整理"和页面链接
   - 优先级：从"优先级 P"字段映射
   - 项目：自动设置为SMBNET
   - Issue类型：自动设置为Story

### 失败情况处理

1. **连接失败**：
   - 检查JIRA_BASE_URL是否正确
   - 检查用户名密码是否正确
   - 检查网络连接

2. **权限错误**：
   - 确认用户有SMBNET项目的创建权限
   - 检查Issue类型和版本ID是否正确

3. **字段验证失败**：
   - 检查必填字段是否都有值
   - 检查字段格式是否正确

## 代码结构

```
sync-service/
├── services/
│   ├── jira_client.py      # JIRA API客户端
│   ├── field_mapper.py     # 字段映射引擎
│   ├── sync_service.py     # 同步服务（已更新）
│   └── redis_client.py     # Redis客户端（已更新）
├── config/
│   └── settings.py         # 配置管理（已更新）
├── test_jira_creation.py   # 测试脚本
└── requirements.txt        # 依赖包
```

## 下一步

完成测试后，下一个任务是：

- **任务2.5**：重复检测机制
- **任务2.6**：Notion回写功能

这些功能将在当前基础上继续开发。

## 注意事项

1. **测试环境**：建议在测试环境中先验证，避免在生产JIRA中创建大量测试Issue
2. **清理数据**：测试完成后可以删除创建的测试Issue
3. **日志监控**：注意观察日志输出，了解详细的执行过程
4. **错误处理**：测试各种异常情况，确保错误处理机制正常工作 