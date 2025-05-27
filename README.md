# Notion2JIRA 同步系统

## 项目简介

Notion2JIRA 是一个自动化同步系统，实现 Notion Database 与 JIRA 项目之间的数据同步。该系统专为 EBG 商用产品团队设计，解决需求管理和开发管理系统之间的数据孤岛问题。

## 核心功能

- **双向同步**: Notion ↔ JIRA 自动双向同步
- **智能字段映射**: 支持多种字段类型的智能映射和数据转换
- **状态回写**: 同步完成后自动更新Notion状态和JIRA链接
- **增量检测**: 基于时间戳的增量同步机制
- **重复检测**: 防止重复创建 JIRA Issue
- **错误处理**: 完善的错误处理和重试机制
- **灵活触发**: 支持按钮点击和复选框控制的同步触发

## 项目状态

- ✅ **第0阶段**: 项目调研与准备（已完成 100%）
- ✅ **第1阶段**: 基础设施搭建（已完成 100%）
- ✅ **第2阶段**: 核心同步功能开发（已完成 80%）
- 🔄 **第3阶段**: 反向同步功能开发（进行中 30%）
- 📋 **第4阶段**: 测试与部署（待开始）

### 最新进展
- ✅ 公网 Webhook 服务（端口 7654）
- ✅ Redis 消息队列集成
- ✅ 增强的字段解析和存储策略
- ✅ CORS 配置优化（开发/生产环境适配）
- ✅ 移除 Formula 字段依赖
- ✅ 支持多种同步触发方式
- ✅ 完善的错误处理和日志记录
- 🔄 同步服务开发中
- 🔄 JIRA Issue 创建逻辑开发中

## 核心文档

### 📋 [PRD.md](./PRD.md) - 产品需求文档
- 项目背景与目标
- 功能需求清单
- 字段映射规范
- 验收标准

### 🏗️ [Architecture.md](./Architecture.md) - 架构设计文档
- 系统架构设计
- 核心模块设计
- 部署架构
- 安全架构
- 性能优化

### 📝 [tasks.md](./tasks.md) - 任务分解文档
- 详细任务分解
- 分阶段实施计划
- 进度跟踪
- 风险管理

### 📄 [CHANGELOG.md](./CHANGELOG.md) - 变更日志
- 版本更新记录
- 功能改进历史
- 问题修复记录

## 快速开始

### 环境要求

- **Node.js**: >= 16.0.0
- **Redis**: >= 6.0
- **Python**: >= 3.8 (同步服务)
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

#### 系统要求
- CentOS 7+ / Ubuntu 18.04+
- 4GB+ RAM
- 20GB+ 磁盘空间
- 公网 IP 和域名

#### 部署步骤

1. **创建用户和目录**
```bash
sudo useradd -m -s /bin/bash notion2jira
sudo mkdir -p /opt/notion2jira
sudo chown notion2jira:notion2jira /opt/notion2jira
```

2. **安装依赖**
```bash
# Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Redis
sudo yum install -y redis
sudo systemctl enable redis
sudo systemctl start redis

# Python 3.8+
sudo yum install -y python3 python3-pip

# PM2 (进程管理)
sudo npm install -g pm2
```

3. **部署代码**
```bash
sudo -u notion2jira git clone <repository-url> /opt/notion2jira
cd /opt/notion2jira

# 安装 Webhook 服务依赖
cd webhook-server
sudo -u notion2jira npm install --production

# 安装同步服务依赖
cd ../sync-service
sudo -u notion2jira pip3 install -r requirements.txt
```

4. **配置环境**
```bash
sudo -u notion2jira cp .env_example .env
sudo -u notion2jira vim .env
```

5. **配置 Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:7654;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

6. **启动服务**
```bash
# 使用 PM2 启动 Webhook 服务
cd /opt/notion2jira/webhook-server
sudo -u notion2jira pm2 start ecosystem.config.js

# 启动同步服务
cd ../sync-service
sudo -u notion2jira python3 main.py &
```

#### Docker Compose 部署

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

## 核心特性

### 字段存储策略

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

系统支持多种同步触发方式，不再依赖 Formula 字段：

1. **Button Property 点击**（推荐）
   - 用户点击 Notion 页面中的按钮属性
   - 系统自动检测按钮点击事件

2. **Checkbox 控制**
   - 支持字段名：`sync2jira`、`同步到JIRA`、`Sync to JIRA`
   - 勾选复选框即触发同步

3. **默认策略**
   - 收到 webhook 即认为需要同步
   - 适用于简单场景

### CORS 配置

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

### 监控和调试

#### 查看 Webhook 数据
```bash
# 查看实时日志
tail -f webhook-server/logs/webhook.log

# 查看错误日志
tail -f webhook-server/logs/error.log
```

#### 查看 Redis 数据
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

#### 管理接口
```bash
# 健康检查
curl http://localhost:7654/health

# 获取统计信息
curl http://localhost:7654/stats

# 查看队列状态
curl http://localhost:7654/queue/status
```

## 技术栈

- **公网代理**: Node.js + Express + Redis
- **内网服务**: Python + FastAPI + Redis
- **部署**: Docker + Nginx + PM2
- **监控**: 自定义监控面板 + 结构化日志

## 项目结构

```
Notion2JIRA/
├── PRD.md                          # 产品需求文档
├── Architecture.md                 # 架构设计文档
├── tasks.md                        # 任务分解文档
├── CHANGELOG.md                    # 变更日志
├── webhook-server/                 # 公网代理服务
│   ├── config/                     # 配置文件
│   ├── middleware/                 # 中间件
│   ├── routes/                     # 路由处理
│   ├── scripts/                    # 工具脚本
│   ├── test/                       # 测试文件
│   ├── server.js                   # 主服务文件
│   ├── ecosystem.config.js         # PM2 配置
│   └── package.json                # 依赖配置
├── sync-service/                   # 内网同步服务
│   ├── config/                     # 配置管理
│   ├── services/                   # 业务逻辑
│   ├── data/                       # 数据存储
│   └── logs/                       # 日志文件
├── field_mapping_analyzer.py       # 字段映射分析工具
├── test_rest_api.py               # JIRA API测试脚本
└── requirements.txt               # Python依赖
```

## 常见问题

### Q: Redis 认证错误怎么解决？
A: 如果遇到 `ERR Client sent AUTH, but no password is set` 错误，请：
1. 移除 `.env` 文件中的 `REDIS_PASSWORD` 配置，或
2. 为 Redis 设置密码：`redis-cli CONFIG SET requirepass yourpassword`

### Q: 如何查看同步状态？
A: 可以通过以下方式：
1. 查看日志文件：`tail -f webhook-server/logs/webhook.log`
2. 使用管理接口：`curl http://localhost:7654/stats`
3. 检查 Redis 队列：`redis-cli LLEN notion_sync_queue`

### Q: 如何重新触发同步？
A: 可以：
1. 在 Notion 中重新点击同步按钮
2. 重新勾选同步复选框
3. 使用管理接口手动触发

## 版本历史

- **v1.0.0** - 基础 Webhook 服务和字段解析
- **v1.1.0** - 增强字段存储策略和 CORS 配置
- **v1.2.0** - 移除 Formula 依赖，优化同步触发机制
- **v1.3.0** - 完善错误处理和监控功能

## 联系方式

- **项目负责人**: 产品团队
- **技术负责人**: 开发团队
- **问题反馈**: 通过 JIRA 或团队群组

## 许可证

内部项目，仅供 EBG 商用产品团队使用。 