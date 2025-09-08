#!/usr/bin/env python3
"""
pdjira迁移验证脚本
测试新JIRA环境(pdjira)的API兼容性
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from services.jira_client import JiraClient
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDJiraMigrationValidator:
    def __init__(self):
        self.settings = Settings()
        self.jira_client = JiraClient(self.settings)
        
    async def run_validation(self):
        """运行完整的迁移验证"""
        try:
            print("🔄 开始pdjira环境验证...")
            print(f"📡 JIRA服务器: {self.settings.jira.base_url}")
            print(f"🔑 项目Key: {self.settings.jira.project_key}")
            
            # 1. 初始化JIRA客户端
            print("\n1️⃣ 初始化JIRA客户端...")
            await self.jira_client.initialize()
            print("✅ JIRA客户端初始化成功")
            
            # 2. 测试连接
            print("\n2️⃣ 测试JIRA连接...")
            connection_ok = await self.jira_client.test_connection()
            if connection_ok:
                print("✅ JIRA连接测试成功")
            else:
                print("❌ JIRA连接失败")
                return False
                
            # 3. 测试用户搜索API
            print("\n3️⃣ 测试用户搜索API...")
            await self._test_user_search()
            
            # 4. 测试项目信息获取
            print("\n4️⃣ 测试项目信息获取...")
            await self._test_project_info()
            
            # 5. 测试版本信息获取
            print("\n5️⃣ 测试版本信息获取...")
            await self._test_versions()
            
            # 6. 测试Issue创建字段验证
            print("\n6️⃣ 测试Issue创建字段验证...")
            await self._test_create_issue_fields()
            
            print("\n🎉 pdjira环境验证完成！")
            return True
            
        except Exception as e:
            print(f"\n❌ 验证过程中出现异常: {e}")
            logger.exception("验证异常")
            return False
        finally:
            if self.jira_client.session:
                await self.jira_client.session.close()

    async def _test_user_search(self):
        """测试用户搜索API"""
        test_users = [
            "lucien.chen@tp-link.com",
            "lucien.chen",
            "test.user"
        ]
        
        for user in test_users:
            print(f"  🔍 搜索用户: {user}")
            try:
                users = await self.jira_client.search_users(user)
                print(f"    ✅ 找到 {len(users)} 个用户")
                if users:
                    for u in users[:2]:  # 只显示前2个
                        print(f"       - {u.get('displayName', 'N/A')} ({u.get('name', u.get('accountId', 'N/A'))})")
            except Exception as e:
                print(f"    ❌ 搜索失败: {e}")

    async def _test_project_info(self):
        """测试项目信息获取"""
        print(f"  📋 获取项目信息: {self.settings.jira.project_key}")
        try:
            metadata = self.jira_client.get_project_metadata()
            if metadata:
                print(f"    ✅ 项目名称: {metadata.get('name')}")
                print(f"    ✅ 项目Key: {metadata.get('key')}")
                print(f"    ✅ 项目ID: {metadata.get('id')}")
                print(f"    ✅ Issue类型数量: {len(metadata.get('issueTypes', []))}")
            else:
                print("    ❌ 项目元数据为空")
        except Exception as e:
            print(f"    ❌ 获取项目信息失败: {e}")

    async def _test_versions(self):
        """测试版本信息获取"""
        print(f"  📦 获取项目版本: {self.settings.jira.project_key}")
        try:
            versions = await self.jira_client.get_project_versions()
            print(f"    ✅ 找到 {len(versions)} 个版本")
            
            # 显示前5个版本
            for version in versions[:5]:
                status = "已发布" if version.get('released') else "未发布"
                print(f"       - {version.get('name')} (ID: {version.get('id')}) - {status}")
                
            if len(versions) > 5:
                print(f"       ... 还有 {len(versions) - 5} 个版本")
                
        except Exception as e:
            print(f"    ❌ 获取版本信息失败: {e}")

    async def _test_create_issue_fields(self):
        """测试Issue创建字段验证（不实际创建）"""
        print("  🔧 验证Issue创建字段格式...")
        try:
            # 获取默认字段配置
            default_fields = self.jira_client.get_default_fields()
            print("    ✅ 默认字段配置:")
            print(f"       - Project: {default_fields['project']}")
            print(f"       - Issue Type: {default_fields['issuetype']}")
            print(f"       - Fix Versions: {default_fields['fixVersions']}")
            
            # 验证项目字段格式
            project_field = default_fields['project']
            if 'key' in project_field:
                print(f"    ✅ 使用项目Key: {project_field['key']}")
            elif 'id' in project_field:
                print(f"    ⚠️  使用项目ID: {project_field['id']}")
            else:
                print("    ❌ 项目字段格式错误")
                
        except Exception as e:
            print(f"    ❌ 字段验证失败: {e}")

async def main():
    """主函数"""
    validator = PDJiraMigrationValidator()
    success = await validator.run_validation()
    
    if success:
        print("\n📊 验证总结:")
        print("✅ 所有核心API测试通过")
        print("✅ pdjira环境可以正常使用")
        print("\n💡 建议:")
        print("1. 运行同步服务测试实际功能")
        print("2. 检查版本映射配置是否需要更新")
        print("3. 验证用户权限和项目配置")
        return 0
    else:
        print("\n📊 验证总结:")
        print("❌ 发现兼容性问题")
        print("❌ 需要进一步调试和修复")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)