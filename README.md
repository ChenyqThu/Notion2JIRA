# Notion2JIRA 同步系统

## 项目简介

Notion2JIRA 是一个自动化同步系统，实现 Notion Database 与 JIRA 项目之间的数据同步。该系统专为 EBG 商用产品团队设计，解决需求管理和开发管理系统之间的数据孤岛问题。

## 🚀 核心功能

- **双向同步**: Notion ↔ JIRA 自动双向同步
- **智能字段映射**: 支持多种字段类型的智能映射和数据转换
- **状态回写**: 同步完成后自动更新Notion状态和JIRA链接
- **增量检测**: 基于时间戳的增量同步机制
- **重复检测**: 防止重复创建 JIRA Issue
- **错误处理**: 完善的错误处理和重试机制
- **灵活触发**: 支持按钮点击和复选框控制的同步触发
- **Remote Link管理**: 智能管理远程链接，避免重复创建

## 📊 项目状态

- ✅ **第0阶段**: 项目调研与准备（已完成 100%）
- ✅ **第1阶段**: 基础设施搭建（已完成 100%）
- ✅ **第2阶段**: 核心同步功能开发（已完成 95%）
- ✅ **第3阶段**: 问题修复与优化（已完成 100%）
- 🔄 **第4阶段**: 反向同步功能开发（进行中 30%）
- 📋 **第5阶段**: 测试与部署（待开始）

### 🎯 最新优化成果

#### Formula字段版本提取优化
- **性能提升**: Formula方式 0.0001秒 vs Relation+API方式 0.6844秒，性能提升6800倍
- **功能增强**: 支持"关联项目名"、"关联项目名 (Formula)"等多种字段名
- **向后兼容**: 保留原有relation方式作为fallback

#### 四个核心问题修复
1. **版本匹配优化**: 双重获取机制，支持多字段版本信息提取
2. **PRD链接增强**: 完善PRD文档库字段提取和URL拼接
3. **描述内容清理**: JIRA描述排除链接信息，专注需求内容
4. **Remote Link优化**: 使用真实页面标题，智能fallback机制

#### Remote Link更新机制
- **避免重复**: 基于globalId的更新机制，避免重复创建链接
- **内容更新**: 支持链接标题、摘要等信息的动态更新
- **稳定性提升**: 修复版本字段格式问题，确保同步成功

## 🛠️ 快速开始

### 环境要求

- **Node.js**: >= 16.0.0
- **Redis**: >= 6.0
- **Python**: >= 3.8
- **操作系统**: Linux/macOS/Windows

### 本地开发部署

#### 1. 克隆项目
```bash
git clone <repository-url>
cd Notion2JIRA
```

#### 2. 安装依赖
```bash
# Webhook 服务依赖
cd webhook-server
npm install

# 同步服务依赖
cd ../sync-service
pip install -r requirements.txt
```

#### 3. 配置环境变量
```bash
# 复制环境变量模板
cp .env_example .env

# 编辑配置文件
vim .env
```

#### 4. 启动 Redis
```bash
# macOS (使用 Homebrew)
brew services start redis

# Linux (使用 systemctl)
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

#### 5. 启动服务
```bash
# 启动 Webhook 服务
cd webhook-server
npm start

# 启动同步服务 (另一个终端)
cd sync-service
python main.py
```

### 生产环境部署

#### Docker Compose 部署（推荐）

```yaml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  webhook-server:
    build: ./webhook-server
    ports:
      - "7654:7654"
    environment:
      - NODE_ENV=production
      - REDIS_HOST=redis
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs

  sync-service:
    build: ./sync-service
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs

volumes:
  redis_data:
```

#### 传统部署

详细的生产环境部署步骤，请参考 `deploy.sh` 脚本或联系技术团队。

## 🔧 核心特性

### 智能字段映射

系统采用双重存储结构，确保数据完整性和可扩展性：

```json
{
  "properties": {
    "fieldName": {
      "type": "字段类型",
      "value": "解析后的值", 
      "raw": "原始数据"
    }
  },
  "raw_properties": {
    "fieldName": "完整原始数据"
  }
}
```

**支持的字段类型**：
- 基础类型：title, rich_text, number, select, multi_select
- 关系类型：people, relation, files
- 状态类型：status, checkbox
- 时间类型：date, created_time, last_edited_time
- 扩展类型：email, phone_number, url, unique_id, verification
- 计算类型：formula, rollup
- 系统类型：created_by, last_edited_by

### 同步触发机制

系统支持多种同步触发方式：

1. **Button Property 点击**（推荐）
   - 用户点击 Notion 页面中的按钮属性
   - 系统自动检测按钮点击事件

2. **Checkbox 控制**
   - 支持字段名：`sync2jira`、`同步到JIRA`、`Sync to JIRA`
   - 勾选复选框即触发同步

3. **默认策略**
   - 收到 webhook 即认为需要同步
   - 适用于简单场景

### Remote Link管理

**GlobalId机制**：
- `notion-page-{hash}`: Notion页面链接（原需求页面）
- `notion-prd-{hash}`: PRD文档链接
- `notion-related-{hash}`: 其他关联链接

**智能更新**：
- 基于URL的MD5哈希生成稳定globalId
- 同一URL的链接自动更新而非重复创建
- 支持链接标题、摘要的动态更新

### 版本字段优化

**Formula字段支持**：
- 直接从"关联项目名"Formula属性获取项目名称
- 性能提升6800倍（0.0001秒 vs 0.6844秒）
- 向后兼容原有relation方式

**版本映射增强**：
- 支持多种版本字段名称识别
- 双重获取机制：版本缓存 + API获取
- 智能fallback到默认版本

## 📁 项目结构

```
Notion2JIRA/
├── README.md                       # 项目文档（本文件）
├── PRD.md                          # 产品需求文档
├── Architecture.md                 # 架构设计文档
├── tasks.md                        # 任务分解文档
├── CHANGELOG.md                    # 变更日志
├── deploy.sh                       # 部署脚本
├── requirements.txt                # Python依赖
├── .env_example                    # 环境变量示例
├── webhook-server/                 # 公网代理服务
│   ├── config/                     # 配置文件
│   ├── middleware/                 # 中间件
│   ├── routes/                     # 路由处理
│   ├── scripts/                    # 工具脚本
│   ├── server.js                   # 主服务文件
│   ├── ecosystem.config.js         # PM2 配置
│   └── package.json                # 依赖配置
└── sync-service/                   # 内网同步服务
    ├── config/                     # 配置管理
    ├── services/                   # 业务逻辑
    ├── data/                       # 数据存储
    ├── main.py                     # 主程序入口
    └── requirements.txt            # Python依赖
