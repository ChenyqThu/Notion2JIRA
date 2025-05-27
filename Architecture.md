# Notion2JIRA 系统架构设计

## 1. 系统架构概览

### 1.1 整体架构图

```
┌─────────────┐    webhook    ┌─────────────────┐    Redis     ┌──────────────────┐
│   Notion    │──────────────→│  公网代理服务器   │─────────────→│   内网同步服务     │
│  (公网)     │               │   (Webhook接收)  │   消息队列     │  (业务处理)       │
└─────────────┘               └─────────────────┘              └──────────────────┘
                                       │                                  │
                                       │                                  │ API调用
                                       ▼                                  ▼
┌─────────────────────────────────────────────────────────────┐ ┌─────────────┐
│                监控管理面板                                   │ │   RDJIRA    │
│          (部署在内网服务器)                                    │ │  (内网)     │
└─────────────────────────────────────────────────────────────┘ └─────────────┘
```

### 1.2 架构特点

- **分层架构**：公网接入层 + 内网处理层 + 数据存储层
- **异步处理**：基于消息队列的异步同步机制
- **高可用性**：多重错误处理和重试机制
- **安全隔离**：公网和内网服务分离，最小化安全风险
- **可扩展性**：模块化设计，支持功能扩展

## 2. 核心模块设计

### 2.1 公网代理服务模块

#### 2.1.1 模块职责
- 接收 Notion webhook 请求
- 基础请求验证和安全检查
- 消息队列管理
- 健康检查和监控接口

#### 2.1.2 技术栈
```javascript
// 核心依赖
{
  "express": "^4.18.0",        // Web框架
  "redis": "^4.0.0",           // Redis客户端
  "helmet": "^6.0.0",          // 安全中间件
  "express-rate-limit": "^6.0.0", // 限流中间件
  "winston": "^3.8.0",         // 日志管理
  "dotenv": "^16.0.0"          // 环境变量管理
}
```

#### 2.1.3 核心类设计
```javascript
class WebhookServer {
  constructor() {
    this.app = express();
    this.redis = new RedisClient();
    this.logger = new Logger();
    this.rateLimiter = new RateLimiter();
  }
  
  // 初始化中间件
  setupMiddleware() {
    this.app.use(helmet());
    this.app.use(this.rateLimiter.middleware);
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(this.requestLogger);
  }
  
  // 核心webhook处理
  async handleWebhook(req, res) {
    try {
      const event = this.parseNotionEvent(req.body);
      await this.redis.pushToQueue('sync_queue', event);
      res.json({ success: true, message: 'Event queued' });
    } catch (error) {
      this.logger.error('Webhook处理失败', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
}
```

#### 2.1.4 API 接口设计
```javascript
// 主要接口
POST /webhook/notion          // Notion webhook接收
GET  /health                  // 健康检查
GET  /admin/status           // 管理状态接口
GET  /admin/queue/stats      // 队列统计
POST /admin/queue/clear      // 清空队列（管理员）
```

### 2.2 内网同步服务模块

#### 2.2.1 模块架构
```
内网同步服务
├── 消息消费器 (MessageConsumer)
├── 字段映射引擎 (FieldMapper)
├── JIRA API 客户端 (JiraClient)
├── Notion API 客户端 (NotionClient)
├── 同步状态管理 (SyncStateManager)
├── 错误处理器 (ErrorHandler)
└── 监控服务 (MonitorService)
```

#### 2.2.2 核心类设计

##### SyncService 主服务类
```python
class SyncService:
    def __init__(self):
        self.redis_client = RedisClient()
        self.jira_client = JiraClient()
        self.notion_client = NotionClient()
        self.field_mapper = FieldMapper()
        self.state_manager = SyncStateManager()
        self.error_handler = ErrorHandler()
    
    async def start_consumer(self):
        """启动消息消费器"""
        while True:
            try:
                message = await self.redis_client.pop_from_queue('sync_queue')
                if message:
                    await self.process_sync_event(message)
            except Exception as e:
                self.logger.error(f"消费消息失败: {e}")
                await asyncio.sleep(5)
    
    async def process_sync_event(self, event):
        """处理同步事件"""
        try:
            if event['type'] == 'notion_update':
                await self.handle_notion_update(event['data'])
            elif event['type'] == 'jira_update':
                await self.handle_jira_update(event['data'])
        except Exception as e:
            await self.error_handler.handle_sync_error(event, e)
```

