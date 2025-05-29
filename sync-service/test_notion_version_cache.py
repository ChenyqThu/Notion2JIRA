#!/usr/bin/env python3
"""
测试Notion版本缓存功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.notion_client import NotionClient
from services.notion_version_cache import NotionVersionCache
from services.field_mapper import FieldMapper

async def test_notion_version_cache():
    """测试Notion版本缓存功能"""
    print("🧪 测试Notion版本缓存功能")
    print("=" * 60)
    
    # 初始化
    settings = Settings()
    
    # 检查配置
    print("📋 配置检查:")
    print(f"- Notion Token: {'已配置' if settings.notion.token else '未配置'}")
    print(f"- 版本库Database ID: {settings.notion.version_database_id}")
    
    if not settings.notion.token or not settings.notion.version_database_id:
        print("❌ 缺少必要配置，无法进行测试")
        return
    
    # 初始化Notion客户端
    notion_client = NotionClient(settings)
    await notion_client.initialize()
    print("✅ Notion客户端初始化完成")
    
    try:
        # 测试连接
        connection_ok = await notion_client.test_connection()
        if not connection_ok:
            print("❌ Notion连接测试失败")
            return
        print("✅ Notion连接测试成功")
        
        # 初始化版本缓存
        version_cache = NotionVersionCache(settings, notion_client)
        print("✅ 版本缓存初始化完成")
        
        # 获取缓存状态
        cache_status = await version_cache.get_cache_status()
        print(f"\n📊 缓存状态:")
        print(f"- 缓存文件: {cache_status['cache_file']}")
        print(f"- 已缓存版本数: {cache_status['cached_versions']}")
        print(f"- 上次更新: {cache_status['last_update'] or '从未更新'}")
        print(f"- 缓存TTL: {cache_status['cache_ttl_hours']} 小时")
        
        # 测试获取版本名称（这会触发缓存刷新）
        print(f"\n🔍 测试版本获取:")
        test_version_id = "1a715375-830d-80ca-8c96-fb4758a39f0c"
        print(f"测试版本ID: {test_version_id}")
        
        version_name = await version_cache.get_version_name(test_version_id)
        if version_name:
            print(f"✅ 获取到版本名称: {version_name}")
        else:
            print(f"❌ 未获取到版本名称")
        
        # 再次获取缓存状态
        cache_status = await version_cache.get_cache_status()
        print(f"\n📊 更新后缓存状态:")
        print(f"- 已缓存版本数: {cache_status['cached_versions']}")
        print(f"- 上次更新: {cache_status['last_update'] or '从未更新'}")
        
        # 测试字段映射器的版本提取
        print(f"\n🔧 测试字段映射器版本提取:")
        field_mapper = FieldMapper(settings, notion_client)
        
        # 模拟关联项目数据
        test_notion_data = {
            "page_id": "test-page",
            "properties": {
                "关联项目": {
                    "value": [{"id": test_version_id}],
                    "type": "relation"
                },
                "功能 Name": {
                    "value": "测试需求",
                    "type": "title"
                }
            }
        }
        
        versions = await field_mapper._extract_version(test_notion_data)
        if versions and len(versions) > 0:
            version_id = versions[0]['id']
            print(f"✅ 字段映射器提取到版本ID: {version_id}")
            
            # 获取版本映射信息
            mapping_data = await field_mapper.version_mapper.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            if version_id in version_mappings:
                jira_name = version_mappings[version_id]['jira_name']
                print(f"📋 对应JIRA版本: {jira_name}")
            else:
                print(f"⚠️  版本ID {version_id} 在映射表中未找到")
        else:
            print("❌ 字段映射器未提取到版本信息")
        
        print(f"\n🎉 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        await notion_client.close()

if __name__ == "__main__":
    asyncio.run(test_notion_version_cache()) 