#!/usr/bin/env python3
"""
测试完整的同步流程
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


async def test_complete_sync():
    """测试完整的同步流程"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_complete_sync")
    
    logger.info("开始测试完整的同步流程")
    
    try:
        # 初始化客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        jira_client = JiraClient(settings)
        await jira_client.test_connection()
        
        field_mapper = FieldMapper(settings)
        
        # 从队列中获取真实数据
        queue_length = await redis_client.get_queue_length("sync_queue")
        logger.info(f"队列长度: {queue_length}")
        
        if queue_length > 0:
            # 获取队列中的消息
            message_data = await redis_client.client.lindex("sync_queue", 0)
            if message_data:
                message = json.loads(message_data)
                event_data = message.get("data", {}).get("event_data", {})
                
                page_id = event_data.get('page_id')
                logger.info(f"处理页面: {page_id}")
                
                # 检查是否已经同步过
                existing_mapping = await redis_client.get_sync_mapping(page_id)
                if existing_mapping:
                    logger.info(f"页面已同步过，JIRA Issue: {existing_mapping.get('jira_issue_key')}")
                    print(f"✅ 页面已同步，JIRA Issue: {existing_mapping.get('jira_issue_key')}")
                    print(f"   浏览链接: {existing_mapping.get('jira_browse_url')}")
                    return True
                
                # 构建测试数据
                notion_data = {
                    'page_id': page_id,
                    'properties': event_data.get('properties', {}),
                    'raw_data': event_data.get('raw_data', {}),
                    'url': event_data.get('raw_data', {}).get('url')
                }
                
                print("\n=== 开始完整同步流程 ===")
                
                # 1. 字段映射
                print("1. 字段映射...")
                jira_fields = await field_mapper.map_notion_to_jira(notion_data, page_url=notion_data.get('url'))
                
                print(f"   标题: {jira_fields.get('summary')}")
                print(f"   优先级: {jira_fields.get('priority', {}).get('id')}")
                print(f"   分配人员: {jira_fields.get('assignee', {}).get('name')}")
                print(f"   描述长度: {len(jira_fields.get('description', ''))}")
                
                # 2. 验证必填字段
                print("2. 验证必填字段...")
                missing_fields = field_mapper.validate_required_fields(jira_fields)
                if missing_fields:
                    print(f"   ❌ 缺少必填字段: {missing_fields}")
                    return False
                else:
                    print("   ✅ 所有必填字段都已填充")
                
                # 3. 创建JIRA Issue
                print("3. 创建JIRA Issue...")
                jira_result = await jira_client.create_issue(jira_fields)
                
                if jira_result:
                    issue_key = jira_result.get('key')
                    issue_id = jira_result.get('id')
                    browse_url = jira_result.get('browse_url')
                    
                    print(f"   ✅ JIRA Issue创建成功")
                    print(f"   Issue Key: {issue_key}")
                    print(f"   Issue ID: {issue_id}")
                    print(f"   浏览链接: {browse_url}")
                    
                    # 4. 保存同步映射
                    print("4. 保存同步映射...")
                    mapping_data = {
                        'jira_issue_key': issue_key,
                        'jira_issue_id': issue_id,
                        'jira_browse_url': browse_url,
                        'created_at': asyncio.get_event_loop().time(),
                        'last_sync': asyncio.get_event_loop().time(),
                        'status': 'synced'
                    }
                    
                    success = await redis_client.set_sync_mapping(page_id, mapping_data)
                    if success:
                        print("   ✅ 同步映射保存成功")
                    else:
                        print("   ❌ 同步映射保存失败")
                    
                    # 5. 从队列中移除消息
                    print("5. 清理队列...")
                    await redis_client.client.lpop("sync_queue")
                    print("   ✅ 消息已从队列移除")
                    
                    print(f"\n🎉 完整同步流程成功完成！")
                    print(f"   Notion页面: {page_id}")
                    print(f"   JIRA Issue: {issue_key}")
                    print(f"   浏览链接: {browse_url}")
                    
                    return True
                else:
                    print("   ❌ JIRA Issue创建失败")
                    return False
        else:
            logger.warning("队列为空，无法测试")
            print("❌ 队列为空，无法测试同步流程")
            return False
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        print(f"❌ 测试失败: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    print("=== 完整同步流程测试 ===\n")
    
    success = await test_complete_sync()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 