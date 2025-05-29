#!/usr/bin/env python3
"""
测试创建新的JIRA Issue（使用修复后的字段映射器）
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


async def test_new_jira_creation():
    """测试创建新的JIRA Issue"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_new_jira_creation")
    
    logger.info("开始测试创建新的JIRA Issue")
    
    try:
        # 初始化客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        jira_client = JiraClient(settings)
        await jira_client.initialize()
        
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
                
                # 构建测试数据
                notion_data = {
                    'page_id': page_id,
                    'properties': event_data.get('properties', {}),
                    'raw_data': event_data.get('raw_data', {}),
                    'url': event_data.get('raw_data', {}).get('url')
                }
                
                print("\n=== 测试新的JIRA Issue创建 ===")
                
                # 1. 字段映射
                print("1. 字段映射...")
                jira_fields = await field_mapper.map_notion_to_jira(notion_data, page_url=notion_data.get('url'))
                
                print(f"   标题: {jira_fields.get('summary')}")
                print(f"   优先级: {jira_fields.get('priority', {}).get('id')}")
                print(f"   分配人员: {jira_fields.get('assignee', {}).get('name')}")
                print(f"   描述长度: {len(jira_fields.get('description', ''))}")
                
                # 显示描述内容的前300字符
                description = jira_fields.get('description', '')
                if description:
                    print(f"   描述预览: {description[:300]}...")
                
                # 2. 验证必填字段
                print("\n2. 验证必填字段...")
                missing_fields = field_mapper.validate_required_fields(jira_fields)
                if missing_fields:
                    print(f"   ❌ 缺少必填字段: {missing_fields}")
                    return False
                else:
                    print("   ✅ 所有必填字段都已填充")
                
                # 3. 创建JIRA Issue
                print("\n3. 创建JIRA Issue...")
                jira_result = await jira_client.create_issue(jira_fields)
                
                if jira_result:
                    issue_key = jira_result.get('key')
                    issue_id = jira_result.get('id')
                    browse_url = jira_result.get('browse_url')
                    
                    print(f"   ✅ JIRA Issue创建成功")
                    print(f"   Issue Key: {issue_key}")
                    print(f"   Issue ID: {issue_id}")
                    print(f"   浏览链接: {browse_url}")
                    
                    # 4. 立即验证创建的Issue
                    print("\n4. 验证创建的Issue...")
                    issue_details = await jira_client.get_issue(issue_key)
                    
                    if issue_details:
                        fields = issue_details.get('fields', {})
                        
                        print(f"   标题: {fields.get('summary')}")
                        print(f"   优先级: {fields.get('priority', {}).get('name')}")
                        
                        assignee = fields.get('assignee')
                        if assignee:
                            print(f"   分配人员: {assignee.get('displayName')} ({assignee.get('name')})")
                        else:
                            print(f"   分配人员: 未分配")
                        
                        description = fields.get('description', '')
                        print(f"   描述长度: {len(description)} 字符")
                        
                        # 检查关键内容
                        expected_content = [
                            "这是一条测试的需求",
                            "需求说明",
                            "需求整理(AI)",
                            "酒店投屏解决方案",
                            "原始需求链接"
                        ]
                        
                        print(f"\n   内容验证:")
                        for content in expected_content:
                            if content in description or content in fields.get('summary', ''):
                                print(f"     ✅ 包含: {content}")
                            else:
                                print(f"     ❌ 缺少: {content}")
                    
                    print(f"\n🎉 新JIRA Issue创建和验证完成！")
                    print(f"   Issue Key: {issue_key}")
                    print(f"   浏览链接: {browse_url}")
                    
                    return True
                else:
                    print("   ❌ JIRA Issue创建失败")
                    return False
        else:
            logger.warning("队列为空，无法测试")
            print("❌ 队列为空，无法测试")
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
        if 'jira_client' in locals():
            await jira_client.close()


async def main():
    """主函数"""
    print("=== 新JIRA Issue创建测试 ===\n")
    
    success = await test_new_jira_creation()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 