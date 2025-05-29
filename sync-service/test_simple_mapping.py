#!/usr/bin/env python3
"""
简化的本地版本映射测试
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.notion_version_cache import NotionVersionCache

async def test_simple_mapping():
    """测试简化的本地映射功能"""
    print("🔧 测试本地版本映射功能")
    print("=" * 50)
    
    try:
        # 获取配置
        settings = Settings()
        
        # 创建版本缓存（不需要Notion客户端）
        version_cache = NotionVersionCache(settings, notion_client=None)
        
        # 1. 测试版本缓存状态
        print("\n1. 检查版本缓存状态:")
        cache_status = await version_cache.get_cache_status()
        for key, value in cache_status.items():
            print(f"   {key}: {value}")
        
        # 2. 测试本地映射查询
        print("\n2. 测试本地映射查询:")
        test_ids = [
            "1a715375-830d-80ca-8c96-fb4758a39f0c",  # Controller 6.1 ePOS
            "1a015375-830d-81eb-93f0-efc363db46da",  # Controller 6.0
            "nonexistent-id"  # 不存在的ID
        ]
        
        for test_id in test_ids:
            version_name = await version_cache.get_version_name(test_id)
            status = "✅" if version_name else "❌"
            print(f"   {status} {test_id} -> {version_name}")
        
        print("\n✅ 本地版本映射测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

def test_mapping_manager():
    """测试版本映射管理器"""
    print("\n🔧 测试版本映射管理器")
    print("=" * 50)
    
    try:
        # 导入管理器
        from scripts.manage_notion_version_mapping import NotionVersionMappingManager
        
        manager = NotionVersionMappingManager()
        
        # 测试列出映射
        print("\n1. 列出所有映射:")
        manager.list_mappings()
        
        # 测试搜索
        print("\n2. 搜索映射:")
        manager.search_mappings("Controller")
        
        # 测试获取版本名称
        print("\n3. 测试获取版本名称:")
        test_id = "1a715375-830d-80ca-8c96-fb4758a39f0c"
        version_name = manager.get_version_name(test_id)
        print(f"   {test_id} -> {version_name}")
        
        print("\n✅ 版本映射管理器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

def main():
    """主函数"""
    print("🚀 开始测试本地版本映射系统")
    
    # 运行异步测试
    asyncio.run(test_simple_mapping())
    
    # 运行同步测试
    test_mapping_manager()
    
    print("\n🎉 所有测试完成")

if __name__ == "__main__":
    main() 