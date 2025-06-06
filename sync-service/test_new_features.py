#!/usr/bin/env python3
"""
测试新功能
1. 内存告警阈值修改
2. 产品线字段映射Assignee
3. Relation字段创建远程链接
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.field_mapper import FieldMapper
from services.monitor_service import MonitorService
from services.redis_client import RedisClient


async def test_memory_alert_threshold():
    """测试内存告警阈值修改"""
    print("=== 测试内存告警阈值 ===")
    
    try:
        settings = Settings()
        redis_client = RedisClient(settings)
        await redis_client.initialize()
        
        monitor_service = MonitorService(settings, redis_client)
        await monitor_service.initialize()
        
        # 模拟内存使用率数据
        test_metrics = [
            {"system": {"memory_percent": 85}, "redis": {"connected": True}},  # 应该不触发告警
            {"system": {"memory_percent": 92}, "redis": {"connected": True}},  # 应该触发warning
            {"system": {"memory_percent": 96}, "redis": {"connected": True}},  # 应该触发critical
        ]
        
        for i, metrics in enumerate(test_metrics):
            print(f"\n测试场景 {i+1}: 内存使用率 {metrics['system']['memory_percent']}%")
            await monitor_service._check_alerts(metrics)
        
        await redis_client.close()
        print("✓ 内存告警阈值测试完成")
        
    except Exception as e:
        print(f"✗ 内存告警阈值测试失败: {e}")


async def test_product_line_assignee_mapping():
    """测试产品线字段映射Assignee"""
    print("\n=== 测试产品线字段映射Assignee ===")
    
    try:
        settings = Settings()
        field_mapper = FieldMapper(settings)
        
        # 测试不同产品线的映射
        test_cases = [
            ("Controller", "ludingyang@tp-link.com.hk"),
            ("Gateway", "zhujiayin@tp-link.com.hk"), 
            ("Managed Switch", "huangguangrun@tp-link.com.hk"),
            ("Unmanaged Switch", "huangguangrun@tp-link.com.hk"),
            ("EAP", "ouhuanrui@tp-link.com.hk"),
            ("OLT", "fancunlian@tp-link.com.hk"),
            ("APP", "xingxiaosong@tp-link.com.hk"),
            ("Unknown Product", "ludingyang@tp-link.com.hk"),  # 默认值
            (None, "ludingyang@tp-link.com.hk"),  # 无产品线
        ]
        
        all_passed = True
        for product_line, expected_assignee in test_cases:
            notion_data = {
                'properties': {}
            }
            
            if product_line:
                notion_data['properties']['产品线'] = {
                    'value': product_line,
                    'type': 'select'
                }
            
            assignee = await field_mapper._extract_assignee(notion_data)
            actual_assignee = assignee.get('name') if assignee else None
            
            status = "✓" if actual_assignee == expected_assignee else "✗"
            print(f"{status} 产品线: {product_line or '无'} -> 经办人: {actual_assignee}")
            
            if actual_assignee != expected_assignee:
                print(f"  期望: {expected_assignee}, 实际: {actual_assignee}")
                all_passed = False
        
        if all_passed:
            print("✓ 产品线映射测试全部通过")
        else:
            print("✗ 部分产品线映射测试失败")
    
    except Exception as e:
        print(f"✗ 产品线映射测试失败: {e}")


async def test_relation_extraction():
    """测试关联字段提取"""
    print("\n=== 测试关联字段提取 ===")
    
    try:
        settings = Settings()
        field_mapper = FieldMapper(settings)
        
        # 测试不同类型的relation数据
        test_cases = [
            # 测试formula类型（逗号分隔的链接）
            {
                'name': 'Formula类型relation',
                'data': {
                    'properties': {
                        'relation': {
                            'value': 'https://www.notion.so/page1,https://www.notion.so/page2',
                            'type': 'formula'
                        }
                    }
                },
                'expected_count': 2
            },
            # 测试直接relation类型
            {
                'name': '直接relation类型',
                'data': {
                    'properties': {
                        'relation': {
                            'value': [
                                {'id': 'abc123def456'},
                                {'id': 'def456ghi789'}
                            ],
                            'type': 'relation'
                        }
                    }
                },
                'expected_count': 2
            },
            # 测试空relation
            {
                'name': '空relation',
                'data': {
                    'properties': {
                        'relation': {
                            'value': '',
                            'type': 'formula'
                        }
                    }
                },
                'expected_count': 0
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            print(f"\n测试 {test_case['name']}:")
            relations = field_mapper._extract_relations(test_case['data'])
            actual_count = len(relations) if relations else 0
            
            status = "✓" if actual_count == test_case['expected_count'] else "✗"
            print(f"{status} 期望链接数: {test_case['expected_count']}, 实际: {actual_count}")
            
            if actual_count != test_case['expected_count']:
                all_passed = False
            
            if relations:
                for i, link in enumerate(relations):
                    print(f"  链接 {i+1}: {link}")
        
        if all_passed:
            print("✓ 关联字段提取测试全部通过")
        else:
            print("✗ 部分关联字段提取测试失败")
    
    except Exception as e:
        print(f"✗ 关联字段提取测试失败: {e}")


async def test_remote_issue_links():
    """测试远程链接构建"""
    print("\n=== 测试远程链接构建 ===")
    
    try:
        settings = Settings()
        field_mapper = FieldMapper(settings)
        
        # 测试链接构建
        test_links = [
            'https://www.notion.so/page1',
            'https://www.notion.so/page2',
            'https://example.com/other-page'
        ]
        
        issue_summary = "测试Issue标题"
        remote_links = field_mapper.build_remote_issue_links(test_links, issue_summary)
        
        print(f"构建了 {len(remote_links)} 个远程链接对象")
        
        all_valid = True
        for i, link in enumerate(remote_links):
            print(f"\n远程链接 {i+1}:")
            print(f"  URL: {link['object']['url']}")
            print(f"  标题: {link['object']['title']}")
            print(f"  关系: {link['relationship']}")
            print(f"  应用: {link['application']['name']}")
            
            # 验证必要字段
            required_fields = ['globalId', 'application', 'relationship', 'object']
            for field in required_fields:
                if field not in link:
                    print(f"  ✗ 缺少必要字段: {field}")
                    all_valid = False
        
        if all_valid and len(remote_links) == len(test_links):
            print("✓ 远程链接构建测试通过")
        else:
            print("✗ 远程链接构建测试失败")
    
    except Exception as e:
        print(f"✗ 远程链接构建测试失败: {e}")


async def main():
    """主测试函数"""
    print("开始测试新功能...")
    
    # 测试内存告警阈值
    await test_memory_alert_threshold()
    
    # 测试产品线映射
    await test_product_line_assignee_mapping()
    
    # 测试关联字段提取
    await test_relation_extraction()
    
    # 测试远程链接构建
    await test_remote_issue_links()
    
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main()) 