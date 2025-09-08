#!/usr/bin/env python3
"""
版本映射测试脚本
验证Notion版本名称到JIRA版本ID的映射是否正确
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from services.version_mapper import VersionMapper
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VersionMappingTester:
    def __init__(self):
        self.settings = Settings()
        self.version_mapper = VersionMapper(self.settings)
        
    async def test_version_mapping(self):
        """测试版本映射功能"""
        try:
            print("🔄 开始版本映射测试...")
            
            # 加载版本映射配置
            mapping_data = await self.version_mapper.load_mapping()
            print(f"📋 加载了 {len(mapping_data.get('version_mappings', {}))} 个版本映射")
            
            # 测试用例：常见的Notion版本名称
            test_cases = [
                # 同名匹配测试
                "Network v6.3",      # 应该同名匹配到JIRA的"Network v6.3"
                "Controller v6.0",   # 应该同名匹配到JIRA的"Controller v6.0"  
                "AP v6.0",           # 应该同名匹配到JIRA的"AP v6.0"
                "25H2",              # 应该同名匹配到JIRA的"25H2"
                
                # 映射表匹配测试
                "network 6.3",       # 应该通过映射表匹配到Network v6.3
                "Network 6.3",       # 应该通过映射表匹配到Network v6.3
                "网络6.3",           # 应该通过映射表匹配到Network v6.3
                "Controller 6.0",    # 应该通过映射表匹配到Controller v6.0
                "Design Center 1.1", # 应该通过映射表匹配到ODC v1.1
                "待定 TBD",          # 应该通过映射表匹配到默认版本
                
                # 默认版本测试
                "不存在的版本",       # 不存在的版本（应该返回默认值）
                "随便什么名字",       # 随机名称（应该返回默认值）
            ]
            
            print("\n🧪 开始测试用例...")
            print("=" * 80)
            
            for notion_version in test_cases:
                jira_version_id = await self.version_mapper.get_jira_version_id(notion_version)
                
                if jira_version_id:
                    # 获取对应的JIRA版本信息
                    version_mappings = mapping_data.get('version_mappings', {})
                    jira_info = version_mappings.get(jira_version_id, {})
                    jira_name = jira_info.get('jira_name', '未知')
                    
                    print(f"✅ '{notion_version}' -> JIRA版本ID: {jira_version_id} ('{jira_name}')")
                else:
                    default_id = mapping_data.get('default_version_id', 'N/A')
                    print(f"⚠️  '{notion_version}' -> 使用默认版本ID: {default_id}")
            
            print("=" * 80)
            
            # 测试特定的Network v6.3映射
            print("\n🎯 专门测试 'network 6.3' 映射...")
            network_63_id = await self.version_mapper.get_jira_version_id("network 6.3")
            
            if network_63_id == "10879":
                print("🎉 'network 6.3' 正确映射到 Network v6.3 (ID: 10879)")
                return True
            else:
                print(f"❌ 'network 6.3' 映射错误，期望: 10879, 实际: {network_63_id}")
                return False
                
        except Exception as e:
            print(f"❌ 版本映射测试失败: {e}")
            logger.exception("测试异常")
            return False

    async def show_mapping_summary(self):
        """显示映射配置摘要"""
        try:
            mapping_data = await self.version_mapper.load_mapping()
            version_mappings = mapping_data.get('version_mappings', {})
            
            print(f"\n📊 版本映射配置摘要:")
            print(f"默认版本ID: {mapping_data.get('default_version_id', 'N/A')}")
            print(f"总版本数: {len(version_mappings)}")
            
            # 统计有映射的版本
            mapped_count = sum(1 for v in version_mappings.values() if v.get('notion_names'))
            print(f"已配置映射: {mapped_count}")
            print(f"未配置映射: {len(version_mappings) - mapped_count}")
            
            # 显示前10个有映射的版本
            print(f"\n前10个已配置映射的版本:")
            print("-" * 60)
            count = 0
            for version_id, version_info in version_mappings.items():
                if version_info.get('notion_names') and count < 10:
                    jira_name = version_info.get('jira_name', 'N/A')
                    notion_names = version_info.get('notion_names', [])
                    print(f"{jira_name} (ID: {version_id})")
                    print(f"  -> Notion映射: {notion_names}")
                    count += 1
                    
        except Exception as e:
            print(f"❌ 显示映射摘要失败: {e}")

async def main():
    """主函数"""
    print("🚀 版本映射测试工具")
    print("=" * 50)
    
    tester = VersionMappingTester()
    
    # 显示配置摘要
    await tester.show_mapping_summary()
    
    # 执行测试
    success = await tester.test_version_mapping()
    
    if success:
        print("\n✅ 版本映射测试通过！")
        print("💡 'network 6.3' 能正确映射到 JIRA 'Network v6.3' 版本")
        return 0
    else:
        print("\n❌ 版本映射测试失败！")
        print("💡 请检查版本映射配置")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)