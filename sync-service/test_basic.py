#!/usr/bin/env python3
"""
基础功能测试脚本
用于验证内网同步服务的基础架构是否正常工作
"""

import asyncio
import sys
import os
import time
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.redis_client import RedisClient


async def test_settings():
    """测试配置管理"""
    print("🔧 测试配置管理...")
    
    try:
        # 设置测试环境变量
        os.environ.update({
            'JIRA_BASE_URL': 'http://test.example.com',
            'JIRA_USERNAME': 'test_user',
            'JIRA_PASSWORD': 'test_pass',
            'NOTION_TOKEN': 'secret_test_token',
            'NOTION_DATABASE_ID': 'test_db_id',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379'
        })
        
        settings = Settings()
        
        # 验证配置加载
        assert settings.jira.base_url == 'http://test.example.com'
        assert settings.jira.username == 'test_user'
        assert settings.notion.token == 'secret_test_token'
        assert settings.redis.host == 'localhost'
        assert settings.redis.port == 6379
        
        print("✅ 配置管理测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置管理测试失败: {e}")
        return False


def test_logger():
    """测试日志系统"""
    print("📝 测试日志系统...")
    
    try:
        logger = get_logger("test_logger")
        
        # 测试各种日志级别
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志")
        logger.error("这是一条错误日志")
        logger.debug("这是一条调试日志")
        
        # 测试结构化日志
        logger.log_sync_event("test_event", "test_page_id", "success", extra_info="测试数据")
        
        print("✅ 日志系统测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 日志系统测试失败: {e}")
        return False


async def test_redis_client():
    """测试Redis客户端"""
    print("🔴 测试Redis客户端...")
    
    try:
        # 设置测试环境变量
        os.environ.update({
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '1'  # 使用测试数据库
        })
        
        settings = Settings()
        redis_client = RedisClient(settings)
        
        # 测试连接
        try:
            await redis_client.connect()
            print("  ✓ Redis连接成功")
        except Exception as e:
            print(f"  ⚠️  Redis连接失败: {e}")
            print("  💡 请确保Redis服务正在运行")
            return False
        
        # 测试基础操作
        test_key = "test_key"
        test_value = {"message": "hello", "timestamp": time.time()}
        
        # 测试缓存操作
        await redis_client.set_cache(test_key, test_value, expire=60)
        retrieved_value = await redis_client.get_cache(test_key)
        assert retrieved_value == test_value
        print("  ✓ 缓存操作测试通过")
        
        # 测试队列操作
        queue_name = "test_queue"
        test_message = {"type": "test", "data": "test_data"}
        
        await redis_client.push_to_queue(queue_name, test_message, priority=1)
        retrieved_message = await redis_client.pop_from_queue(queue_name, timeout=1)
        assert retrieved_message == test_message
        print("  ✓ 队列操作测试通过")
        
        # 测试同步映射
        notion_page_id = "test_page_123"
        jira_issue_key = "TEST-456"
        
        await redis_client.set_sync_mapping(notion_page_id, jira_issue_key)
        mapping = await redis_client.get_sync_mapping(notion_page_id)
        assert mapping["jira_issue_key"] == jira_issue_key
        print("  ✓ 同步映射测试通过")
        
        # 测试统计信息
        stats = await redis_client.get_stats()
        assert "connected" in stats
        print("  ✓ 统计信息测试通过")
        
        # 清理测试数据
        await redis_client.delete_cache(test_key)
        await redis_client.clear_queue(queue_name)
        await redis_client.delete_cache(f"sync_mapping:{notion_page_id}")
        await redis_client.delete_cache(f"reverse_mapping:{jira_issue_key}")
        
        # 关闭连接
        await redis_client.disconnect()
        
        print("✅ Redis客户端测试通过")
        return True
        
    except Exception as e:
        print(f"❌ Redis客户端测试失败: {e}")
        return False


async def test_integration():
    """集成测试"""
    print("🔗 测试系统集成...")
    
    try:
        # 模拟完整的消息处理流程
        settings = Settings()
        redis_client = RedisClient(settings)
        
        await redis_client.connect()
        
        # 模拟webhook消息
        webhook_message = {
            "event_type": "notion_to_jira_create",
            "page_id": "integration_test_page",
            "database_id": "test_db",
            "properties": {
                "功能 Name": "集成测试功能",
                "Status": "待输入 WI",
                "优先级 P": "中 Medium"
            },
            "timestamp": time.time()
        }
        
        # 推送到队列
        await redis_client.push_to_queue("sync_queue", webhook_message, priority=0)
        
        # 从队列获取
        retrieved_message = await redis_client.pop_from_queue("sync_queue", timeout=1)
        assert retrieved_message == webhook_message
        
        # 模拟处理成功，设置映射
        await redis_client.set_sync_mapping(
            webhook_message["page_id"], 
            "SMBNET-9999"
        )
        
        # 验证映射
        mapping = await redis_client.get_sync_mapping(webhook_message["page_id"])
        assert mapping["jira_issue_key"] == "SMBNET-9999"
        
        # 清理
        await redis_client.delete_cache(f"sync_mapping:{webhook_message['page_id']}")
        await redis_client.delete_cache("reverse_mapping:SMBNET-9999")
        await redis_client.disconnect()
        
        print("✅ 系统集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 系统集成测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始基础功能测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(await test_settings())
    test_results.append(test_logger())
    test_results.append(await test_redis_client())
    test_results.append(await test_integration())
    
    print("=" * 50)
    
    # 统计结果
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 所有测试通过! ({passed}/{total})")
        print("✅ 基础架构工作正常，可以继续开发")
        return 0
    else:
        print(f"⚠️  部分测试失败 ({passed}/{total})")
        print("❌ 请检查失败的测试项目")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 