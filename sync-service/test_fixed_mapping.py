#!/usr/bin/env python3
"""
测试修复后的字段映射功能
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


async def test_fixed_mapping():
    """测试修复后的字段映射功能"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_fixed_mapping")
    
    # 设置DEBUG日志级别
    import logging
    logging.getLogger("field_mapper").setLevel(logging.DEBUG)
    
    logger.info("开始测试修复后的字段映射功能")
    
    try:
        # 初始化Redis客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 从队列中获取真实数据
        queue_length = await redis_client.get_queue_length("sync_queue")
        logger.info(f"队列长度: {queue_length}")
        
        if queue_length > 0:
            # 获取队列中的消息
            message_data = await redis_client.client.lindex("sync_queue", 0)
            if message_data:
                message = json.loads(message_data)
                event_data = message.get("data", {}).get("event_data", {})
                
                logger.info(f"获取到消息，页面ID: {event_data.get('page_id')}")
                
                # 构建测试数据
                notion_data = {
                    'page_id': event_data.get('page_id'),
                    'properties': event_data.get('properties', {}),
                    'raw_data': event_data.get('raw_data', {}),
                    'url': event_data.get('raw_data', {}).get('url')
                }
                
                # 初始化字段映射器并测试
                field_mapper = FieldMapper(settings)
                
                logger.info("开始测试字段映射...")
                
                # 测试各个字段提取
                print("\n=== 字段提取测试 ===")
                
                # 测试标题提取
                title = field_mapper._extract_title(notion_data)
                print(f"标题: {title}")
                
                # 测试优先级提取
                priority = field_mapper._extract_priority(notion_data)
                print(f"优先级: {priority}")
                
                # 测试状态提取
                status = field_mapper._extract_status(notion_data)
                print(f"状态: {status}")
                
                # 测试分配人员提取
                assignee = await field_mapper._extract_assignee(notion_data)
                print(f"分配人员: {assignee}")
                
                # 测试描述构建
                description = field_mapper._build_description(notion_data, notion_data.get('url'))
                print(f"描述长度: {len(description)}")
                print(f"描述预览: {description[:200]}...")
                
                # 完整字段映射测试
                print("\n=== 完整字段映射测试 ===")
                jira_fields = await field_mapper.map_notion_to_jira(notion_data, page_url=notion_data.get('url'))
                
                print("映射结果:")
                print(json.dumps(jira_fields, ensure_ascii=False, indent=2))
                
                # 验证必填字段
                missing_fields = field_mapper.validate_required_fields(jira_fields)
                if missing_fields:
                    print(f"\n❌ 缺少必填字段: {missing_fields}")
                else:
                    print("\n✅ 所有必填字段都已填充")
                
                return True
        else:
            logger.warning("队列为空，无法测试")
            return False
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    print("=== 修复后字段映射功能测试 ===\n")
    
    success = await test_fixed_mapping()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 