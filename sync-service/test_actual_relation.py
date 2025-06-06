#!/usr/bin/env python3
"""
测试实际的Relation字段数据解析
基于实际的日志信息进行测试
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from services.field_mapper import FieldMapper


async def test_actual_relation_data():
    """测试实际的Relation字段数据"""
    print("=== 测试实际Relation字段数据 ===")
    
    try:
        settings = Settings()
        field_mapper = FieldMapper(settings)
        
        # 模拟实际的数据结构
        # 基于您提供的信息：@http://rdjira.tp-link.com/browse/SMBNET-218,http://rdjira.tp-link.com/browse/SMBNET-219,http://rdjira.tp-link.com/browse/SMBNET-220
        test_notion_data = {
            'page_id': '20015375-830d-8051-9b72-d3fcec2b7ef4',
            'properties': {
                # 测试不同可能的字段名和数据结构
                'Relation': {
                    'value': 'http://rdjira.tp-link.com/browse/SMBNET-218,http://rdjira.tp-link.com/browse/SMBNET-219,http://rdjira.tp-link.com/browse/SMBNET-220',
                    'type': 'formula'
                },
                '功能 Name': {
                    'value': '这是一条测试的需求',
                    'type': 'title'
                },
                '涉及产品线': {
                    'value': 'Gateway',
                    'type': 'select'
                }
            }
        }
        
        print(f"测试页面ID: {test_notion_data['page_id']}")
        print(f"Relation字段内容: {test_notion_data['properties']['Relation']['value']}")
        
        # 测试关联字段提取
        print("\n1. 测试关联字段提取...")
        relations = field_mapper._extract_relations(test_notion_data)
        
        if relations:
            print(f"✓ 成功提取到 {len(relations)} 个关联链接:")
            for i, link in enumerate(relations):
                print(f"  {i+1}. {link}")
        else:
            print("✗ 未提取到关联链接")
        
        # 测试完整的字段映射
        print("\n2. 测试完整字段映射...")
        jira_fields = await field_mapper.map_notion_to_jira(test_notion_data)
        
        notion_relations = jira_fields.get('_notion_relations')
        if notion_relations:
            print(f"✓ 字段映射中包含 {len(notion_relations)} 个关联链接")
        else:
            print("✗ 字段映射中未包含关联链接")
        
        # 测试远程链接构建
        if notion_relations:
            print("\n3. 测试远程链接构建...")
            remote_links = field_mapper.build_remote_issue_links(
                notion_relations, 
                jira_fields.get('summary', '测试Issue')
            )
            
            print(f"✓ 构建了 {len(remote_links)} 个远程链接对象:")
            for i, link in enumerate(remote_links):
                print(f"  {i+1}. URL: {link['object']['url']}")
                print(f"      标题: {link['object']['title']}")
                print(f"      关系: {link['relationship']}")
        
        # 测试其他可能的字段名
        print("\n4. 测试其他可能的字段名...")
        test_variants = [
            ('关联', '关联字段'),
            ('关系', '关系字段'),
            ('关联链接', '关联链接字段'),
            ('Related Links', '英文关联链接字段')
        ]
        
        for field_name, description in test_variants:
            test_data = {
                'page_id': '20015375-830d-8051-9b72-d3fcec2b7ef4',
                'properties': {
                    field_name: {
                        'value': 'http://rdjira.tp-link.com/browse/SMBNET-218,http://rdjira.tp-link.com/browse/SMBNET-219',
                        'type': 'formula'
                    }
                }
            }
            
            relations = field_mapper._extract_relations(test_data)
            status = "✓" if relations else "✗"
            count = len(relations) if relations else 0
            print(f"  {status} {description} ({field_name}): {count} 个链接")
    
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_empty_and_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")
    
    try:
        settings = Settings()
        field_mapper = FieldMapper(settings)
        
        test_cases = [
            {
                'name': '空字符串',
                'data': {
                    'properties': {
                        'Relation': {
                            'value': '',
                            'type': 'formula'
                        }
                    }
                }
            },
            {
                'name': '只有逗号',
                'data': {
                    'properties': {
                        'Relation': {
                            'value': ',,,',
                            'type': 'formula'
                        }
                    }
                }
            },
            {
                'name': '单个链接',
                'data': {
                    'properties': {
                        'Relation': {
                            'value': 'http://rdjira.tp-link.com/browse/SMBNET-218',
                            'type': 'formula'
                        }
                    }
                }
            },
            {
                'name': '带空格的链接',
                'data': {
                    'properties': {
                        'Relation': {
                            'value': ' http://rdjira.tp-link.com/browse/SMBNET-218 , http://rdjira.tp-link.com/browse/SMBNET-219 ',
                            'type': 'formula'
                        }
                    }
                }
            }
        ]
        
        for test_case in test_cases:
            relations = field_mapper._extract_relations(test_case['data'])
            count = len(relations) if relations else 0
            print(f"  {test_case['name']}: {count} 个链接")
            if relations:
                for i, link in enumerate(relations):
                    print(f"    {i+1}. '{link}'")
    
    except Exception as e:
        print(f"✗ 边界测试失败: {e}")


async def main():
    """主测试函数"""
    print("开始测试实际Relation字段解析...")
    
    await test_actual_relation_data()
    await test_empty_and_edge_cases()
    
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(main()) 