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

#### 一键部署脚本
```bash
# 在服务器上运行（需要 root 权限）
sudo ./deploy.sh
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
| `ALLOWED_ORIGINS` | 否 | notion.com | 允许的 CORS 来源 |
| `RATE_LIMIT_MAX_REQUESTS` | 否 | 100 | 限流最大请求数 |
| `LOG_LEVEL` | 否 | info | 日志级别 |

## 📡 API 接口

### Webhook 接口

#### POST /webhook/notion
接收 Notion 的 Webhook 事件

**请求头：**
- `Content-Type`: application/json

**请求体：**
```json
{
  "event_type": "page.updated",
  "page_id": "page-uuid",
  "database_id": "database-uuid",
  "properties": {
    "title": "页面标题",
    "sync2jira": true,
    "priority": "High"
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
  "timestamp": "2024-01-15T10:30:00.000Z"
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
  "pageId": "test-page-123",
  "eventType": "page.updated",
  "properties": {
    "title": "Test Page",
    "sync2jira": true
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
- **80 (HTTP)**：自动重定向到 HTTPS
- **443 (HTTPS)**：主要服务端口，SSL 加密
- **7654 (Node.js)**：仅本地访问，通过 Nginx 反向代理
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
curl https://notion2jira.chenge.ink/health

# 测试 Webhook
curl -X POST https://notion2jira.chenge.ink/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{"event_type":"page.updated","page_id":"test"}'

# 测试管理接口
curl -H "X-API-Key: your-admin-key" \
  https://notion2jira.chenge.ink/admin/status
```

### 使用测试脚本
```bash
# 设置环境变量
export WEBHOOK_URL=https://notion2jira.chenge.ink
export ADMIN_API_KEY=your-admin-key

# 运行测试
node scripts/test-webhook.js
```

## 🚀 部署指南

### 快速部署

1. **上传代码到服务器**
```bash
scp -r webhook-server/ user@your-server:/tmp/
```

2. **运行部署脚本**
```bash
ssh user@your-server
cd /tmp/webhook-server
sudo ./deploy.sh
```

3. **配置 SSL 证书**
```bash
# 使用 Let's Encrypt（推荐）
sudo certbot --nginx -d notion2jira.chenge.ink

# 或参考 SSL_SETUP.md 文档
```

4. **配置环境变量**
```bash
sudo nano /opt/notion2jira/webhook-server/.env
```

5. **重启服务**
```bash
sudo -u webhook pm2 restart notion-webhook
```

### Docker 部署
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 7654
CMD ["npm", "start"]
```

### Nginx 配置

已包含完整的 Nginx 配置文件 `nginx.conf`，支持：
- HTTPS 重定向
- SSL 安全配置
- 反向代理
- 安全头部
- 静态文件缓存

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
- 移除签名验证（Notion 不支持）

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## �� 许可证

MIT License 