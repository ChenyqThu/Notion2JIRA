#!/usr/bin/env python3
"""
检查Redis队列中的消息内容
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


async def inspect_queue():
    """检查队列中的消息"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("inspect_queue")
    
    logger.info("开始检查Redis队列")
    
    try:
        # 初始化Redis客户端
        redis_client = RedisClient(settings)
        await redis_client.connect()
        
        # 检查主队列长度
        queue_length = await redis_client.get_queue_length("sync_queue")
        logger.info(f"sync_queue队列长度: {queue_length}")
        
        # 检查失败队列长度
        failed_queue_length = await redis_client.get_queue_length("failed_sync_queue")
        logger.info(f"failed_sync_queue队列长度: {failed_queue_length}")
        
        if queue_length == 0 and failed_queue_length == 0:
            logger.info("所有队列都为空")
            return True
        
        # 检查主队列
        if queue_length > 0:
            logger.info("\n=== 检查主队列 sync_queue ===")
            await inspect_queue_messages(redis_client, "sync_queue", queue_length)
        
        # 检查失败队列
        if failed_queue_length > 0:
            logger.info("\n=== 检查失败队列 failed_sync_queue ===")
            await inspect_queue_messages(redis_client, "failed_sync_queue", failed_queue_length)
        
        return True
        
    except Exception as e:
        logger.error(f"检查队列过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'redis_client' in locals():
            await redis_client.disconnect()


async def inspect_queue_messages(redis_client, queue_name, queue_length):
    """检查指定队列中的消息"""
    logger = get_logger("inspect_queue")
    
    # 获取消息但不移除（使用Redis的LINDEX命令）
    for i in range(min(queue_length, 5)):  # 最多查看5条消息
        try:
            # 直接使用Redis命令查看消息
            message_data = await redis_client.redis.lindex(queue_name, i)
            if message_data:
                message = json.loads(message_data)
                logger.info(f"\n=== 消息 {i+1} ===")
                logger.info(f"消息ID: {message.get('id')}")
                logger.info(f"时间戳: {message.get('timestamp')}")
                
                # 处理不同的消息结构
                if "message" in message:
                    # 失败队列的消息结构
                    original_message = message["message"]
                    data = original_message.get("data", {})
                    event_data = data.get("event_data", {})
                    logger.info(f"错误信息: {message.get('error')}")
                    logger.info(f"重试次数: {message.get('retry_count', 0)}")
                else:
                    # 正常队列的消息结构
                    data = message.get("data", {})
                    event_data = data.get("event_data", {})
                
                logger.info(f"事件类型: {data.get('type')}")
                logger.info(f"页面ID: {event_data.get('page_id')}")
                logger.info(f"数据库ID: {event_data.get('database_id')}")
                
                properties = event_data.get("properties", {})
                logger.info(f"属性字段数量: {len(properties)}")
                logger.info(f"属性字段名称: {list(properties.keys())}")
                
                # 打印前3个属性的详细信息
                for j, (field_name, field_data) in enumerate(list(properties.items())[:3]):
                    logger.info(f"字段 '{field_name}': {json.dumps(field_data, ensure_ascii=False, indent=2)}")
                
                if len(properties) > 3:
                    logger.info(f"... 还有 {len(properties) - 3} 个字段")
                
        except Exception as e:
            logger.error(f"解析消息 {i+1} 失败: {str(e)}")


async def main():
    """主函数"""
    print("=== Redis队列检查工具 ===\n")
    
    success = await inspect_queue()
    
    if success:
        print("✅ 检查完成")
        return 0
    else:
        print("❌ 检查失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 