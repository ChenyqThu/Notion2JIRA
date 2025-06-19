# Notion Webhook Server

这是 Notion-JIRA 同步系统的外网 Webhook 接收服务器，负责接收 Notion 的页面变更事件并转发到内网同步服务。

## 🚀 功能特性

- ✅ **安全的 Webhook 接收**：基础请求验证和内容类型检查
- ✅ **消息队列**：使用 Redis 队列确保消息可靠传输
- ✅ **限流保护**：防止恶意请求和 DDoS 攻击
- ✅ **完整日志**：详细的请求和错误日志记录
- ✅ **健康检查**：提供服务状态监控端点
- ✅ **管理接口**：队列管理和系统监控
- ✅ **优雅关闭**：支持平滑重启和关闭

## 📋 系统要求

- Node.js 16.0+
- Redis 6.0+
- 公网 IP 地址
- SSL 证书（生产环境推荐）

## 🛠️ 安装部署

### 1. 克隆代码
```bash
git clone <repository>
cd webhook-server
```

### 2. 安装依赖
```bash
npm install
```

### 3. 配置环境变量
```bash
cp env.example .env
# 编辑 .env 文件，设置必要的配置
```

### 4. 启动服务

#### 开发环境
```bash
npm run dev
```

#### 生产环境
```bash
npm start
```

#### 使用 PM2 部署
```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```



## ⚙️ 环境变量配置

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `PORT` | 否 | 7654 | 服务器端口 |
| `NODE_ENV` | 否 | development | 运行环境 |
| `DOMAIN` | 否 | - | 服务器域名 |
| `NOTION_API_KEY` | 是 | - | Notion API 密钥 |
| `REDIS_HOST` | 否 | localhost | Redis 服务器地址 |
| `REDIS_PORT` | 否 | 6379 | Redis 端口 |
| `REDIS_PASSWORD` | 否 | - | Redis 密码 |
| `ADMIN_API_KEY` | 是 | - | 管理接口 API 密钥 |
| `CORS_ENABLED` | 否 | true | 是否启用 CORS |
| `ALLOWED_ORIGINS` | 否 | notion.com | 允许的 CORS 来源 |
| `RATE_LIMIT_MAX_REQUESTS` | 否 | 100 | 限流最大请求数 |
| `LOG_LEVEL` | 否 | info | 日志级别 |

## 📊 Notion 数据字段映射

### 主要属性字段

根据实际收到的 Notion Webhook 数据，系统支持以下字段：

| Notion 字段名 | 字段类型 | 说明 | 示例值 |
|---------------|----------|------|--------|
| `Function Name` | title | 功能名称（主标题） | "roaming等功能联动wifi navi" |
| `Status` | status | 状态 | "待评估 UR" |
| `优先级 P` | select | 优先级 | "低 Low" |
| `类型 Type` | multi_select | 类型标签 | ["APP"] |
| `JIRA Card` | url | JIRA 卡片链接 | null 或 URL |
| `需求来源 Source` | select | 需求来源 | "[反馈] - 客户拜访" |
| `功能类别 Feature Type` | select | 功能类别 | "UI体验优化 UI Optimization" |
| `规划版本 Release Version` | multi_select | 规划版本 | ["Omada APP 4.22"] |
| `涉及产品线` | multi_select | 产品线 | ["Controller", "APP"] |
| `Owner` | people | 负责人员 | 用户对象数组 |
| `Description` | rich_text | 功能描述 | 富文本内容 |
| `AI Desc` | rich_text | AI 生成描述 | 富文本内容 |

### 同步触发条件

页面会在以下情况下触发同步到 JIRA：

1. **用户点击 Button Property**：这是主要的同步触发方式
   - Notion database 中配置了 button property
   - 用户点击该按钮时会自动发送 webhook
2. **页面未被归档或删除**：`archived: false` 且 `in_trash: false`
3. **可选的控制字段**：可以通过 checkbox 字段来控制是否允许同步
   - 支持字段名：`sync2jira`、`同步到JIRA`、`Sync to JIRA`
   - 当该字段值为 `false` 时，将跳过同步

### 字段存储策略

为了最大化兼容性和未来扩展性，系统采用以下字段存储策略：

#### 1. 双重存储结构
```json
{
  "properties": {
    "字段名": {
      "type": "字段类型",
      "value": "解析后的值",
      "raw": "原始数据"
    }
  },
  "raw_properties": {
    "字段名": "完整的原始 Notion 属性数据"
  }
}
```