##### FieldMapper 字段映射引擎
```python
class FieldMapper:
    def __init__(self):
        self.mapping_config = self.load_mapping_config()
        self.jira_metadata = None
    
    async def map_notion_to_jira(self, notion_data):
        """Notion字段映射到JIRA字段"""
        jira_fields = {
            'project': {'id': '13904'},  # SMBNET项目
            'issuetype': {'id': '10001'},  # Story类型
            'fixVersions': [{'id': '14577'}]  # 默认版本
        }
        
        # 标题映射
        if 'title' in notion_data:
            jira_fields['summary'] = notion_data['title']
        
        # 描述组合映射
        description_parts = []
        if notion_data.get('description'):
            description_parts.append(f"## 需求说明\n{notion_data['description']}")
        if notion_data.get('ai_summary'):
            description_parts.append(f"## 需求整理(AI)\n{notion_data['ai_summary']}")
        if notion_data.get('notion_url'):
            description_parts.append(f"## 原始需求链接\n{notion_data['notion_url']}")
        
        if description_parts:
            jira_fields['description'] = '\n\n'.join(description_parts)
        
        # 优先级映射
        if notion_data.get('priority'):
            priority_mapping = {
                '高 High': {'id': '1'},
                '中 Medium': {'id': '3'},
                '低 Low': {'id': '4'},
                '无 None': {'id': '5'}
            }
            if notion_data['priority'] in priority_mapping:
                jira_fields['priority'] = priority_mapping[notion_data['priority']]
        
        # 分配人员映射
        if notion_data.get('assignee_email'):
            assignee = await self.find_jira_user_by_email(notion_data['assignee_email'])
            if assignee:
                jira_fields['assignee'] = {'accountId': assignee['accountId']}
        
        return jira_fields
    
    async def find_jira_user_by_email(self, email):
        """根据邮箱查找JIRA用户"""
        users = await self.jira_client.search_users(email)
        return users[0] if users else None
```

##### JiraClient JIRA API客户端
```python
class JiraClient:
    def __init__(self):
        self.base_url = os.getenv('JIRA_BASE_URL')
        self.auth = (
            os.getenv('JIRA_USER_EMAIL'),
            os.getenv('JIRA_USER_PASSWORD')
        )
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = False  # 内网环境
    
    async def create_issue(self, fields):
        """创建JIRA Issue"""
        payload = {'fields': fields}
        response = await self.session.post(
            f'{self.base_url}/rest/api/2/issue',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def update_issue(self, issue_key, fields):
        """更新JIRA Issue"""
        payload = {'fields': fields}
        response = await self.session.put(
            f'{self.base_url}/rest/api/2/issue/{issue_key}',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def add_comment(self, issue_key, comment):
        """添加评论"""
        payload = {'body': comment}
        response = await self.session.post(
            f'{self.base_url}/rest/api/2/issue/{issue_key}/comment',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_project_metadata(self, project_key):
        """获取项目元数据"""
        # 获取项目信息
        project_response = await self.session.get(
            f'{self.base_url}/rest/api/2/project/{project_key}'
        )
        
        # 获取创建元数据
        meta_response = await self.session.get(
            f'{self.base_url}/rest/api/2/issue/createmeta',
            params={'projectKeys': project_key, 'expand': 'projects.issuetypes.fields'}
        )
        
        return {
            'project': project_response.json(),
            'create_meta': meta_response.json()
        }
```

### 2.3 数据存储设计

#### 2.3.1 Redis 数据结构
```python
# 消息队列
sync_queue = [
    {
        "id": "uuid",
        "type": "notion_update|jira_update",
        "data": {...},
        "timestamp": 1234567890,
        "retry_count": 0,
        "priority": "normal|high"
    }
]

# 同步状态缓存
sync_mappings = {
    "notion_page_id": {
        "jira_key": "SMBNET-123",
        "jira_id": "116617",
        "created_at": "2024-01-15T10:30:00Z",
        "last_sync": "2024-01-15T10:30:00Z",
        "status": "synced|error|pending"
    }
}

# 用户映射缓存
user_mappings = {
    "notion_user_id": "jira_account_id",
    "user_email": "jira_account_id"
}

# 项目元数据缓存
jira_metadata = {
    "SMBNET": {
        "project_id": "13904",
        "issue_types": [...],
        "versions": [...],
        "users": [...],
        "statuses": [...],
        "priorities": [...]
    }
}
```

