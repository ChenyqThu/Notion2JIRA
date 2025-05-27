# Notion2JIRA 内网同步服务

这是Notion2JIRA系统的内网同步服务组件，负责处理Notion和JIRA之间的数据同步。

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Notion API    │───▶│ webhook-server  │───▶│     Redis       │
│   (Webhook)     │    │   (公网部署)     │    │   (消息队列)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   JIRA API      │◀───│  sync-service   │
                       │                 │    │   (内网部署)     │
                       └─────────────────┘    └─────────────────┘
```

**各服务职责**:
- **webhook-server**: 接收Notion webhook，验证签名，推送到Redis队列
- **sync-service**: 从Redis队列消费消息，调用JIRA API进行同步
- **Redis**: 作为消息队列，解耦两个服务

> **注意**: sync-service作为内网服务，只负责消费Redis队列中的消息并调用JIRA API。
> Webhook相关配置属于webhook-server的职责范围。

## ✨ 功能特性

- ✅ 异步消息队列处理
- ✅ Redis连接管理
- ✅ JIRA API集成
- ✅ 字段映射引擎
- ✅ 结构化日志记录
- ✅ 系统监控和健康检查
- ✅ 配置管理
- ✅ 错误处理和重试机制
- ✅ 优雅关闭

## 📋 系统要求

- Python 3.8+
- Redis 服务器
- 内网访问JIRA权限
- Notion API访问权限（可选，用于反向同步）

## 🚀 快速开始

### 1. 创建配置文件

```bash
cd sync-service
python scripts/init_config.py create
```

### 2. 编辑配置文件

```bash
# 编辑 .env 文件，填入实际配置值
vim .env
```

### 3. 验证配置

```bash
python scripts/init_config.py validate
```

### 4. 启动服务

```bash
# 启动服务（会自动设置虚拟环境和安装依赖）
./start.sh
```

### 5. 验证服务

服务启动后，你应该看到类似的日志输出：

```
[INFO] 正在初始化内网同步服务...
[INFO] Redis连接已建立
[INFO] JIRA客户端初始化完成
[INFO] 字段映射器初始化完成
[INFO] 同步服务已初始化
[INFO] 内网同步服务启动成功
[INFO] 启动消息消费器
```

## ⚙️ 配置说明

sync-service使用位于 `sync-service/.env` 文件中的环境变量进行配置。

### 🔧 服务配置
```bash
# 服务运行环境 (development/production)
ENVIRONMENT=development

# 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_LEVEL=INFO

# 服务端口
SERVICE_PORT=8001
```

### 📊 Redis 配置
```bash
# Redis服务器地址
REDIS_HOST=localhost

# Redis服务器端口
REDIS_PORT=6379

# Redis数据库编号
REDIS_DB=0

# Redis密码（可选）
REDIS_PASSWORD=

# Redis连接池大小
REDIS_POOL_SIZE=10
```

### 🎫 JIRA 配置（必填）
```bash
# JIRA服务器地址
JIRA_BASE_URL=http://rdjira.tp-link.com

# JIRA用户邮箱
JIRA_USER_EMAIL=your_email@tp-link.com

# JIRA用户密码或API Token
JIRA_USER_PASSWORD=your_password_here

# JIRA项目Key
JIRA_PROJECT_KEY=SMBNET

# JIRA默认Issue类型
JIRA_DEFAULT_ISSUE_TYPE=Story

# JIRA请求超时时间（秒）
JIRA_TIMEOUT=30

# 是否验证SSL证书（内网环境建议设为false）
JIRA_VERIFY_SSL=false
```

### 📝 Notion 配置（可选，用于反向同步）
```bash
# Notion集成Token
NOTION_TOKEN=secret_your_notion_integration_token_here

# Notion数据库ID
NOTION_DATABASE_ID=your_notion_database_id_here

# Notion API版本
NOTION_API_VERSION=2022-06-28
```

### 🔄 同步配置
```bash
# 同步间隔（秒）
SYNC_INTERVAL=300

# 批处理大小
BATCH_SIZE=10

# 最大重试次数
MAX_RETRY_COUNT=3

# 重试间隔（秒）
RETRY_INTERVAL=5
```

### 🐛 调试配置
```bash
# 是否启用调试模式
DEBUG=true

# 是否保存详细日志
VERBOSE_LOGGING=true

