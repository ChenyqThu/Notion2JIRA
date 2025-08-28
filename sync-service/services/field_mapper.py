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
import logging


class UserValidationCache:
    """JIRA用户验证缓存 - 简化版本，不设置过期时间"""
    def __init__(self):
        self._cache = {}  # {email: is_valid} - 永久缓存，miss时更新
        self.logger = get_logger("user_validation_cache")
        
    async def validate_user(self, email: str, jira_client) -> bool:
        """验证用户，带缓存机制"""
        # 检查缓存
        if email in self._cache:
            self.logger.debug(f"缓存命中: {email} -> {self._cache[email]}")
            return self._cache[email]
        
        # 缓存miss，进行实际验证
        try:
            user = await jira_client.find_user_by_email(email)
            is_valid = user is not None
            
            # 更新缓存（永久存储）
            self._cache[email] = is_valid
            self.logger.info(f"用户验证完成: {email} -> {'有效' if is_valid else '无效'}")
            return is_valid
            
        except Exception as e:
            self.logger.error(f"用户验证异常: {email}, 错误: {str(e)}")
            # 验证出错时保守处理，不缓存错误结果
            return True  # 保守处理，假设用户存在
            
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            'total_cached': len(self._cache),
            'valid_users': sum(1 for v in self._cache.values() if v),
            'invalid_users': sum(1 for v in self._cache.values() if not v)
        }