#### 2.3.2 文件配置存储
```yaml
# config/field_mapping.yaml
field_mappings:
  notion_to_jira:
    title: summary
    description: description
    priority:
      type: mapping
      values:
        "高 High": {id: "1"}
        "中 Medium": {id: "3"}
        "低 Low": {id: "4"}
        "无 None": {id: "5"}
    
    status:
      type: mapping
      values:
        "初始反馈 OR": "待可行性评估"
        "待评估 UR": "待可行性评估"
        "待输入 WI": "TODO"
        "DEVING": "开发中"
        "已发布 DONE": "完成"

# config/jira_config.yaml
jira:
  project:
    key: "SMBNET"
    id: "13904"
    default_issue_type: "10001"  # Story
    default_version: "14577"     # 待评估版本
  
  required_fields:
    - summary
    - issuetype
    - project
    - fixVersions
```

### 2.4 错误处理与重试机制

#### 2.4.1 错误分类
```python
class ErrorHandler:
    ERROR_TYPES = {
        'AUTHENTICATION_ERROR': {
            'retry': False,
            'action': 'CHECK_CREDENTIALS'
        },
        'PERMISSION_ERROR': {
            'retry': False,
            'action': 'CHECK_PERMISSIONS'
        },
        'VALIDATION_ERROR': {
            'retry': False,
            'action': 'FIX_DATA'
        },
        'NETWORK_ERROR': {
            'retry': True,
            'max_retries': 3,
            'backoff': 'exponential'
        },
        'SERVER_ERROR': {
            'retry': True,
            'max_retries': 5,
            'backoff': 'exponential'
        }
    }
    
    async def handle_sync_error(self, event, error):
        """处理同步错误"""
        error_type = self.classify_error(error)
        error_config = self.ERROR_TYPES.get(error_type)
        
        if error_config and error_config.get('retry'):
            await self.schedule_retry(event, error_config)
        else:
            await self.log_permanent_failure(event, error)
```

#### 2.4.2 重试策略
```python
class RetryManager:
    async def schedule_retry(self, event, delay_seconds=None):
        """安排重试任务"""
        retry_count = event.get('retry_count', 0) + 1
        max_retries = 3
        
        if retry_count > max_retries:
            await self.mark_as_failed(event)
            return
        
        # 指数退避
        if delay_seconds is None:
            delay_seconds = min(300, 2 ** retry_count * 10)  # 最大5分钟
        
        retry_event = {
            **event,
            'retry_count': retry_count,
            'scheduled_at': time.time() + delay_seconds
        }
        
        await self.redis_client.schedule_delayed_task(
            'retry_queue', 
            retry_event, 
            delay_seconds
        )
```

### 2.5 监控与日志系统

#### 2.5.1 监控指标
```python
class MonitorService:
    def __init__(self):
        self.metrics = {
            'sync_success_count': 0,
            'sync_failure_count': 0,
            'avg_sync_duration': 0,
            'queue_length': 0,
            'error_rate': 0
        }
    
    async def record_sync_success(self, duration):
        """记录同步成功"""
        self.metrics['sync_success_count'] += 1
        self.update_avg_duration(duration)
        await self.update_success_rate()
    
    async def record_sync_failure(self, error_type):
        """记录同步失败"""
        self.metrics['sync_failure_count'] += 1
        await self.update_error_rate()
        await self.send_alert_if_needed(error_type)
```

#### 2.5.2 日志结构
```python
# 结构化日志格式
{
    "timestamp": "2024-01-15T10:30:00.000Z",
    "level": "INFO|WARN|ERROR",
    "service": "sync-service",
    "module": "field_mapper",
    "event_type": "sync_success|sync_failure|api_call",
    "notion_page_id": "abc123",
    "jira_key": "SMBNET-123",
    "duration_ms": 1500,
    "error_code": "VALIDATION_ERROR",
    "message": "字段映射完成",
    "metadata": {
        "user_id": "user123",
        "retry_count": 0,
        "api_endpoint": "/rest/api/2/issue"
    }
}
```

## 3. 部署架构

### 3.1 服务器规划

