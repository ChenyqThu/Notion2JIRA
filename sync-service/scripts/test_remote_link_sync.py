#!/usr/bin/env python3
"""
远程链接同步功能测试脚本
验证删除不需要的远程链接功能是否正常工作
"""

import asyncio
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

class RemoteLinkSyncTester:
    def __init__(self):
        self.settings = Settings()
        self.jira_client = JiraClient(self.settings)
        
    async def test_remote_link_sync(self):
        """测试远程链接同步功能"""
        try:
            print("🔄 开始远程链接同步测试...")
            
            # 初始化JIRA客户端
            await self.jira_client.initialize()
            
            # 测试Issue Key（请手动设置一个存在的Issue）
            test_issue_key = input("请输入要测试的JIRA Issue Key (如 SMBNET-123): ").strip()
            if not test_issue_key:
                print("❌ 未提供测试Issue Key，测试退出")
                return False
            
            print(f"📋 测试Issue: {test_issue_key}")
            
            # 1. 获取当前的远程链接
            print("\n1️⃣ 获取当前远程链接...")
            existing_links = await self.jira_client.get_existing_remote_links(test_issue_key)
            print(f"✅ 当前有 {len(existing_links)} 个远程链接")
            
            for i, link in enumerate(existing_links, 1):
                title = link.get('object', {}).get('title', 'N/A')
                url = link.get('object', {}).get('url', 'N/A')
                global_id = link.get('globalId', 'N/A')
                print(f"   {i}. {title} ({url}) [GlobalId: {global_id}]")
            
            # 2. 创建测试用的目标远程链接列表
            print("\n2️⃣ 准备测试用的目标远程链接...")
            test_links = [
                {
                    "globalId": "test-link-1",
                    "object": {
                        "url": "https://test.example.com/page1",
                        "title": "测试链接1",
                        "summary": "这是一个测试链接1"
                    }
                },
                {
                    "globalId": "test-link-2", 
                    "object": {
                        "url": "https://test.example.com/page2",
                        "title": "测试链接2",
                        "summary": "这是一个测试链接2"
                    }
                }
            ]
            
            print(f"📝 将同步 {len(test_links)} 个目标链接:")
            for link in test_links:
                print(f"   - {link['object']['title']} ({link['object']['url']})")
            
            # 3. 执行同步操作
            print("\n3️⃣ 执行远程链接同步...")
            confirm = input("确认要执行同步操作吗？这将删除不匹配的现有链接 (y/n): ").strip().lower()
            if confirm != 'y':
                print("⏹ 用户取消操作")
                return False
                
            success = await self.jira_client.sync_remote_links(test_issue_key, test_links)
            
            if success:
                print("✅ 远程链接同步成功")
            else:
                print("❌ 远程链接同步失败")
                return False
            
            # 4. 验证同步结果
            print("\n4️⃣ 验证同步结果...")
            await asyncio.sleep(2)  # 等待JIRA处理
            updated_links = await self.jira_client.get_existing_remote_links(test_issue_key)
            print(f"🔍 同步后有 {len(updated_links)} 个远程链接")
            
            for i, link in enumerate(updated_links, 1):
                title = link.get('object', {}).get('title', 'N/A')
                url = link.get('object', {}).get('url', 'N/A')
                global_id = link.get('globalId', 'N/A')
                print(f"   {i}. {title} ({url}) [GlobalId: {global_id}]")
            
            # 5. 清理测试数据
            print("\n5️⃣ 清理测试数据...")
            cleanup = input("是否要清理测试数据？(删除刚才创建的测试链接) (y/n): ").strip().lower()
            if cleanup == 'y':
                await self.jira_client.sync_remote_links(test_issue_key, [])
                print("🗑️ 测试数据清理完成")
            else:
                print("ℹ️ 保留测试数据，请手动清理")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中出现异常: {e}")
            logger.exception("测试异常")
            return False
        finally:
            if self.jira_client.session:
                await self.jira_client.session.close()

    async def test_link_deletion_only(self):
        """测试仅删除功能"""
        try:
            print("🗑️ 开始远程链接删除测试...")
            
            # 初始化JIRA客户端
            await self.jira_client.initialize()
            
            # 测试Issue Key
            test_issue_key = input("请输入要测试的JIRA Issue Key (如 SMBNET-123): ").strip()
            if not test_issue_key:
                print("❌ 未提供测试Issue Key，测试退出")
                return False
                
            # 获取现有链接
            existing_links = await self.jira_client.get_existing_remote_links(test_issue_key)
            
            if not existing_links:
                print("ℹ️ 该Issue没有远程链接，无法测试删除功能")
                return False
                
            print(f"📋 找到 {len(existing_links)} 个远程链接:")
            for i, link in enumerate(existing_links, 1):
                title = link.get('object', {}).get('title', 'N/A')
                print(f"   {i}. {title} (ID: {link.get('id')})")
            
            # 选择要删除的链接
            try:
                choice = int(input(f"选择要删除的链接编号 (1-{len(existing_links)}): "))
                if choice < 1 or choice > len(existing_links):
                    print("❌ 无效的选择")
                    return False
                    
                link_to_delete = existing_links[choice - 1]
                link_id = str(link_to_delete['id'])
                link_title = link_to_delete.get('object', {}).get('title', 'N/A')
                
                confirm = input(f"确认要删除链接 '{link_title}' (ID: {link_id}) 吗? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("⏹ 用户取消删除操作")
                    return False
                    
                # 执行删除
                success = await self.jira_client.delete_remote_link(test_issue_key, link_id)
                
                if success:
                    print(f"✅ 远程链接 '{link_title}' 删除成功")
                    return True
                else:
                    print(f"❌ 远程链接 '{link_title}' 删除失败")
                    return False
                    
            except ValueError:
                print("❌ 请输入有效的数字")
                return False
                
        except Exception as e:
            print(f"❌ 删除测试过程中出现异常: {e}")
            logger.exception("删除测试异常")
            return False
        finally:
            if self.jira_client.session:
                await self.jira_client.session.close()

async def main():
    """主函数"""
    print("🚀 远程链接同步功能测试工具")
    print("=" * 50)
    
    print("选择测试模式:")
    print("1. 完整同步测试 (创建、更新、删除)")
    print("2. 仅删除功能测试")
    
    try:
        choice = int(input("请选择 (1 或 2): ").strip())
        
        tester = RemoteLinkSyncTester()
        
        if choice == 1:
            success = await tester.test_remote_link_sync()
        elif choice == 2:
            success = await tester.test_link_deletion_only()
        else:
            print("❌ 无效选择")
            return 1
            
        if success:
            print("\n✅ 测试完成！")
            print("💡 远程链接同步功能工作正常")
            return 0
        else:
            print("\n❌ 测试失败！")
            print("💡 请检查错误日志并修复问题")
            return 1
            
    except ValueError:
        print("❌ 请输入有效的数字")
        return 1
    except KeyboardInterrupt:
        print("\n⏹ 用户中断测试")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)