#### 2. 支持的字段类型
- **基础类型**：title, rich_text, select, multi_select, status, checkbox, url
- **数值类型**：number, date, email, phone_number
- **关系类型**：people, files, relation, rollup
- **系统类型**：created_time, last_edited_time, created_by, last_edited_by
- **特殊类型**：button, unique_id, verification
- **未知类型**：自动保存原始数据，便于未来支持

#### 3. 容错机制
- 解析失败时保存原始数据和错误信息
- 发现新字段类型时自动记录日志
- 向后兼容，不会因新字段类型导致处理失败

### 数据解析逻辑

系统会自动解析 Notion 的复杂数据结构：

- **title/rich_text**: 提取 `plain_text` 内容
- **select**: 提取选项的 `name` 值
- **multi_select**: 提取所有选项的 `name` 数组
- **status**: 提取状态的 `name` 值
- **people**: 提取用户信息（ID、姓名、邮箱）
- **url**: 直接使用 URL 值
- **number/date/email/phone**: 提取对应类型的值
- **files**: 提取文件信息（名称、URL、类型）
- **relation**: 提取关联页面的 ID 数组
- **rollup**: 提取汇总计算结果

## 📡 API 接口

### Webhook 接口

#### POST /webhook/notion
接收 Notion 的 Webhook 事件

**请求头：**
- `Content-Type`: application/json

**请求体：**
```json
{
  "source": {
    "type": "automation",
    "automation_id": "1ff74ddb-b9d2-8054-a6d9-004d3461e70b",
    "action_id": "1ff74ddb-b9d2-800c-a4cc-005a2cd58f76",
    "event_id": "05c5ce90-09e3-4ddd-b321-9bd6e45a6e53",
    "user_id": "e2840e64-4f99-4edf-817c-bd6f13112556",
    "attempt": 1
  },
  "data": {
    "object": "page",
    "id": "d1cdcd9d-c6b0-44ca-9439-318d5a92fac7",
    "created_time": "2024-09-11T03:13:00.000Z",
    "last_edited_time": "2025-05-26T06:18:00.000Z",
    "parent": {
      "type": "database_id",
      "database_id": "3f8426c6-7f44-4bf8-baf5-9eacd7008eef"
    },
    "archived": false,
    "in_trash": false,
    "properties": {
      "Function Name": {
        "id": "title",
        "type": "title",
        "title": [
          {
            "type": "text",
            "text": {
              "content": "roaming等功能联动wifi navi"
            },
            "plain_text": "roaming等功能联动wifi navi"
          }
        ]
      },
      "Status": {
        "id": "AM%3AA",
        "type": "status",
        "status": {
          "id": "6227d97b-73b8-4619-b78f-096552c097a8",
          "name": "待评估 UR",
          "color": "default"
        }
      },
      "优先级 P": {
        "id": "Gt%3AZ",
        "type": "select",
        "select": {
          "id": "TPR:",
          "name": "低 Low",
          "color": "gray"
        }
      },
      "JIRA Card": {
        "id": "iSzx",
        "type": "url",
        "url": null
      }
    }
  }
}
```

**响应：**
```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "result": {
    "processed": true,
    "action": "page_updated"
  },
  "timestamp": "2025-05-26T14:27:55.994Z"
}
```

#### GET /webhook/test
测试 Webhook 服务是否正常

### 管理接口

所有管理接口都需要在请求头中包含 `X-API-Key`。

#### GET /admin/status
获取系统状态信息

**响应：**
```json
{
  "success": true,
  "data": {
    "service": "webhook-server",
    "version": "1.0.0",
    "uptime": 3600,
    "memory": {...},
    "redis": {
      "connected": true,
      "ready": true
    },
    "queue": {
      "sync_queue_length": 5
    }
  }
}
```

#### GET /admin/queue/stats
获取队列统计信息

#### POST /admin/queue/clear
清空指定队列

**请求体：**
```json
{
  "queueName": "sync_queue"
}
```

#### POST /admin/test/webhook
创建测试 Webhook 事件

**请求体：**
```json
{
  "pageId": "d1cdcd9d-c6b0-44ca-9439-318d5a92fac7",
  "eventType": "page.updated",
  "properties": {
    "Function Name": "测试页面",
    "Status": "待评估 UR",
    "优先级 P": "低 Low"
  }
}
```

### 系统接口

#### GET /health
健康检查端点

#### GET /
服务基本信息

