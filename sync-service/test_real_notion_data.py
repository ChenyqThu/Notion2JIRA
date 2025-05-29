#!/usr/bin/env python3
"""
使用真实Notion数据结构测试字段映射
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
from services.field_mapper import FieldMapper


async def test_real_notion_data():
    """测试真实的Notion数据结构"""
    
    # 初始化配置和日志
    settings = Settings()
    logger = get_logger("test_real_notion_data")
    
    # 设置DEBUG日志级别
    import logging
    logging.getLogger("field_mapper").setLevel(logging.DEBUG)
    
    logger.info("开始测试真实Notion数据结构")
    
    try:
        # 模拟真实的Notion webhook数据结构
        real_notion_data = {
            'page_id': '20015375-830d-8051-9b72-d3fcec2b7ef4',
            'properties': {
                '功能 Name': {
                    'id': 'title',
                    'type': 'title',
                    'title': [
                        {
                            'type': 'text',
                            'text': {
                                'content': 'roaming等功能联动wifi navi',
                                'link': None
                            },
                            'annotations': {
                                'bold': False,
                                'italic': False,
                                'strikethrough': False,
                                'underline': False,
                                'code': False,
                                'color': 'default'
                            },
                            'plain_text': 'roaming等功能联动wifi navi',
                            'href': None
                        }
                    ]
                },
                'Status': {
                    'id': 'status',
                    'type': 'status',
                    'status': {
                        'id': 'initial_feedback',
                        'name': '初始反馈 OR',
                        'color': 'red'
                    }
                },
                '优先级 P': {
                    'id': 'priority',
                    'type': 'select',
                    'select': {
                        'id': 'medium',
                        'name': '中 Medium',
                        'color': 'yellow'
                    }
                },
                '功能说明 Desc': {
                    'id': 'description',
                    'type': 'rich_text',
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': '当用户在不同AP之间漫游时，希望wifi导航功能能够自动适应新的网络环境，提供连续的导航服务。',
                                'link': None
                            },
                            'annotations': {
                                'bold': False,
                                'italic': False,
                                'strikethrough': False,
                                'underline': False,
                                'code': False,
                                'color': 'default'
                            },
                            'plain_text': '当用户在不同AP之间漫游时，希望wifi导航功能能够自动适应新的网络环境，提供连续的导航服务。',
                            'href': None
                        }
                    ]
                },
                '需求整理': {
                    'id': 'ai_summary',
                    'type': 'rich_text',
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': '## 功能需求\n- 实现roaming功能与wifi导航的联动\n- 确保漫游过程中导航服务的连续性\n- 优化用户体验，减少网络切换时的服务中断\n\n## 技术要点\n- AP间漫游检测\n- 导航状态保持\n- 网络环境适应',
                                'link': None
                            },
                            'annotations': {
                                'bold': False,
                                'italic': False,
                                'strikethrough': False,
                                'underline': False,
                                'code': False,
                                'color': 'default'
                            },
                            'plain_text': '## 功能需求\n- 实现roaming功能与wifi导航的联动\n- 确保漫游过程中导航服务的连续性\n- 优化用户体验，减少网络切换时的服务中断\n\n## 技术要点\n- AP间漫游检测\n- 导航状态保持\n- 网络环境适应',
                            'href': None
                        }
                    ]
                },
                '需求录入': {
                    'id': 'assignee',
                    'type': 'people',
                    'people': [
                        {
                            'object': 'user',
                            'id': 'user-123',
                            'name': '陈源泉',
                            'avatar_url': 'https://example.com/avatar.jpg',
                            'type': 'person',
                            'person': {
                                'email': 'lucien.chen@tp-link.com'
                            }
                        }
                    ]
                },
                '关联项目': {
                    'id': 'relation',
                    'type': 'relation',
                    'relation': [
                        {
                            'id': 'project-123'
                        }
                    ]
                },
                'JIRA Card': {
                    'id': 'jira_url',
                    'type': 'url',
                    'url': None
                }
            },
            'url': 'https://notion.so/20015375830d80519b72d3fcec2b7ef4'
        }
        
        logger.info(f"测试数据页面ID: {real_notion_data['page_id']}")
        logger.info(f"属性字段数量: {len(real_notion_data['properties'])}")
        logger.info(f"属性字段名称: {list(real_notion_data['properties'].keys())}")
        
        # 初始化字段映射器
        field_mapper = FieldMapper(settings)
        
        # 执行字段映射
        logger.info("开始执行字段映射...")
        jira_fields = await field_mapper.map_notion_to_jira(
            real_notion_data, 
            page_url=real_notion_data['url']
        )
        
        logger.info("字段映射成功完成")
        logger.info(f"映射结果: {json.dumps(jira_fields, ensure_ascii=False, indent=2)}")
        
        # 验证必填字段
        missing_fields = field_mapper.validate_required_fields(jira_fields)
        if missing_fields:
            logger.error(f"缺少必填字段: {missing_fields}")
            return False
        else:
            logger.info("✅ 所有必填字段验证通过")
        
        # 验证具体字段内容
        expected_summary = 'roaming等功能联动wifi navi'
        actual_summary = jira_fields.get('summary')
        if actual_summary == expected_summary:
            logger.info(f"✅ 标题字段正确: {actual_summary}")
        else:
            logger.error(f"❌ 标题字段错误: 期望 '{expected_summary}', 实际 '{actual_summary}'")
            return False
        
        # 验证优先级
        expected_priority_id = '3'  # 中 Medium
        actual_priority = jira_fields.get('priority', {})
        if actual_priority.get('id') == expected_priority_id:
            logger.info(f"✅ 优先级字段正确: {actual_priority}")
        else:
            logger.error(f"❌ 优先级字段错误: 期望ID '{expected_priority_id}', 实际 {actual_priority}")
            return False
        
        # 验证描述字段
        description = jira_fields.get('description', '')
        if '需求说明' in description and '需求整理(AI)' in description and '原始需求链接' in description:
            logger.info("✅ 描述字段包含所有必要部分")
        else:
            logger.error("❌ 描述字段缺少必要部分")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


async def main():
    """主函数"""
    print("=== 真实Notion数据结构测试 ===\n")
    
    success = await test_real_notion_data()
    
    if success:
        print("✅ 测试通过")
        return 0
    else:
        print("❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 