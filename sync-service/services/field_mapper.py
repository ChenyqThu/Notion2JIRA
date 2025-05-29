"""
字段映射引擎模块
负责Notion和JIRA之间的字段映射转换
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger
from services.version_mapper import VersionMapper
from services.notion_version_cache import NotionVersionCache


class FieldMapper:
    """字段映射引擎"""
    
    def __init__(self, settings: Settings, notion_client=None):
        self.settings = settings
        self.logger = get_logger("field_mapper")
        self.notion_client = notion_client
        
        # 初始化版本映射器
        self.version_mapper = VersionMapper(settings)
        
        # 初始化Notion版本缓存
        self.notion_version_cache = NotionVersionCache(settings, notion_client)
        
        # 状态映射表（Notion状态 -> JIRA状态）
        self.status_mapping = {
            "初始反馈 OR": "待可行性评估",
            "待评估 UR": "待可行性评估", 
            "待输入 WI": "TODO",
            "同步中 SYNC": "TODO",
            "已输入 JIRA": "TODO",
            "PRD Done": "TODO",
            "UI Done": "TODO", 
            "UX Done": "TODO",
            "DEVING": "开发中",
            "DELAYED": "开发中",
            "Testing": "Testing（测试）",
            "已发布 DONE": "完成",
            "重复 DUMP": "完成",
            "无效 INVALID": "完成",
            "暂不支持 PENDING": "完成",
            "无法支持 BAN": "完成"
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
            versions = await self._extract_version(notion_data)
            if versions:
                jira_fields['fixVersions'] = versions
            
            # 映射状态（如果需要的话，JIRA创建时通常不需要设置状态）
            status = self._extract_status(notion_data)
            if status and status in self.status_mapping:
                # 注意：JIRA创建Issue时通常不直接设置状态，而是通过工作流转换
                # 这里记录状态信息，但不添加到jira_fields中
                self.logger.debug(f"检测到状态: {status} -> {self.status_mapping[status]}")
            
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
        
        # 记录可用的字段名用于调试
        available_fields = list(properties.keys())
        self.logger.debug(f"可用的属性字段: {available_fields}")
        
        # 尝试多种可能的标题字段名（按优先级排序）
        title_fields = ['功能 Name', 'title', 'name', 'Title', 'Name', '需求名']
        
        for field_name in title_fields:
            if field_name in properties:
                field_data = properties[field_name]
                self.logger.debug(f"找到标题字段 '{field_name}': {field_data}")
                
                # 处理webhook-server处理后的格式（包含value字段）
                if isinstance(field_data, dict) and 'value' in field_data:
                    title = field_data['value']
                    if isinstance(title, str) and title.strip():
                        self.logger.debug(f"提取到标题(value): {title}")
                        return title
                
                # 处理原始Notion API格式（title类型）
                elif isinstance(field_data, dict) and 'title' in field_data:
                    title_array = field_data['title']
                    if title_array and len(title_array) > 0:
                        title = title_array[0].get('plain_text', '')
                        if title.strip():  # 确保标题不为空
                            self.logger.debug(f"提取到标题(title): {title}")
                            return title
                
                # 处理rich_text类型（有些标题可能存储为rich_text）
                elif isinstance(field_data, dict) and 'rich_text' in field_data:
                    rich_text_array = field_data['rich_text']
                    if rich_text_array and len(rich_text_array) > 0:
                        title = ''.join([item.get('plain_text', '') for item in rich_text_array])
                        if title.strip():
                            self.logger.debug(f"提取到标题(rich_text): {title}")
                            return title
                
                # 处理字符串类型
                elif isinstance(field_data, str) and field_data.strip():
                    self.logger.debug(f"提取到标题(字符串): {field_data}")
                    return field_data
                
                # 记录字段数据结构用于调试
                self.logger.debug(f"字段 '{field_name}' 数据结构: {type(field_data)}, 内容: {field_data}")
        
        # 如果没找到预期的字段，尝试查找任何title类型的字段
        for field_name, field_data in properties.items():
            if isinstance(field_data, dict):
                # 检查webhook-server格式
                if 'value' in field_data and 'type' in field_data and field_data['type'] == 'title':
                    title = field_data['value']
                    if isinstance(title, str) and title.strip():
                        self.logger.info(f"在字段 '{field_name}' 中找到标题(value): {title}")
                        return title
                
                # 检查原始格式
                elif 'title' in field_data:
                    title_array = field_data['title']
                    if title_array and len(title_array) > 0:
                        title = title_array[0].get('plain_text', '')
                        if title.strip():  # 确保标题不为空
                            self.logger.info(f"在字段 '{field_name}' 中找到标题(title): {title}")
                            return title
        
        # 如果仍然找不到标题，尝试生成一个默认标题
        page_id = notion_data.get('page_id', 'unknown')
        
        # 尝试从其他字段组合生成标题
        scenario = self._extract_field_value(properties, ['需求场景 Scenario'])
        if scenario and isinstance(scenario, (str, list)):
            scenario_text = scenario if isinstance(scenario, str) else ', '.join(scenario) if scenario else ''
            if scenario_text.strip():
                default_title = f"需求: {scenario_text[:50]}..." if len(scenario_text) > 50 else f"需求: {scenario_text}"
                self.logger.info(f"使用需求场景生成默认标题: {default_title}")
                return default_title
        
        # 尝试使用功能说明作为标题
        desc = self._extract_field_value(properties, ['功能说明 Desc'])
        if desc and isinstance(desc, str) and desc.strip():
            default_title = f"功能: {desc[:50]}..." if len(desc) > 50 else f"功能: {desc}"
            self.logger.info(f"使用功能说明生成默认标题: {default_title}")
            return default_title
        
        # 最后使用页面ID生成标题
        default_title = f"Notion页面 {page_id[:8]}"
        self.logger.warning(f"未找到合适的标题字段，使用默认标题: {default_title}")
        self.logger.warning(f"可用字段: {available_fields}")
        return default_title
    
    def _build_description(self, notion_data: Dict[str, Any], page_url: str = None) -> str:
        """构建描述字段（组合多个字段）"""
        description_parts = []
        properties = notion_data.get('properties', {})
        
        # 功能说明
        func_desc = self._extract_field_value(properties, ['功能说明 Desc', 'description', 'Description'])
        if func_desc and isinstance(func_desc, str):
            description_parts.append(f"## 需求说明\n{func_desc}")
        
        # 移除AI整理部分 - 不在JIRA中显示
        # ai_summary = self._extract_field_value(properties, ['需求整理', 'ai_summary', 'AI整理'])
        # if ai_summary and isinstance(ai_summary, str):
        #     description_parts.append(f"## 需求整理(AI)\n{ai_summary}")
        
        # 原始需求链接
        # 优先使用raw_data中的URL
        raw_data = notion_data.get('raw_data', {})
        notion_url = raw_data.get('url') or page_url or notion_data.get('url')
        if notion_url:
            description_parts.append(f"## 原始需求链接\n{notion_url}")
        
        return '\n\n'.join(description_parts) if description_parts else "无详细描述"
    
    def _extract_field_value(self, properties: Dict[str, Any], field_names: List[str]) -> Optional[Any]:
        """通用字段值提取方法，支持webhook-server和原始Notion格式"""
        for field_name in field_names:
            if field_name in properties:
                field_data = properties[field_name]
                
                # 处理webhook-server处理后的格式（包含value字段）
                if isinstance(field_data, dict) and 'value' in field_data:
                    return field_data['value']
                
                # 处理原始Notion API格式
                elif isinstance(field_data, dict):
                    # rich_text类型
                    if 'rich_text' in field_data:
                        rich_text_array = field_data['rich_text']
                        if rich_text_array and len(rich_text_array) > 0:
                            return ''.join([item.get('plain_text', '') for item in rich_text_array])
                    
                    # select类型
                    elif 'select' in field_data:
                        select_data = field_data['select']
                        if select_data and 'name' in select_data:
                            return select_data['name']
                    
                    # multi_select类型
                    elif 'multi_select' in field_data:
                        multi_select_array = field_data['multi_select']
                        if multi_select_array:
                            return [item.get('name', '') for item in multi_select_array]
                    
                    # status类型
                    elif 'status' in field_data:
                        status_data = field_data['status']
                        if status_data and 'name' in status_data:
                            return status_data['name']
                    
                    # people类型
                    elif 'people' in field_data:
                        people_array = field_data['people']
                        if people_array and len(people_array) > 0:
                            return people_array[0]
                    
                    # title类型
                    elif 'title' in field_data:
                        title_array = field_data['title']
                        if title_array and len(title_array) > 0:
                            return title_array[0].get('plain_text', '')
                    
                    # relation类型
                    elif 'relation' in field_data:
                        relation_array = field_data['relation']
                        if relation_array and len(relation_array) > 0:
                            return relation_array  # 返回整个关联数组
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    def _extract_priority(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取优先级字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的优先级字段名（按优先级排序）
        priority_fields = ['优先级 P', 'priority', 'Priority', '优先级']
        
        priority_value = self._extract_field_value(properties, priority_fields)
        if isinstance(priority_value, str):
            return priority_value
        
        return None
    
    async def _extract_assignee(self, notion_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """提取分配人员字段 - 统一设置为鲁定阳"""
        # 统一设置经办人为鲁定阳，使用用户名而不是邮箱
        return {'name': 'ludingyang@tp-link.com.hk'}
    
    async def _extract_version(self, notion_data: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
        """提取版本字段"""
        properties = notion_data.get('properties', {})
        
        # 首先尝试从关联项目字段获取版本信息
        version_name = await self._extract_version_from_relation(properties)
        
        if not version_name:
            # 如果关联项目没有版本信息，尝试其他版本字段
            version_fields = ['计划版本', 'version', 'Version', 'fixVersion']
            version_value = self._extract_field_value(properties, version_fields)
            
            if version_value:
                # 处理多选版本（计划版本字段通常是multi_select）
                if isinstance(version_value, list) and len(version_value) > 0:
                    # 检查是否是字符串列表（multi_select）
                    if isinstance(version_value[0], str):
                        version_name = version_value[0]
                    # 检查是否是关联对象列表（relation）
                    elif isinstance(version_value[0], dict) and 'id' in version_value[0]:
                        # 这是relation类型，需要特殊处理
                        version_name = await self._get_relation_page_name(version_value[0]['id'])
                # 处理单个版本
                elif isinstance(version_value, str) and version_value.strip():
                    version_name = version_value
        
        if version_name:
            self.logger.info(f"提取到版本名称: {version_name}")
            version_id = await self.version_mapper.get_jira_version_id(version_name)
            return [{'id': version_id}]
        
        # 如果没有找到版本信息，使用默认版本
        self.logger.warning("未找到版本信息，使用默认版本")
        return [{'id': self.settings.jira.default_version_id}]
    
    async def _extract_version_from_relation(self, properties: Dict[str, Any]) -> Optional[str]:
        """从关联项目字段提取版本信息"""
        try:
            # 查找关联项目字段
            relation_fields = ['关联项目', 'related_project', 'project_relation']
            
            for field_name in relation_fields:
                if field_name in properties:
                    field_data = properties[field_name]
                    
                    # 处理webhook-server格式
                    if isinstance(field_data, dict) and 'value' in field_data:
                        relation_data = field_data['value']
                    # 处理原始Notion格式
                    elif isinstance(field_data, dict) and 'relation' in field_data:
                        relation_data = field_data['relation']
                    else:
                        continue
                    
                    # 检查是否有关联的页面
                    if isinstance(relation_data, list) and len(relation_data) > 0:
                        # 获取第一个关联页面的ID
                        if isinstance(relation_data[0], dict):
                            related_page_id = relation_data[0].get('id')
                        elif isinstance(relation_data[0], str):
                            related_page_id = relation_data[0]
                        else:
                            continue
                        
                        if related_page_id:
                            self.logger.info(f"找到关联项目页面ID: {related_page_id}")
                            
                            # 使用版本缓存获取版本名称
                            version_name = await self.notion_version_cache.get_version_name(related_page_id)
                            if version_name:
                                self.logger.info(f"从关联项目页面提取到版本名称: {version_name}")
                                return version_name
                            
            return None
            
        except Exception as e:
            self.logger.error(f"从关联项目提取版本信息失败: {str(e)}")
            return None
    
    async def _get_relation_page_name(self, page_id: str) -> Optional[str]:
        """获取关联页面的名称"""
        try:
            # 如果有Notion客户端，尝试获取关联页面的信息
            if self.notion_client:
                try:
                    # 获取关联页面的详细信息
                    related_page = await self.notion_client.get_page(page_id)
                    if related_page and 'properties' in related_page:
                        # 从关联页面提取版本信息
                        related_properties = related_page['properties']
                        
                        # 尝试从关联页面的标题或名称字段获取版本信息
                        version_name = self._extract_field_value(related_properties, 
                                                                ['Name', 'name', '名称', 'title'])
                        if version_name and isinstance(version_name, str):
                            return version_name
                        
                        # 尝试从版本字段获取
                        version_name = self._extract_field_value(related_properties, 
                                                                ['版本', 'version', 'Version'])
                        if version_name and isinstance(version_name, str):
                            return version_name
                        
                except Exception as e:
                    self.logger.warning(f"获取关联页面信息失败: {str(e)}")
            
            # 如果无法获取关联页面详情，返回None
            self.logger.warning(f"无法获取关联页面详情，页面ID: {page_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"获取关联页面名称失败: {str(e)}")
            return None
    
    def _extract_status(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取状态字段"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的状态字段名
        status_fields = ['Status', 'status', '状态']
        
        status_value = self._extract_field_value(properties, status_fields)
        if isinstance(status_value, str):
            return status_value
        
        return None
    
    def validate_required_fields(self, jira_fields: Dict[str, Any]) -> List[str]:
        """验证必填字段"""
        required_fields = ['project', 'issuetype', 'summary']
        missing_fields = []
        
        for field in required_fields:
            if field not in jira_fields or not jira_fields[field]:
                missing_fields.append(field)
        
        return missing_fields 