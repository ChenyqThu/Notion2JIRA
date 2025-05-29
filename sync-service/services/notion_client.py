"""
Notion API客户端模块
负责与Notion系统进行API交互，主要用于回写JIRA信息
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger


class NotionClient:
    """Notion API客户端"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.notion_config = settings.notion
        self.logger = get_logger("notion_client")
        self.session = None
        
    async def initialize(self):
        """初始化Notion客户端"""
        try:
            self.logger.info("正在初始化Notion客户端...")
            
            # 创建HTTP会话
            connector = aiohttp.TCPConnector(
                verify_ssl=True,
                limit=10,
                limit_per_host=5
            )
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.notion_config.token}',
                    'Content-Type': 'application/json',
                    'Notion-Version': '2022-06-28'
                }
            )
            
            self.logger.info("Notion客户端初始化完成")
            
        except Exception as e:
            self.logger.error("Notion客户端初始化失败", error=str(e))
            raise
    
    async def close(self):
        """关闭Notion客户端"""
        if self.session:
            await self.session.close()
            self.logger.info("Notion客户端已关闭")
    
    async def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> bool:
        """更新页面属性"""
        try:
            self.logger.info("开始更新Notion页面属性", page_id=page_id)
            
            # 构建请求数据
            payload = {
                'properties': properties
            }
            
            # 发送更新请求
            url = f"https://api.notion.com/v1/pages/{page_id}"
            
            async with self.session.patch(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    self.logger.info(
                        "Notion页面属性更新成功",
                        page_id=page_id,
                        updated_properties=list(properties.keys())
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "Notion页面属性更新失败",
                        page_id=page_id,
                        status=response.status,
                        error=error_text
                    )
                    return False
                    
        except Exception as e:
            self.logger.error("更新Notion页面属性异常", error=str(e), page_id=page_id)
            return False
    
    async def update_jira_card_url(self, page_id: str, jira_browse_url: str) -> bool:
        """更新JIRA Card URL字段"""
        try:
            properties = {
                'JIRA Card': {
                    'url': jira_browse_url
                }
            }
            
            success = await self.update_page_properties(page_id, properties)
            if success:
                self.logger.info(
                    "JIRA Card URL更新成功",
                    page_id=page_id,
                    jira_url=jira_browse_url
                )
            return success
            
        except Exception as e:
            self.logger.error("更新JIRA Card URL异常", error=str(e), page_id=page_id)
            return False
    
    async def update_status(self, page_id: str, status_name: str) -> bool:
        """更新页面状态"""
        try:
            # 状态映射：JIRA状态 -> Notion状态
            status_mapping = {
                "TODO": "已输入 JIRA",
                "开发中": "DEVING", 
                "Testing（测试）": "Testing",
                "完成": "已发布 DONE"
            }
            
            notion_status = status_mapping.get(status_name, "已输入 JIRA")
            
            properties = {
                'Status': {
                    'status': {
                        'name': notion_status
                    }
                }
            }
            
            success = await self.update_page_properties(page_id, properties)
            if success:
                self.logger.info(
                    "页面状态更新成功",
                    page_id=page_id,
                    jira_status=status_name,
                    notion_status=notion_status
                )
            return success
            
        except Exception as e:
            self.logger.error("更新页面状态异常", error=str(e), page_id=page_id)
            return False
    
    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """获取页面信息"""
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "获取Notion页面失败",
                        page_id=page_id,
                        status=response.status,
                        error=error_text
                    )
                    return None
                    
        except Exception as e:
            self.logger.error("获取Notion页面异常", error=str(e), page_id=page_id)
            return None
    
    async def query_database(self, database_id: str, filter_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """查询数据库"""
        try:
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            
            payload = {}
            if filter_data:
                payload['filter'] = filter_data
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "查询Notion数据库失败",
                        database_id=database_id,
                        status=response.status,
                        error=error_text
                    )
                    return None
                    
        except Exception as e:
            self.logger.error("查询Notion数据库异常", error=str(e), database_id=database_id)
            return None
    
    async def test_connection(self) -> bool:
        """测试Notion连接"""
        try:
            # 测试获取用户信息
            url = "https://api.notion.com/v1/users/me"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    user_info = await response.json()
                    self.logger.info(
                        "Notion连接测试成功",
                        user_name=user_info.get('name', 'Unknown'),
                        user_type=user_info.get('type', 'Unknown')
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "Notion连接测试失败",
                        status=response.status,
                        error=error_text
                    )
                    return False
                    
        except Exception as e:
            self.logger.error("Notion连接测试异常", error=str(e))
            return False 