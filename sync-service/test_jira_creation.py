#!/usr/bin/env python3
"""
测试JIRA Issue创建功能
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.jira_client import JiraClient
from services.field_mapper import FieldMapper


async def test_jira_creation():
    """测试JIRA Issue创建"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_jira_creation")
    
    logger.info("开始测试JIRA Issue创建功能")
    
    try:
        # 初始化JIRA客户端
        jira_client = JiraClient(settings)
        await jira_client.initialize()
        logger.info("JIRA客户端初始化成功")
        
        # 初始化字段映射器
        field_mapper = FieldMapper(settings)
        logger.info("字段映射器初始化成功")
        
        # 模拟Notion数据
        notion_data = {
            'page_id': 'test-page-12345',
            'properties': {
                '功能 Name': {
                    'title': [
                        {
                            'plain_text': '测试JIRA Issue创建功能'
                        }
                    ]
                },
                '功能说明 Desc': {
                    'rich_text': [
                        {
                            'plain_text': '这是一个测试需求，用于验证Notion到JIRA的同步功能是否正常工作。'
                        }
                    ]
                },
                '需求整理': {
                    'rich_text': [
                        {
                            'plain_text': '经过AI整理后的需求描述，包含了详细的功能说明和实现要点。'
                        }
                    ]
                },
                '优先级 P': {
                    'select': {
                        'name': '中 Medium'
                    }
                },
                'Status': {
                    'status': {
                        'name': '待输入 WI'
                    }
                }
            },
            'url': 'https://notion.so/test-page-12345'
        }
        
        logger.info(f"准备测试数据，页面ID: {notion_data['page_id']}")
        
        # 执行字段映射
        jira_fields = await field_mapper.map_notion_to_jira(
            notion_data, 
            page_url=notion_data['url']
        )
        
        logger.info(f"字段映射完成，字段数量: {len(jira_fields)}")
        
        # 验证必填字段
        missing_fields = field_mapper.validate_required_fields(jira_fields)
        if missing_fields:
            logger.error(f"缺少必填字段: {missing_fields}")
            return False
        
        # 创建JIRA Issue
        logger.info("开始创建JIRA Issue...")
        jira_result = await jira_client.create_issue(jira_fields)
        
        if jira_result:
            issue_key = jira_result.get('key')
            issue_id = jira_result.get('id')
            browse_url = jira_result.get('browse_url', f"http://rdjira.tp-link.com/browse/{issue_key}")
            
            logger.info(
                f"JIRA Issue创建成功！Key: {issue_key}, "
                f"ID: {issue_id}, URL: {browse_url}"
            )
            
            # 验证创建的Issue
            issue_key = jira_result.get('key')
            if issue_key:
                issue_details = await jira_client.get_issue(issue_key)
                fields = issue_details.get('fields', {})
                logger.info(
                    f"Issue详情验证 - 标题: {fields.get('summary')}, "
                    f"状态: {fields.get('status', {}).get('name')}, "
                    f"优先级: {fields.get('priority', {}).get('name')}"
                )
            
            return True
        else:
            logger.error("JIRA Issue创建失败")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'jira_client' in locals():
            await jira_client.close()


async def test_jira_connection():
    """测试JIRA连接"""
    
    settings = Settings()
    logger = get_logger("test_jira_connection")
    
    logger.info("测试JIRA连接...")
    
    try:
        jira_client = JiraClient(settings)
        await jira_client.initialize()
        
        # 测试连接
        connection_ok = await jira_client.test_connection()
        
        if connection_ok:
            logger.info("JIRA连接测试成功")
            
            # 获取项目元数据
            metadata = jira_client.get_project_metadata()
            if metadata:
                project_info = metadata.get('project', {})
                logger.info(
                    f"项目信息 - 名称: {project_info.get('name')}, "
                    f"Key: {project_info.get('key')}, ID: {project_info.get('id')}"
                )
            
            return True
        else:
            logger.error("JIRA连接测试失败")
            return False
            
    except Exception as e:
        logger.error(f"JIRA连接测试异常: {str(e)}")
        return False
    finally:
        if 'jira_client' in locals():
            await jira_client.close()


async def main():
    """主函数"""
    print("=== JIRA Issue创建功能测试 ===\n")
    
    # 测试连接
    print("1. 测试JIRA连接...")
    connection_ok = await test_jira_connection()
    
    if not connection_ok:
        print("❌ JIRA连接失败，请检查配置")
        return 1
    
    print("✅ JIRA连接成功\n")
    
    # 测试Issue创建
    print("2. 测试JIRA Issue创建...")
    creation_ok = await test_jira_creation()
    
    if creation_ok:
        print("✅ JIRA Issue创建测试成功")
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("❌ JIRA Issue创建测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 