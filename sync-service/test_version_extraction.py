#!/usr/bin/env python3
"""
测试版本提取功能，包括关联项目字段的处理
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.field_mapper import FieldMapper

async def test_version_extraction():
    """测试版本提取功能"""
    print("🧪 测试版本提取功能")
    print("=" * 50)
    
    # 初始化
    settings = Settings()
    field_mapper = FieldMapper(settings)  # 不传入NotionClient，测试fallback逻辑
    
    # 测试用例1：直接版本字段
    test_case_1 = {
        "page_id": "test-1",
        "properties": {
            "计划版本": {
                "value": ["Controller 6.1 ePOS"],
                "type": "multi_select"
            },
            "功能 Name": {
                "value": "测试需求1",
                "type": "title"
            }
        }
    }
    
    # 测试用例2：关联项目字段（无法获取关联页面时的fallback）
    test_case_2 = {
        "page_id": "test-2", 
        "properties": {
            "关联项目": {
                "value": [{"id": "1a715375-830d-80ca-8c96-fb4758a39f0c"}],
                "type": "relation"
            },
            "计划版本": {
                "value": ["Controller 6.0"],
                "type": "multi_select"
            },
            "功能 Name": {
                "value": "测试需求2",
                "type": "title"
            }
        }
    }
    
    # 测试用例3：无版本信息（应该使用默认版本）
    test_case_3 = {
        "page_id": "test-3",
        "properties": {
            "功能 Name": {
                "value": "测试需求3",
                "type": "title"
            }
        }
    }
    
    test_cases = [
        ("直接版本字段", test_case_1),
        ("关联项目+计划版本", test_case_2),
        ("无版本信息", test_case_3)
    ]
    
    for case_name, test_data in test_cases:
        print(f"\n📋 测试用例: {case_name}")
        print(f"页面ID: {test_data['page_id']}")
        
        try:
            # 提取版本信息
            versions = await field_mapper._extract_version(test_data)
            
            if versions and len(versions) > 0:
                version_id = versions[0]['id']
                print(f"✅ 提取到版本ID: {version_id}")
                
                # 获取版本映射信息
                mapping_data = await field_mapper.version_mapper.load_mapping()
                version_mappings = mapping_data.get('version_mappings', {})
                
                if version_id in version_mappings:
                    jira_name = version_mappings[version_id]['jira_name']
                    print(f"📋 对应JIRA版本: {jira_name}")
                    
                    # 检查是否是默认版本
                    if version_id == settings.jira.default_version_id:
                        print("🔄 使用了默认版本")
                    else:
                        print("🎯 使用了映射版本")
                else:
                    print(f"⚠️  版本ID {version_id} 在映射表中未找到")
            else:
                print("❌ 未提取到版本信息")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n🎉 版本提取测试完成")

if __name__ == "__main__":
    asyncio.run(test_version_extraction()) 