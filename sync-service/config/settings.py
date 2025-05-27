"""
配置管理模块
负责加载和管理所有的环境变量和配置项
"""

import os
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 10
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    retry_on_timeout: bool = True


@dataclass
class JiraConfig:
    """JIRA配置"""
    base_url: str
    username: str
    password: str
    project_key: str = "SMBNET"
    project_id: str = "13904"
    default_issue_type_id: str = "10001"  # Story
    default_version_id: str = "14577"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class NotionConfig:
    """Notion配置（可选，用于反向同步）"""
    token: Optional[str] = None
    database_id: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


@dataclass
class SyncConfig:
    """同步配置"""
    queue_name: str = "sync_queue"
    batch_size: int = 10
    max_retry_attempts: int = 3
    retry_delay: int = 60  # 秒
    sync_interval: int = 300  # 反向同步间隔（秒）
    enable_reverse_sync: bool = True


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/sync_service.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class Settings:
    """配置管理类"""
    
    def __init__(self):
        self._load_env_file()
        self.redis = self._load_redis_config()
        self.jira = self._load_jira_config()
        self.notion = self._load_notion_config()
        self.sync = self._load_sync_config()
        self.log = self._load_log_config()
        
        # 验证必要配置
        self._validate_config()
    
    def _load_env_file(self):
        """加载.env文件"""
        # 统一使用sync-service目录下的.env文件
        sync_service_dir = os.path.dirname(os.path.dirname(__file__))
        env_file = os.path.join(sync_service_dir, '.env')
        
        if os.path.exists(env_file):
            print(f"Loading environment from: {env_file}")
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        else:
            print(f"Warning: .env file not found at {env_file}")
            print("Please create .env file in sync-service directory with required configuration")
            print("Using system environment variables as fallback")
    
    def _load_redis_config(self) -> RedisConfig:
        """加载Redis配置"""
        return RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "30")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "30")),
            retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        )
    
    def _load_jira_config(self) -> JiraConfig:
        """加载JIRA配置"""
        base_url = os.getenv("JIRA_BASE_URL")
        username = os.getenv("JIRA_USER_EMAIL")  # 使用.env_example中的字段名
        password = os.getenv("JIRA_USER_PASSWORD")  # 使用.env_example中的字段名
        
        if not all([base_url, username, password]):
            raise ValueError("JIRA配置不完整，请检查环境变量: JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_USER_PASSWORD")
        
        return JiraConfig(
            base_url=base_url,
            username=username,
            password=password,
            project_key=os.getenv("JIRA_PROJECT_KEY", "SMBNET"),
            project_id=os.getenv("JIRA_PROJECT_ID", "13904"),
            default_issue_type_id=os.getenv("JIRA_DEFAULT_ISSUE_TYPE_ID", "10001"),
            default_version_id=os.getenv("JIRA_DEFAULT_VERSION_ID", "14577"),
            timeout=int(os.getenv("JIRA_TIMEOUT", "30")),
            max_retries=int(os.getenv("JIRA_MAX_RETRIES", "3"))
        )
    
    def _load_notion_config(self) -> NotionConfig:
        """加载Notion配置（可选，用于反向同步）"""
        token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")
        
        # Notion配置是可选的，主要用于反向同步
        if token and database_id:
            print("Notion配置已加载，支持反向同步")
        else:
            print("Notion配置未完整，仅支持单向同步（Notion → JIRA）")
        
        return NotionConfig(
            token=token if token and token != "secret_your_notion_integration_token_here" else None,
            database_id=database_id if database_id and database_id != "your_notion_database_id_here" else None,
            timeout=int(os.getenv("NOTION_TIMEOUT", "30")),
            max_retries=int(os.getenv("NOTION_MAX_RETRIES", "3"))
        )
    
    def _load_sync_config(self) -> SyncConfig:
        """加载同步配置"""
        return SyncConfig(
            queue_name=os.getenv("SYNC_QUEUE_NAME", "sync_queue"),
            batch_size=int(os.getenv("SYNC_BATCH_SIZE", "10")),
            max_retry_attempts=int(os.getenv("SYNC_MAX_RETRY_ATTEMPTS", "3")),
            retry_delay=int(os.getenv("SYNC_RETRY_DELAY", "60")),
            sync_interval=int(os.getenv("SYNC_INTERVAL", "300")),
            enable_reverse_sync=os.getenv("ENABLE_REVERSE_SYNC", "true").lower() == "true"
        )
    
    def _load_log_config(self) -> LogConfig:
        """加载日志配置"""
        return LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file_path=os.getenv("LOG_FILE_PATH", "logs/sync_service.log"),
            max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
        )
    
    def _validate_config(self):
        """验证配置的有效性"""
        errors = []
        
        # 验证JIRA配置
        if not self.jira.base_url.startswith(('http://', 'https://')):
            errors.append("JIRA_BASE_URL必须以http://或https://开头")
        
        # 验证Redis配置
        if not (1 <= self.redis.port <= 65535):
            errors.append("REDIS_PORT必须在1-65535范围内")
        
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
    
    def get_env_summary(self) -> dict:
        """获取环境配置摘要（不包含敏感信息）"""
        return {
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db,
                "has_password": bool(self.redis.password)
            },
            "jira": {
                "base_url": self.jira.base_url,
                "project_key": self.jira.project_key,
                "project_id": self.jira.project_id,
                "username": self.jira.username
            },
            "notion": {
                "database_id": self.notion.database_id,
                "has_token": bool(self.notion.token)
            },
            "sync": {
                "queue_name": self.sync.queue_name,
                "batch_size": self.sync.batch_size,
                "enable_reverse_sync": self.sync.enable_reverse_sync
            },
            "log": {
                "level": self.log.level,
                "file_path": self.log.file_path
            }
        } 