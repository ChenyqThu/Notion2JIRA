#!/usr/bin/env python3
"""
测试新的同步逻辑（基于Notion页面JIRA Card字段判断创建还是更新）
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.redis_client import RedisClient
from services.field_mapper import FieldMapper
from services.jira_client import JiraClient
from services.notion_client import NotionClient
from services.sync_service import SyncService


async def test_new_sync_logic():
    """测试新的同步逻辑"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_new_sync_logic")
    
    logger.info("开始测试新的同步逻辑")
    
    try:
        # 初始化客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 初始化同步服务
        sync_service = SyncService(settings, redis_client)
        await sync_service.initialize()
        
        print("✅ 同步服务初始化成功")
        
        # 测试JIRA URL解析功能
        print("\n=== 测试JIRA URL解析功能 ===")
        test_urls = [
            "http://rdjira.tp-link.com/browse/SMBNET-216",
            "http://rdjira.tp-link.com/browse/SMBEAP-123",
            "invalid-url",
            None,
            ""
        ]
        
        for url in test_urls:
            result = sync_service._parse_jira_url(url)
            if result:
                project_key, issue_key = result
                print(f"   URL: {url} -> 项目: {project_key}, Issue: {issue_key}")
            else:
                print(f"   URL: {url} -> 解析失败")
        
        # 测试获取Notion页面JIRA Card字段
        print("\n=== 测试获取Notion页面JIRA Card字段 ===")
        test_page_id = "20015375-830d-8051-9b72-d3fcec2b7ef4"
        
        if sync_service.notion_client:
            jira_card_url = await sync_service._get_notion_jira_card(test_page_id)
            if jira_card_url:
                print(f"   页面 {test_page_id} 的JIRA Card: {jira_card_url}")
                
                # 解析JIRA链接
                jira_info = sync_service._parse_jira_url(jira_card_url)
                if jira_info:
                    project_key, issue_key = jira_info
                    print(f"   解析结果: 项目={project_key}, Issue={issue_key}")
                else:
                    print(f"   JIRA链接解析失败")
            else:
                print(f"   页面 {test_page_id} 没有JIRA Card或获取失败")
        else:
            print("   未配置Notion客户端，跳过测试")
        
        # 模拟同步消息处理
        print("\n=== 测试同步消息处理 ===")
        
        # 构造测试消息
        test_message = {
            "id": "test-message-001",
            "timestamp": 1748345521202,
            "data": {
                "type": "notion_to_jira_create",
                "event_data": {
                    "page_id": test_page_id,
                    "database_id": "19a15375-830d-81cb-b107-f8131b2d4cc0",
                    "last_edited_time": "2025-05-27T09:58:00.000Z",
                    "properties": {
                        "功能 Name": {
                            "value": "测试新同步逻辑的需求",
                            "type": "title"
                        },
                        "优先级 P": {
                            "value": "中 Medium",
                            "type": "select"
                        },
                        "Status": {
                            "value": "待评估 UR",
                            "type": "status"
                        },
                        "功能说明 Desc": {
                            "value": "这是一个测试新同步逻辑的需求描述",
                            "type": "rich_text"
                        }
                    },
                    "raw_data": {
                        "url": f"https://www.notion.so/{test_page_id.replace('-', '')}"
                    }
                }
            }
        }
        
        print(f"   处理测试消息: {test_message['id']}")
        
        try:
            # 处理消息
            await sync_service._process_message(test_message)
            print("   ✅ 消息处理成功")
        except Exception as e:
            print(f"   ❌ 消息处理失败: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        print(f"❌ 测试失败: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'sync_service' in locals():
            await sync_service.stop()
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    print("=== 新同步逻辑测试 ===\n")
    
    success = await test_new_sync_logic()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 