#### 3.1.1 公网代理服务器
```yaml
# 服务器配置
server:
  cpu: 2核
  memory: 4GB
  disk: 50GB SSD
  os: Ubuntu 20.04 LTS
  network: 公网IP + 域名

# 软件栈
software:
  runtime: Node.js 16+
  web_server: Nginx (反向代理)
  cache: Redis 6+
  process_manager: PM2
  ssl: Let's Encrypt
  monitoring: PM2 Monit
```

#### 3.1.2 内网同步服务器
```yaml
# 服务器配置
server:
  cpu: 4核
  memory: 8GB
  disk: 100GB SSD
  os: Ubuntu 20.04 LTS / CentOS 7+
  network: 内网 + 公网访问

# 软件栈
software:
  runtime: Python 3.9+
  web_framework: FastAPI
  database: SQLite / MySQL
  cache: Redis Client
  process_manager: Supervisor
  monitoring: Prometheus + Grafana
```

### 3.2 网络架构

#### 3.2.1 网络拓扑
```
Internet
    │
    ▼
┌─────────────────┐
│   公网代理服务器   │  (notion2jira.chenge.ink)
│   Nginx + Node.js │
│   Redis Server   │
└─────────────────┘
    │ VPN/内网穿透
    ▼
┌─────────────────────────────────┐
│           公司内网               │
│  ┌─────────────┐ ┌─────────────┐ │
│  │ 同步服务器   │ │   RDJIRA    │ │
│  │ Python服务  │ │   服务器     │ │
│  └─────────────┘ └─────────────┘ │
└─────────────────────────────────┘
```

#### 3.2.2 端口配置
| 服务 | 端口 | 访问范围 | 用途 |
|------|------|----------|------|
| Nginx | 80/443 | 公网 | HTTPS服务 |
| Node.js | 7654 | 本地 | 应用服务 |
| Redis | 6379 | 内网 | 消息队列 |
| SSH | 22 | 管理员 | 远程管理 |
| 监控面板 | 8080 | 内网 | 状态监控 |

### 3.3 容器化部署

#### 3.3.1 Docker 配置
```dockerfile
# webhook-server/Dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 7654
CMD ["npm", "start"]

# sync-service/Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

#### 3.3.2 Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  webhook-server:
    build: ./webhook-server
    ports:
      - "7654:7654"
    environment:
      - NODE_ENV=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
  
  sync-service:
    build: ./sync-service
    environment:
      - REDIS_URL=redis://redis:6379
      - JIRA_BASE_URL=${JIRA_BASE_URL}
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
```

## 4. 安全架构

### 4.1 网络安全

#### 4.1.1 HTTPS 配置
```nginx
# nginx配置
server {
    listen 443 ssl http2;
    server_name notion2jira.chenge.ink;
    
    ssl_certificate /etc/letsencrypt/live/notion2jira.chenge.ink/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/notion2jira.chenge.ink/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
}
```

#### 4.1.2 防火墙配置
```bash
# UFW防火墙规则
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow from 内网IP段 to any port 6379  # Redis访问
ufw enable
```

### 4.2 应用安全

#### 4.2.1 认证授权
```javascript
// API Key认证中间件
const authenticateAdmin = (req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  const validApiKey = process.env.ADMIN_API_KEY;
  
  if (!apiKey || apiKey !== validApiKey) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  next();
};

// 限流配置
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 100, // 最多100个请求
  message: 'Too many requests from this IP'
});
```

#### 4.2.2 数据验证
```python
# 输入验证
class NotionEventValidator:
    def validate_webhook_data(self, data):
        required_fields = ['event_type', 'page_id', 'database_id']
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        # 验证数据类型和格式
        if not isinstance(data['page_id'], str) or len(data['page_id']) < 10:
            raise ValidationError("Invalid page_id format")
        
        return True
```

### 4.3 数据安全

#### 4.3.1 敏感信息管理
```bash
# 环境变量文件权限
chmod 600 .env
chown webhook:webhook .env

# 密钥轮换策略
# 1. JIRA密码定期更换
# 2. Redis密码定期更换
# 3. API Key定期更换
```

#### 4.3.2 日志脱敏
```python
class SecureLogger:
    SENSITIVE_FIELDS = ['password', 'api_key', 'token', 'secret']
    
    def sanitize_log_data(self, data):
        """脱敏敏感信息"""
        if isinstance(data, dict):
            return {
                k: '***' if k.lower() in self.SENSITIVE_FIELDS else v
                for k, v in data.items()
            }
        return data
```

