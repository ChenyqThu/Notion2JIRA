#!/usr/bin/env python3
"""
Notion版本映射管理脚本
用于手动管理Notion项目库ID和名称的映射关系
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logger import get_logger

class NotionVersionMappingManager:
    """Notion版本映射管理器"""
    
    def __init__(self):
        self.logger = get_logger("notion_version_mapping")
        
        # 映射文件路径
        self.mapping_file = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "notion_version_mapping.json"
        )
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
        
        # 加载现有映射
        self.mappings = self._load_mappings()
    
    def _load_mappings(self) -> Dict[str, Any]:
        """加载现有映射"""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"加载了 {len(data.get('mappings', {}))} 个版本映射")
                    return data
            else:
                self.logger.info("映射文件不存在，创建新的映射")
                return {
                    "mappings": {},
                    "last_updated": None,
                    "version": "1.0.0",
                    "description": "Notion项目库ID到名称的映射关系"
                }
        except Exception as e:
            self.logger.error(f"加载映射文件失败: {str(e)}")
            return {"mappings": {}, "last_updated": None}
    
    def _save_mappings(self):
        """保存映射到文件"""
        try:
            self.mappings["last_updated"] = datetime.now().isoformat()
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"映射已保存到 {self.mapping_file}")
            
        except Exception as e:
            self.logger.error(f"保存映射文件失败: {str(e)}")
    
    def add_mapping(self, notion_id: str, version_name: str, description: str = ""):
        """添加新的映射关系"""
        try:
            # 验证输入
            if not notion_id or not version_name:
                raise ValueError("Notion ID和版本名称不能为空")
            
            # 格式化Notion ID（确保包含连字符）
            if len(notion_id) == 32 and '-' not in notion_id:
                # 格式化为标准UUID格式
                formatted_id = f"{notion_id[:8]}-{notion_id[8:12]}-{notion_id[12:16]}-{notion_id[16:20]}-{notion_id[20:]}"
            else:
                formatted_id = notion_id
            
            # 添加映射
            self.mappings["mappings"][formatted_id] = {
                "name": version_name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self._save_mappings()
            
            print(f"✅ 成功添加映射: {formatted_id} -> {version_name}")
            
        except Exception as e:
            print(f"❌ 添加映射失败: {str(e)}")
    
    def update_mapping(self, notion_id: str, version_name: str, description: str = ""):
        """更新现有映射"""
        try:
            if notion_id not in self.mappings["mappings"]:
                raise ValueError(f"映射不存在: {notion_id}")
            
            self.mappings["mappings"][notion_id]["name"] = version_name
            self.mappings["mappings"][notion_id]["description"] = description
            self.mappings["mappings"][notion_id]["updated_at"] = datetime.now().isoformat()
            
            self._save_mappings()
            
            print(f"✅ 成功更新映射: {notion_id} -> {version_name}")
            
        except Exception as e:
            print(f"❌ 更新映射失败: {str(e)}")
    
    def remove_mapping(self, notion_id: str):
        """删除映射"""
        try:
            if notion_id not in self.mappings["mappings"]:
                raise ValueError(f"映射不存在: {notion_id}")
            
            version_name = self.mappings["mappings"][notion_id]["name"]
            del self.mappings["mappings"][notion_id]
            
            self._save_mappings()
            
            print(f"✅ 成功删除映射: {notion_id} ({version_name})")
            
        except Exception as e:
            print(f"❌ 删除映射失败: {str(e)}")
    
    def list_mappings(self):
        """列出所有映射"""
        mappings = self.mappings.get("mappings", {})
        
        if not mappings:
            print("📋 当前没有版本映射")
            return
        
        print(f"📋 当前版本映射 (共 {len(mappings)} 个):")
        print("=" * 80)
        
        for notion_id, info in mappings.items():
            name = info.get("name", "未知")
            description = info.get("description", "")
            created_at = info.get("created_at", "未知")
            
            print(f"🔗 Notion ID: {notion_id}")
            print(f"   版本名称: {name}")
            if description:
                print(f"   描述: {description}")
            print(f"   创建时间: {created_at}")
            print("-" * 40)
        
        last_updated = self.mappings.get("last_updated")
        if last_updated:
            print(f"\n📅 最后更新时间: {last_updated}")
    
    def get_version_name(self, notion_id: str) -> Optional[str]:
        """根据Notion ID获取版本名称"""
        mappings = self.mappings.get("mappings", {})
        mapping_info = mappings.get(notion_id)
        
        if mapping_info:
            return mapping_info.get("name")
        
        return None
    
    def search_mappings(self, keyword: str):
        """搜索映射"""
        mappings = self.mappings.get("mappings", {})
        results = []
        
        for notion_id, info in mappings.items():
            name = info.get("name", "")
            description = info.get("description", "")
            
            if (keyword.lower() in name.lower() or 
                keyword.lower() in description.lower() or 
                keyword in notion_id):
                results.append((notion_id, info))
        
        if not results:
            print(f"🔍 未找到包含 '{keyword}' 的映射")
            return
        
        print(f"🔍 搜索结果 (共 {len(results)} 个):")
        print("=" * 60)
        
        for notion_id, info in results:
            name = info.get("name", "未知")
            description = info.get("description", "")
            
            print(f"🔗 {notion_id} -> {name}")
            if description:
                print(f"   描述: {description}")
            print("-" * 30)
    
    def import_from_csv(self, csv_file: str):
        """从CSV文件导入映射"""
        try:
            import csv
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    notion_id = row.get('notion_id', '').strip()
                    version_name = row.get('version_name', '').strip()
                    description = row.get('description', '').strip()
                    
                    if notion_id and version_name:
                        self.add_mapping(notion_id, version_name, description)
                        count += 1
                
                print(f"✅ 成功导入 {count} 个映射")
                
        except Exception as e:
            print(f"❌ 导入失败: {str(e)}")
    
    def export_to_csv(self, csv_file: str):
        """导出映射到CSV文件"""
        try:
            import csv
            
            mappings = self.mappings.get("mappings", {})
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['notion_id', 'version_name', 'description', 'created_at'])
                
                for notion_id, info in mappings.items():
                    writer.writerow([
                        notion_id,
                        info.get('name', ''),
                        info.get('description', ''),
                        info.get('created_at', '')
                    ])
            
            print(f"✅ 成功导出到 {csv_file}")
            
        except Exception as e:
            print(f"❌ 导出失败: {str(e)}")

def main():
    """主函数"""
    manager = NotionVersionMappingManager()
    
    if len(sys.argv) < 2:
        print("📋 Notion版本映射管理工具")
        print("=" * 40)
        print("用法:")
        print("  python manage_notion_version_mapping.py <命令> [参数]")
        print("")
        print("命令:")
        print("  list                     - 列出所有映射")
        print("  add <id> <name> [desc]   - 添加新映射")
        print("  update <id> <name> [desc] - 更新映射")
        print("  remove <id>              - 删除映射")
        print("  search <keyword>         - 搜索映射")
        print("  import <csv_file>        - 从CSV导入")
        print("  export <csv_file>        - 导出到CSV")
        print("")
        print("示例:")
        print("  python manage_notion_version_mapping.py add 1a715375-830d-80ca-8c96-fb4758a39f0c \"Controller 6.1 ePOS\" \"控制器6.1版本\"")
        print("  python manage_notion_version_mapping.py list")
        print("  python manage_notion_version_mapping.py search \"Controller\"")
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "list":
            manager.list_mappings()
            
        elif command == "add":
            if len(sys.argv) < 4:
                print("❌ 用法: add <notion_id> <version_name> [description]")
                return
            
            notion_id = sys.argv[2]
            version_name = sys.argv[3]
            description = sys.argv[4] if len(sys.argv) > 4 else ""
            
            manager.add_mapping(notion_id, version_name, description)
            
        elif command == "update":
            if len(sys.argv) < 4:
                print("❌ 用法: update <notion_id> <version_name> [description]")
                return
            
            notion_id = sys.argv[2]
            version_name = sys.argv[3]
            description = sys.argv[4] if len(sys.argv) > 4 else ""
            
            manager.update_mapping(notion_id, version_name, description)
            
        elif command == "remove":
            if len(sys.argv) < 3:
                print("❌ 用法: remove <notion_id>")
                return
            
            notion_id = sys.argv[2]
            manager.remove_mapping(notion_id)
            
        elif command == "search":
            if len(sys.argv) < 3:
                print("❌ 用法: search <keyword>")
                return
            
            keyword = sys.argv[2]
            manager.search_mappings(keyword)
            
        elif command == "import":
            if len(sys.argv) < 3:
                print("❌ 用法: import <csv_file>")
                return
            
            csv_file = sys.argv[2]
            manager.import_from_csv(csv_file)
            
        elif command == "export":
            if len(sys.argv) < 3:
                print("❌ 用法: export <csv_file>")
                return
            
            csv_file = sys.argv[2]
            manager.export_to_csv(csv_file)
            
        else:
            print(f"❌ 未知命令: {command}")
            
    except Exception as e:
        print(f"❌ 执行命令失败: {str(e)}")

if __name__ == "__main__":
    main() 