"""
Notion版本缓存管理器
负责从Notion版本库获取版本信息并建立ID到名称的映射关系
"""

import asyncio
import json
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from config.settings import Settings
from config.logger import get_logger


class NotionVersionCache:
    """Notion版本缓存管理器"""
    
    def __init__(self, settings: Settings, notion_client=None):
        self.settings = settings
        self.notion_client = notion_client
        self.logger = get_logger("notion_version_cache")
        
        # 缓存文件路径
        self.cache_file = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "notion_version_cache.json"
        )
        
        # 本地映射文件路径
        self.mapping_file = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "notion_version_mapping.json"
        )
        
        # 内存缓存
        self._version_cache = {}
        self._local_mappings = {}
        self._last_update = None
        self._cache_ttl = timedelta(hours=1)  # 缓存1小时
    
    async def get_version_name(self, version_id: str) -> Optional[str]:
        """根据版本ID获取版本名称"""
        try:
            # 首先尝试从本地映射文件获取
            await self._load_local_mappings()
            if version_id in self._local_mappings:
                version_name = self._local_mappings[version_id].get('name')
                self.logger.debug(f"从本地映射获取版本名称: {version_id} -> {version_name}")
                return version_name
            
            # 检查缓存是否需要更新
            if await self._should_refresh_cache():
                await self._refresh_cache()
            
            # 从缓存中获取版本名称
            version_info = self._version_cache.get(version_id)
            if version_info:
                version_name = version_info.get('name')
                self.logger.debug(f"从API缓存获取版本名称: {version_id} -> {version_name}")
                return version_name
            
            # 如果缓存中没有，尝试单独获取
            if self.notion_client and self.settings.notion.version_database_id:
                version_name = await self._fetch_single_version(version_id)
                if version_name:
                    # 更新缓存
                    self._version_cache[version_id] = {
                        'name': version_name,
                        'updated_at': datetime.now().isoformat()
                    }
                    await self._save_cache()
                    return version_name
            
            self.logger.warning(f"未找到版本ID对应的名称: {version_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"获取版本名称失败: {str(e)}", version_id=version_id)
            return None
    
    async def _load_local_mappings(self):
        """加载本地映射文件"""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._local_mappings = data.get('mappings', {})
                    self.logger.debug(f"加载了 {len(self._local_mappings)} 个本地版本映射")
            else:
                self._local_mappings = {}
                self.logger.debug("本地映射文件不存在")
        except Exception as e:
            self.logger.error(f"加载本地映射文件失败: {str(e)}")
            self._local_mappings = {}

    async def _should_refresh_cache(self) -> bool:
        """检查是否需要刷新缓存"""
        # 如果没有Notion客户端或版本库ID，不需要刷新
        if not self.notion_client or not self.settings.notion.version_database_id:
            return False
        
        # 如果缓存为空，需要刷新
        if not self._version_cache:
            await self._load_cache()
            if not self._version_cache:
                return True
        
        # 如果超过TTL，需要刷新
        if self._last_update:
            if datetime.now() - self._last_update > self._cache_ttl:
                return True
        else:
            return True
        
        return False
    
    async def _refresh_cache(self):
        """刷新版本缓存"""
        try:
            if not self.notion_client or not self.settings.notion.version_database_id:
                self.logger.warning("未配置Notion客户端或版本库ID，跳过缓存刷新")
                return
            
            self.logger.info("开始刷新Notion版本缓存")
            
            # 查询版本库中的所有版本
            versions = await self._fetch_all_versions()
            
            if versions:
                # 更新缓存
                new_cache = {}
                for version in versions:
                    version_id = version.get('id')
                    version_name = self._extract_version_name(version)
                    
                    if version_id and version_name:
                        new_cache[version_id] = {
                            'name': version_name,
                            'updated_at': datetime.now().isoformat(),
                            'properties': version.get('properties', {})
                        }
                
                self._version_cache = new_cache
                self._last_update = datetime.now()
                
                # 保存到文件
                await self._save_cache()
                
                self.logger.info(f"版本缓存刷新完成，共缓存 {len(new_cache)} 个版本")
            else:
                self.logger.warning("未获取到版本数据")
                
        except Exception as e:
            self.logger.error(f"刷新版本缓存失败: {str(e)}")
    
    async def _fetch_all_versions(self) -> List[Dict[str, Any]]:
        """从Notion版本库获取所有版本"""
        try:
            database_id = self.settings.notion.version_database_id
            
            # 查询数据库中的所有页面
            results = await self.notion_client.query_database(database_id)
            
            if results and 'results' in results:
                self.logger.info(f"从版本库获取到 {len(results['results'])} 个版本")
                return results['results']
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取版本库数据失败: {str(e)}")
            return []
    
    async def _fetch_single_version(self, version_id: str) -> Optional[str]:
        """获取单个版本的名称"""
        try:
            page_data = await self.notion_client.get_page(version_id)
            if page_data:
                return self._extract_version_name(page_data)
            return None
            
        except Exception as e:
            self.logger.error(f"获取单个版本失败: {str(e)}", version_id=version_id)
            return None
    
    def _extract_version_name(self, page_data: Dict[str, Any]) -> Optional[str]:
        """从页面数据中提取版本名称"""
        try:
            properties = page_data.get('properties', {})
            
            # 尝试多种可能的名称字段
            name_fields = ['项目', 'Name', 'name', '名称', 'title', '版本名称', 'Version']
            
            for field_name in name_fields:
                if field_name in properties:
                    field_data = properties[field_name]
                    
                    # title类型
                    if isinstance(field_data, dict) and 'title' in field_data:
                        title_array = field_data['title']
                        if title_array and len(title_array) > 0:
                            name = title_array[0].get('plain_text', '')
                            if name.strip():
                                return name.strip()
                    
                    # rich_text类型
                    elif isinstance(field_data, dict) and 'rich_text' in field_data:
                        rich_text_array = field_data['rich_text']
                        if rich_text_array and len(rich_text_array) > 0:
                            name = ''.join([item.get('plain_text', '') for item in rich_text_array])
                            if name.strip():
                                return name.strip()
                    
                    # select类型
                    elif isinstance(field_data, dict) and 'select' in field_data:
                        select_data = field_data['select']
                        if select_data and 'name' in select_data:
                            return select_data['name']
            
            # 如果没有找到名称字段，使用页面ID作为fallback
            page_id = page_data.get('id', '')
            self.logger.warning(f"未找到版本名称字段，使用页面ID: {page_id}")
            return f"Version-{page_id[:8]}"
            
        except Exception as e:
            self.logger.error(f"提取版本名称失败: {str(e)}")
            return None
    
    async def _load_cache(self):
        """从文件加载缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                    self._version_cache = cache_data.get('versions', {})
                    last_update_str = cache_data.get('last_update')
                    
                    if last_update_str:
                        self._last_update = datetime.fromisoformat(last_update_str)
                    
                    self.logger.info(f"从文件加载版本缓存，共 {len(self._version_cache)} 个版本")
            
        except Exception as e:
            self.logger.error(f"加载版本缓存失败: {str(e)}")
            self._version_cache = {}
            self._last_update = None
    
    async def _save_cache(self):
        """保存缓存到文件"""
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            cache_data = {
                'versions': self._version_cache,
                'last_update': self._last_update.isoformat() if self._last_update else None,
                'cache_ttl_hours': self._cache_ttl.total_seconds() / 3600
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug("版本缓存已保存到文件")
            
        except Exception as e:
            self.logger.error(f"保存版本缓存失败: {str(e)}")
    
    async def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态信息"""
        await self._load_local_mappings()
        
        return {
            "cache_file": self.cache_file,
            "mapping_file": self.mapping_file,
            "cached_versions": len(self._version_cache),
            "local_mappings": len(self._local_mappings),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "cache_ttl_hours": self._cache_ttl.total_seconds() / 3600,
            "has_notion_client": bool(self.notion_client),
            "version_database_id": self.settings.notion.version_database_id
        }
    
    async def clear_cache(self):
        """清空缓存"""
        self._version_cache = {}
        self._last_update = None
        
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        
        self.logger.info("版本缓存已清空") 