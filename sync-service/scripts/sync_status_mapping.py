#!/usr/bin/env python3
"""
状态映射同步脚本
获取Notion和JIRA的当前状态，并同步更新状态映射表
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import setup_logger
from services.jira_client import JiraClient
from services.notion_client import NotionClient


class StatusMappingSync:
    """状态映射同步器"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logger()
        self.jira_client = None
        self.notion_client = None
        
        # 当前的状态映射表
        self.current_status_mapping = {
            '初始反馈 OR': '待可行性评估',
            '待评估 UR': '待可行性评估', 
            '待输入 WI': 'TODO',
            '同步中 SYNC': 'TODO',
            'JIRA Wait Review': 'TODO',
            'DEVING': '开发中',
            'Testing': 'Testing（测试）',
            '已发布 DONE': '完成'
        }
    
    async def initialize(self):
        """初始化客户端"""
        try:
            # 初始化JIRA客户端
            self.jira_client = JiraClient(self.settings)
            await self.jira_client.initialize()
            self.logger.info("JIRA客户端初始化完成")
            
            # 初始化Notion客户端
            if hasattr(self.settings, 'notion') and self.settings.notion.token:
                self.notion_client = NotionClient(self.settings)
                self.logger.info("Notion客户端初始化完成")
            else:
                self.logger.warning("Notion配置不完整，跳过Notion客户端初始化")
                
        except Exception as e:
            self.logger.error(f"客户端初始化失败: {e}")
            raise
    
    async def get_jira_statuses(self) -> List[Dict[str, Any]]:
        """获取JIRA项目的所有状态"""
        try:
            project_key = self.settings.jira.project_key
            self.logger.info(f"获取JIRA项目 {project_key} 的状态列表...")
            
            # 获取项目的工作流状态
            url = f"{self.jira_client.jira_config.base_url}/rest/api/2/project/{project_key}/statuses"
            
            async with self.jira_client.session.get(url) as response:
                if response.status == 200:
                    statuses_data = await response.json()
                    
                    # 提取所有唯一的状态
                    all_statuses = {}
                    for issue_type in statuses_data:
                        for status in issue_type.get('statuses', []):
                            status_id = status['id']
                            if status_id not in all_statuses:
                                all_statuses[status_id] = {
                                    'id': status_id,
                                    'name': status['name'],
                                    'description': status.get('description', ''),
                                    'category': status.get('statusCategory', {}).get('name', ''),
                                    'category_key': status.get('statusCategory', {}).get('key', '')
                                }
                    
                    statuses_list = list(all_statuses.values())
                    self.logger.info(f"获取到 {len(statuses_list)} 个JIRA状态")
                    return statuses_list
                else:
                    error_text = await response.text()
                    raise Exception(f"获取JIRA状态失败: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"获取JIRA状态异常: {e}")
            raise
    
    async def get_notion_statuses(self, database_id: str) -> List[Dict[str, Any]]:
        """获取Notion数据库的状态选项"""
        try:
            if not self.notion_client:
                self.logger.warning("Notion客户端未初始化，跳过获取Notion状态")
                return []
            
            self.logger.info(f"获取Notion数据库 {database_id} 的状态选项...")
            
            # 获取数据库结构
            database_info = await self.notion_client.get_database(database_id)
            
            # 查找Status字段
            properties = database_info.get('properties', {})
            status_field = None
            
            for field_name, field_data in properties.items():
                if field_name.lower() in ['status', '状态'] and field_data.get('type') == 'status':
                    status_field = field_data
                    break
            
            if not status_field:
                self.logger.warning("未找到Status字段")
                return []
            
            # 提取状态选项
            status_options = status_field.get('status', {}).get('options', [])
            
            statuses_list = []
            for option in status_options:
                statuses_list.append({
                    'id': option.get('id'),
                    'name': option.get('name'),
                    'color': option.get('color')
                })
            
            self.logger.info(f"获取到 {len(statuses_list)} 个Notion状态")
            return statuses_list
            
        except Exception as e:
            self.logger.error(f"获取Notion状态异常: {e}")
            return []
    
    def analyze_status_mapping(self, jira_statuses: List[Dict], notion_statuses: List[Dict]) -> Dict[str, Any]:
        """分析状态映射情况"""
        analysis = {
            'jira_statuses': jira_statuses,
            'notion_statuses': notion_statuses,
            'current_mapping': self.current_status_mapping,
            'mapping_analysis': {
                'mapped_notion_statuses': [],
                'unmapped_notion_statuses': [],
                'mapped_jira_statuses': [],
                'unmapped_jira_statuses': []
            },
            'suggestions': []
        }
        
        # 分析当前映射覆盖情况
        jira_status_names = {status['name'] for status in jira_statuses}
        notion_status_names = {status['name'] for status in notion_statuses}
        
        # 检查已映射的Notion状态
        for notion_status in self.current_status_mapping.keys():
            if notion_status in notion_status_names:
                analysis['mapping_analysis']['mapped_notion_statuses'].append(notion_status)
            else:
                # 当前映射中的状态在Notion中不存在
                analysis['suggestions'].append({
                    'type': 'obsolete_notion_status',
                    'status': notion_status,
                    'message': f"映射表中的Notion状态 '{notion_status}' 在当前数据库中不存在"
                })
        
        # 检查未映射的Notion状态
        for status in notion_statuses:
            status_name = status['name']
            if status_name not in self.current_status_mapping:
                analysis['mapping_analysis']['unmapped_notion_statuses'].append(status_name)
                analysis['suggestions'].append({
                    'type': 'new_notion_status',
                    'status': status_name,
                    'message': f"发现新的Notion状态 '{status_name}'，需要添加映射"
                })
        
        # 检查已映射的JIRA状态
        mapped_jira_statuses = set(self.current_status_mapping.values())
        for jira_status in jira_statuses:
            status_name = jira_status['name']
            if status_name in mapped_jira_statuses:
                analysis['mapping_analysis']['mapped_jira_statuses'].append(status_name)
            else:
                analysis['mapping_analysis']['unmapped_jira_statuses'].append(status_name)
        
        return analysis
    
    def generate_updated_mapping(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """生成更新后的状态映射表"""
        updated_mapping = self.current_status_mapping.copy()
        
        # 为新的Notion状态建议映射
        unmapped_notion = analysis['mapping_analysis']['unmapped_notion_statuses']
        unmapped_jira = analysis['mapping_analysis']['unmapped_jira_statuses']
        
        # 简单的自动映射逻辑（可以根据需要优化）
        for notion_status in unmapped_notion:
            # 尝试找到相似的JIRA状态
            best_match = None
            notion_lower = notion_status.lower()
            
            for jira_status in unmapped_jira:
                jira_lower = jira_status.lower()
                if notion_lower in jira_lower or jira_lower in notion_lower:
                    best_match = jira_status
                    break
            
            if best_match:
                updated_mapping[notion_status] = best_match
                unmapped_jira.remove(best_match)
            else:
                # 如果没有找到匹配，建议映射到TODO
                updated_mapping[notion_status] = 'TODO'
        
        return updated_mapping
    
    def save_mapping_to_file(self, mapping: Dict[str, str], analysis: Dict[str, Any]):
        """保存映射表到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细分析报告
        report_file = f"data/status_mapping_analysis_{timestamp}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        report_data = {
            'timestamp': timestamp,
            'analysis': analysis,
            'updated_mapping': mapping,
            'summary': {
                'total_jira_statuses': len(analysis['jira_statuses']),
                'total_notion_statuses': len(analysis['notion_statuses']),
                'mapped_notion_statuses': len(analysis['mapping_analysis']['mapped_notion_statuses']),
                'unmapped_notion_statuses': len(analysis['mapping_analysis']['unmapped_notion_statuses']),
                'suggestions_count': len(analysis['suggestions'])
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"状态映射分析报告已保存到: {report_file}")
        
        # 保存更新后的映射表（Python格式）
        mapping_file = f"data/updated_status_mapping_{timestamp}.py"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write("# 更新后的状态映射表\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("status_mapping = {\n")
            for notion_status, jira_status in mapping.items():
                f.write(f"    '{notion_status}': '{jira_status}',\n")
            f.write("}\n")
        
        self.logger.info(f"更新后的状态映射表已保存到: {mapping_file}")
        
        return report_file, mapping_file
    
    def print_analysis_summary(self, analysis: Dict[str, Any]):
        """打印分析摘要"""
        print("\n" + "="*60)
        print("状态映射分析摘要")
        print("="*60)
        
        print(f"\n📊 统计信息:")
        print(f"  JIRA状态总数: {len(analysis['jira_statuses'])}")
        print(f"  Notion状态总数: {len(analysis['notion_statuses'])}")
        print(f"  已映射Notion状态: {len(analysis['mapping_analysis']['mapped_notion_statuses'])}")
        print(f"  未映射Notion状态: {len(analysis['mapping_analysis']['unmapped_notion_statuses'])}")
        
        print(f"\n📋 JIRA状态列表:")
        for status in analysis['jira_statuses']:
            category = status.get('category', 'Unknown')
            print(f"  - {status['name']} ({category})")
        
        print(f"\n📋 Notion状态列表:")
        for status in analysis['notion_statuses']:
            color = status.get('color', 'default')
            print(f"  - {status['name']} ({color})")
        
        print(f"\n🔗 当前状态映射:")
        for notion_status, jira_status in analysis['current_mapping'].items():
            print(f"  {notion_status} → {jira_status}")
        
        if analysis['suggestions']:
            print(f"\n💡 建议:")
            for suggestion in analysis['suggestions']:
                print(f"  - {suggestion['message']}")
        
        print("\n" + "="*60)
    
    async def run(self, notion_database_id: str = None):
        """运行状态映射同步"""
        try:
            await self.initialize()
            
            # 获取JIRA状态
            jira_statuses = await self.get_jira_statuses()
            
            # 获取Notion状态
            notion_statuses = []
            if notion_database_id:
                notion_statuses = await self.get_notion_statuses(notion_database_id)
            else:
                self.logger.warning("未提供Notion数据库ID，跳过Notion状态获取")
            
            # 分析状态映射
            analysis = self.analyze_status_mapping(jira_statuses, notion_statuses)
            
            # 生成更新后的映射表
            updated_mapping = self.generate_updated_mapping(analysis)
            
            # 打印分析摘要
            self.print_analysis_summary(analysis)
            
            # 保存到文件
            report_file, mapping_file = self.save_mapping_to_file(updated_mapping, analysis)
            
            print(f"\n✅ 分析完成!")
            print(f"📄 详细报告: {report_file}")
            print(f"🔧 更新后的映射表: {mapping_file}")
            
        except Exception as e:
            self.logger.error(f"状态映射同步失败: {e}")
            raise
        finally:
            # 清理资源
            if self.jira_client:
                await self.jira_client.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='同步Notion和JIRA的状态映射')
    parser.add_argument('--notion-db-id', help='Notion数据库ID')
    parser.add_argument('--show-help', action='store_true', help='显示帮助信息')
    
    args = parser.parse_args()
    
    if args.show_help:
        print("\n状态映射同步脚本使用说明:")
        print("="*50)
        print("1. 获取JIRA项目的所有状态")
        print("2. 获取Notion数据库的状态选项（如果提供数据库ID）")
        print("3. 分析当前映射表的覆盖情况")
        print("4. 生成建议和更新后的映射表")
        print("5. 保存分析报告和更新后的映射表到文件")
        print("\n使用示例:")
        print("python sync_status_mapping.py --notion-db-id your-database-id")
        print("python sync_status_mapping.py  # 仅分析JIRA状态")
        return
    
    sync_tool = StatusMappingSync()
    await sync_tool.run(args.notion_db_id)


if __name__ == "__main__":
    asyncio.run(main()) 