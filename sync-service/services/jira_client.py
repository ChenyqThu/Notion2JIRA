"""
JIRA API客户端模块
负责与JIRA系统进行API交互
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import Settings, JiraConfig
from config.logger import get_logger


class JiraClient:
    """JIRA API客户端"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jira_config = settings.jira
        self.logger = get_logger("jira_client")
        self.session = None
        
        # 缓存项目元数据
        self._project_metadata = None
        self._users_cache = {}
        
    async def initialize(self):
        """初始化JIRA客户端"""
        try:
            self.logger.info("正在初始化JIRA客户端...")
            
            # 创建HTTP会话
            connector = aiohttp.TCPConnector(
                verify_ssl=False,  # 内网环境通常不验证SSL
                limit=10,
                limit_per_host=5
            )
            
            timeout = aiohttp.ClientTimeout(total=self.jira_config.timeout)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                auth=aiohttp.BasicAuth(
                    self.jira_config.username,
                    self.jira_config.password
                ),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            # 测试连接并获取项目元数据
            await self._load_project_metadata()
            
            self.logger.info("JIRA客户端初始化完成")
            
        except Exception as e:
            self.logger.error("JIRA客户端初始化失败", error=str(e))
            raise
    
    async def close(self):
        """关闭JIRA客户端"""
        if self.session:
            await self.session.close()
            self.logger.info("JIRA客户端已关闭")
    
    async def create_issue(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """创建JIRA Issue"""
        try:
            self.logger.info("开始创建JIRA Issue", summary=fields.get('summary'))
            
            # 构建请求数据
            payload = {
                'fields': fields
            }
            
            # 发送创建请求
            url = f"{self.jira_config.base_url}/rest/api/2/issue"
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    result = await response.json()
                    issue_key = result.get('key')
                    issue_id = result.get('id')
                    
                    # 构建完整的返回结果，包含正确的browse URL
                    result['browse_url'] = f"{self.jira_config.base_url}/browse/{issue_key}"
                    
                    self.logger.info(
                        "JIRA Issue创建成功",
                        issue_key=issue_key,
                        issue_id=issue_id,
                        browse_url=result['browse_url'],
                        summary=fields.get('summary')
                    )
                    
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "JIRA Issue创建失败",
                        status=response.status,
                        error=error_text,
                        summary=fields.get('summary')
                    )
                    raise Exception(f"创建Issue失败: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error("创建JIRA Issue异常", error=str(e), summary=fields.get('summary'))
            raise
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """获取JIRA Issue详情"""
        try:
            url = f"{self.jira_config.base_url}/rest/api/2/issue/{issue_key}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"获取Issue失败: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error("获取JIRA Issue异常", error=str(e), issue_key=issue_key)
            raise
    
    async def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """更新JIRA Issue"""
        try:
            payload = {
                'fields': fields
            }
            
            url = f"{self.jira_config.base_url}/rest/api/2/issue/{issue_key}"
            
            async with self.session.put(url, json=payload) as response:
                if response.status == 204:
                    self.logger.info("JIRA Issue更新成功", issue_key=issue_key)
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "JIRA Issue更新失败",
                        issue_key=issue_key,
                        status=response.status,
                        error=error_text
                    )
                    return False
                    
        except Exception as e:
            self.logger.error("更新JIRA Issue异常", error=str(e), issue_key=issue_key)
            raise
    
    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """搜索JIRA用户"""
        try:
            # 先检查缓存
            if query in self._users_cache:
                return self._users_cache[query]
            
            url = f"{self.jira_config.base_url}/rest/api/2/user/search"
            params = {
                'query': query,
                'maxResults': 10
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    users = await response.json()
                    # 缓存结果
                    self._users_cache[query] = users
                    return users
                else:
                    self.logger.warning("搜索用户失败", query=query, status=response.status)
                    return []
                    
        except Exception as e:
            self.logger.error("搜索用户异常", error=str(e), query=query)
            return []
    
    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱查找用户"""
        users = await self.search_users(email)
        for user in users:
            if user.get('emailAddress', '').lower() == email.lower():
                return user
        return None
    
    async def _load_project_metadata(self):
        """加载项目元数据"""
        try:
            self.logger.info("正在加载项目元数据", project_key=self.jira_config.project_key)
            
            # 获取项目信息
            project_url = f"{self.jira_config.base_url}/rest/api/2/project/{self.jira_config.project_key}"
            
            async with self.session.get(project_url) as response:
                if response.status == 200:
                    project_info = await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"获取项目信息失败: {response.status} - {error_text}")
            
            # 获取创建元数据
            meta_url = f"{self.jira_config.base_url}/rest/api/2/issue/createmeta"
            params = {
                'projectKeys': self.jira_config.project_key,
                'expand': 'projects.issuetypes.fields'
            }
            
            async with self.session.get(meta_url, params=params) as response:
                if response.status == 200:
                    create_meta = await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"获取创建元数据失败: {response.status} - {error_text}")
            
            self._project_metadata = {
                'project': project_info,
                'create_meta': create_meta,
                'loaded_at': datetime.now()
            }
            
            self.logger.info(
                "项目元数据加载完成",
                project_name=project_info.get('name'),
                project_key=project_info.get('key'),
                issue_types_count=len(create_meta.get('projects', [{}])[0].get('issuetypes', []))
            )
            
        except Exception as e:
            self.logger.error("加载项目元数据失败", error=str(e))
            raise
    
    def get_project_metadata(self) -> Optional[Dict[str, Any]]:
        """获取项目元数据"""
        return self._project_metadata
    
    def get_default_fields(self) -> Dict[str, Any]:
        """获取默认字段配置"""
        return {
            'project': {'id': self.jira_config.project_id},
            'issuetype': {'id': self.jira_config.default_issue_type_id},
            'fixVersions': [{'id': self.jira_config.default_version_id}]
        }
    
    async def test_connection(self) -> bool:
        """测试JIRA连接"""
        try:
            url = f"{self.jira_config.base_url}/rest/api/2/myself"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    user_info = await response.json()
                    self.logger.info(
                        "JIRA连接测试成功",
                        user=user_info.get('displayName'),
                        email=user_info.get('emailAddress')
                    )
                    return True
                else:
                    self.logger.error("JIRA连接测试失败", status=response.status)
                    return False
                    
        except Exception as e:
            self.logger.error("JIRA连接测试异常", error=str(e))
            return False 