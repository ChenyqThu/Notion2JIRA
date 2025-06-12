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
            # 确保fixVersions字段的ID为字符串格式
            if 'fixVersions' in fields and fields['fixVersions']:
                for version in fields['fixVersions']:
                    if 'id' in version:
                        version['id'] = str(version['id'])  # 确保ID为字符串
            
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
                    project_data = await response.json()
                    
                    self._project_metadata = {
                        'project': project_data,
                        'issue_types': project_data.get('issueTypes', [])
                    }
                    
                    self.logger.info(
                        "项目元数据加载完成",
                        project_name=project_data.get('name'),
                        project_key=project_data.get('key'),
                        issue_types_count=len(self._project_metadata['issue_types'])
                    )
                else:
                    raise Exception(f"获取项目信息失败: {response.status}")
                    
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
            'fixVersions': [{'id': str(self.jira_config.default_version_id)}]  # 确保ID为字符串
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
    
    async def get_project_versions(self, project_key: str = None) -> List[Dict[str, Any]]:
        """获取项目版本列表"""
        try:
            if not project_key:
                project_key = self.jira_config.project_key
            
            url = f"{self.jira_config.base_url}/rest/api/2/project/{project_key}/versions"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    versions = await response.json()
                    self.logger.info("项目版本获取成功", project_key=project_key, version_count=len(versions))
                    return versions
                else:
                    error_text = await response.text()
                    self.logger.error("获取项目版本失败", project_key=project_key, status=response.status, error=error_text)
                    return []
                    
        except Exception as e:
            self.logger.error("获取项目版本异常", error=str(e), project_key=project_key)
            return []
    
    async def get_existing_remote_links(self, issue_key: str) -> List[Dict[str, Any]]:
        """获取Issue的现有Remote Links"""
        try:
            url = f"{self.jira_config.base_url}/rest/api/2/issue/{issue_key}/remotelink"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    links = await response.json()
                    self.logger.debug(f"获取到 {len(links)} 个现有Remote Links", issue_key=issue_key)
                    return links
                else:
                    error_text = await response.text()
                    self.logger.warning(
                        "获取现有Remote Links失败",
                        issue_key=issue_key,
                        status=response.status,
                        error=error_text
                    )
                    return []
                    
        except Exception as e:
            self.logger.error("获取现有Remote Links异常", error=str(e), issue_key=issue_key)
            return []
    
    async def create_remote_issue_link(self, issue_key: str, remote_link: Dict[str, Any]) -> bool:
        """为JIRA Issue创建单个远程链接"""
        try:
            if not remote_link:
                self.logger.debug("没有远程链接需要创建", issue_key=issue_key)
                return True
                
            self.logger.info(
                "开始创建远程链接",
                issue_key=issue_key,
                link_title=remote_link.get('object', {}).get('title', 'Unknown')
            )
            
            url = f"{self.jira_config.base_url}/rest/api/2/issue/{issue_key}/remotelink"
            
            async with self.session.post(url, json=remote_link) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    status_text = "更新" if response.status == 200 else "创建"
                    self.logger.info(
                        f"远程链接{status_text}成功",
                        issue_key=issue_key,
                        link_id=result.get('id'),
                        link_title=remote_link.get('object', {}).get('title', 'Unknown')
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "远程链接创建失败",
                        issue_key=issue_key,
                        status=response.status,
                        error=error_text,
                        link_title=remote_link.get('object', {}).get('title', 'Unknown')
                    )
                    return False
            
        except Exception as e:
            self.logger.error("创建远程链接异常", error=str(e), issue_key=issue_key)
            return False
    
    async def create_or_update_remote_links(self, issue_key: str, remote_links: List[Dict[str, Any]]) -> bool:
        """创建或更新多个远程链接（支持基于globalId的更新）"""
        try:
            if not remote_links:
                self.logger.debug("没有远程链接需要创建", issue_key=issue_key)
                return True
                
            self.logger.info(
                "开始创建/更新远程链接",
                issue_key=issue_key,
                link_count=len(remote_links)
            )
            
            success_count = 0
            for remote_link in remote_links:
                # 使用globalId来支持更新功能
                # 如果提供了globalId，JIRA会自动判断是创建还是更新
                success = await self.create_remote_issue_link(issue_key, remote_link)
                if success:
                    success_count += 1
            
            self.logger.info(
                "远程链接创建/更新完成",
                issue_key=issue_key,
                success_count=success_count,
                total_count=len(remote_links)
            )
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error("创建/更新远程链接异常", error=str(e), issue_key=issue_key)
            return False
    
    async def create_remote_issue_links(self, issue_key: str, remote_links: List[Dict[str, Any]]) -> bool:
        """为JIRA Issue创建多个远程链接（保持兼容性）"""
        return await self.create_or_update_remote_links(issue_key, remote_links)
    
    async def get_issue_link_types(self) -> List[Dict[str, Any]]:
        """获取JIRA支持的issue link types"""
        try:
            url = f"{self.jira_config.base_url}/rest/api/2/issueLinkType"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    link_types = result.get('issueLinkTypes', [])
                    self.logger.info(f"获取到 {len(link_types)} 个issue link types")
                    return link_types
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "获取issue link types失败",
                        status=response.status,
                        error=error_text
                    )
                    return []
                    
        except Exception as e:
            self.logger.error("获取issue link types异常", error=str(e))
            return []
    
    async def create_issue_link(self, from_issue_key: str, to_issue_key: str, 
                               link_type_id: str = "10003") -> bool:
        """创建issue之间的链接关系"""
        try:
            self.logger.info(
                "开始创建issue链接",
                from_issue=from_issue_key,
                to_issue=to_issue_key,
                link_type_id=link_type_id
            )
            
            payload = {
                "type": {
                    "id": link_type_id
                },
                "inwardIssue": {
                    "key": to_issue_key
                },
                "outwardIssue": {
                    "key": from_issue_key
                }
            }
            
            url = f"{self.jira_config.base_url}/rest/api/2/issueLink"
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    self.logger.info(
                        "issue链接创建成功",
                        from_issue=from_issue_key,
                        to_issue=to_issue_key,
                        link_type_id=link_type_id
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "issue链接创建失败",
                        from_issue=from_issue_key,
                        to_issue=to_issue_key,
                        status=response.status,
                        error=error_text
                    )
                    return False
            
        except Exception as e:
            self.logger.error(
                "创建issue链接异常",
                error=str(e),
                from_issue=from_issue_key,
                to_issue=to_issue_key
            )
            return False
    
    async def create_issue_links(self, from_issue_key: str, to_issue_keys: List[str], 
                                link_type_id: str = "10003") -> int:
        """批量创建issue链接关系"""
        try:
            if not to_issue_keys:
                self.logger.debug("没有需要创建的issue链接", from_issue=from_issue_key)
                return 0
                
            self.logger.info(
                "开始批量创建issue链接",
                from_issue=from_issue_key,
                to_issues_count=len(to_issue_keys),
                link_type_id=link_type_id
            )
            
            success_count = 0
            for to_issue_key in to_issue_keys:
                success = await self.create_issue_link(from_issue_key, to_issue_key, link_type_id)
                if success:
                    success_count += 1
            
            self.logger.info(
                "批量issue链接创建完成",
                from_issue=from_issue_key,
                success_count=success_count,
                total_count=len(to_issue_keys)
            )
            
            return success_count
            
        except Exception as e:
            self.logger.error(
                "批量创建issue链接异常",
                error=str(e),
                from_issue=from_issue_key
            )
            return 0
    
    def extract_jira_issue_keys(self, text: str) -> List[str]:
        """从文本中提取JIRA issue keys"""
        import re
        
        if not text:
            return []
        
        # JIRA issue key 模式：项目前缀-数字
        # 例如：SMBNET-123, ABC-456
        pattern = r'\b([A-Z]+)-(\d+)\b'
        matches = re.findall(pattern, text)
        
        issue_keys = [f"{prefix}-{number}" for prefix, number in matches]
        
        if issue_keys:
            self.logger.info(f"从文本中提取到 {len(issue_keys)} 个JIRA issue keys: {issue_keys}")
        
        return issue_keys 