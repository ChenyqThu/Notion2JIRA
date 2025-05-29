#!/usr/bin/env python3
"""
测试关联项目字段的版本提取功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.field_mapper import FieldMapper
from services.notion_client import NotionClient

async def test_relation_version():
    """测试关联项目字段的版本提取"""
    print("🧪 测试关联项目字段的版本提取功能")
    print("=" * 60)
    
    # 初始化
    settings = Settings()
    
    # 初始化Notion客户端
    notion_client = None
    if settings.notion.token:
        notion_client = NotionClient(settings)
        await notion_client.initialize()
        print("✅ Notion客户端初始化完成")
    else:
        print("⚠️  未配置Notion token，无法测试关联页面获取")
    
    # 初始化字段映射器
    field_mapper = FieldMapper(settings, notion_client)
    
    # 模拟关联项目数据（基于您提供的示例）
    test_notion_data = {
        "page_id": "20015375-830d-8051-9b72-d3fcec2b7ef4",
        "properties": {
            "关联项目": {
                "id": "H%3Ac%60",
                "type": "relation",
                "relation": [
                    {
                        "id": "1a715375-830d-80ca-8c96-fb4758a39f0c"
                    }
                ],
                "has_more": False
            },
            "功能 Name": {
                "value": "这是一条测试的需求",
                "type": "title"
            }
        }
    }
    
    print("📋 测试数据:")
    print(f"页面ID: {test_notion_data['page_id']}")
    print(f"关联项目ID: {test_notion_data['properties']['关联项目']['relation'][0]['id']}")
    
    try:
        # 测试版本提取
        print("\n🔍 开始提取版本信息...")
        versions = await field_mapper._extract_version(test_notion_data)
        
        if versions:
            version_id = versions[0]['id']
            print(f"✅ 提取到版本ID: {version_id}")
            
            # 获取版本映射信息
            mapping_data = await field_mapper.version_mapper.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            if version_id in version_mappings:
                jira_name = version_mappings[version_id]['jira_name']
                print(f"📋 对应JIRA版本: {jira_name}")
            else:
                print(f"⚠️  版本ID {version_id} 在映射表中未找到")
        else:
            print("❌ 未提取到版本信息")
        
        # 测试关联项目字段提取
        print("\n🔗 测试关联项目字段提取...")
        relation_version = await field_mapper._extract_version_from_relation(
            test_notion_data['properties']
        )
        
        if relation_version:
            print(f"✅ 从关联项目提取到版本名称: {relation_version}")
        else:
            print("❌ 未从关联项目提取到版本信息")
        
        # 如果有Notion客户端，测试获取关联页面信息
        if notion_client:
            print("\n📄 测试获取关联页面信息...")
            related_page_id = test_notion_data['properties']['关联项目']['relation'][0]['id']
            page_name = await field_mapper._get_relation_page_name(related_page_id)
            
            if page_name:
                print(f"✅ 获取到关联页面名称: {page_name}")
            else:
                print("❌ 未获取到关联页面名称")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        if notion_client:
            await notion_client.close()

if __name__ == "__main__":
    asyncio.run(test_relation_version()) 