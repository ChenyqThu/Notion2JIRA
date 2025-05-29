#!/usr/bin/env python3
"""
版本映射配置生成工具

这个工具会从JIRA获取所有版本，生成一个人性化的配置文件，
用户可以直接编辑JSON文件来配置版本映射关系。
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from services.jira_client import JiraClient
from services.version_mapper import VersionMapper
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VersionConfigGenerator:
    def __init__(self):
        self.settings = Settings()
        self.jira_client = JiraClient(self.settings)
        self.version_mapper = VersionMapper(self.settings)
        
    async def generate_config(self, output_file: str = None):
        """生成人性化的版本映射配置文件"""
        try:
            print("🔄 正在初始化JIRA客户端...")
            
            # 初始化JIRA客户端
            await self.jira_client.initialize()
            
            print("🔄 正在测试JIRA连接...")
            
            # 测试JIRA连接
            if not await self.jira_client.test_connection():
                print("❌ JIRA连接失败，请检查配置")
                return False
            
            # 获取项目版本
            versions = await self.jira_client.get_project_versions()
            if not versions:
                print("❌ 未获取到JIRA项目版本")
                return False
            
            print(f"✅ 获取到 {len(versions)} 个JIRA版本")
            
            # 加载现有配置（如果存在）
            existing_config = await self.version_mapper.load_mapping()
            existing_mappings = existing_config.get('version_mappings', {})
            
            # 生成新的配置结构
            config = {
                "_metadata": {
                    "description": "JIRA版本到Notion版本名称的映射配置",
                    "generated_time": datetime.now().isoformat(),
                    "jira_project": self.settings.jira.project_key,
                    "total_versions": len(versions),
                    "instructions": {
                        "如何配置": [
                            "1. 在每个JIRA版本的notion_names数组中添加对应的Notion版本名称",
                            "2. 如果某个JIRA版本没有对应的Notion版本，保持notion_names为空数组[]",
                            "3. 可以在comment字段添加备注说明",
                            "4. 修改后保存文件，系统会自动加载新配置"
                        ],
                        "示例": {
                            "notion_names": ["V1.0", "版本1.0", "第一版"],
                            "comment": "这是第一个正式版本"
                        }
                    }
                },
                "default_version_id": self.settings.jira.default_version_id,
                "last_updated": datetime.now().isoformat(),
                "jira_sync_time": datetime.now().isoformat(),
                "version_mappings": {}
            }
            
            # 按版本名称排序
            sorted_versions = sorted(versions, key=lambda v: v.get('name', ''))
            
            # 为每个JIRA版本创建配置条目
            for version in sorted_versions:
                version_id = version.get('id')
                version_name = version.get('name')
                
                if not version_id or not version_name:
                    continue
                
                # 保留现有的映射配置
                existing_mapping = existing_mappings.get(version_id, {})
                
                config["version_mappings"][version_id] = {
                    "jira_name": version_name,
                    "notion_names": existing_mapping.get('notion_names', []),
                    "released": version.get('released', False),
                    "archived": version.get('archived', False),
                    "description": version.get('description', ''),
                    "comment": existing_mapping.get('comment', '')
                }
            
            # 确定输出文件路径
            if not output_file:
                output_file = self.version_mapper.mapping_file
            
            # 保存配置文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 配置文件已生成: {output_file}")
            print(f"📊 包含 {len(config['version_mappings'])} 个JIRA版本")
            
            # 显示配置预览
            self._show_config_preview(config)
            
            return True
            
        except Exception as e:
            logger.error("生成配置文件失败", error=str(e))
            print(f"❌ 生成配置文件失败: {str(e)}")
            return False
        finally:
            # 关闭JIRA客户端
            if self.jira_client.session:
                await self.jira_client.close()
    
    def _show_config_preview(self, config):
        """显示配置预览"""
        print("\n=== 配置预览 ===")
        print(f"默认版本ID: {config['default_version_id']}")
        print(f"JIRA版本总数: {len(config['version_mappings'])}")
        
        # 统计已配置的映射
        mapped_count = sum(1 for mapping in config['version_mappings'].values() 
                          if mapping.get('notion_names'))
        print(f"已配置映射: {mapped_count}")
        print(f"未配置映射: {len(config['version_mappings']) - mapped_count}")
        
        print("\n前10个版本:")
        print(f"{'版本ID':<12} {'版本名称':<25} {'状态':<10} {'Notion映射'}")
        print("-" * 70)
        
        for i, (version_id, mapping) in enumerate(config['version_mappings'].items()):
            if i >= 10:
                break
                
            jira_name = mapping['jira_name']
            notion_names = mapping.get('notion_names', [])
            
            # 状态
            status_parts = []
            if mapping.get('released'):
                status_parts.append('已发布')
            if mapping.get('archived'):
                status_parts.append('已归档')
            status = ','.join(status_parts) if status_parts else '活跃'
            
            # Notion映射
            notion_text = ', '.join(notion_names) if notion_names else '[未配置]'
            
            print(f"{version_id:<12} {jira_name:<25} {status:<10} {notion_text}")
        
        if len(config['version_mappings']) > 10:
            print(f"... 还有 {len(config['version_mappings']) - 10} 个版本")
        
        print(f"\n💡 请编辑文件 {self.version_mapper.mapping_file} 来配置版本映射")

async def main():
    """主函数"""
    generator = VersionConfigGenerator()
    
    print("🚀 JIRA版本映射配置生成工具")
    print("=" * 50)
    
    # 检查配置
    try:
        if not generator.settings.jira.base_url:
            print("❌ 请先配置JIRA服务器信息")
            return
        
        print(f"JIRA服务器: {generator.settings.jira.base_url}")
        print(f"项目: {generator.settings.jira.project_key}")
        print(f"用户: {generator.settings.jira.username}")
        
    except Exception as e:
        print(f"❌ 配置检查失败: {str(e)}")
        return
    
    # 生成配置
    success = await generator.generate_config()
    
    if success:
        print("\n🎉 配置生成完成！")
        print("\n下一步:")
        print("1. 编辑生成的配置文件")
        print("2. 在notion_names数组中添加对应的Notion版本名称")
        print("3. 保存文件后系统会自动加载新配置")
    else:
        print("\n❌ 配置生成失败")

if __name__ == "__main__":
    asyncio.run(main()) 