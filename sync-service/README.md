# Notion2JIRA 内网同步服务

这是Notion2JIRA系统的内网同步服务组件，负责处理Notion和JIRA之间的数据同步。

## 功能特性

- ✅ 异步消息队列处理
- ✅ Redis连接管理
- ✅ 结构化日志记录
- ✅ 系统监控和健康检查
- ✅ 配置管理
- ✅ 错误处理和重试机制
- ✅ 优雅关闭

## 系统要求

- Python 3.8+
- Redis 服务器
- 内网访问JIRA权限
- Notion API访问权限

## 快速开始

### 1. 环境准备

```bash
# 检查Python版本
python3 --version

# 检查Redis服务
redis-cli ping
```

### 2. 配置环境变量

复制并编辑环境变量文件：

```bash
# 在项目根目录创建.env文件
cp .env_example .env
```

编辑`.env`文件，配置以下必要参数：

```bash
# JIRA配置
JIRA_BASE_URL=http://rdjira.tp-link.com
JIRA_USERNAME=your_username
JIRA_PASSWORD=your_password

# Notion配置  
NOTION_TOKEN=secret_your_notion_token
NOTION_DATABASE_ID=your_database_id

# Redis配置（如果不是默认配置）
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. 启动服务

```bash
# 进入服务目录
cd sync-service

# 启动服务（会自动设置虚拟环境和安装依赖）
./start.sh
```

### 4. 验证服务

服务启动后，你应该看到类似的日志输出：

```
[INFO] 正在初始化内网同步服务...
[INFO] Redis连接已建立
[INFO] 同步服务已初始化
[INFO] 监控服务已初始化
[INFO] 内网同步服务初始化完成
[INFO] 内网同步服务启动成功
[INFO] 启动消息消费器
[INFO] 启动系统监控
```

## 使用方法

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

## 项目结构

```
sync-service/
├── main.py                 # 主程序入口
├── start.sh               # 启动脚本
├── requirements.txt       # Python依赖
├── README.md             # 说明文档
├── config/               # 配置模块
│   ├── settings.py       # 配置管理
│   └── logger.py         # 日志配置
├── services/             # 服务模块
│   ├── redis_client.py   # Redis客户端
│   ├── sync_service.py   # 同步服务
│   └── monitor_service.py # 监控服务
├── logs/                 # 日志目录
├── data/                 # 数据目录
└── venv/                 # Python虚拟环境
```

## 配置说明

### 必需配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| JIRA_BASE_URL | JIRA服务器地址 | http://rdjira.tp-link.com |
| JIRA_USERNAME | JIRA用户名 | your_username |
| JIRA_PASSWORD | JIRA密码 | your_password |
| NOTION_TOKEN | Notion API令牌 | secret_xxx |
| NOTION_DATABASE_ID | Notion数据库ID | xxx-xxx-xxx |

### 可选配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| REDIS_HOST | localhost | Redis服务器地址 |
| REDIS_PORT | 6379 | Redis端口 |
| LOG_LEVEL | INFO | 日志级别 |
| SYNC_QUEUE_NAME | sync_queue | 同步队列名称 |
| SYNC_BATCH_SIZE | 10 | 批处理大小 |

## 监控和日志

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

## 故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 检查Redis服务状态
   redis-cli ping
   
   # 检查Redis配置
   grep REDIS .env
   ```

2. **Python依赖安装失败**
   ```bash
   # 手动安装依赖
   cd sync-service
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **环境变量配置错误**
   ```bash
   # 检查环境变量
   ./start.sh --check
   ```

4. **权限问题**
   ```bash
   # 确保脚本可执行
   chmod +x start.sh
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

## 开发说明

### 代码结构

- `main.py`: 应用程序入口，负责服务的启动和关闭
- `config/`: 配置管理模块，处理环境变量和设置
- `services/`: 核心服务模块，包含业务逻辑
- `start.sh`: 启动脚本，处理环境设置和服务启动

### 扩展开发

如需添加新功能：

1. 在`services/`目录下创建新的服务模块
2. 在`main.py`中注册新服务
3. 在`config/settings.py`中添加相关配置
4. 更新`requirements.txt`添加新依赖

## 版本信息

- 版本：1.0.0
- 状态：开发中
- 最后更新：2025年5月26日

## 支持

如有问题，请查看：

1. 日志文件：`logs/sync_service.log`
2. 项目文档：`../README.md`
3. 架构文档：`../Architecture.md` 