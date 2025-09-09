"""
同步服务核心模块
负责处理Notion和JIRA之间的数据同步
"""

import asyncio
import time
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger
from services.redis_client import RedisClient
from services.jira_client import JiraClient
from services.field_mapper import FieldMapper
from services.notion_client import NotionClient
from services.version_mapper import VersionMapper


class SyncService:
    """同步服务主类"""
    
    def __init__(self, settings: Settings, redis_client: RedisClient):
        self.settings = settings
        self.redis_client = redis_client
        self.logger = get_logger("sync_service")
        self.running = False
        self.consumer_task = None
        
        # 初始化客户端
        self.jira_client = None
        self.field_mapper = None
        
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
            
            # 初始化JIRA客户端
            self.jira_client = JiraClient(self.settings)
            await self.jira_client.initialize()
            self.logger.info("JIRA客户端初始化完成")
            
            # 初始化版本映射器
            self.version_mapper = VersionMapper(self.settings)
            self.logger.info("版本映射器初始化完成")
            
            # 初始化Notion客户端（如果配置了token）
            if self.settings.notion.token:
                self.notion_client = NotionClient(self.settings)
                await self.notion_client.initialize()
                self.logger.info("Notion客户端初始化完成")
            else:
                self.notion_client = None
                self.logger.warning("未配置Notion token，跳过Notion客户端初始化")
            
            # 初始化字段映射器（传入JiraClient和NotionClient）
            self.field_mapper = FieldMapper(self.settings, self.jira_client, self.notion_client)
            self.logger.info("字段映射器初始化完成")
            
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
        
        # 关闭JIRA客户端
        if self.jira_client:
            await self.jira_client.close()
        
        # 关闭Notion客户端
        if self.notion_client:
            await self.notion_client.close()
        
        self.logger.info("同步服务已停止")
    
    def get_status(self) -> bool:
        """获取服务状态"""
        return self.running
    
    def _parse_jira_url(self, jira_url: str) -> Optional[Tuple[str, str]]:
        """解析JIRA URL，提取项目键和Issue Key
        
        Args:
            jira_url: JIRA链接，如 "https://pdjira.tp-link.com/browse/SMBNET-123"
            
        Returns:
            Tuple[project_key, issue_key] 或 None
        """
        if not jira_url:
            return None
            
        # 匹配JIRA URL模式 - 同时支持新旧域名
        pattern = r'https?://(rdjira|pdjira)\.tp-link\.com/browse/([A-Z]+)-(\d+)'
        match = re.match(pattern, jira_url)
        
        if match:
            # group(1) = 域名(rdjira|pdjira), group(2) = 项目键, group(3) = issue号码
            project_key = match.group(2)  # SMBNET 或 SMBEAP
            issue_number = match.group(3)  # 123
            issue_key = f"{project_key}-{issue_number}"
            return project_key, issue_key
        
        return None
    
    async def _get_notion_jira_card(self, page_id: str) -> Optional[str]:
        """获取Notion页面中的JIRA Card字段值
        
        Args:
            page_id: Notion页面ID
            
        Returns:
            JIRA Card URL或None
        """
        if not self.notion_client:
            return None
            
        try:
            page_data = await self.notion_client.get_page(page_id)
            if not page_data:
                return None
            
            properties = page_data.get('properties', {})
            jira_card_field = properties.get('JIRA Card', {})
            
            # 检查URL字段
            if 'url' in jira_card_field and jira_card_field['url']:
                return jira_card_field['url']
            
            return None
            
        except Exception as e:
            self.logger.error("获取Notion页面JIRA Card字段失败", page_id=page_id, error=str(e))
            return None
    
    async def _process_message(self, message: Dict[str, Any]):
        """处理单个消息"""
        try:
            self.stats["processed_messages"] += 1
            self.stats["last_activity"] = time.time()
            
            # 适配新的数据结构 - 现在message就是完整的消息对象
            data = message.get("data", {})
            event_data = data.get("event_data", {})
            
            # 从正确的位置获取事件类型和页面ID
            event_type = data.get("type")  # 从data.type获取
            page_id = event_data.get("page_id")  # 从event_data.page_id获取
            message_id = message.get("id")
            
            self.logger.info(
                "处理同步消息",
                event_type=event_type,
                page_id=page_id,
                message_id=message_id,
                database_id=event_data.get("database_id"),
                last_edited_time=event_data.get("last_edited_time"),
                message_priority=message.get("priority"),
                message_timestamp=message.get("timestamp")
            )
            
            # 记录详细的数据结构用于调试
            properties = event_data.get("properties", {})
            self.logger.debug(
                "消息详细信息",
                message_keys=list(message.keys()),
                data_keys=list(data.keys()),
                event_data_keys=list(event_data.keys()),
                properties_count=len(properties),
                properties_keys=list(properties.keys()),
                raw_properties_count=len(event_data.get("raw_properties", {}))
            )
            
            # 根据事件类型分发处理
            if event_type == "notion_to_jira_create":
                await self._handle_notion_to_jira_sync(message, event_data)
            elif event_type == "notion_to_jira_update":
                await self._handle_notion_to_jira_sync(message, event_data)
            elif event_type == "jira_to_notion_update":
                await self._handle_jira_to_notion_update(message, event_data)
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
                event_type=message.get("data", {}).get("type")
            )
            
            # 可以考虑将失败的消息重新入队或记录到失败队列
            await self._handle_sync_failure(message, e)
    
    async def _handle_notion_to_jira_sync(self, message: Dict[str, Any], event_data: Dict[str, Any]):
        """处理Notion到JIRA的同步（创建或更新）"""
        page_id = event_data.get("page_id")
        
        self.logger.info("开始Notion到JIRA同步", page_id=page_id)
        
        try:
            # 1. 检查Notion页面中的JIRA Card字段
            existing_jira_url = await self._get_notion_jira_card(page_id)
            
            if existing_jira_url:
                # 解析现有的JIRA链接
                jira_info = self._parse_jira_url(existing_jira_url)
                if jira_info:
                    project_key, issue_key = jira_info
                    self.logger.info(
                        "检测到现有JIRA Card，执行更新操作",
                        page_id=page_id,
                        existing_jira_url=existing_jira_url,
                        project_key=project_key,
                        issue_key=issue_key
                    )
                    await self._update_existing_jira_issue(message, event_data, project_key, issue_key)
                else:
                    self.logger.warning(
                        "JIRA Card URL格式无效，执行创建操作",
                        page_id=page_id,
                        invalid_url=existing_jira_url
                    )
                    await self._create_new_jira_issue(message, event_data)
            else:
                # 没有JIRA Card，执行创建操作
                self.logger.info("未检测到JIRA Card，执行创建操作", page_id=page_id)
                await self._create_new_jira_issue(message, event_data)
            
        except Exception as e:
            self.logger.error("Notion到JIRA同步失败", page_id=page_id, error=str(e))
            raise
    
    async def _create_new_jira_issue(self, message: Dict[str, Any], event_data: Dict[str, Any]):
        """创建新的JIRA Issue"""
        page_id = event_data.get("page_id")
        
        self.logger.info("开始创建新的JIRA Issue", page_id=page_id)
        
        try:
            # 构建Notion页面数据
            raw_data = event_data.get("raw_data", {})
            notion_url = raw_data.get('url') or f"https://notion.so/{page_id.replace('-', '')}"
            
            notion_data = {
                'page_id': page_id,
                'properties': event_data.get("properties", {}),
                'raw_properties': event_data.get("raw_properties", {}),
                'raw_data': raw_data,
                'url': notion_url
            }
            
            # 字段映射转换
            jira_fields = await self.field_mapper.map_notion_to_jira(notion_data, notion_url)
            
            # 提取特殊字段（remote links 和 issue links）
            remote_links_data = jira_fields.pop('_remote_links', {})
            issue_links_data = jira_fields.pop('_issue_links', [])
            
            # 计算远程链接总数
            remote_links_count = 0
            if isinstance(remote_links_data, dict):
                remote_links_count = len(remote_links_data.get('original', [])) + len(remote_links_data.get('prd', [])) + len(remote_links_data.get('other', []))
            elif isinstance(remote_links_data, list):
                remote_links_count = len(remote_links_data)  # 向后兼容
            
            self.logger.info(
                "字段映射完成，准备创建JIRA Issue",
                page_id=page_id,
                summary=jira_fields.get('summary'),
                priority=jira_fields.get('priority', {}).get('id'),
                has_assignee=bool(jira_fields.get('assignee')),
                description_length=len(jira_fields.get('description', '')),
                remote_links_count=remote_links_count,
                issue_links_count=len(issue_links_data)
            )
            
            # 创建JIRA Issue
            jira_result = await self.jira_client.create_issue(jira_fields)
            
            if not jira_result:
                raise Exception("JIRA Issue创建失败")
            
            jira_issue_key = jira_result.get('key')
            jira_issue_id = jira_result.get('id')
            
            if not jira_issue_key:
                raise Exception("JIRA Issue创建失败：未返回Issue Key")
            
            # 处理远程链接
            if remote_links_data:
                try:
                    # 支持新的分类格式和旧格式
                    if isinstance(remote_links_data, dict):
                        remote_links = await self.field_mapper.build_categorized_remote_links(
                            remote_links_data, 
                            jira_fields.get('summary', 'Notion页面')
                        )
                    else:
                        # 向后兼容旧格式
                        remote_links = await self.field_mapper.build_remote_links_from_data_with_titles(
                            remote_links_data, 
                            jira_fields.get('summary', 'Notion页面')
                        )
                    
                    # 同步远程链接（包括删除不需要的链接）
                    success = await self.jira_client.sync_remote_links(
                        jira_issue_key, 
                        remote_links if remote_links else []
                    )
                        
                    if success:
                        link_count = len(remote_links) if remote_links else 0
                        self.logger.info(
                            "远程链接同步成功",
                            page_id=page_id,
                            jira_issue_key=jira_issue_key,
                            link_count=link_count
                        )
                    else:
                        self.logger.warning(
                            "远程链接同步失败",
                            page_id=page_id,
                            jira_issue_key=jira_issue_key
                        )
                            
                except Exception as link_e:
                    self.logger.error(
                        "创建远程链接异常",
                        page_id=page_id,
                        jira_issue_key=jira_issue_key,
                        error=str(link_e)
                    )
                    # 远程链接创建失败不影响主流程
            
            # 处理JIRA issue链接
            if issue_links_data:
                try:
                    # 使用"Relates"类型的链接（ID: 10003）
                    success_count = await self.jira_client.create_issue_links(
                        jira_issue_key,
                        issue_links_data,
                        "10003"  # Relates类型
                    )
                    
                    if success_count > 0:
                        self.logger.info(
                            "JIRA issue链接创建成功",
                            page_id=page_id,
                            jira_issue_key=jira_issue_key,
                            success_count=success_count,
                            total_count=len(issue_links_data)
                        )
                    else:
                        self.logger.warning(
                            "JIRA issue链接创建失败",
                            page_id=page_id,
                            jira_issue_key=jira_issue_key,
                            issue_keys=issue_links_data
                        )
                        
                except Exception as issue_link_e:
                    self.logger.error(
                        "创建JIRA issue链接异常",
                        page_id=page_id,
                        jira_issue_key=jira_issue_key,
                        error=str(issue_link_e)
                    )
                    # JIRA issue链接创建失败不影响主流程
            
            # 保存映射关系
            mapping_data = {
                'jira_issue_key': jira_issue_key,
                'jira_issue_id': jira_issue_id,
                'jira_browse_url': jira_result.get('browse_url', f"{self.settings.jira.base_url}/browse/{jira_issue_key}"),
                'created_at': datetime.now().isoformat(),
                'last_sync': datetime.now().isoformat(),
                'status': 'synced'
            }
            await self.redis_client.set_sync_mapping(page_id, mapping_data)
            
            # 回写JIRA信息到Notion
            await self._write_back_to_notion(page_id, jira_result)
            
            self.logger.info(
                "JIRA Issue创建完成",
                page_id=page_id,
                jira_issue_key=jira_issue_key,
                jira_issue_id=jira_issue_id,
                summary=jira_fields.get('summary')
            )
            
        except Exception as e:
            self.logger.error("创建JIRA Issue失败", page_id=page_id, error=str(e))
            raise
    
    async def _update_existing_jira_issue(self, message: Dict[str, Any], event_data: Dict[str, Any], 
                                        project_key: str, issue_key: str):
        """更新现有的JIRA Issue"""
        page_id = event_data.get("page_id")
        
        self.logger.info(
            "开始更新现有JIRA Issue",
            page_id=page_id,
            project_key=project_key,
            issue_key=issue_key
        )
        
        # 调试：打印event_data中的properties信息
        properties = event_data.get("properties", {})
        self.logger.info(
            "event_data中的properties信息",
            page_id=page_id,
            properties_count=len(properties),
            has_relation_field='Relation' in properties,
            all_field_names=list(properties.keys())[:10]  # 只显示前10个字段名
        )
        
        try:
            # 检查项目空间，如果是SMBEAP需要特殊处理
            if project_key == "SMBEAP":
                self.logger.warning(
                    "检测到SMBEAP项目，当前版本暂不支持更新SMBEAP空间的Issue",
                    page_id=page_id,
                    issue_key=issue_key
                )
                # TODO: 实现SMBEAP项目的更新逻辑
                # 可能需要不同的配置或客户端
                return
            
            # 构建Notion页面数据
            raw_data = event_data.get("raw_data", {})
            notion_url = raw_data.get('url') or f"https://notion.so/{page_id.replace('-', '')}"
            
            notion_data = {
                'page_id': page_id,
                'properties': event_data.get("properties", {}),
                'raw_properties': event_data.get("raw_properties", {}),
                'raw_data': raw_data,
                'url': notion_url
            }
            
            # 字段映射转换
            jira_fields = await self.field_mapper.map_notion_to_jira(notion_data, notion_url)
            
            # 提取特殊字段（remote links 和 issue links）
            remote_links_data = jira_fields.pop('_remote_links', {})
            issue_links_data = jira_fields.pop('_issue_links', [])
            
            # 计算远程链接总数
            remote_links_count = 0
            if isinstance(remote_links_data, dict):
                remote_links_count = len(remote_links_data.get('original', [])) + len(remote_links_data.get('prd', [])) + len(remote_links_data.get('other', []))
            elif isinstance(remote_links_data, list):
                remote_links_count = len(remote_links_data)  # 向后兼容
            
            self.logger.info(
                "字段映射完成，准备更新JIRA Issue",
                page_id=page_id,
                issue_key=issue_key,
                summary=jira_fields.get('summary'),
                priority=jira_fields.get('priority', {}).get('id'),
                has_assignee=bool(jira_fields.get('assignee')),
                description_length=len(jira_fields.get('description', '')),
                remote_links_count=remote_links_count,
                issue_links_count=len(issue_links_data)
            )
            
            # 移除创建时才需要的字段，用于更新
            update_fields = {k: v for k, v in jira_fields.items() 
                            if k not in ['project', 'issuetype']}
            
            # 更新JIRA Issue
            success = await self.jira_client.update_issue(issue_key, update_fields)
            
            # 处理远程链接
            if remote_links_data:
                try:
                    # 支持新的分类格式和旧格式
                    if isinstance(remote_links_data, dict):
                        remote_links = await self.field_mapper.build_categorized_remote_links(
                            remote_links_data, 
                            jira_fields.get('summary', 'Notion页面')
                        )
                    else:
                        # 向后兼容旧格式
                        remote_links = await self.field_mapper.build_remote_links_from_data_with_titles(
                            remote_links_data, 
                            jira_fields.get('summary', 'Notion页面')
                        )
                    
                    # 同步远程链接（包括删除不需要的链接）
                    success = await self.jira_client.sync_remote_links(
                        issue_key, 
                        remote_links if remote_links else []
                    )
                    
                    if success:
                        link_count = len(remote_links) if remote_links else 0
                        self.logger.info(
                            "更新操作中远程链接同步成功",
                            page_id=page_id,
                            issue_key=issue_key,
                            link_count=link_count
                        )
                    else:
                        self.logger.warning(
                            "更新操作中远程链接同步失败",
                            page_id=page_id,
                            issue_key=issue_key
                        )
                            
                except Exception as link_e:
                    self.logger.error(
                        "更新操作中创建远程链接异常",
                        page_id=page_id,
                        issue_key=issue_key,
                        error=str(link_e)
                    )
                    # 远程链接创建失败不影响主流程
            
            # 处理JIRA issue链接
            if issue_links_data:
                try:
                    # 使用"Relates"类型的链接（ID: 10003）
                    success_count = await self.jira_client.create_issue_links(
                        issue_key,
                        issue_links_data,
                        "10003"  # Relates类型
                    )
                    
                    if success_count > 0:
                        self.logger.info(
                            "更新操作中JIRA issue链接创建成功",
                            page_id=page_id,
                            issue_key=issue_key,
                            success_count=success_count,
                            total_count=len(issue_links_data)
                        )
                    else:
                        self.logger.warning(
                            "更新操作中JIRA issue链接创建失败",
                            page_id=page_id,
                            issue_key=issue_key,
                            issue_keys=issue_links_data
                        )
                        
                except Exception as issue_link_e:
                    self.logger.error(
                        "更新操作中创建JIRA issue链接异常",
                        page_id=page_id,
                        issue_key=issue_key,
                        error=str(issue_link_e)
                    )
                    # JIRA issue链接创建失败不影响主流程
            
            if success:
                # 更新映射关系的同步时间
                existing_mapping = await self.redis_client.get_sync_mapping(page_id)
                if existing_mapping:
                    existing_mapping['last_sync'] = datetime.now().isoformat()
                    await self.redis_client.set_sync_mapping(page_id, existing_mapping)
                
                # 回写Notion状态（更新操作也需要回写）
                if self.notion_client:
                    try:
                        # 更新页面状态为"JIRA Wait Review"
                        await self.notion_client.update_status(page_id, "TODO")
                        self.logger.info(
                            "更新操作Notion状态回写完成",
                            page_id=page_id,
                            issue_key=issue_key
                        )
                    except Exception as e:
                        self.logger.error(
                            "更新操作Notion状态回写失败",
                            page_id=page_id,
                            issue_key=issue_key,
                            error=str(e)
                        )
                        # 回写失败不影响主流程
                
                self.logger.info(
                    "JIRA Issue更新完成",
                    page_id=page_id,
                    issue_key=issue_key,
                    summary=update_fields.get('summary')
                )
            else:
                raise Exception(f"JIRA Issue更新失败: {issue_key}")
            
        except Exception as e:
            self.logger.error("更新JIRA Issue失败", page_id=page_id, issue_key=issue_key, error=str(e))
            raise
    
    async def _write_back_to_notion(self, page_id: str, jira_result: Dict[str, Any]):
        """回写JIRA信息到Notion"""
        if not self.notion_client:
            self.logger.warning("未配置Notion客户端，跳过回写操作")
            return
        
        try:
            # 1. 更新JIRA Card URL字段
            jira_browse_url = jira_result.get('browse_url')
            if jira_browse_url:
                await self.notion_client.update_jira_card_url(page_id, jira_browse_url)
            
            # 2. 更新页面状态为"JIRA Wait Review"
            await self.notion_client.update_status(page_id, "TODO")
            
            self.logger.info(
                "Notion回写完成",
                page_id=page_id,
                jira_url=jira_browse_url
            )
        except Exception as e:
            self.logger.error(
                "Notion回写失败",
                page_id=page_id,
                error=str(e)
            )
            # 回写失败不影响主流程，只记录错误
    
    async def _handle_jira_to_notion_update(self, message: Dict[str, Any], event_data: Dict[str, Any]):
        """处理JIRA到Notion的更新同步"""
        jira_issue_key = event_data.get("jira_issue_key")
        
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