## 🔒 安全特性

### 1. 基础请求验证
- 内容类型验证，确保为 JSON 格式
- 请求数据格式验证
- 详细的请求日志记录

### 2. 限流保护
- IP 级别限流：15分钟内最多 100 请求
- 可配置的限流参数

### 3. CORS 保护
- 严格的跨域资源共享策略
- 只允许 Notion 官方域名

### 4. 安全头部
- 使用 Helmet 中间件设置安全头部
- HSTS、CSP 等安全策略

### 5. 端口安全配置
- **22 (SSH)**：管理访问，建议配置密钥认证
- **80 (HTTP)**：自动重定向到 HTTPS（如果配置了 Nginx）
- **443 (HTTPS)**：主要服务端口，SSL 加密（如果配置了 Nginx）
- **7654 (Node.js)**：应用默认端口，建议通过 Nginx 反向代理，不直接暴露
- **6379 (Redis)**：仅内网访问，密码保护 + IP 限制

#### Redis 安全配置
```bash
# 仅允许内网 IP 段访问 Redis
ufw allow from 10.0.0.0/8 to any port 6379
ufw allow from 172.16.0.0/12 to any port 6379  
ufw allow from 192.168.0.0/16 to any port 6379

# 或限制特定 IP（推荐）
ufw allow from <内网服务器IP> to any port 6379
```

## 📊 监控和日志

### 日志文件
- `logs/combined.log`: 所有日志
- `logs/error.log`: 错误日志

### 日志格式
```json
{
  "timestamp": "2024-01-15 10:30:00",
  "level": "info",
  "message": "接收到Notion Webhook事件",
  "service": "notion-webhook",
  "eventType": "page.updated",
  "pageId": "page-uuid",
  "ip": "1.2.3.4"
}
```

### 监控指标
- 请求数量和响应时间
- 错误率统计
- 队列长度监控
- Redis 连接状态

## 🧪 测试

### 运行测试
```bash
npm test
```

### 测试覆盖率
```bash
npm run test:coverage
```

### 手动测试
```bash
# 测试健康检查
curl http://localhost:7654/health
# 或通过域名（如果配置了 Nginx）
curl https://your-domain.com/health

# 测试 Webhook
curl -X POST http://localhost:7654/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{
    "source": {
      "type": "automation",
      "automation_id": "test-automation",
      "user_id": "test-user"
    },
    "data": {
      "object": "page",
      "id": "test-page-123",
      "parent": {
        "type": "database_id",
        "database_id": "test-database"
      },
      "properties": {
        "Formula": {
          "type": "formula",
          "formula": {
            "type": "string",
            "string": "sync2jira"
          }
        }
      }
    }
  }'

# 测试管理接口
curl -H "X-API-Key: your-admin-key" \
  http://localhost:7654/admin/status
```

### 使用测试脚本
```bash
# 设置环境变量
export WEBHOOK_URL=http://localhost:7654
export ADMIN_API_KEY=your-admin-key

# 运行测试
node scripts/test-webhook.js
```

## 🚀 部署指南

### 手动部署步骤

#### 1. 系统要求
- Ubuntu 18.04+ / CentOS 7+ / Debian 9+
- Node.js 16.0+
- Redis 6.0+
- Nginx（可选，用于反向代理）
- 公网 IP 地址

#### 2. 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y curl wget gnupg2 software-properties-common nginx redis-server

# 安装 Node.js 16.x
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo bash -
sudo apt install -y nodejs

# 安装 PM2
sudo npm install -g pm2
```

#### 3. 创建应用用户和目录
```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -d /home/webhook -m webhook

# 创建应用目录
sudo mkdir -p /opt/notion2jira/webhook-server
sudo chown webhook:webhook /opt/notion2jira/webhook-server
```

#### 4. 部署应用代码
```bash
# 上传代码到服务器
scp -r webhook-server/ user@your-server:/tmp/

