#!/usr/bin/env python3
"""
测试完整的同步流程（包含修改后的字段映射和Notion回写）
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


async def test_complete_flow():
    """测试完整的同步流程"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_complete_flow")
    
    logger.info("开始测试完整的同步流程")
    
    try:
        # 初始化客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        jira_client = JiraClient(settings)
        await jira_client.initialize()
        
        field_mapper = FieldMapper(settings)
        
        # 初始化Notion客户端（如果配置了）
        notion_client = None
        if settings.notion.token:
            notion_client = NotionClient(settings)
            await notion_client.initialize()
            print("✅ Notion客户端初始化成功")
        else:
            print("⚠️  未配置Notion token，跳过Notion客户端初始化")
        
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
                raw_data = event_data.get("raw_data", {})
                notion_url = raw_data.get('url') or f"https://notion.so/{page_id.replace('-', '')}"
                
                notion_data = {
                    'page_id': page_id,
                    'properties': event_data.get('properties', {}),
                    'raw_data': raw_data,
                    'url': notion_url
                }
                
                print("\n=== 测试修改后的字段映射 ===")
                
                # 1. 字段映射测试
                print("1. 字段映射...")
                jira_fields = await field_mapper.map_notion_to_jira(notion_data, page_url=notion_data.get('url'))
                
                print(f"   标题: {jira_fields.get('summary')}")
                print(f"   优先级: {jira_fields.get('priority', {}).get('id')}")
                print(f"   分配人员: {jira_fields.get('assignee', {}).get('name')}")
                print(f"   版本: {jira_fields.get('fixVersions', [])}")
                print(f"   描述长度: {len(jira_fields.get('description', ''))}")
                
                # 检查是否移除了AI字段
                description = jira_fields.get('description', '')
                if "需求整理(AI)" in description:
                    print("   ❌ AI字段仍然存在于描述中")
                else:
                    print("   ✅ AI字段已成功移除")
                
                # 检查经办人是否为鲁定阳
                assignee = jira_fields.get('assignee', {}).get('name')
                if assignee == 'ludingyang@tp-link.com':
                    print("   ✅ 经办人已设置为鲁定阳")
                else:
                    print(f"   ❌ 经办人设置错误: {assignee}")
                
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
                    
                    # 4. 测试Notion回写（如果配置了）
                    if notion_client:
                        print("\n4. 测试Notion回写...")
                        
                        try:
                            # 更新JIRA Card URL
                            success1 = await notion_client.update_jira_card_url(page_id, browse_url)
                            if success1:
                                print("   ✅ JIRA Card URL更新成功")
                            else:
                                print("   ❌ JIRA Card URL更新失败")
                            
                            # 更新状态
                            success2 = await notion_client.update_status(page_id, "TODO")
                            if success2:
                                print("   ✅ 页面状态更新成功")
                            else:
                                print("   ❌ 页面状态更新失败")
                            
                            if success1 and success2:
                                print("   🎉 Notion回写完全成功！")
                            
                        except Exception as e:
                            print(f"   ❌ Notion回写异常: {str(e)}")
                    else:
                        print("\n4. 跳过Notion回写（未配置客户端）")
                    
                    # 5. 保存同步映射
                    print("\n5. 保存同步映射...")
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
                    
                    print(f"\n🎉 完整流程测试成功！")
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
        if 'jira_client' in locals():
            await jira_client.close()
        if 'notion_client' in locals() and notion_client:
            await notion_client.close()


async def main():
    """主函数"""
    print("=== 完整流程测试（修改后版本） ===\n")
    
    success = await test_complete_flow()
    
    if success:
        print("\n✅ 测试完成")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 