#!/usr/bin/env python3
"""
分析Redis队列中的真实消息数据结构
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


async def analyze_real_message():
    """分析真实的消息数据结构"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("analyze_real_message")
    
    # 设置DEBUG日志级别
    import logging
    logging.getLogger("field_mapper").setLevel(logging.DEBUG)
    
    logger.info("开始分析真实消息数据结构")
    
    try:
        # 初始化Redis客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 检查同步映射中的最新数据
        # 从Redis中获取最新的同步映射信息
        mapping_keys = await redis_client.redis.keys("sync_mapping:*")
        logger.info(f"找到 {len(mapping_keys)} 个同步映射")
        
        if mapping_keys:
            # 获取最新的映射
            latest_key = mapping_keys[-1]  # 获取最后一个
            page_id = latest_key.decode().replace("sync_mapping:", "")
            logger.info(f"分析最新同步的页面: {page_id}")
        else:
            page_id = "20015375-830d-8051-9b72-d3fcec2b7ef4"  # 使用已知的页面ID
            logger.info(f"使用已知页面ID进行分析: {page_id}")
        
        # 检查失败队列中的消息
        failed_queue_length = await redis_client.get_queue_length("failed_sync_queue")
        logger.info(f"失败队列长度: {failed_queue_length}")
        
        # 检查主队列
        queue_length = await redis_client.get_queue_length("sync_queue")
        logger.info(f"主队列长度: {queue_length}")
        
        # 尝试从webhook原始数据中获取信息
        # 检查是否有原始webhook数据存储
        webhook_data_key = f"webhook_data:{page_id}"
        webhook_data = await redis_client.redis.get(webhook_data_key)
        
        if webhook_data:
            logger.info("从webhook原始数据获取信息")
            webhook_json = json.loads(webhook_data)
            event_data = webhook_json
        else:
            logger.warning("未找到webhook原始数据，尝试构造测试数据")
            # 如果没有原始数据，我们需要手动触发一个webhook来获取数据
            event_data = None
        
        if event_data is None:
            logger.error("无法获取事件数据，无法进行分析")
            return False
        
        # 分析消息结构
        if isinstance(event_data, dict) and "event_data" in event_data:
            # 如果是完整的webhook消息结构
            actual_event_data = event_data.get("event_data", {})
            page_id = actual_event_data.get("page_id")
            properties = actual_event_data.get("properties", {})
        else:
            # 如果直接是event_data
            page_id = event_data.get("page_id")
            properties = event_data.get("properties", {})
        
        logger.info(f"页面ID: {page_id}")
        logger.info(f"属性字段数量: {len(properties)}")
        logger.info(f"属性字段名称: {list(properties.keys())}")
        
        # 打印完整的原始数据结构
        logger.info("=== 完整原始数据结构 ===")
        logger.info(json.dumps(event_data, ensure_ascii=False, indent=2))
        
        # 重点分析 '功能 Name' 字段
        if '功能 Name' in properties:
            name_field = properties['功能 Name']
            logger.info(f"\n=== '功能 Name' 字段详细分析 ===")
            logger.info(f"类型: {type(name_field)}")
            logger.info(f"完整内容: {json.dumps(name_field, ensure_ascii=False, indent=2)}")
            
            # 尝试提取标题
            if isinstance(name_field, dict):
                logger.info(f"字段类型标识: {name_field.get('type')}")
                logger.info(f"是否包含title: {'title' in name_field}")
                
                if 'title' in name_field:
                    title_array = name_field['title']
                    logger.info(f"title数组: {title_array}")
                    logger.info(f"title数组长度: {len(title_array) if title_array else 0}")
                    
                    if title_array and len(title_array) > 0:
                        first_title = title_array[0]
                        logger.info(f"第一个title元素: {json.dumps(first_title, ensure_ascii=False, indent=2)}")
                        
                        plain_text = first_title.get('plain_text', '')
                        logger.info(f"提取的plain_text: '{plain_text}'")
                        logger.info(f"plain_text长度: {len(plain_text)}")
                        logger.info(f"plain_text是否为空: {not plain_text.strip()}")
        else:
            logger.warning("未找到 '功能 Name' 字段")
        
        # 分析其他重要字段
        important_fields = ['功能说明 Desc', '需求整理', '需求场景 Scenario', 'Status', '优先级 P']
        for field_name in important_fields:
            if field_name in properties:
                field_data = properties[field_name]
                logger.info(f"\n=== '{field_name}' 字段分析 ===")
                logger.info(f"类型: {type(field_data)}")
                logger.info(f"内容: {json.dumps(field_data, ensure_ascii=False, indent=2)}")
        
        # 构建测试数据
        notion_data = {
            'page_id': page_id,
            'properties': properties,
            'url': f"https://notion.so/{page_id.replace('-', '') if page_id else 'unknown'}"
        }
        
        # 初始化字段映射器并测试
        field_mapper = FieldMapper(settings)
        
        logger.info("开始测试字段映射...")
        try:
            jira_fields = await field_mapper.map_notion_to_jira(notion_data, page_url=notion_data['url'])
            logger.info("字段映射成功")
            logger.info(f"映射结果: {json.dumps(jira_fields, ensure_ascii=False, indent=2)}")
        except Exception as e:
            logger.error(f"字段映射失败: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"分析过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    print("=== 真实消息数据结构分析 ===\n")
    
    success = await analyze_real_message()
    
    if success:
        print("✅ 分析完成")
        return 0
    else:
        print("❌ 分析失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 