# 测试模式（不实际创建JIRA Issue）
TEST_MODE=false
```

## 📁 项目结构

```
sync-service/
├── main.py                    # 主程序入口
├── start.sh                   # 启动脚本
├── requirements.txt           # Python依赖
├── README.md                  # 说明文档
├── .env                       # 环境配置文件
├── config/                    # 配置模块
│   ├── settings.py            # 配置管理
│   └── logger.py              # 日志配置
├── services/                  # 服务模块
│   ├── redis_client.py        # Redis客户端
│   ├── sync_service.py        # 同步服务
│   ├── jira_client.py         # JIRA客户端
│   ├── field_mapper.py        # 字段映射器
│   └── monitor_service.py     # 监控服务
├── scripts/                   # 工具脚本
│   └── init_config.py         # 配置初始化脚本
├── logs/                      # 日志目录
├── data/                      # 数据目录
├── test_jira_creation.py      # JIRA功能测试
├── test_basic.py              # 基础功能测试
└── venv/                      # Python虚拟环境
```

## 🔧 使用方法

### 环境检查

```bash
# 仅检查环境，不启动服务
./start.sh --check
```

### 设置环境

```bash
# 仅设置虚拟环境和安装依赖
./start.sh --setup-only
```

### 详细输出

```bash
# 启动时显示详细信息
./start.sh --verbose
```

### 测试功能

```bash
# 测试JIRA连接和Issue创建
python test_jira_creation.py

# 测试基础功能
python test_basic.py
```

## 📊 监控和日志

### 日志文件

- 默认日志文件：`logs/sync_service.log`
- 日志轮转：10MB，保留5个文件
- 日志级别：INFO（可配置）

### 系统监控

服务内置监控功能，会自动监控：

- CPU使用率
- 内存使用率
- 磁盘使用率
- Redis连接状态
- 队列长度
- 同步成功率

### 健康检查

服务提供健康检查功能，可以通过以下方式检查：

- 查看日志输出
- 检查进程状态
- 监控系统资源

## 🔍 故障排除

### 配置加载失败
```bash
# 检查文件是否存在
ls -la sync-service/.env

# 验证配置格式
python scripts/init_config.py validate
```

### JIRA连接失败
```bash
# 测试JIRA连接
python test_jira_creation.py

# 检查网络连接
curl -I http://rdjira.tp-link.com
```

### Redis连接失败
```bash
# 检查Redis服务状态
redis-cli ping

# 测试连接配置
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print(r.ping())"
```

### 常见问题

1. **Python依赖安装失败**
   ```bash
   # 手动安装依赖
   cd sync-service
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **权限问题**
   ```bash
   # 确保脚本可执行
   chmod +x start.sh
   ```

3. **环境变量配置错误**
   ```bash
   # 检查环境变量
   ./start.sh --check
   ```

### 日志分析

查看详细日志：

```bash
# 实时查看日志
tail -f logs/sync_service.log

# 查看错误日志
grep ERROR logs/sync_service.log

# 查看最近的同步活动
grep "同步事件" logs/sync_service.log | tail -20
```

## 🔒 安全注意事项

1. **敏感信息保护**
   - `.env` 文件已被 `.gitignore` 忽略
   - 不要将包含真实密码的 `.env` 文件提交到版本控制

2. **权限设置**
   ```bash
   # 设置适当的文件权限
   chmod 600 sync-service/.env
   ```

3. **环境隔离**
   - 开发环境和生产环境使用不同的配置文件
   - 生产环境建议使用环境变量而非文件

## 🛠️ 开发说明

### 代码结构

- `main.py`: 应用程序入口，负责服务的启动和关闭
- `config/`: 配置管理模块，处理环境变量和设置
- `services/`: 核心服务模块，包含业务逻辑
- `scripts/`: 工具脚本，配置管理等
- `start.sh`: 启动脚本，处理环境设置和服务启动

### 扩展开发

如需添加新功能：

1. 在`services/`目录下创建新的服务模块
2. 在`main.py`中注册新服务
3. 在`config/settings.py`中添加相关配置
4. 更新`requirements.txt`添加新依赖

### 配置示例

#### 开发环境配置
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
JIRA_BASE_URL=http://rdjira.tp-link.com
JIRA_VERIFY_SSL=false
DEBUG=true
TEST_MODE=false
```

#### 生产环境配置
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
JIRA_BASE_URL=https://jira.company.com
JIRA_VERIFY_SSL=true
DEBUG=false
TEST_MODE=false
```

## 📝 版本信息

- 版本：1.0.0
- 状态：开发中
- 最后更新：2025年5月26日

## 📞 支持

如有问题，请查看：

1. 日志文件：`logs/sync_service.log`
2. 项目文档：`../README.md`
3. 架构文档：`../Architecture.md`
4. 任务文档：`../tasks.md` 