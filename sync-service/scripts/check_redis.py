#!/usr/bin/env python3
"""
Redis状态检查脚本
用于快速检查Redis连接状态、队列数据和系统信息
"""

import asyncio
import json
import sys
import os

# 添加sync-service到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import Settings
from services.redis_client import RedisClient


async def check_redis_status():
    """检查Redis状态和数据"""
    print("=" * 60)
    print("Redis状态检查工具")
    print("=" * 60)
    
    try:
        # 初始化配置和客户端
        settings = Settings()
        redis_client = RedisClient(settings)
        
        # 连接Redis
        print(f"正在连接Redis: {settings.redis.host}:{settings.redis.port}")
        await redis_client.connect()
        print("✅ Redis连接成功")
        
        # 1. 基本信息
        print("\n📊 Redis基本信息:")
        ping_result = await redis_client.ping()
        print(f"  PING测试: {'✅ 成功' if ping_result else '❌ 失败'}")
        
        # 2. 队列信息
        print("\n📋 队列状态:")
        
        # sync_queue
        sync_queue_len = await redis_client.get_queue_length("sync_queue")
        print(f"  sync_queue 长度: {sync_queue_len}")
        
        if sync_queue_len > 0:
            print("  sync_queue 前3条消息:")
            for i in range(min(3, sync_queue_len)):
                try:
                    message_data = await redis_client.client.lindex("sync_queue", i)
                    if message_data:
                        message = json.loads(message_data)
                        print(f"    [{i}] 时间: {message.get('timestamp', 'N/A')}, "
                              f"优先级: {message.get('priority', 'N/A')}, "
                              f"ID: {message.get('id', 'N/A')}")
                except Exception as e:
                    print(f"    [{i}] 解析失败: {e}")
        
        # failed_sync_queue
        failed_queue_len = await redis_client.get_queue_length("failed_sync_queue")
        print(f"  failed_sync_queue 长度: {failed_queue_len}")
        
        # 3. 映射数据
        print("\n🔗 映射数据:")
        
        # 同步映射
        mapping_keys = await redis_client.client.keys("sync_mapping:*")
        print(f"  同步映射数量: {len(mapping_keys)}")
        
        if mapping_keys:
            print("  最近5个映射:")
            for i, key in enumerate(mapping_keys[:5]):
                try:
                    mapping_data = await redis_client.client.get(key)
                    if mapping_data:
                        mapping = json.loads(mapping_data)
                        print(f"    {key}: JIRA-{mapping.get('jira_issue_key', 'N/A')}")
                except Exception as e:
                    print(f"    {key}: 解析失败 - {e}")
        
        # webhook数据
        webhook_keys = await redis_client.client.keys("webhook_data:*")
        print(f"  Webhook数据数量: {len(webhook_keys)}")
        
        # 4. Redis统计信息
        print("\n📈 Redis统计:")
        try:
            info = await redis_client.client.info()
            print(f"  已连接客户端: {info.get('connected_clients', 'N/A')}")
            print(f"  使用内存: {info.get('used_memory_human', 'N/A')}")
            print(f"  总命令数: {info.get('total_commands_processed', 'N/A')}")
            print(f"  运行时间: {info.get('uptime_in_seconds', 'N/A')} 秒")
        except Exception as e:
            print(f"  获取统计信息失败: {e}")
        
        # 5. 网络连接测试
        print("\n🌐 网络连接测试:")
        try:
            # 执行简单操作测试连接稳定性
            test_key = "connection_test"
            await redis_client.client.set(test_key, "test_value", ex=10)
            test_value = await redis_client.client.get(test_key)
            await redis_client.client.delete(test_key)
            print(f"  读写测试: {'✅ 成功' if test_value == 'test_value' else '❌ 失败'}")
        except Exception as e:
            print(f"  读写测试: ❌ 失败 - {e}")
        
        # 6. 提供建议
        print("\n💡 建议:")
        if sync_queue_len > 100:
            print("  ⚠️  sync_queue堆积较多，建议检查同步服务状态")
        if failed_queue_len > 0:
            print("  ⚠️  存在失败的同步任务，建议查看错误日志")
        if len(mapping_keys) == 0:
            print("  ℹ️  暂无同步映射数据，可能是首次运行")
        
        print("\n✅ 检查完成")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        print("\n🔧 故障排除建议:")
        print("  1. 检查Redis服务是否运行")
        print("  2. 检查网络连接和防火墙设置")
        print("  3. 验证Redis配置信息")
        print("  4. 查看Redis服务器日志")
        
    finally:
        if 'redis_client' in locals():
            await redis_client.disconnect()


if __name__ == "__main__":
    asyncio.run(check_redis_status()) 