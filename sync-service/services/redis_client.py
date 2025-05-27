"""
Redis客户端模块
负责消息队列管理和数据缓存
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger


class RedisClient:
    """异步Redis客户端"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("redis_client")
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """建立Redis连接"""
        try:
            # 创建连接池
            self.pool = ConnectionPool(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                max_connections=self.settings.redis.max_connections,
                socket_timeout=self.settings.redis.socket_timeout,
                socket_connect_timeout=self.settings.redis.socket_connect_timeout,
                retry_on_timeout=self.settings.redis.retry_on_timeout,
                decode_responses=True,
                encoding='utf-8'
            )
            
            # 创建Redis客户端
            self.client = redis.Redis(connection_pool=self.pool)
            
            # 测试连接
            await self.client.ping()
            self._connected = True
            
            self.logger.info(
                "Redis连接成功",
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                db=self.settings.redis.db
            )
            
        except Exception as e:
            self.logger.error("Redis连接失败", error=str(e))
            raise
    
    async def disconnect(self):
        """关闭Redis连接"""
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()
            
            self._connected = False
            self.logger.info("Redis连接已关闭")
            
        except Exception as e:
            self.logger.error("关闭Redis连接时发生错误", error=str(e))
    
    async def ping(self) -> bool:
        """检查Redis连接状态"""
        try:
            if not self.client:
                return False
            await self.client.ping()
            return True
        except Exception:
            return False
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    # 队列操作方法
    
    async def push_to_queue(self, queue_name: str, data: Dict[str, Any], priority: int = 0) -> bool:
        """
        推送数据到队列
        
        Args:
            queue_name: 队列名称
            data: 要推送的数据
            priority: 优先级（数字越小优先级越高）
        
        Returns:
            是否成功推送
        """
        try:
            # 添加时间戳和优先级
            message = {
                "data": data,
                "timestamp": time.time(),
                "priority": priority,
                "id": f"{int(time.time() * 1000000)}"  # 微秒级时间戳作为ID
            }
            
            # 使用简单的列表结构，兼容低版本Redis
            if priority == 0:
                # 高优先级消息从左侧推入
                result = await self.client.lpush(queue_name, json.dumps(message))
            else:
                # 普通优先级消息从右侧推入
                result = await self.client.rpush(queue_name, json.dumps(message))
            
            if result:
                self.logger.debug(
                    "消息已推送到队列",
                    queue=queue_name,
                    message_id=message["id"],
                    priority=priority
                )
                return True
            else:
                self.logger.warning("推送消息到队列失败", queue=queue_name)
                return False
                
        except Exception as e:
            self.logger.error(
                "推送消息到队列时发生错误",
                queue=queue_name,
                error=str(e)
            )
            return False
    
    async def pop_from_queue(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        从队列中弹出数据
        
        Args:
            queue_name: 队列名称
            timeout: 超时时间（秒）
        
        Returns:
            弹出的数据，如果队列为空则返回None
        """
        try:
            # 使用BLPOP实现阻塞式弹出（兼容低版本Redis）
            result = await self.client.blpop(queue_name, timeout=timeout)
            
            if result:
                queue, message_json = result
                message = json.loads(message_json)
                
                self.logger.debug(
                    "从队列弹出消息",
                    queue=queue_name,
                    message_id=message.get("id"),
                    priority=message.get("priority")
                )
                
                # 返回消息数据，兼容webhook-server格式
                return message
            else:
                # 超时，没有消息
                return None
                
        except Exception as e:
            self.logger.error(
                "从队列弹出消息时发生错误",
                queue=queue_name,
                error=str(e)
            )
            return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """获取队列长度"""
        try:
            return await self.client.llen(queue_name)
        except Exception as e:
            self.logger.error("获取队列长度失败", queue=queue_name, error=str(e))
            return 0
    
    async def clear_queue(self, queue_name: str) -> bool:
        """清空队列"""
        try:
            result = await self.client.delete(queue_name)
            self.logger.info("队列已清空", queue=queue_name)
            return bool(result)
        except Exception as e:
            self.logger.error("清空队列失败", queue=queue_name, error=str(e))
            return False
    
    # 缓存操作方法
    
    async def set_cache(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await self.client.set(key, value, ex=expire)
            return bool(result)
            
        except Exception as e:
            self.logger.error("设置缓存失败", key=key, error=str(e))
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在则返回None
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            self.logger.error("获取缓存失败", key=key, error=str(e))
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存"""
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            self.logger.error("删除缓存失败", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception as e:
            self.logger.error("检查键存在性失败", key=key, error=str(e))
            return False
    
    # 同步状态管理
    
    async def set_sync_mapping(self, notion_page_id: str, jira_issue_key: str) -> bool:
        """设置Notion页面和JIRA Issue的映射关系"""
        try:
            mapping_key = f"sync_mapping:{notion_page_id}"
            mapping_data = {
                "jira_issue_key": jira_issue_key,
                "created_at": time.time(),
                "last_sync": time.time()
            }
            
            result = await self.set_cache(mapping_key, mapping_data)
            
            # 同时设置反向映射
            reverse_key = f"reverse_mapping:{jira_issue_key}"
            reverse_data = {
                "notion_page_id": notion_page_id,
                "created_at": time.time(),
                "last_sync": time.time()
            }
            await self.set_cache(reverse_key, reverse_data)
            
            return result
            
        except Exception as e:
            self.logger.error(
                "设置同步映射失败",
                notion_page_id=notion_page_id,
                jira_issue_key=jira_issue_key,
                error=str(e)
            )
            return False
    
    async def get_sync_mapping(self, notion_page_id: str) -> Optional[Dict[str, Any]]:
        """获取Notion页面对应的JIRA Issue信息"""
        mapping_key = f"sync_mapping:{notion_page_id}"
        return await self.get_cache(mapping_key)
    
    async def get_reverse_mapping(self, jira_issue_key: str) -> Optional[Dict[str, Any]]:
        """获取JIRA Issue对应的Notion页面信息"""
        reverse_key = f"reverse_mapping:{jira_issue_key}"
        return await self.get_cache(reverse_key)
    
    async def update_last_sync_time(self, notion_page_id: str) -> bool:
        """更新最后同步时间"""
        try:
            mapping = await self.get_sync_mapping(notion_page_id)
            if mapping:
                mapping["last_sync"] = time.time()
                mapping_key = f"sync_mapping:{notion_page_id}"
                return await self.set_cache(mapping_key, mapping)
            return False
        except Exception as e:
            self.logger.error("更新同步时间失败", notion_page_id=notion_page_id, error=str(e))
            return False
    
    # 统计信息
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Redis统计信息"""
        try:
            info = await self.client.info()
            queue_length = await self.get_queue_length(self.settings.sync.queue_name)
            
            return {
                "connected": self.is_connected,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "queue_length": queue_length,
                "uptime_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            self.logger.error("获取Redis统计信息失败", error=str(e))
            return {"connected": False, "error": str(e)} 