# 复制到应用目录
sudo cp -r /tmp/webhook-server/* /opt/notion2jira/webhook-server/
sudo chown -R webhook:webhook /opt/notion2jira/webhook-server

# 安装依赖
cd /opt/notion2jira/webhook-server
sudo -u webhook npm install --production
```

#### 5. 配置环境变量
```bash
# 复制环境变量模板
sudo -u webhook cp env.example .env

# 编辑配置文件
sudo -u webhook nano .env

# 必须配置的变量：
# - NOTION_API_KEY: Notion API 密钥
# - ADMIN_API_KEY: 管理接口密钥（建议使用随机生成）
# - REDIS_PASSWORD: Redis 密码（如果设置了）
```

#### 6. 配置 Redis
```bash
# 启动 Redis 服务
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 配置 Redis 安全（可选）
sudo nano /etc/redis/redis.conf
# 添加以下配置：
# requirepass your_redis_password
# bind 127.0.0.1

# 重启 Redis
sudo systemctl restart redis-server
```

#### 7. 启动应用
```bash
# 切换到应用目录
cd /opt/notion2jira/webhook-server

# 使用 PM2 启动
sudo -u webhook pm2 start ecosystem.config.js --env production
sudo -u webhook pm2 save

# 设置开机自启
sudo pm2 startup systemd -u webhook --hp /home/webhook
```

#### 8. 配置 Nginx 反向代理（推荐）
```bash
# 创建 Nginx 配置文件
sudo nano /etc/nginx/sites-available/notion2jira

# 添加以下配置：
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:7654;
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

# 启用站点
sudo ln -s /etc/nginx/sites-available/notion2jira /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. 配置 SSL 证书（推荐）
```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 或手动配置 SSL 证书
# 将证书文件放置在 /etc/ssl/certs/ 和 /etc/ssl/private/
```

#### 10. 配置防火墙
```bash
# 使用 UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Redis 端口仅允许内网访问（如果需要）
sudo ufw allow from 10.0.0.0/8 to any port 6379
sudo ufw allow from 172.16.0.0/12 to any port 6379
sudo ufw allow from 192.168.0.0/16 to any port 6379

sudo ufw --force enable
```

#### 11. 验证部署
```bash
# 检查服务状态
sudo systemctl status nginx
sudo systemctl status redis-server
sudo -u webhook pm2 status

# 检查端口监听
sudo netstat -tlnp | grep :7654
sudo netstat -tlnp | grep :6379

# 测试应用
curl http://localhost:7654/health

# 查看日志
sudo -u webhook pm2 logs notion-webhook
```

### 本地开发部署

对于本地开发环境，可以简化部署流程：

```bash
# 1. 安装依赖
npm install

# 2. 配置环境变量
cp env.example .env
# 编辑 .env 文件，设置：
# NODE_ENV=development
# CORS_ENABLED=true  # 开发环境会自动允许所有来源

# 3. 启动 Redis（如果需要）
redis-server

# 4. 启动应用
npm run dev
# 或
npm start
```

### Docker 部署

#### 使用 Docker Compose（推荐）

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  webhook-server:
    build: .
    ports:
      - "7654:7654"
    environment:
      - NODE_ENV=production
      - PORT=7654
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass your_redis_password
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/ssl
    depends_on:
      - webhook-server
    restart: unless-stopped

volumes:
  redis_data:
```

创建 `Dockerfile`：

```dockerfile
FROM node:16-alpine

# 设置工作目录
WORKDIR /app

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production && npm cache clean --force

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S webhook -u 1001

# 设置权限
RUN chown -R webhook:nodejs /app
USER webhook

# 暴露端口
EXPOSE 7654

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7654/health || exit 1

# 启动应用
CMD ["npm", "start"]
```

部署命令：

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f webhook-server

# 停止服务
docker-compose down
```

## 🔧 故障排除

### 常见问题

1. **Redis 连接失败**
   - 检查 Redis 服务是否运行：`systemctl status redis-server`
   - 验证连接参数和密码

2. **Webhook 请求失败**
   - 检查内容类型是否为 `application/json`
   - 验证请求数据格式是否正确

3. **限流触发**
   - 调整 `RATE_LIMIT_MAX_REQUESTS` 参数
   - 检查是否有异常请求

4. **SSL 证书问题**
   - 参考 `SSL_SETUP.md` 文档
   - 检查证书路径和权限

### 调试模式
```bash
DEBUG=* npm run dev
```

### 查看日志
```bash
# 应用日志
sudo -u webhook pm2 logs notion-webhook

# Nginx 日志
sudo tail -f /var/log/nginx/notion2jira.access.log
sudo tail -f /var/log/nginx/notion2jira.error.log

# 系统日志
sudo journalctl -u nginx -f
```

## 📝 更新日志

### v1.0.0
- 初始版本发布
- 基础 Webhook 接收功能
- Redis 队列集成
- 管理接口实现
- 安全特性完善

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## �� 许可证

MIT License 