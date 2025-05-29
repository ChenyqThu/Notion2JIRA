#!/usr/bin/env python3
"""
验证JIRA Issue的内容
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.jira_client import JiraClient


async def verify_jira_issue():
    """验证JIRA Issue的内容"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("verify_jira_issue")
    
    logger.info("开始验证JIRA Issue内容")
    
    try:
        # 初始化JIRA客户端
        jira_client = JiraClient(settings)
        await jira_client.initialize()
        
        # 要验证的Issue Key
        issue_key = "SMBNET-216"
        
        print(f"=== 验证JIRA Issue: {issue_key} ===\n")
        
        # 获取Issue详情
        print("1. 获取Issue详情...")
        issue_details = await jira_client.get_issue(issue_key)
        
        if issue_details:
            print("   ✅ Issue获取成功")
            
            # 提取关键信息
            fields = issue_details.get('fields', {})
            
            print(f"\n2. Issue基本信息:")
            print(f"   Key: {issue_details.get('key')}")
            print(f"   ID: {issue_details.get('id')}")
            print(f"   标题: {fields.get('summary')}")
            print(f"   状态: {fields.get('status', {}).get('name')}")
            print(f"   类型: {fields.get('issuetype', {}).get('name')}")
            print(f"   项目: {fields.get('project', {}).get('name')}")
            
            # 优先级
            priority = fields.get('priority')
            if priority:
                print(f"   优先级: {priority.get('name')} (ID: {priority.get('id')})")
            else:
                print(f"   优先级: 未设置")
            
            # 分配人员
            assignee = fields.get('assignee')
            if assignee:
                print(f"   分配人员: {assignee.get('displayName')} ({assignee.get('name')})")
            else:
                print(f"   分配人员: 未分配")
            
            # 版本信息
            fix_versions = fields.get('fixVersions', [])
            if fix_versions:
                version_names = [v.get('name') for v in fix_versions]
                print(f"   修复版本: {', '.join(version_names)}")
            else:
                print(f"   修复版本: 未设置")
            
            # 描述
            description = fields.get('description', '')
            print(f"\n3. 描述内容:")
            print(f"   长度: {len(description)} 字符")
            if description:
                # 显示描述的前200个字符
                preview = description[:200] + "..." if len(description) > 200 else description
                print(f"   预览: {preview}")
                
                # 检查是否包含预期的内容
                expected_content = [
                    "需求说明",
                    "需求整理(AI)",
                    "原始需求链接",
                    "这是一条测试的需求",
                    "酒店投屏解决方案",
                    "notion.so"
                ]
                
                print(f"\n4. 内容验证:")
                for content in expected_content:
                    if content in description:
                        print(f"   ✅ 包含: {content}")
                    else:
                        print(f"   ❌ 缺少: {content}")
            else:
                print(f"   ❌ 描述为空")
            
            # 浏览链接
            browse_url = f"http://rdjira.tp-link.com/browse/{issue_key}"
            print(f"\n5. 浏览链接:")
            print(f"   {browse_url}")
            
            print(f"\n🎉 Issue验证完成！")
            return True
        else:
            print("   ❌ Issue获取失败")
            return False
        
    except Exception as e:
        logger.error(f"验证过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        print(f"❌ 验证失败: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'jira_client' in locals():
            await jira_client.close()


async def main():
    """主函数"""
    print("=== JIRA Issue内容验证 ===\n")
    
    success = await verify_jira_issue()
    
    if success:
        print("\n✅ 验证完成")
        return 0
    else:
        print("\n❌ 验证失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 