#!/usr/bin/env python3
"""
调试脚本：查看Redis中的同步字段数据
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import Settings
from services.redis_client import RedisClient


async def debug_redis_fields():
    """调试Redis中的字段数据"""
    
    # 初始化配置和Redis客户端
    settings = Settings()
    redis_client = RedisClient(settings)
    
    try:
        await redis_client.connect()
        print("✅ Redis连接成功")
        
        # 1. 查看队列中的消息
        print("\n" + "="*60)
        print("📋 查看队列中的消息")
        print("="*60)
        
        queue_length = await redis_client.get_queue_length("sync_queue")
        print(f"队列长度: {queue_length}")
        
        if queue_length > 0:
            # 查看队列中的消息（不弹出）
            client = redis_client.client
            messages = await client.lrange("sync_queue", 0, -1)
            
            for i, msg_json in enumerate(messages):
                print(f"\n--- 消息 {i+1} ---")
                try:
                    message = json.loads(msg_json)
                    await analyze_message_fields(message)
                except Exception as e:
                    print(f"解析消息失败: {e}")
        
        # 2. 查看映射关系
        print("\n" + "="*60)
        print("🔗 查看同步映射关系")
        print("="*60)
        
        # 获取所有映射键
        mapping_keys = []
        async for key in redis_client.client.scan_iter(match="sync_mapping:*"):
            mapping_keys.append(key)
        
        print(f"找到 {len(mapping_keys)} 个映射关系:")
        
        for key in mapping_keys:
            mapping_data = await redis_client.get_cache(key)
            if mapping_data:
                notion_page_id = key.replace("sync_mapping:", "")
                print(f"  📄 Notion页面: {notion_page_id}")
                print(f"  🎫 JIRA Issue: {mapping_data.get('jira_issue_key')}")
                print(f"  📅 创建时间: {mapping_data.get('created_at')}")
                print(f"  🔄 最后同步: {mapping_data.get('last_sync')}")
                print()
        
        # 3. 查看失败队列
        print("\n" + "="*60)
        print("❌ 查看失败队列")
        print("="*60)
        
        failed_length = await redis_client.get_queue_length("failed_sync_queue")
        print(f"失败队列长度: {failed_length}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await redis_client.disconnect()


async def analyze_message_fields(message):
    """分析消息中的字段数据"""
    
    print(f"消息ID: {message.get('id')}")
    print(f"时间戳: {message.get('timestamp')}")
    print(f"优先级: {message.get('priority')}")
    
    data = message.get("data", {})
    event_data = data.get("event_data", {})
    
    print(f"事件类型: {data.get('type')}")
    print(f"页面ID: {event_data.get('page_id')}")
    print(f"数据库ID: {event_data.get('database_id')}")
    print(f"最后编辑时间: {event_data.get('last_edited_time')}")
    print(f"同步标志: {event_data.get('sync2jira')}")
    
    # 分析properties字段
    properties = event_data.get("properties", {})
    raw_properties = event_data.get("raw_properties", {})
    
    print(f"\n📊 字段统计:")
    print(f"  解析后字段数量: {len(properties)}")
    print(f"  原始字段数量: {len(raw_properties)}")
    
    print(f"\n🔍 解析后的字段详情:")
    for field_name, field_data in properties.items():
        field_type = field_data.get("type", "unknown")
        field_value = field_data.get("value")
        
        # 截断长值
        if isinstance(field_value, str) and len(field_value) > 50:
            display_value = field_value[:50] + "..."
        elif isinstance(field_value, list) and len(field_value) > 3:
            display_value = f"[列表，{len(field_value)}项]"
        else:
            display_value = field_value
            
        print(f"  📝 {field_name}")
        print(f"     类型: {field_type}")
        print(f"     值: {display_value}")
        print()
    
    # 显示一些关键字段的原始数据
    print(f"\n🔧 关键字段的原始数据:")
    key_fields = ["Function Name", "功能 Name", "Status", "优先级 P", "Description", "功能说明 Desc"]
    
    for field_name in key_fields:
        if field_name in raw_properties:
            raw_data = raw_properties[field_name]
            print(f"  📝 {field_name} (原始):")
            print(f"     {json.dumps(raw_data, ensure_ascii=False, indent=6)}")
            print()


def extract_and_display_fields(properties):
    """提取并显示关键字段"""
    
    print(f"\n🎯 提取的关键字段:")
    
    # 提取标题
    title_fields = ["Function Name", "功能 Name", "Name", "title", "标题"]
    title = "未找到"
    for field in title_fields:
        if field in properties:
            prop = properties[field]
            if prop.get("type") == "title":
                title = prop.get("value", "")
                break
    print(f"  📋 标题: {title}")
    
    # 提取状态
    status_fields = ["Status", "状态"]
    status = "未找到"
    for field in status_fields:
        if field in properties:
            prop = properties[field]
            if prop.get("type") in ["status", "select"]:
                status = prop.get("value", "")
                break
    print(f"  🔄 状态: {status}")
    
    # 提取优先级
    priority_fields = ["优先级 P", "Priority", "优先级"]
    priority = "未找到"
    for field in priority_fields:
        if field in properties:
            prop = properties[field]
            if prop.get("type") == "select":
                priority = prop.get("value", "")
                break
    print(f"  ⭐ 优先级: {priority}")
    
    # 提取描述
    desc_fields = ["Description", "功能说明 Desc", "需求整理", "描述"]
    description = "未找到"
    for field in desc_fields:
        if field in properties:
            prop = properties[field]
            if prop.get("type") == "rich_text":
                desc_value = prop.get("value", "")
                if len(desc_value) > 100:
                    description = desc_value[:100] + "..."
                else:
                    description = desc_value
                break
    print(f"  📝 描述: {description}")


if __name__ == "__main__":
    asyncio.run(debug_redis_fields()) 