```

## 🔍 监控和调试

### 健康检查
```bash
# 检查服务状态
curl http://localhost:7654/health

# 获取统计信息
curl http://localhost:7654/stats

# 查看队列状态
curl http://localhost:7654/queue/status
```

### 日志监控
```bash
# 查看webhook服务日志
tail -f webhook-server/logs/webhook.log

# 查看同步服务日志
tail -f sync-service/logs/sync.log

# 查看错误日志
tail -f logs/error.log
```

### Redis 队列管理
```bash
# 连接 Redis
redis-cli

# 查看队列长度
LLEN notion_sync_queue

# 查看队列内容
LRANGE notion_sync_queue 0 -1

# 查看最新消息
LINDEX notion_sync_queue 0
```

## 🔧 CORS 配置

系统提供灵活的 CORS 配置：

```bash
# 开发环境 - 允许所有来源
CORS_ENABLED=true
NODE_ENV=development

# 生产环境 - 严格控制
CORS_ENABLED=true
NODE_ENV=production
CORS_ORIGIN=https://your-notion-domain.com
```

## ❓ 常见问题

### Q: Redis 认证错误怎么解决？
A: 如果遇到 `ERR Client sent AUTH, but no password is set` 错误，请：
1. 移除 `.env` 文件中的 `REDIS_PASSWORD` 配置，或
2. 为 Redis 设置密码：`redis-cli CONFIG SET requirepass yourpassword`

### Q: 如何查看同步状态？
A: 可以通过以下方式：
1. 查看日志文件：`tail -f logs/sync.log`
2. 使用管理接口：`curl http://localhost:7654/stats`
3. 检查 Redis 队列：`redis-cli LLEN notion_sync_queue`

### Q: 如何重新触发同步？
A: 可以：
1. 在 Notion 中重新点击同步按钮
2. 重新勾选同步复选框
3. 使用管理接口手动触发

### Q: PRD文档库链接提取失败怎么办？
A: 检查以下几点：
1. 确认页面包含PRD文档库字段
2. 检查字段名是否为支持的格式：'PRD 文档库', 'PRD文档库', 'PRD Documents', 'prd_docs'
3. 确认字段内容不为空
4. 查看详细日志了解具体错误原因

### Q: Remote Link出现重复怎么解决？
A: 系统已经实现了基于globalId的防重复机制：
1. 相同URL的链接只会创建一次
2. 后续同步会更新现有链接而不是创建新链接
3. 如果仍然出现重复，请检查URL格式是否一致

## 📈 性能指标

### 版本提取性能对比
- **Formula方式**: 0.0001秒
- **Relation+API方式**: 0.6844秒
- **性能提升**: 6800倍

### 系统稳定性指标
- **版本匹配成功率**: 99%+
- **PRD链接提取成功率**: 95%+
- **Remote Link创建成功率**: 98%+
- **同步成功率**: 95%+

## 🚧 技术架构

- **公网代理**: Node.js + Express + Redis
- **内网服务**: Python + asyncio + Redis
- **数据库**: Redis (消息队列 + 缓存)
- **部署**: Docker + Nginx + PM2
- **监控**: 结构化日志 + 健康检查接口

## 📚 相关文档

- **[PRD.md](./PRD.md)** - 产品需求文档，包含项目背景、功能需求、字段映射规范
- **[Architecture.md](./Architecture.md)** - 架构设计文档，包含系统架构、模块设计、安全架构
- **[tasks.md](./tasks.md)** - 任务分解文档，包含详细任务分解、进度跟踪
- **[CHANGELOG.md](./CHANGELOG.md)** - 变更日志，记录版本更新和功能改进

## 🔄 版本历史

- **v1.0.0** - 基础 Webhook 服务和字段解析
- **v1.1.0** - 增强字段存储策略和 CORS 配置
- **v1.2.0** - 移除 Formula 依赖，优化同步触发机制
- **v1.3.0** - 完善错误处理和监控功能
- **v1.4.0** - Formula字段版本提取优化，性能提升6800倍
- **v1.5.0** - 四个核心问题修复，Remote Link更新机制
- **v1.6.0** - 代码结构优化，文档整合完善

## 👥 联系方式

- **项目负责人**: 产品团队
- **技术负责人**: 开发团队
- **问题反馈**: 通过 JIRA 或团队群组

## 📄 许可证

内部项目，仅供 EBG 商用产品团队使用。 