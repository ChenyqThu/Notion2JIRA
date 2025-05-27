"""
字段映射引擎模块
负责Notion和JIRA之间的字段映射转换
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger


class FieldMapper:
    """字段映射引擎"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("field_mapper")
        
        # 状态映射表
        self.status_mapping = {
            "初始反馈 OR": "待可行性评估",
            "待评估 UR": "待可行性评估", 
            "待输入 WI": "TODO",
            "同步中 SYNC": "TODO",
            "已输入 JIRA": "TODO",
            "DEVING": "开发中",
            "Testing": "Testing（测试）",
            "已发布 DONE": "完成"
        }
        
        # 优先级映射表
        self.priority_mapping = {
            "高 High": {"id": "1"},
            "中 Medium": {"id": "3"},
            "低 Low": {"id": "4"},
            "无 None": {"id": "5"}
        }
    
    async def map_notion_to_jira(self, notion_data: Dict[str, Any], page_url: str = None) -> Dict[str, Any]:
        """将Notion数据映射为JIRA字段"""
        try:
            self.logger.info("开始字段映射转换", page_id=notion_data.get('page_id'))
            
            # 获取基础字段
            jira_fields = {
                'project': {'id': self.settings.jira.project_id},
                'issuetype': {'id': self.settings.jira.default_issue_type_id},
                'fixVersions': [{'id': self.settings.jira.default_version_id}]
            }
            
            # 映射标题
            title = self._extract_title(notion_data)
            if title:
                jira_fields['summary'] = title
            else:
                raise ValueError("缺少必需的标题字段")
            
            # 映射描述（组合多个字段）
            description = self._build_description(notion_data, page_url)
            if description:
                jira_fields['description'] = description
            
            # 映射优先级
            priority = self._extract_priority(notion_data)
            if priority and priority in self.priority_mapping:
                jira_fields['priority'] = self.priority_mapping[priority]
            
            # 映射分配人员
            assignee = await self._extract_assignee(notion_data)
            if assignee:
                jira_fields['assignee'] = assignee
            
            # 映射版本信息
            version = self._extract_version(notion_data)
            if version:
                jira_fields['fixVersions'] = [version]
            
            self.logger.info(
                "字段映射转换完成",
                page_id=notion_data.get('page_id'),
                summary=jira_fields.get('summary'),
                priority=jira_fields.get('priority', {}).get('id'),
                has_assignee=bool(jira_fields.get('assignee')),
                description_length=len(jira_fields.get('description', ''))
            )
            
            return jira_fields
            
        except Exception as e:
            self.logger.error("字段映射转换失败", error=str(e), page_id=notion_data.get('page_id'))
            raise
    
    def _extract_title(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取标题字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的标题字段名
        title_fields = ['功能 Name', 'title', 'name', 'Title', 'Name']
        
        for field_name in title_fields:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理title类型
                if isinstance(field_data, dict) and 'title' in field_data:
                    title_array = field_data['title']
                    if title_array and len(title_array) > 0:
                        return title_array[0].get('plain_text', '')
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    def _build_description(self, notion_data: Dict[str, Any], page_url: str = None) -> str:
        """构建描述字段（组合多个字段）"""
        description_parts = []
        properties = notion_data.get('properties', {})
        
        # 功能说明
        func_desc = self._extract_rich_text_field(properties, ['功能说明 Desc', 'description', 'Description'])
        if func_desc:
            description_parts.append(f"## 需求说明\n{func_desc}")
        
        # AI整理
        ai_summary = self._extract_rich_text_field(properties, ['需求整理', 'ai_summary', 'AI整理'])
        if ai_summary:
            description_parts.append(f"## 需求整理(AI)\n{ai_summary}")
        
        # 原始需求链接
        if page_url:
            description_parts.append(f"## 原始需求链接\n{page_url}")
        elif notion_data.get('url'):
            description_parts.append(f"## 原始需求链接\n{notion_data['url']}")
        
        return '\n\n'.join(description_parts) if description_parts else "无详细描述"
    
    def _extract_rich_text_field(self, properties: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """提取富文本字段"""
        for field_name in field_names:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理rich_text类型
                if isinstance(field_data, dict) and 'rich_text' in field_data:
                    rich_text_array = field_data['rich_text']
                    if rich_text_array and len(rich_text_array) > 0:
                        return ''.join([item.get('plain_text', '') for item in rich_text_array])
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    def _extract_priority(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取优先级字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的优先级字段名
        priority_fields = ['优先级 P', 'priority', 'Priority']
        
        for field_name in priority_fields:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理select类型
                if isinstance(field_data, dict) and 'select' in field_data:
                    select_data = field_data['select']
                    if select_data and 'name' in select_data:
                        return select_data['name']
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    async def _extract_assignee(self, notion_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """提取分配人员字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的分配人员字段名
        assignee_fields = ['需求录入', 'assignee', 'Assignee', '分配人员']
        
        for field_name in assignee_fields:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理people类型
                if isinstance(field_data, dict) and 'people' in field_data:
                    people_array = field_data['people']
                    if people_array and len(people_array) > 0:
                        person = people_array[0]
                        
                        # 尝试获取邮箱
                        email = person.get('person', {}).get('email')
                        if email:
                            # 这里应该调用JiraClient来查找用户
                            # 为了简化，先返回邮箱格式
                            return {'name': email}
                        
                        # 如果没有邮箱，使用名称
                        name = person.get('name')
                        if name:
                            return {'name': name}
        
        return None
    
    def _extract_version(self, notion_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """提取版本字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的版本字段名
        version_fields = ['关联项目', 'version', 'Version', 'fixVersion']
        
        for field_name in version_fields:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理relation类型
                if isinstance(field_data, dict) and 'relation' in field_data:
                    relation_array = field_data['relation']
                    if relation_array and len(relation_array) > 0:
                        # 这里需要根据关联的项目信息来确定版本
                        # 暂时使用默认版本
                        return {'id': self.settings.jira.default_version_id}
                
                # 处理select类型
                elif isinstance(field_data, dict) and 'select' in field_data:
                    select_data = field_data['select']
                    if select_data and 'name' in select_data:
                        # 根据名称查找对应的版本ID
                        # 暂时使用默认版本
                        return {'id': self.settings.jira.default_version_id}
        
        return None
    
    def _extract_status(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取状态字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的状态字段名
        status_fields = ['Status', 'status', '状态']
        
        for field_name in status_fields:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理status类型
                if isinstance(field_data, dict) and 'status' in field_data:
                    status_data = field_data['status']
                    if status_data and 'name' in status_data:
                        return status_data['name']
                
                # 处理select类型
                elif isinstance(field_data, dict) and 'select' in field_data:
                    select_data = field_data['select']
                    if select_data and 'name' in select_data:
                        return select_data['name']
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    def validate_required_fields(self, jira_fields: Dict[str, Any]) -> List[str]:
        """验证必填字段"""
        required_fields = ['project', 'issuetype', 'summary']
        missing_fields = []
        
        for field in required_fields:
            if field not in jira_fields or not jira_fields[field]:
                missing_fields.append(field)
        
        return missing_fields 