## 5. 性能优化

### 5.1 缓存策略

#### 5.1.1 多层缓存
```python
class CacheManager:
    def __init__(self):
        self.memory_cache = {}  # 内存缓存
        self.redis_cache = RedisClient()  # Redis缓存
    
    async def get_jira_metadata(self, project_key):
        # L1: 内存缓存 (5分钟)
        cache_key = f"jira_meta_{project_key}"
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # L2: Redis缓存 (1小时)
        cached_data = await self.redis_cache.get(cache_key)
        if cached_data:
            self.memory_cache[cache_key] = cached_data
            return cached_data
        
        # L3: 从JIRA API获取
        metadata = await self.jira_client.get_project_metadata(project_key)
        await self.redis_cache.setex(cache_key, 3600, metadata)
        self.memory_cache[cache_key] = metadata
        return metadata
```

### 5.2 异步处理

#### 5.2.1 并发控制
```python
import asyncio
from asyncio import Semaphore

class SyncProcessor:
    def __init__(self, max_concurrent=5):
        self.semaphore = Semaphore(max_concurrent)
    
    async def process_batch(self, events):
        """批量处理同步事件"""
        tasks = []
        for event in events:
            task = self.process_single_event(event)
            tasks.append(task)
        
        # 限制并发数
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def process_single_event(self, event):
        async with self.semaphore:
            return await self.sync_service.process_sync_event(event)
```

### 5.3 数据库优化

#### 5.3.1 索引策略
```sql
-- 同步映射表索引
CREATE INDEX idx_notion_page_id ON sync_mappings(notion_page_id);
CREATE INDEX idx_jira_key ON sync_mappings(jira_key);
CREATE INDEX idx_last_sync ON sync_mappings(last_sync);

-- 同步日志表索引
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
CREATE INDEX idx_sync_logs_created_at ON sync_logs(created_at);
CREATE INDEX idx_sync_logs_mapping_id ON sync_logs(mapping_id);
```

## 6. 可扩展性设计

### 6.1 模块化架构

#### 6.1.1 插件系统
```python
class SyncPlugin:
    """同步插件基类"""
    def __init__(self, name):
        self.name = name
    
    async def before_sync(self, event):
        """同步前钩子"""
        pass
    
    async def after_sync(self, event, result):
        """同步后钩子"""
        pass
    
    async def on_error(self, event, error):
        """错误处理钩子"""
        pass

class EmailNotificationPlugin(SyncPlugin):
    """邮件通知插件"""
    async def after_sync(self, event, result):
        if result.get('success'):
            await self.send_success_notification(event, result)

class SlackNotificationPlugin(SyncPlugin):
    """Slack通知插件"""
    async def on_error(self, event, error):
        await self.send_error_notification(event, error)
```

### 6.2 配置管理

#### 6.2.1 动态配置
```python
class ConfigManager:
    def __init__(self):
        self.config_cache = {}
        self.config_watchers = []
    
    async def get_field_mapping(self, project_key):
        """获取字段映射配置"""
        config_key = f"field_mapping_{project_key}"
        
        # 检查缓存
        if config_key in self.config_cache:
            return self.config_cache[config_key]
        
        # 从配置文件加载
        config = await self.load_config_file(f"mappings/{project_key}.yaml")
        self.config_cache[config_key] = config
        return config
    
    async def reload_config(self, config_key):
        """重新加载配置"""
        if config_key in self.config_cache:
            del self.config_cache[config_key]
        
        # 通知所有监听器
        for watcher in self.config_watchers:
            await watcher.on_config_changed(config_key)
```

### 6.3 多项目支持

#### 6.3.1 项目隔离
```python
class ProjectManager:
    def __init__(self):
        self.projects = {}
    
    def register_project(self, project_config):
        """注册新项目"""
        project_key = project_config['key']
        self.projects[project_key] = {
            'config': project_config,
            'sync_service': SyncService(project_config),
            'field_mapper': FieldMapper(project_config),
            'jira_client': JiraClient(project_config)
        }
    
    async def process_event_for_project(self, project_key, event):
        """为特定项目处理事件"""
        if project_key not in self.projects:
            raise ValueError(f"Unknown project: {project_key}")
        
        project_services = self.projects[project_key]
        return await project_services['sync_service'].process_sync_event(event)
```

