"""
版本映射管理器
负责维护Notion版本名称到JIRA版本ID的映射关系
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger


class VersionMapper:
    """版本映射管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("version_mapper")
        
        # 映射文件路径
        self.mapping_file = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "config", 
            "version_mapping.json"
        )
        
        # 内存中的映射缓存
        self._mapping_cache = None
        self._last_load_time = None
    
    async def load_mapping(self) -> Dict[str, Any]:
        """加载版本映射配置"""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    self._mapping_cache = mapping_data
                    self._last_load_time = datetime.now()
                    
                    # 检查是否是旧格式，如果是则转换为新格式
                    if 'mappings' in mapping_data and 'version_mappings' not in mapping_data:
                        mapping_data = await self._convert_to_new_format(mapping_data)
                    
                    # 统计有效映射数量（排除空值）
                    version_mappings = mapping_data.get('version_mappings', {})
                    valid_mappings = sum(1 for mapping in version_mappings.values() 
                                       if mapping.get('notion_names'))
                    
                    self.logger.info(
                        "版本映射配置加载成功",
                        total_versions=len(version_mappings),
                        valid_mappings=valid_mappings,
                        last_updated=mapping_data.get('last_updated')
                    )
                    return mapping_data
            else:
                # 创建默认配置文件
                default_mapping = await self._create_default_mapping()
                await self.save_mapping(default_mapping)
                return default_mapping
                
        except Exception as e:
            self.logger.error("加载版本映射配置失败", error=str(e))
            # 返回默认映射
            return await self._create_default_mapping()
    
    async def save_mapping(self, mapping_data: Dict[str, Any]) -> bool:
        """保存版本映射配置"""
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self.mapping_file)
            os.makedirs(config_dir, exist_ok=True)
            
            # 更新时间戳
            mapping_data['last_updated'] = datetime.now().isoformat()
            
            # 保存到文件
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self._mapping_cache = mapping_data
            self._last_load_time = datetime.now()
            
            self.logger.info("版本映射配置保存成功", mapping_count=len(mapping_data.get('version_mappings', {})))
            return True
            
        except Exception as e:
            self.logger.error("保存版本映射配置失败", error=str(e))
            return False
    
    async def _create_default_mapping(self) -> Dict[str, Any]:
        """创建默认映射配置"""
        return {
            "last_updated": datetime.now().isoformat(),
            "description": "JIRA版本到Notion版本名称的映射关系",
            "default_version_id": self.settings.jira.default_version_id,
            "version_mappings": {},
            "jira_sync_time": None
        }
    
    async def _convert_to_new_format(self, old_mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """将旧格式转换为新格式"""
        self.logger.info("检测到旧格式配置，正在转换为新格式")
        
        # 创建新格式的基础结构
        new_mapping = {
            "last_updated": datetime.now().isoformat(),
            "description": "JIRA版本到Notion版本名称的映射关系",
            "default_version_id": self.settings.jira.default_version_id,
            "version_mappings": {},
            "jira_sync_time": old_mapping_data.get('jira_sync_time')
        }
        
        # 转换JIRA版本信息
        jira_versions = old_mapping_data.get('jira_versions', {})
        old_mappings = old_mapping_data.get('mappings', {})
        
        # 为每个JIRA版本创建映射条目
        for version_id, version_info in jira_versions.items():
            # 查找指向这个版本ID的Notion版本名称
            notion_names = []
            for notion_name, mapped_version_id in old_mappings.items():
                if mapped_version_id == version_id:
                    notion_names.append(notion_name)
            
            new_mapping["version_mappings"][version_id] = {
                "jira_name": version_info.get('name', ''),
                "notion_names": notion_names,
                "released": version_info.get('released', False),
                "archived": version_info.get('archived', False),
                "description": version_info.get('description', ''),
                "comment": ""
            }
        
        self.logger.info("配置格式转换完成", 
                        old_mappings_count=len(old_mappings),
                        new_versions_count=len(new_mapping["version_mappings"]))
        
        return new_mapping
    
    async def get_jira_version_id(self, notion_version_name: str) -> Optional[str]:
        """根据Notion版本名称获取JIRA版本ID"""
        try:
            # 加载最新映射
            mapping_data = await self.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            # 在所有版本映射中查找匹配的Notion版本名称
            for version_id, mapping_info in version_mappings.items():
                notion_names = mapping_info.get('notion_names', [])
                
                # 精确匹配
                if notion_version_name in notion_names:
                    return version_id
                
                # 模糊匹配（去除空格和大小写）
                normalized_name = notion_version_name.strip().lower()
                for notion_name in notion_names:
                    if notion_name.strip().lower() == normalized_name:
                        return version_id
            
            # 未找到映射，使用默认版本
            default_version_id = mapping_data.get('default_version_id', self.settings.jira.default_version_id)
            self.logger.warning(
                "未找到版本映射，使用默认版本",
                notion_version=notion_version_name,
                default_version_id=default_version_id
            )
            return default_version_id
            
        except Exception as e:
            self.logger.error("获取JIRA版本ID失败", error=str(e), notion_version=notion_version_name)
            return self.settings.jira.default_version_id
    
    async def update_jira_versions(self, jira_client) -> bool:
        """从JIRA获取最新的版本列表并更新配置"""
        try:
            self.logger.info("开始从JIRA获取版本列表")
            
            # 获取项目版本
            versions = await jira_client.get_project_versions()
            if not versions:
                self.logger.warning("未获取到JIRA项目版本")
                return False
            
            # 加载当前映射
            mapping_data = await self.load_mapping()
            current_mappings = mapping_data.get('version_mappings', {})
            
            # 更新版本映射
            updated_mappings = {}
            
            for version in versions:
                version_id = version.get('id')
                version_name = version.get('name')
                if version_id and version_name:
                    # 保留现有的Notion映射，如果存在的话
                    existing_mapping = current_mappings.get(version_id, {})
                    
                    updated_mappings[version_id] = {
                        'jira_name': version_name,
                        'notion_names': existing_mapping.get('notion_names', []),
                        'released': version.get('released', False),
                        'archived': version.get('archived', False),
                        'description': version.get('description', ''),
                        'comment': existing_mapping.get('comment', '')
                    }
            
            mapping_data['version_mappings'] = updated_mappings
            mapping_data['jira_sync_time'] = datetime.now().isoformat()
            
            # 保存更新后的配置
            success = await self.save_mapping(mapping_data)
            
            if success:
                self.logger.info(
                    "JIRA版本列表更新成功",
                    version_count=len(updated_mappings)
                )
            
            return success
            
        except Exception as e:
            self.logger.error("更新JIRA版本列表失败", error=str(e))
            return False
    
    async def add_version_mapping(self, notion_version: str, jira_version_id: str) -> bool:
        """添加新的版本映射"""
        try:
            mapping_data = await self.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            # 检查JIRA版本是否存在
            if jira_version_id not in version_mappings:
                self.logger.error("JIRA版本ID不存在", jira_version_id=jira_version_id)
                return False
            
            # 添加Notion版本名称到对应的JIRA版本
            notion_names = version_mappings[jira_version_id].get('notion_names', [])
            if notion_version not in notion_names:
                notion_names.append(notion_version)
                version_mappings[jira_version_id]['notion_names'] = notion_names
            
            mapping_data['version_mappings'] = version_mappings
            
            # 保存配置
            success = await self.save_mapping(mapping_data)
            
            if success:
                self.logger.info(
                    "版本映射添加成功",
                    notion_version=notion_version,
                    jira_version_id=jira_version_id,
                    jira_name=version_mappings[jira_version_id].get('jira_name')
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "添加版本映射失败",
                error=str(e),
                notion_version=notion_version,
                jira_version_id=jira_version_id
            )
            return False
    
    async def remove_version_mapping(self, notion_version: str) -> bool:
        """移除版本映射"""
        try:
            mapping_data = await self.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            # 在所有JIRA版本中查找并移除指定的Notion版本名称
            found = False
            for version_id, mapping_info in version_mappings.items():
                notion_names = mapping_info.get('notion_names', [])
                if notion_version in notion_names:
                    notion_names.remove(notion_version)
                    mapping_info['notion_names'] = notion_names
                    found = True
                    break
            
            if found:
                mapping_data['version_mappings'] = version_mappings
                
                # 保存配置
                success = await self.save_mapping(mapping_data)
                
                if success:
                    self.logger.info("版本映射移除成功", notion_version=notion_version)
                
                return success
            else:
                self.logger.warning("版本映射不存在", notion_version=notion_version)
                return True
                
        except Exception as e:
            self.logger.error("移除版本映射失败", error=str(e), notion_version=notion_version)
            return False
    
    def get_jira_version_name(self, version_id: str) -> Optional[str]:
        """根据JIRA版本ID获取版本名称"""
        try:
            if self._mapping_cache is None:
                return None
            
            version_mappings = self._mapping_cache.get('version_mappings', {})
            mapping_info = version_mappings.get(str(version_id))
            
            if mapping_info:
                return mapping_info.get('jira_name')
            
            return None
            
        except Exception as e:
            self.logger.error("获取JIRA版本名称失败", error=str(e), version_id=version_id)
            return None
    
    async def get_mapping_status(self) -> Dict[str, Any]:
        """获取映射状态信息"""
        try:
            mapping_data = await self.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            # 统计有效映射数量
            valid_mappings = sum(1 for mapping in version_mappings.values() 
                               if mapping.get('notion_names'))
            
            # 统计总的Notion版本名称数量
            total_notion_names = sum(len(mapping.get('notion_names', [])) 
                                   for mapping in version_mappings.values())
            
            return {
                "mapping_file": self.mapping_file,
                "last_updated": mapping_data.get('last_updated'),
                "jira_sync_time": mapping_data.get('jira_sync_time'),
                "default_version_id": mapping_data.get('default_version_id'),
                "total_jira_versions": len(version_mappings),
                "mapped_jira_versions": valid_mappings,
                "total_notion_names": total_notion_names,
                "version_mappings": version_mappings
            }
            
        except Exception as e:
            self.logger.error("获取映射状态失败", error=str(e))
            return {"error": str(e)} 