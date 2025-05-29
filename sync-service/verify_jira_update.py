#!/usr/bin/env python3
"""
验证JIRA Issue更新结果
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from services.jira_client import JiraClient


async def check_issue():
    """检查JIRA Issue更新结果"""
    settings = Settings()
    jira_client = JiraClient(settings)
    await jira_client.initialize()
    
    try:
        issue = await jira_client.get_issue('SMBNET-217')
        
        print("=== JIRA Issue 更新验证 ===")
        print(f"Issue Key: {issue['key']}")
        print(f"Summary: {issue['fields']['summary']}")
        print(f"Priority: {issue['fields']['priority']['name']}")
        print(f"Assignee: {issue['fields']['assignee']['displayName']}")
        
        fix_versions = issue['fields']['fixVersions']
        if fix_versions:
            print(f"Fix Version: {fix_versions[0]['name']} (ID: {fix_versions[0]['id']})")
        else:
            print("Fix Version: None")
        
        print(f"Description length: {len(issue['fields']['description'])}")
        
        # 检查版本是否正确映射
        if fix_versions and fix_versions[0]['id'] == '14613':
            print("✅ 版本映射正确 - Omada v6.1")
        else:
            print("❌ 版本映射不正确")
        
        # 检查优先级是否正确
        if issue['fields']['priority']['id'] == '1':
            print("✅ 优先级映射正确 - Highest")
        else:
            print("❌ 优先级映射不正确")
            
    except Exception as e:
        print(f"❌ 获取Issue失败: {str(e)}")
    finally:
        await jira_client.close()


if __name__ == "__main__":
    asyncio.run(check_issue())
 