## 7. 测试策略

### 7.1 单元测试

#### 7.1.1 测试覆盖
```python
# 测试字段映射
class TestFieldMapper(unittest.TestCase):
    def setUp(self):
        self.field_mapper = FieldMapper()
    
    def test_notion_to_jira_mapping(self):
        notion_data = {
            'title': '测试需求',
            'priority': '高 High',
            'description': '这是一个测试需求'
        }
        
        jira_fields = self.field_mapper.map_notion_to_jira(notion_data)
        
        self.assertEqual(jira_fields['summary'], '测试需求')
        self.assertEqual(jira_fields['priority']['id'], '1')
        self.assertIn('这是一个测试需求', jira_fields['description'])
```

### 7.2 集成测试

#### 7.2.1 API测试
```python
class TestJiraIntegration(unittest.TestCase):
    def setUp(self):
        self.jira_client = JiraClient()
    
    async def test_create_issue_flow(self):
        # 创建测试Issue
        fields = {
            'project': {'id': '13904'},
            'summary': 'API测试Issue',
            'issuetype': {'id': '10001'},
            'fixVersions': [{'id': '14577'}]
        }
        
        issue = await self.jira_client.create_issue(fields)
        self.assertIsNotNone(issue['key'])
        
        # 清理测试数据
        await self.jira_client.delete_issue(issue['key'])
```

### 7.3 端到端测试

#### 7.3.1 完整流程测试
```python
class TestEndToEndSync(unittest.TestCase):
    async def test_complete_sync_flow(self):
        # 1. 模拟Notion webhook事件
        webhook_data = {
            'event_type': 'page.updated',
            'page_id': 'test-page-123',
            'properties': {
                'title': 'E2E测试需求',
                'priority': '中 Medium',
                'sync2jira': True
            }
        }
        
        # 2. 发送到webhook服务器
        response = await self.send_webhook(webhook_data)
        self.assertEqual(response.status_code, 200)
        
        # 3. 等待同步完成
        await asyncio.sleep(10)
        
        # 4. 验证JIRA中创建了Issue
        jira_issue = await self.find_jira_issue_by_notion_id('test-page-123')
        self.assertIsNotNone(jira_issue)
        self.assertEqual(jira_issue['fields']['summary'], 'E2E测试需求')
```

## 8. 运维监控

### 8.1 健康检查

#### 8.1.1 多层健康检查
```python
class HealthChecker:
    async def check_system_health(self):
        """系统健康检查"""
        checks = {
            'redis': await self.check_redis_connection(),
            'jira': await self.check_jira_api(),
            'disk_space': await self.check_disk_space(),
            'memory': await self.check_memory_usage(),
            'queue_length': await self.check_queue_length()
        }
        
        overall_status = 'healthy' if all(checks.values()) else 'unhealthy'
        
        return {
            'status': overall_status,
            'checks': checks,
            'timestamp': datetime.utcnow().isoformat()
        }
```

### 8.2 告警系统

#### 8.2.1 告警规则
```python
class AlertManager:
    ALERT_RULES = {
        'high_error_rate': {
            'condition': lambda metrics: metrics['error_rate'] > 0.1,
            'message': '同步错误率过高: {error_rate:.2%}',
            'severity': 'warning'
        },
        'queue_backlog': {
            'condition': lambda metrics: metrics['queue_length'] > 100,
            'message': '队列积压严重: {queue_length} 个待处理事件',
            'severity': 'critical'
        },
        'service_down': {
            'condition': lambda health: health['status'] == 'unhealthy',
            'message': '服务状态异常',
            'severity': 'critical'
        }
    }
    
    async def check_alerts(self, metrics, health_status):
        """检查告警条件"""
        alerts = []
        
        for rule_name, rule in self.ALERT_RULES.items():
            if rule['condition'](metrics if 'metrics' in rule_name else health_status):
                alert = {
                    'rule': rule_name,
                    'message': rule['message'].format(**metrics),
                    'severity': rule['severity'],
                    'timestamp': datetime.utcnow().isoformat()
                }
                alerts.append(alert)
        
        if alerts:
            await self.send_alerts(alerts)
        
        return alerts
```

这个架构设计文档涵盖了系统的核心技术架构、模块设计、部署方案、安全措施、性能优化和运维监控等各个方面，为项目的技术实现提供了详细的指导。 