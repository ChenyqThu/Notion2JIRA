#!/usr/bin/env python3
"""
测试更新后的同步功能
验证版本映射和Notion状态回写功能
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
from services.version_mapper import VersionMapper


async def test_updated_sync():
    """测试更新后的同步功能"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_updated_sync")
    
    logger.info("开始测试更新后的同步功能")
    
    try:
        # 初始化客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 初始化同步服务
        sync_service = SyncService(settings, redis_client)
        await sync_service.initialize()
        
        print("✅ 同步服务初始化成功")
        
        # 测试版本映射功能
        print("\n=== 测试版本映射功能 ===")
        
        version_mapper = VersionMapper(settings)
        
        # 测试已存在的映射
        test_versions = ["Omada v6.1", "待评估版本", "不存在的版本"]
        
        for version_name in test_versions:
            version_id = await version_mapper.get_jira_version_id(version_name)
            print(f"   版本 '{version_name}' -> ID: {version_id}")
        
        # 测试字段映射器的版本提取
        print("\n=== 测试字段映射器版本提取 ===")
        
        field_mapper = FieldMapper(settings)
        
        # 模拟包含版本信息的Notion数据
        test_notion_data = {
            'page_id': 'test-page-001',
            'properties': {
                '计划版本': {
                    'value': ['Omada v6.1'],
                    'type': 'multi_select'
                }
            }
        }
        
        versions = await field_mapper._extract_version(test_notion_data)
        print(f"   提取到的版本: {versions}")
        
        # 测试完整的字段映射
        print("\n=== 测试完整字段映射 ===")
        
        full_notion_data = {
            'page_id': 'test-page-002',
            'properties': {
                '功能 Name': {
                    'value': '测试版本映射功能的需求',
                    'type': 'title'
                },
                '优先级 P': {
                    'value': '中 Medium',
                    'type': 'select'
                },
                'Status': {
                    'value': '待评估 UR',
                    'type': 'status'
                },
                '功能说明 Desc': {
                    'value': '这是一个测试版本映射功能的需求描述',
                    'type': 'rich_text'
                },
                '计划版本': {
                    'value': ['Omada v6.1'],
                    'type': 'multi_select'
                }
            },
            'raw_data': {
                'url': 'https://www.notion.so/test-page-002'
            }
        }
        
        jira_fields = await field_mapper.map_notion_to_jira(
            full_notion_data, 
            page_url=full_notion_data['raw_data']['url']
        )
        
        print(f"   映射结果:")
        print(f"     标题: {jira_fields.get('summary')}")
        print(f"     优先级: {jira_fields.get('priority')}")
        print(f"     版本: {jira_fields.get('fixVersions')}")
        print(f"     分配人员: {jira_fields.get('assignee')}")
        print(f"     描述长度: {len(jira_fields.get('description', ''))}")
        
        # 测试同步消息处理（模拟更新操作）
        print("\n=== 测试同步消息处理（更新操作） ===")
        
        # 构造测试消息（模拟更新现有JIRA Issue）
        test_message = {
            "id": "test-update-message-001",
            "timestamp": 1748345521202,
            "data": {
                "type": "notion_to_jira_create",  # 会根据JIRA Card字段判断是创建还是更新
                "event_data": {
                    "page_id": "20015375-830d-8051-9b72-d3fcec2b7ef4",  # 这个页面已有JIRA Card
                    "database_id": "19a15375-830d-81cb-b107-f8131b2d4cc0",
                    "last_edited_time": "2025-05-27T12:00:00.000Z",
                    "properties": {
                        "功能 Name": {
                            "value": "测试更新操作和版本映射",
                            "type": "title"
                        },
                        "优先级 P": {
                            "value": "高 High",
                            "type": "select"
                        },
                        "Status": {
                            "value": "同步中 SYNC",
                            "type": "status"
                        },
                        "功能说明 Desc": {
                            "value": "这是一个测试更新操作和版本映射的需求描述，包含新的版本信息",
                            "type": "rich_text"
                        },
                        "计划版本": {
                            "value": ["Omada v6.1"],
                            "type": "multi_select"
                        }
                    },
                    "raw_data": {
                        "url": "https://www.notion.so/20015375830d80519b72d3fcec2b7ef4"
                    }
                }
            }
        }
        
        print(f"   处理测试消息: {test_message['id']}")
        print(f"   页面ID: {test_message['data']['event_data']['page_id']}")
        print(f"   操作类型: 检查JIRA Card字段决定创建或更新")
        
        try:
            # 处理消息
            await sync_service._process_message(test_message)
            print("   ✅ 消息处理成功")
        except Exception as e:
            print(f"   ❌ 消息处理失败: {str(e)}")
            import traceback
            print(f"   错误详情: {traceback.format_exc()}")
        
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
    print("=== 更新后同步功能测试 ===\n")
    
    success = await test_updated_sync()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 