class FieldMapper:
    """字段映射引擎"""
    
    def __init__(self, settings: Settings, jira_client=None, notion_client=None):
        self.settings = settings
        self.jira_client = jira_client
        self.notion_client = notion_client
        self.logger = get_logger("field_mapper")
        
        # 初始化字段映射表
        self.priority_mapping = {
            '高 High': '1',    # Highest
            '中 Medium': '3',  # Medium  
            '低 Low': '4',     # Low
            '无 None': '5'     # Lowest
        }
        
        self.status_mapping = {
            '初始反馈 OR': '待可行性评估',
            '待评估 UR': '待可行性评估', 
            '待输入 WI': 'TODO',
            '同步中 SYNC': 'TODO',
            'JIRA Wait Review': 'TODO',
            'DEVING': '开发中',
            'Testing': 'Testing（测试）',
            '已发布 DONE': '完成'
        }
        
        # 产品线到经办人的映射
        self.product_line_assignee_mapping = {
            'Controller': 'ludingyang@tp-link.com.hk',
            'Gateway': 'zhujiayin@tp-link.com.hk', 
            'Managed Switch': 'huangguangrun@tp-link.com.hk',
            'Unmanaged Switch': 'huangguangrun@tp-link.com.hk',
            'EAP': 'ouhuanrui@tp-link.com.hk',
            'EAP硬件': 'xiexinhua@tp-link.com.hk',
            'OLT': 'fancunlian@tp-link.com.hk',
            'APP': 'xingxiaosong@tp-link.com.hk'
        }
        
        # 默认经办人（其他未命中的产品线）
        self.default_assignee = 'ludingyang@tp-link.com.hk'
        
        # 产品线到Reporter的映射 - 产品负责人
        self.product_line_reporter_mapping = {
            'Controller': 'echo.liu@tp-link.com',          # echo
            'Gateway': 'xavier.chen@tp-link.com',          # xavier
            'Managed Switch': 'aiden.wang@tp-link.com',   # aiden
            'Unmanaged Switch': 'neil.qin@tp-link.com',   # neil
            'EAP': 'shon.yang@tp-link.com',               # shon
            'OLT': 'bill.wang@tp-link.com',               # bill
            'APP': 'edward.rui@tp-link.com',              # edward
            'Cloud Portal': 'bill.wang@tp-link.com',     # bill
            'Tools': 'harry.zhao@tp-link.com',            # harry
            'All-in-one machine': 'xavier.chen@tp-link.com',  # xavier
            'Combination': 'lucien.chen@tp-link.com'      # lucien
        }
        
        # 默认Reporter（最后的fallback）
        self.default_reporter = 'lucien.chen@tp-link.com'  # lucien作为兜底
        
        # 初始化版本缓存（如果需要）
        try:
            if hasattr(settings.notion, 'enable_version_mapping') and settings.notion.enable_version_mapping:
                from services.notion_version_cache import NotionVersionCache
                self.notion_version_cache = NotionVersionCache(settings)
            else:
                self.notion_version_cache = None
        except (ImportError, AttributeError):
            self.logger.warning("版本映射功能不可用")
            self.notion_version_cache = None
        
        # 初始化版本映射器
        try:
            from services.version_mapper import VersionMapper
            self.version_mapper = VersionMapper(settings)
        except ImportError:
            self.logger.warning("版本映射器不可用，VersionMapper模块未找到")
            self.version_mapper = None
        
        # 初始化用户验证缓存
        self.user_cache = UserValidationCache()
    
    def get_default_fields(self) -> Dict[str, Any]:
        """获取默认字段配置"""
        return {
            'project': {'id': self.settings.jira.project_id},
            'issuetype': {'id': self.settings.jira.default_issue_type_id},
            'fixVersions': [{'id': self.settings.jira.default_version_id}]
        }
    
    async def map_notion_to_jira(self, notion_data: Dict[str, Any], page_url: str = None) -> Dict[str, Any]:
        """将Notion数据映射为JIRA字段"""
        try:
            page_id = notion_data.get('page_id', 'Unknown')
            self.logger.info("开始字段映射转换", page_id=page_id)
            
            # 基础字段映射
            jira_fields = self.get_default_fields()
            
            # 标题映射
            title = self._extract_title(notion_data)
            if title:
                jira_fields['summary'] = title
            
            # 描述字段映射（不再包含原需求链接和PRD链接）
            description = self._build_description_without_links(notion_data)
            if description:
                jira_fields['description'] = description
            
            # 优先级映射
            priority = self._extract_priority(notion_data)
            if priority and priority in self.priority_mapping:
                jira_fields['priority'] = {'id': self.priority_mapping[priority]}
                self.logger.debug(f"优先级映射: {priority} -> {self.priority_mapping[priority]}")
            
            # 经办人映射
            assignee = await self._extract_assignee(notion_data)
            if assignee:
                # 检查assignee是否已经是字典格式
                if isinstance(assignee, dict):
                    jira_fields['assignee'] = assignee
                else:
                    jira_fields['assignee'] = {'name': assignee}
                self.logger.debug(f"经办人映射成功")
            
            # Reporter映射 - 从Owner字段提取邮箱，直接使用邮箱
            reporter = await self._extract_reporter(notion_data)
            if reporter:
                jira_fields['reporter'] = reporter
                self.logger.debug(f"Reporter映射成功")
            
            # 版本映射
            try:
                version_id = await self._extract_version(notion_data)
                if version_id:
                    # version_id已经是字符串格式
                    jira_fields['fixVersions'] = [{'id': version_id}]
                    self.logger.debug(f"版本映射成功: {version_id}")
                else:
                    # 使用默认版本，确保ID为字符串格式
                    jira_fields['fixVersions'] = [{'id': str(self.settings.jira.default_version_id)}]
            except Exception as e:
                self.logger.warning(f"版本映射失败: {str(e)}")
                # 使用默认版本，确保ID为字符串格式
                jira_fields['fixVersions'] = [{'id': str(self.settings.jira.default_version_id)}]
            
            # 提取关联链接信息（用于remote link和issue link）
            relations = self._extract_relations(notion_data)
            original_links = self._extract_original_links(notion_data, page_url)
            prd_links = self._extract_prd_links_for_remote(notion_data)
            
            # 分离JIRA issue keys 和 其他链接
            jira_issue_keys = []
            other_links = []
            
            if relations:
                for relation in relations:
                    if self._is_jira_issue_link(relation):
                        # 提取JIRA issue keys
                        issue_keys = self._extract_jira_issue_keys_from_text(relation)
                        jira_issue_keys.extend(issue_keys)
                    else:
                        other_links.append(relation)
            
            # 收集需要创建remote link的链接（按类型分类）
            remote_links_data = {
                'original': original_links if original_links else [],
                'prd': prd_links if prd_links else [], 
                'other': other_links if other_links else []
            }
            
            # 计算总链接数
            total_remote_links = len(remote_links_data['original']) + len(remote_links_data['prd']) + len(remote_links_data['other'])
            
            # 将特殊字段添加到jira_fields中，供同步服务使用
            if total_remote_links > 0:
                jira_fields['_remote_links'] = remote_links_data
                self.logger.info(f"字段映射中包含 {total_remote_links} 个远程链接，将在JIRA操作后处理 (原始需求:{len(remote_links_data['original'])}, PRD:{len(remote_links_data['prd'])}, 其他:{len(remote_links_data['other'])})")
            
            if jira_issue_keys:
                jira_fields['_issue_links'] = jira_issue_keys
                self.logger.info(f"字段映射中包含 {len(jira_issue_keys)} 个JIRA issue链接，将在JIRA操作后处理")
            
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
                has_reporter=bool(jira_fields.get('reporter')),
                description_length=len(jira_fields.get('description', '')),
                remote_links_count=total_remote_links,
                issue_links_count=len(jira_issue_keys)
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
        title_fields = ['Function Name', '功能 Name', 'title', 'name', 'Title', 'Name', '需求名']
        
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
        desc = self._extract_field_value(properties, ['Description', '功能说明 Desc'])
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
        func_desc = self._extract_field_value(properties, ['Description', '功能说明 Desc', 'description'])
        if func_desc and isinstance(func_desc, str):
            description_parts.append(f"## 需求说明\n{func_desc}")
        
        # PRD 文档库链接
        prd_links = self._extract_prd_links(properties)
        if prd_links:
            description_parts.append(f"## PRD 链接\n{prd_links}")
        
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
    
    def _build_description_without_links(self, notion_data: Dict[str, Any]) -> str:
        """构建描述字段（不包含原需求链接和PRD链接，这些将作为remote link处理）"""
        description_parts = []
        properties = notion_data.get('properties', {})
        raw_properties = notion_data.get('raw_properties', {})
        
        # 功能说明 - 直接使用原始内容，优先使用raw_properties
        func_desc = self._extract_field_value(properties, ['Description', '功能说明 Desc', 'description'], raw_properties)
        if func_desc and isinstance(func_desc, str) and func_desc.strip():
            description_parts.append(func_desc.strip())
        
        # AI整理（如果需要在描述中显示）
        # ai_summary = self._extract_field_value(properties, ['需求整理', 'ai_summary', 'AI整理'])
        # if ai_summary and isinstance(ai_summary, str) and ai_summary.strip():
        #     description_parts.append(f"需求整理(AI):\n{ai_summary.strip()}")
        
        return '\n\n'.join(description_parts) if description_parts else "无详细描述"
    
    def _extract_original_links(self, notion_data: Dict[str, Any], page_url: str = None) -> List[str]:
        """提取原始需求链接"""
        links = []
        
        # 优先使用raw_data中的URL
        raw_data = notion_data.get('raw_data', {})
        notion_url = raw_data.get('url') or page_url or notion_data.get('url')
        
        if notion_url:
            links.append(notion_url)
            self.logger.info(f"提取到原始需求链接: {notion_url}")
        
        return links
    
    def _extract_prd_links_for_remote(self, notion_data: Dict[str, Any]) -> List[str]:
        """提取PRD文档库链接（用于remote link）"""
        properties = notion_data.get('properties', {})
        
        # 先检查是否存在PRD文档库字段
        prd_fields = ['PRD 文档库', 'PRD文档库', 'PRD Documents', 'prd_docs']
        available_fields = list(properties.keys())
        
        # 记录调试信息
        self.logger.debug(f"查找PRD文档库字段，尝试字段名: {prd_fields}")
        self.logger.debug(f"可用字段: {available_fields}")
        
        found_prd_fields = [field for field in prd_fields if field in properties]
        if found_prd_fields:
            self.logger.info(f"找到PRD文档库字段: {found_prd_fields}")
        else:
            self.logger.warning(f"未找到PRD文档库字段，可用字段: {available_fields}")
            return []
        
        prd_links_text = self._extract_prd_links(properties)
        
        if not prd_links_text:
            self.logger.warning("PRD文档库字段存在但无法提取到链接内容")
            return []
        
        # 将多行链接分割为列表
        links = [link.strip() for link in prd_links_text.split('\n') if link.strip()]
        
        if links:
            self.logger.info(f"成功提取到 {len(links)} 个PRD文档库链接用于remote link: {links}")
        else:
            self.logger.warning("PRD文档库链接分割后为空")
        
        return links
    
    def _is_jira_issue_link(self, link: str) -> bool:
        """判断链接是否为JIRA issue链接"""
        if not link:
            return False
        
        # 检查是否包含JIRA issue key模式
        import re
        pattern = r'\b([A-Z]+)-(\d+)\b'
        
        return bool(re.search(pattern, link))
    
    def _extract_jira_issue_keys_from_text(self, text: str) -> List[str]:
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
    
    def _extract_prd_links(self, properties: Dict[str, Any]) -> Optional[str]:
        """提取PRD文档库链接"""
        try:
            # 尝试多种可能的PRD文档库字段名
            prd_fields = ['PRD 文档库', 'PRD文档库', 'PRD Documents', 'prd_docs']
            
            # 增加详细调试信息
            available_fields = list(properties.keys())
            self.logger.debug(f"所有可用字段: {available_fields}")
            self.logger.debug(f"查找PRD字段: {prd_fields}")
            
            for field_name in prd_fields:
                if field_name in properties:
                    self.logger.info(f"找到PRD文档库字段: {field_name}")
                    field_data = properties[field_name]
                    
                    # 记录字段的详细结构
                    self.logger.debug(f"PRD字段数据类型: {type(field_data)}")
                    self.logger.debug(f"PRD字段完整数据: {field_data}")
                    
                    # 处理webhook-server格式
                    if isinstance(field_data, dict) and 'value' in field_data:
                        relation_data = field_data['value']
                        self.logger.debug(f"webhook-server格式，value: {relation_data}")
                    # 处理原始Notion格式
                    elif isinstance(field_data, dict) and 'relation' in field_data:
                        relation_data = field_data['relation']
                        self.logger.debug(f"原始Notion格式，relation: {relation_data}")
                    else:
                        self.logger.warning(f"PRD字段格式不识别: {field_data}")
                        continue
                    
                    # 检查是否有关联的页面
                    if isinstance(relation_data, list) and len(relation_data) > 0:
                        prd_urls = []
                        
                        self.logger.debug(f"开始处理 {len(relation_data)} 个关联项目")
                        for i, item in enumerate(relation_data):
                            page_id = None
                            
                            # 处理字典格式 {'id': 'page_id'}
                            if isinstance(item, dict) and 'id' in item:
                                page_id = item['id']
                                self.logger.debug(f"从字典格式提取页面ID: {page_id}")
                            # 处理直接字符串格式 'page_id'
                            elif isinstance(item, str):
                                page_id = item
                                self.logger.debug(f"从字符串格式提取页面ID: {page_id}")
                            else:
                                self.logger.warning(f"关联项目格式异常: {item} (类型: {type(item)})")
                                continue
                            
                            if page_id:
                                # 去掉连字符生成Notion URL
                                clean_page_id = page_id.replace('-', '')
                                notion_url = f"https://www.notion.so/{clean_page_id}"
                                prd_urls.append(notion_url)
                                self.logger.debug(f"生成PRD链接: {page_id} -> {notion_url}")
                        
                        if prd_urls:
                            # 多个链接用换行分隔
                            links_text = '\n'.join(prd_urls)
                            self.logger.info(f"✅ 成功提取到 {len(prd_urls)} 个PRD文档库链接: {prd_urls}")
                            return links_text
                        else:
                            self.logger.warning("关联数据处理后未生成任何链接")
                    else:
                        self.logger.warning(f"PRD字段relation_data为空或格式错误: {relation_data}")
                        
            self.logger.warning(f"未找到PRD文档库字段或字段为空，可用字段: {available_fields}")
            return None
            
        except Exception as e:
            self.logger.error(f"提取PRD文档库链接失败: {str(e)}")
            import traceback
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            return None
    
    def _extract_field_value(self, properties: Dict[str, Any], field_names: List[str], raw_properties: Dict[str, Any] = None) -> Optional[Any]:
        """通用字段值提取方法，优先使用原始Notion格式"""
        # 优先使用原始properties
        if raw_properties:
            for field_name in field_names:
                if field_name in raw_properties:
                    field_data = raw_properties[field_name]
                    result = self._parse_raw_notion_field(field_data)
                    if result is not None:
                        return result
        
        # 回退到处理过的properties
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
                            # 处理rich_text中的换行和段落结构
                            text_parts = []
                            for item in rich_text_array:
                                text = item.get('plain_text', '')
                                # 保留文本中的原始换行符
                                if text:
                                    text_parts.append(text)
                            # 直接连接，保持原始的换行格式
                            return ''.join(text_parts)
                    
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
                            return people_array  # 返回完整的用户数组
                    
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
                    
                    # formula类型
                    elif 'formula' in field_data:
                        formula_data = field_data['formula']
                        if formula_data:
                            # 检查formula的类型（string, number, boolean, date等）
                            if 'string' in formula_data:
                                return formula_data['string']
                            elif 'number' in formula_data:
                                return formula_data['number']
                            elif 'boolean' in formula_data:
                                return formula_data['boolean']
                            elif 'date' in formula_data:
                                return formula_data['date']
                
                # 处理字符串类型
                elif isinstance(field_data, str):
                    return field_data
        
        return None
    
    def _parse_raw_notion_field(self, field_data: Dict[str, Any]) -> Optional[Any]:
        """解析原始Notion字段数据"""
        if not isinstance(field_data, dict):
            return None
        
        field_type = field_data.get('type')
        
        if field_type == 'rich_text':
            rich_text_array = field_data.get('rich_text', [])
            if rich_text_array and len(rich_text_array) > 0:
                # 连接所有rich_text元素的plain_text，保留完整内容
                text_parts = []
                for item in rich_text_array:
                    text = item.get('plain_text', '')
                    if text:
                        text_parts.append(text)
                return ''.join(text_parts)
        
        elif field_type == 'title':
            title_array = field_data.get('title', [])
            if title_array and len(title_array) > 0:
                return title_array[0].get('plain_text', '')
        
        elif field_type == 'select':
            select_data = field_data.get('select')
            if select_data and 'name' in select_data:
                return select_data['name']
        
        elif field_type == 'multi_select':
            multi_select_array = field_data.get('multi_select', [])
            if multi_select_array:
                return [item.get('name', '') for item in multi_select_array]
        
        elif field_type == 'status':
            status_data = field_data.get('status')
            if status_data and 'name' in status_data:
                return status_data['name']
        
        elif field_type == 'people':
            people_array = field_data.get('people', [])
            if people_array and len(people_array) > 0:
                return people_array  # 返回完整的用户数组
        
        elif field_type == 'relation':
            relation_array = field_data.get('relation', [])
            if relation_array and len(relation_array) > 0:
                return relation_array  # 返回整个关联数组
        
        elif field_type == 'formula':
            formula_data = field_data.get('formula')
            if formula_data:
                # 检查formula的类型
                if 'string' in formula_data:
                    return formula_data['string']
                elif 'number' in formula_data:
                    return formula_data['number']
                elif 'boolean' in formula_data:
                    return formula_data['boolean']
                elif 'date' in formula_data:
                    return formula_data['date']
        
        # 对于其他类型，返回None让回退逻辑处理
        return None
    
    def _extract_priority(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取优先级字段"""
        properties = notion_data.get('properties', {})
        raw_properties = notion_data.get('raw_properties', {})
        
        # 尝试多种可能的优先级字段名（按优先级排序）
        priority_fields = ['优先级 P', 'priority', 'Priority', '优先级']
        
        priority_value = self._extract_field_value(properties, priority_fields, raw_properties)
        if isinstance(priority_value, str):
            return priority_value
        
        return None
    
    async def _extract_assignee(self, notion_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """提取分配人员字段 - 根据产品线字段决定分配人员，直接使用邮箱"""
        properties = notion_data.get('properties', {})
        
        # 尝试多种可能的产品线字段名
        product_line_fields = ['涉及产品线', 'product_line', 'Product Line', 'Product']
        
        product_line_value = self._extract_field_value(properties, product_line_fields)
        
        # 处理不同类型的产品线字段值
        product_line = None
        if product_line_value:
            if isinstance(product_line_value, str):
                # 单选或文本类型
                product_line = product_line_value.strip()
            elif isinstance(product_line_value, list) and len(product_line_value) > 0:
                # multi-select类型，取第一个值
                if isinstance(product_line_value[0], str):
                    product_line = product_line_value[0].strip()
                elif isinstance(product_line_value[0], dict) and 'name' in product_line_value[0]:
                    product_line = product_line_value[0]['name'].strip()
        
        if product_line:
            self.logger.info(f"检测到产品线: {product_line}")
            
            # 根据产品线映射分配人员邮箱
            assignee_email = self.product_line_assignee_mapping.get(product_line, self.default_assignee)
            self.logger.info(f"产品线 '{product_line}' 映射到分配人员: {assignee_email}")
            
            return {'name': assignee_email}  # 直接使用邮箱
        else:
            self.logger.info("未检测到产品线信息，使用默认分配人员")
            return {'name': self.default_assignee}  # 直接使用默认邮箱
    
    async def _extract_reporter(self, notion_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """提取Reporter字段 - 带用户验证缓存和产品线fallback"""
        properties = notion_data.get('properties', {})
        
        # 步骤1: 尝试从Owner字段提取用户邮箱
        original_email = await self._extract_owner_email(properties)
        
        if original_email:
            # 验证用户是否存在于JIRA中（带缓存）
            if await self.user_cache.validate_user(original_email, self.jira_client):
                self.logger.info(f"使用Owner字段中的用户: {original_email}")
                return {'name': original_email}
            else:
                self.logger.warning(f"Owner用户在JIRA中不存在: {original_email}, 尝试产品线fallback")
        
        # 步骤2: 产品线fallback
        fallback_email = await self._get_product_line_reporter_fallback(properties)
        if fallback_email:
            if await self.user_cache.validate_user(fallback_email, self.jira_client):
                self.logger.info(f"使用产品线默认Reporter: {fallback_email}")
                return {'name': fallback_email}
            else:
                self.logger.warning(f"产品线默认Reporter在JIRA中不存在: {fallback_email}")
        
        # 步骤3: 全局默认fallback
        if await self.user_cache.validate_user(self.default_reporter, self.jira_client):
            self.logger.info(f"使用全局默认Reporter: {self.default_reporter}")
            return {'name': self.default_reporter}
        else:
            # 如果连默认用户都不存在，记录严重错误但不阻塞流程
            self.logger.error(f"全局默认Reporter也不存在: {self.default_reporter}")
            return None
    
    async def _extract_version(self, notion_data: Dict[str, Any]) -> Optional[str]:
        """提取版本字段，返回版本ID字符串"""
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
            if self.version_mapper:
                version_id = await self.version_mapper.get_jira_version_id(version_name)
                return str(version_id)  # 确保返回字符串
        
        # 如果没有找到版本信息，使用默认版本
        self.logger.warning("未找到版本信息，使用默认版本")
        return str(self.settings.jira.default_version_id)
    
    async def _extract_version_from_relation(self, properties: Dict[str, Any]) -> Optional[str]:
        """从关联项目字段提取版本信息"""
        try:
            # 优先使用关联项目名 Formula 属性（性能更好，无需API调用）
            formula_fields = ['关联项目名', '关联项目名 (Formula)', 'related_project_name', 'project_name_formula']
            
            for field_name in formula_fields:
                if field_name in properties:
                    self.logger.info(f"找到关联项目名Formula字段: {field_name}")
                    project_name = self._extract_field_value(properties, [field_name])
                    
                    if project_name and isinstance(project_name, str) and project_name.strip():
                        project_name = project_name.strip()
                        self.logger.info(f"从Formula字段提取到关联项目名称: {project_name}")
                        
                        # 直接使用项目名称作为版本名称进行映射
                        return project_name
            
            # Fallback: 如果没有Formula字段，使用原有的relation方式（保持向后兼容）
            relation_fields = ['关联项目', 'related_project', 'project_relation']
            
            for field_name in relation_fields:
                if field_name in properties:
                    self.logger.info(f"未找到Formula字段，尝试使用relation字段: {field_name}")
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
                            
                            # 优先使用版本缓存获取版本名称
                            if self.notion_version_cache:
                                version_name = await self.notion_version_cache.get_version_name(related_page_id)
                                if version_name:
                                    self.logger.info(f"从版本缓存提取到版本名称: {version_name}")
                                    return version_name
                            
                            # 如果版本缓存不可用或未找到，直接通过Notion API获取页面信息
                            if self.notion_client:
                                try:
                                    related_page = await self.notion_client.get_page(related_page_id)
                                    if related_page and 'properties' in related_page:
                                        related_properties = related_page['properties']
                                        
                                        # 尝试从关联项目页面的多种字段获取版本信息
                                        version_fields = ['Name', 'name', '名称', 'title', '版本', 'version', 'Version', '项目版本']
                                        for version_field in version_fields:
                                            if version_field in related_properties:
                                                version_value = self._extract_field_value(related_properties, [version_field])
                                                if version_value and isinstance(version_value, str) and version_value.strip():
                                                    self.logger.info(f"从关联项目页面字段 '{version_field}' 提取到版本名称: {version_value}")
                                                    return version_value.strip()
                                except Exception as e:
                                    self.logger.warning(f"通过Notion API获取关联项目页面信息失败: {str(e)}")
            
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
    
    async def _extract_owner_email(self, properties: Dict[str, Any]) -> Optional[str]:
        """从Owner字段提取邮箱 - 辅助方法"""
        # 尝试多种可能的Owner字段名
        reporter_fields = ['Owner', '需求负责人', '需求录入', 'reporter', 'Reporter', 'owner']
        
        reporter_value = self._extract_field_value(properties, reporter_fields)
        
        if reporter_value:
            # 处理people类型字段
            if isinstance(reporter_value, dict):
                # 单个用户对象
                email = None
                
                # webhook-server格式: {'email': 'xxx@xxx.com'}
                if 'email' in reporter_value:
                    email = reporter_value['email']
                # 原始Notion格式: {'person': {'email': 'xxx@xxx.com'}}
                elif 'person' in reporter_value and isinstance(reporter_value['person'], dict):
                    email = reporter_value['person'].get('email')
                
                if email:
                    return email
            
            elif isinstance(reporter_value, list) and len(reporter_value) > 0:
                # 用户数组，取第一个用户
                first_user = reporter_value[0]
                if isinstance(first_user, dict):
                    email = None
                    
                    # webhook-server格式: {'email': 'xxx@xxx.com'}
                    if 'email' in first_user:
                        email = first_user['email']
                    # 原始Notion格式: {'person': {'email': 'xxx@xxx.com'}}
                    elif 'person' in first_user and isinstance(first_user['person'], dict):
                        email = first_user['person'].get('email')
                    
                    if email:
                        return email
        
        return None
    
    async def _get_product_line_reporter_fallback(self, properties: Dict[str, Any]) -> Optional[str]:
        """根据产品线获取默认Reporter"""
        # 支持多种可能的产品线字段名
        product_line_fields = ['涉及产品线', 'product_line', 'Product Line', 'Product']
        
        product_line_value = self._extract_field_value(properties, product_line_fields)
        
        if product_line_value:
            # 处理多选和单选情况
            if isinstance(product_line_value, list) and len(product_line_value) > 0:
                product_line = product_line_value[0] if isinstance(product_line_value[0], str) else product_line_value[0].get('name', '')
            elif isinstance(product_line_value, str):
                product_line = product_line_value
            else:
                return None
            
            mapped_email = self.product_line_reporter_mapping.get(product_line.strip())
            if mapped_email:
                self.logger.info(f"产品线 '{product_line}' 映射到Reporter: {mapped_email}")
            return mapped_email
        
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
    
    def _extract_relations(self, notion_data: Dict[str, Any]) -> Optional[List[str]]:
        """提取relation字段内容"""
        properties = notion_data.get('properties', {})
        
        # 记录所有可用的字段用于调试
        available_fields = list(properties.keys())
        self.logger.info(f"_extract_relations: 可用的属性字段总数: {len(available_fields)}")
        self.logger.debug(f"_extract_relations: 可用的属性字段: {available_fields}")
        
        # 尝试多种可能的relation字段名
        relation_fields = ['Relation', 'relation', '关联', '关系', '关联链接', 'Related Links']
        
        # 先检查是否存在目标字段
        found_fields = []
        for field in relation_fields:
            if field in properties:
                found_fields.append(field)
                field_data = properties[field]
                self.logger.info(f"_extract_relations: 找到字段 '{field}', 类型: {type(field_data)}, 数据: {str(field_data)[:200]}...")
        
        if not found_fields:
            self.logger.warning(f"_extract_relations: 未找到任何关联字段，尝试的字段名: {relation_fields}")
            # 列出所有可能的关联字段用于调试
            possible_relation_fields = [f for f in available_fields if 'relation' in f.lower() or 'link' in f.lower()]
            if possible_relation_fields:
                self.logger.info(f"_extract_relations: 发现可能的关联字段: {possible_relation_fields}")
            return None
        
        relation_value = self._extract_field_value(properties, relation_fields)
        self.logger.info(f"_extract_relations: 提取到的值类型: {type(relation_value)}, 值: {relation_value}")
        
        if relation_value:
            # 如果是字符串类型（formula结果）
            if isinstance(relation_value, str) and relation_value.strip():
                # 解析逗号分隔的链接
                links = [link.strip() for link in relation_value.split(',') if link.strip()]
                if links:
                    self.logger.info(f"从字符串中提取到 {len(links)} 个关联链接: {links}")
                    return links
            
            # 如果是列表类型（直接的relation字段）
            elif isinstance(relation_value, list) and len(relation_value) > 0:
                # 这种情况下，relation_value是page对象列表
                links = []
                for item in relation_value:
                    if isinstance(item, dict) and 'id' in item:
                        # 构造Notion页面链接
                        page_id = item['id'].replace('-', '')
                        notion_url = f"https://www.notion.so/{page_id}"
                        links.append(notion_url)
                
                if links:
                    self.logger.info(f"从relation对象中提取到 {len(links)} 个关联链接: {links}")
                    return links
            else:
                self.logger.warning(f"_extract_relations: 不支持的关联值类型: {type(relation_value)}, 值: {relation_value}")
        else:
            self.logger.warning("_extract_relations: 未提取到关联值")
        
        return None
    
    def validate_required_fields(self, jira_fields: Dict[str, Any]) -> List[str]:
        """验证必填字段"""
        required_fields = ['project', 'issuetype', 'summary']
        missing_fields = []
        
        for field in required_fields:
            if field not in jira_fields or not jira_fields[field]:
                missing_fields.append(field)
        
        return missing_fields
    
    def build_remote_issue_links(self, relation_links: List[str], issue_summary: str) -> List[Dict[str, Any]]:
        """构建JIRA远程链接对象"""
        if not relation_links:
            return []
        
        remote_links = []
        
        for i, link_url in enumerate(relation_links):
            # 解析链接标题（简化处理）
            link_title = f"关联页面 {i+1}"
            if "notion.so" in link_url:
                link_title = f"Notion页面 {i+1}"
            
            remote_link = {
                "globalId": f"notion-relation-{hash(link_url)}",
                "application": {
                    "type": "com.notion.pages",
                    "name": "Notion"
                },
                "relationship": "relates to",
                "object": {
                    "url": link_url,
                    "title": link_title,
                    "summary": f"来自{issue_summary}的关联页面",
                    "icon": {
                        "url16x16": "https://www.notion.so/images/favicon.ico",
                        "title": "Notion Page"
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": "https://www.notion.so/images/favicon.ico",
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            
            remote_links.append(remote_link)
        
        self.logger.info(f"构建了 {len(remote_links)} 个远程链接对象")
        return remote_links
    
    async def build_remote_links_from_data_with_titles(self, links_data: List[str], issue_summary: str) -> List[Dict[str, Any]]:
        """从链接数据构建JIRA远程链接对象（简化版本，使用固定标题）"""
        if not links_data:
            return []
        
        remote_links = []
        
        for i, link_url in enumerate(links_data):
            # 生成稳定的globalId，基于URL的hash
            import hashlib
            url_hash = hashlib.md5(link_url.encode('utf-8')).hexdigest()[:8]
            
            # 判断链接类型并设置相应的标题和图标（使用固定标题，不再获取真实标题）
            if "notion.so" in link_url:
                link_title = "原始需求链接"
                app_name = "Notion"
                app_type = "com.notion.pages"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "documented by"
                global_id = f"notion-page-{url_hash}"
            elif any(keyword in link_url.lower() for keyword in ['prd', 'document', 'doc']):
                link_title = "需求PRD链接"
                app_name = "Documentation" 
                app_type = "com.notion.pages"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "documented by"
                global_id = f"notion-prd-{url_hash}"
            else:
                link_title = "关联页面"
                app_name = "External Link"
                app_type = "com.external.link"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "relates to"
                global_id = f"notion-related-{url_hash}"
            
            remote_link = {
                "globalId": global_id,  # 使用稳定的globalId支持更新
                "application": {
                    "type": app_type,
                    "name": app_name
                },
                "relationship": relationship,
                "object": {
                    "url": link_url,
                    "title": link_title,
                    "icon": {
                        "url16x16": icon_url,
                        "title": link_title
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": icon_url,
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            
            remote_links.append(remote_link)
        
        self.logger.info(f"构建了 {len(remote_links)} 个远程链接对象（简化版本，使用固定标题）")
        return remote_links

    async def build_categorized_remote_links(self, links_data: Dict[str, List[str]], issue_summary: str) -> List[Dict[str, Any]]:
        """从分类的链接数据构建JIRA远程链接对象（根据类型使用不同标题）"""
        if not links_data:
            return []
        
        remote_links = []
        
        # 处理原始需求链接
        for link_url in links_data.get('original', []):
            import hashlib
            url_hash = hashlib.md5(link_url.encode('utf-8')).hexdigest()[:8]
            
            remote_link = {
                "globalId": f"notion-original-{url_hash}",
                "application": {
                    "type": "com.notion.pages",
                    "name": "Notion"
                },
                "relationship": "documented by",
                "object": {
                    "url": link_url,
                    "title": "原始需求链接",
                    "icon": {
                        "url16x16": "https://www.notion.so/images/favicon.ico",
                        "title": "原始需求链接"
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": "https://www.notion.so/images/favicon.ico",
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            remote_links.append(remote_link)
        
        # 处理PRD文档链接
        for link_url in links_data.get('prd', []):
            import hashlib
            url_hash = hashlib.md5(link_url.encode('utf-8')).hexdigest()[:8]
            
            remote_link = {
                "globalId": f"notion-prd-{url_hash}",
                "application": {
                    "type": "com.notion.pages",
                    "name": "Documentation"
                },
                "relationship": "documented by",
                "object": {
                    "url": link_url,
                    "title": "需求PRD链接",
                    "icon": {
                        "url16x16": "https://www.notion.so/images/favicon.ico",
                        "title": "需求PRD链接"
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": "https://www.notion.so/images/favicon.ico",
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            remote_links.append(remote_link)
        
        # 处理其他关联链接
        for link_url in links_data.get('other', []):
            import hashlib
            url_hash = hashlib.md5(link_url.encode('utf-8')).hexdigest()[:8]
            
            remote_link = {
                "globalId": f"notion-related-{url_hash}",
                "application": {
                    "type": "com.external.link",
                    "name": "External Link"
                },
                "relationship": "relates to",
                "object": {
                    "url": link_url,
                    "title": "关联页面",
                    "icon": {
                        "url16x16": "https://www.notion.so/images/favicon.ico",
                        "title": "关联页面"
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": "https://www.notion.so/images/favicon.ico",
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            remote_links.append(remote_link)
        
        total_links = len(links_data.get('original', [])) + len(links_data.get('prd', [])) + len(links_data.get('other', []))
        self.logger.info(f"构建了 {len(remote_links)} 个分类远程链接对象 (原始:{len(links_data.get('original', []))}, PRD:{len(links_data.get('prd', []))}, 其他:{len(links_data.get('other', []))})")
        return remote_links

    def build_remote_links_from_data(self, links_data: List[str], issue_summary: str) -> List[Dict[str, Any]]:
        """从链接数据构建JIRA远程链接对象（支持多种类型）- 同步版本，保持向后兼容"""
        if not links_data:
            return []
        
        remote_links = []
        
        for i, link_url in enumerate(links_data):
            # 生成稳定的globalId，基于URL的hash
            import hashlib
            url_hash = hashlib.md5(link_url.encode('utf-8')).hexdigest()[:8]
            
            # 判断链接类型并设置相应的标题和图标
            if "notion.so" in link_url:
                link_title = "源需求页面"
                app_name = "Notion"
                app_type = "com.notion.pages"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "documented by"
                link_summary = f"来自{issue_summary}的原始需求页面"
                global_id = f"notion-page-{url_hash}"
            elif any(keyword in link_url.lower() for keyword in ['prd', 'document', 'doc']):
                link_title = "PRD文档"
                app_name = "Documentation"
                app_type = "com.notion.pages"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "documented by"
                link_summary = f"来自{issue_summary}的PRD文档"
                global_id = f"notion-prd-{url_hash}"
            else:
                link_title = "关联页面"
                app_name = "External Link"
                app_type = "com.external.link"
                icon_url = "https://www.notion.so/images/favicon.ico"
                relationship = "relates to"
                link_summary = f"来自{issue_summary}的关联页面"
                global_id = f"notion-related-{url_hash}"
            
            remote_link = {
                "globalId": global_id,  # 使用稳定的globalId支持更新
                "application": {
                    "type": app_type,
                    "name": app_name
                },
                "relationship": relationship,
                "object": {
                    "url": link_url,
                    "title": link_title,
                    "summary": link_summary,
                    "icon": {
                        "url16x16": icon_url,
                        "title": link_title
                    },
                    "status": {
                        "resolved": False,
                        "icon": {
                            "url16x16": icon_url,
                            "title": "Active",
                            "link": link_url
                        }
                    }
                }
            }
            
            remote_links.append(remote_link)
        
        self.logger.info(f"构建了 {len(remote_links)} 个远程链接对象（多种类型，支持globalId更新）")
        return remote_links 