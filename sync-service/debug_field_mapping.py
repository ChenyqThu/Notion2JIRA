#!/usr/bin/env python3
"""
调试字段映射功能
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.field_mapper import FieldMapper
from services.redis_client import RedisClient


async def debug_field_mapping():
    """调试字段映射功能"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("debug_field_mapping")
    
    # 设置DEBUG日志级别
    import logging
    logging.getLogger("field_mapper").setLevel(logging.DEBUG)
    
    logger.info("开始调试字段映射功能")
    
    try:
        # 初始化Redis客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 从Redis队列中获取最新的消息
        message = await redis_client.pop_from_queue("sync_queue", timeout=1)
        
        if not message:
            logger.warning("队列中没有消息，创建测试数据")
            # 创建测试数据
            test_notion_data = {
                'page_id': 'test-debug-12345',
                'properties': {
                    '功能 Name': {
                        'title': [
                            {
                                'plain_text': '调试测试功能'
                            }
                        ]
                    },
                    '功能说明 Desc': {
                        'rich_text': [
                            {
                                'plain_text': '这是一个调试测试功能的描述'
                            }
                        ]
                    },
                    '优先级 P': {
                        'select': {
                            'name': '中 Medium'
                        }
                    }
                },
                'url': 'https://notion.so/test-debug-12345'
            }
        else:
            logger.info(f"从队列获取到消息: {message.get('id')}")
            
            # 解析消息数据
            data = message.get("data", {})
            event_data = data.get("event_data", {})
            
            test_notion_data = {
                'page_id': event_data.get("page_id"),
                'properties': event_data.get("properties", {}),
                'raw_properties': event_data.get("raw_properties", {}),
                'url': f"https://notion.so/{event_data.get('page_id', '').replace('-', '')}"
            }
            
            logger.info(f"解析的Notion数据页面ID: {test_notion_data['page_id']}")
            logger.info(f"属性字段数量: {len(test_notion_data['properties'])}")
            logger.info(f"属性字段名称: {list(test_notion_data['properties'].keys())}")
            
            # 打印详细的属性数据
            for field_name, field_data in test_notion_data['properties'].items():
                logger.info(f"字段 '{field_name}': {json.dumps(field_data, ensure_ascii=False, indent=2)}")
        
        # 初始化字段映射器
        field_mapper = FieldMapper(settings)
        
        # 执行字段映射
        logger.info("开始执行字段映射...")
        jira_fields = await field_mapper.map_notion_to_jira(
            test_notion_data, 
            page_url=test_notion_data['url']
        )
        
        logger.info("字段映射成功完成")
        logger.info(f"映射结果: {json.dumps(jira_fields, ensure_ascii=False, indent=2)}")
        
        # 验证必填字段
        missing_fields = field_mapper.validate_required_fields(jira_fields)
        if missing_fields:
            logger.error(f"缺少必填字段: {missing_fields}")
        else:
            logger.info("✅ 所有必填字段验证通过")
        
        return True
        
    except Exception as e:
        logger.error(f"调试过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    print("=== 字段映射调试工具 ===\n")
    
    success = await debug_field_mapping()
    
    if success:
        print("✅ 调试完成")
        return 0
    else:
        print("❌ 调试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 