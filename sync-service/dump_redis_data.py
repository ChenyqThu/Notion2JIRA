#!/usr/bin/env python3
"""
导出Redis中的所有相关数据
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


async def dump_redis_data():
    """导出Redis中的所有相关数据"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("dump_redis_data")
    
    logger.info("开始导出Redis数据")
    
    try:
        # 初始化Redis客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        print("=== Redis数据导出 ===\n")
        
        # 1. 检查所有队列
        queues = ["sync_queue", "failed_sync_queue"]
        for queue_name in queues:
            length = await redis_client.get_queue_length(queue_name)
            print(f"队列 {queue_name}: {length} 条消息")
            
            if length > 0:
                for i in range(min(length, 3)):  # 最多显示3条
                    message_data = await redis_client.client.lindex(queue_name, i)
                    if message_data:
                        message = json.loads(message_data)
                        print(f"\n--- {queue_name} 消息 {i+1} ---")
                        print(json.dumps(message, ensure_ascii=False, indent=2))
        
        # 2. 检查同步映射
        mapping_keys = await redis_client.client.keys("sync_mapping:*")
        print(f"\n同步映射: {len(mapping_keys)} 个")
        
        for key in mapping_keys[-3:]:  # 显示最新的3个
            key_str = key if isinstance(key, str) else key.decode()
            page_id = key_str.replace("sync_mapping:", "")
            mapping_data = await redis_client.client.get(key)
            if mapping_data:
                mapping = json.loads(mapping_data)
                print(f"\n--- 映射 {page_id} ---")
                print(json.dumps(mapping, ensure_ascii=False, indent=2))
        
        # 3. 检查webhook原始数据
        webhook_keys = await redis_client.client.keys("webhook_data:*")
        print(f"\nWebhook原始数据: {len(webhook_keys)} 个")
        
        for key in webhook_keys[-2:]:  # 显示最新的2个
            key_str = key if isinstance(key, str) else key.decode()
            page_id = key_str.replace("webhook_data:", "")
            webhook_data = await redis_client.client.get(key)
            if webhook_data:
                webhook = json.loads(webhook_data)
                print(f"\n--- Webhook数据 {page_id} ---")
                print(json.dumps(webhook, ensure_ascii=False, indent=2))
        
        # 4. 检查其他可能的键
        all_keys = await redis_client.client.keys("*")
        other_keys = [k if isinstance(k, str) else k.decode() for k in all_keys if not any(prefix in (k if isinstance(k, str) else k.decode()) for prefix in ["sync_mapping:", "webhook_data:", "sync_queue", "failed_sync_queue"])]
        
        if other_keys:
            print(f"\n其他Redis键: {len(other_keys)} 个")
            for key in other_keys[:5]:  # 显示前5个
                data = await redis_client.client.get(key)
                if data:
                    try:
                        parsed_data = json.loads(data)
                        print(f"\n--- {key} ---")
                        print(json.dumps(parsed_data, ensure_ascii=False, indent=2))
                    except:
                        print(f"\n--- {key} (非JSON) ---")
                        print(data if isinstance(data, str) else data.decode())
        
        return True
        
    except Exception as e:
        logger.error(f"导出过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def main():
    """主函数"""
    success = await dump_redis_data()
    
    if success:
        print("\n✅ 导出完成")
        return 0
    else:
        print("\n❌ 导出失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 