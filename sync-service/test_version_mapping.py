#!/usr/bin/env python3
"""
测试版本映射功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.version_mapper import VersionMapper

async def test_version_mapping():
    """测试版本映射功能"""
    print("🧪 测试版本映射功能")
    print("=" * 50)
    
    # 初始化
    settings = Settings()
    version_mapper = VersionMapper(settings)
    
    # 测试用例
    test_cases = [
        "待评估版本",
        "未分配", 
        "TBD",
        "Controller 6.0",
        "Controller 6.1 ePOS",
        "Omada v6.1",
        "v6.1",
        "6.1版本",
        "不存在的版本",
        "V1.0",  # 不存在，应该返回默认版本
        ""  # 空字符串
    ]
    
    print("测试版本名称映射:")
    print(f"{'Notion版本名称':<20} {'JIRA版本ID':<12} {'结果'}")
    print("-" * 50)
    
    for notion_version in test_cases:
        try:
            jira_version_id = await version_mapper.get_jira_version_id(notion_version)
            
            # 获取JIRA版本名称
            mapping_data = await version_mapper.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            jira_name = version_mappings.get(jira_version_id, {}).get('jira_name', '未知')
            
            if jira_version_id == settings.jira.default_version_id:
                result = "✅ 默认版本"
            else:
                result = "✅ 映射成功"
            
            print(f"{notion_version:<20} {jira_version_id:<12} {result} ({jira_name})")
            
        except Exception as e:
            print(f"{notion_version:<20} {'ERROR':<12} ❌ 错误: {str(e)}")
    
    print("\n📊 映射统计:")
    status = await version_mapper.get_mapping_status()
    print(f"- 总JIRA版本数: {status.get('total_jira_versions')}")
    print(f"- 已映射版本数: {status.get('mapped_jira_versions')}")
    print(f"- Notion版本名称总数: {status.get('total_notion_names')}")
    print(f"- 默认版本ID: {status.get('default_version_id')}")

if __name__ == "__main__":
    asyncio.run(test_version_mapping()) 