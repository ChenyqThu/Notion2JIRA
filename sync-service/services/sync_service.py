"""
同步服务核心模块
负责处理Notion和JIRA之间的数据同步
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger
from services.redis_client import RedisClient


class SyncService:
    """同步服务主类"""
    
    def __init__(self, settings: Settings, redis_client: RedisClient):
        self.settings = settings
        self.redis_client = redis_client
        self.logger = get_logger("sync_service")
        self.running = False
        self.consumer_task = None
        
        # 统计信息
        self.stats = {
            "processed_messages": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "start_time": None,
            "last_activity": None
        }
    
    async def initialize(self):
        """初始化同步服务"""
        try:
            self.logger.info("正在初始化同步服务...")
            
            # 这里可以添加其他初始化逻辑
            # 比如加载字段映射配置、验证API连接等
            
            self.stats["start_time"] = time.time()
            self.logger.info("同步服务初始化完成")
            
        except Exception as e:
            self.logger.error("同步服务初始化失败", error=str(e))
            raise
    
    async def start_consumer(self):
        """启动消息消费器"""
        self.running = True
        self.logger.info("启动消息消费器", queue=self.settings.sync.queue_name)
        
        while self.running:
            try:
                # 从队列中获取消息
                message = await self.redis_client.pop_from_queue(
                    self.settings.sync.queue_name,
                    timeout=10
                )
                
                if message:
                    await self._process_message(message)
                else:
                    # 队列为空，短暂休息
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.logger.error("消息消费器发生错误", error=str(e))
                await asyncio.sleep(5)  # 出错时等待5秒再继续
    
    async def stop(self):
        """停止同步服务"""
        self.logger.info("正在停止同步服务...")
        self.running = False
        
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("同步服务已停止")
    
    def get_status(self) -> bool:
        """获取服务状态"""
        return self.running
    
    async def _process_message(self, message: Dict[str, Any]):
        """处理单个消息"""
        try:
            self.stats["processed_messages"] += 1
            self.stats["last_activity"] = time.time()
            
            event_type = message.get("event_type")
            
            self.logger.info(
                "处理同步消息",
                event_type=event_type,
                page_id=message.get("page_id"),
                message_id=message.get("id")
            )
            
            # 根据事件类型分发处理
            if event_type == "notion_to_jira_create":
                await self._handle_notion_to_jira_create(message)
            elif event_type == "notion_to_jira_update":
                await self._handle_notion_to_jira_update(message)
            elif event_type == "jira_to_notion_update":
                await self._handle_jira_to_notion_update(message)
            else:
                self.logger.warning("未知的事件类型", event_type=event_type)
                return
            
            self.stats["successful_syncs"] += 1
            
        except Exception as e:
            self.stats["failed_syncs"] += 1
            self.logger.error(
                "处理消息失败",
                error=str(e),
                message_id=message.get("id"),
                event_type=message.get("event_type")
            )
            
            # 可以考虑将失败的消息重新入队或记录到失败队列
            await self._handle_sync_failure(message, e)
    
    async def _handle_notion_to_jira_create(self, message: Dict[str, Any]):
        """处理Notion到JIRA的创建同步"""
        page_id = message.get("page_id")
        
        self.logger.info("开始Notion到JIRA创建同步", page_id=page_id)
        
        try:
            # 检查是否已经存在映射关系
            existing_mapping = await self.redis_client.get_sync_mapping(page_id)
            if existing_mapping:
                self.logger.warning(
                    "页面已存在JIRA映射，跳过创建",
                    page_id=page_id,
                    jira_issue_key=existing_mapping.get("jira_issue_key")
                )
                return
            
            # TODO: 实现具体的同步逻辑
            # 1. 从Notion获取页面详细信息
            # 2. 字段映射转换
            # 3. 在JIRA中创建Issue
            # 4. 更新Notion页面状态和JIRA链接
            # 5. 保存映射关系
            
            # 临时模拟处理
            await asyncio.sleep(0.1)  # 模拟API调用延迟
            
            # 模拟创建成功，保存映射关系
            mock_jira_key = f"SMBNET-{int(time.time() % 10000)}"
            await self.redis_client.set_sync_mapping(page_id, mock_jira_key)
            
            self.logger.info(
                "Notion到JIRA创建同步完成",
                page_id=page_id,
                jira_issue_key=mock_jira_key
            )
            
        except Exception as e:
            self.logger.error("Notion到JIRA创建同步失败", page_id=page_id, error=str(e))
            raise
    
    async def _handle_notion_to_jira_update(self, message: Dict[str, Any]):
        """处理Notion到JIRA的更新同步"""
        page_id = message.get("page_id")
        
        self.logger.info("开始Notion到JIRA更新同步", page_id=page_id)
        
        try:
            # 获取映射关系
            mapping = await self.redis_client.get_sync_mapping(page_id)
            if not mapping:
                self.logger.warning("未找到页面的JIRA映射关系，转为创建同步", page_id=page_id)
                await self._handle_notion_to_jira_create(message)
                return
            
            jira_issue_key = mapping.get("jira_issue_key")
            
            # TODO: 实现具体的更新同步逻辑
            # 1. 从Notion获取页面最新信息
            # 2. 字段映射转换
            # 3. 更新JIRA Issue
            # 4. 更新同步时间
            
            # 临时模拟处理
            await asyncio.sleep(0.1)  # 模拟API调用延迟
            
            # 更新同步时间
            await self.redis_client.update_last_sync_time(page_id)
            
            self.logger.info(
                "Notion到JIRA更新同步完成",
                page_id=page_id,
                jira_issue_key=jira_issue_key
            )
            
        except Exception as e:
            self.logger.error("Notion到JIRA更新同步失败", page_id=page_id, error=str(e))
            raise
    
    async def _handle_jira_to_notion_update(self, message: Dict[str, Any]):
        """处理JIRA到Notion的更新同步"""
        jira_issue_key = message.get("jira_issue_key")
        
        self.logger.info("开始JIRA到Notion更新同步", jira_issue_key=jira_issue_key)
        
        try:
            # 获取反向映射关系
            mapping = await self.redis_client.get_reverse_mapping(jira_issue_key)
            if not mapping:
                self.logger.warning("未找到JIRA Issue的Notion映射关系", jira_issue_key=jira_issue_key)
                return
            
            notion_page_id = mapping.get("notion_page_id")
            
            # TODO: 实现具体的反向同步逻辑
            # 1. 从JIRA获取Issue最新信息
            # 2. 字段映射转换
            # 3. 更新Notion页面
            # 4. 更新同步时间
            
            # 临时模拟处理
            await asyncio.sleep(0.1)  # 模拟API调用延迟
            
            self.logger.info(
                "JIRA到Notion更新同步完成",
                jira_issue_key=jira_issue_key,
                notion_page_id=notion_page_id
            )
            
        except Exception as e:
            self.logger.error("JIRA到Notion更新同步失败", jira_issue_key=jira_issue_key, error=str(e))
            raise
    
    async def _handle_sync_failure(self, message: Dict[str, Any], error: Exception):
        """处理同步失败的情况"""
        try:
            # 记录失败信息
            failure_info = {
                "message": message,
                "error": str(error),
                "error_type": type(error).__name__,
                "timestamp": time.time(),
                "retry_count": message.get("retry_count", 0)
            }
            
            # 如果重试次数未超过限制，重新入队
            if failure_info["retry_count"] < self.settings.sync.max_retry_attempts:
                failure_info["retry_count"] += 1
                
                # 延迟重试
                await asyncio.sleep(self.settings.sync.retry_delay)
                
                # 重新入队，优先级降低
                await self.redis_client.push_to_queue(
                    self.settings.sync.queue_name,
                    failure_info["message"],
                    priority=failure_info["retry_count"] * 10  # 重试次数越多优先级越低
                )
                
                self.logger.info(
                    "消息已重新入队重试",
                    message_id=message.get("id"),
                    retry_count=failure_info["retry_count"]
                )
            else:
                # 超过重试次数，记录到失败队列
                await self.redis_client.push_to_queue(
                    "failed_sync_queue",
                    failure_info,
                    priority=0
                )
                
                self.logger.error(
                    "消息重试次数超限，已移至失败队列",
                    message_id=message.get("id"),
                    retry_count=failure_info["retry_count"]
                )
                
        except Exception as e:
            self.logger.error("处理同步失败时发生错误", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        current_time = time.time()
        uptime = current_time - self.stats["start_time"] if self.stats["start_time"] else 0
        
        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "processed_messages": self.stats["processed_messages"],
            "successful_syncs": self.stats["successful_syncs"],
            "failed_syncs": self.stats["failed_syncs"],
            "success_rate": (
                self.stats["successful_syncs"] / max(self.stats["processed_messages"], 1) * 100
            ),
            "last_activity": self.stats["last_activity"],
            "last_activity_ago": (
                current_time - self.stats["last_activity"] 
                if self.stats["last_activity"] else None
            )
        } 