#!/usr/bin/env python3
"""
智能版本映射脚本
自动为JIRA版本创建Notion版本名称映射
"""

import json
import re
from pathlib import Path

def create_notion_names_from_jira_name(jira_name: str) -> list:
    """基于JIRA版本名称生成可能的Notion版本名称"""
    notion_names = []
    
    # 添加原始名称
    notion_names.append(jira_name)
    
    # 基于不同的命名模式生成变体
    patterns = [
        # Controller v6.0 -> Controller 6.0
        (r'^(\w+)\s+v(\d+\.\d+)$', r'\1 \2'),
        # Network v6.3 -> Network 6.3, network 6.3
        (r'^(\w+)\s+v(\d+\.\d+)$', r'\1 \2'),
        (r'^(\w+)\s+v(\d+\.\d+)$', lambda m: f"{m.group(1).lower()} {m.group(2)}"),
        # AP v6.0 -> AP 6.0
        (r'^([A-Z]+)\s+v(\d+\.\d+)$', r'\1 \2'),
        # Cloud Portal v5.1 -> Cloud Portal 5.1
        (r'^(.+)\s+v(\d+\.\d+)$', r'\1 \2'),
        # Design Hub 1.2 -> Design Center 1.2 (特殊映射)
        (r'^Design Hub (\d+\.\d+)$', r'Design Center \1'),
        # ODC v1.1 -> Design Center 1.1 (ODC = Omada Design Center)
        (r'^ODC v(\d+\.\d+)$', r'Design Center \1'),
    ]
    
    for pattern, replacement in patterns:
        if callable(replacement):
            match = re.match(pattern, jira_name)
            if match:
                new_name = replacement(match)
                if new_name and new_name not in notion_names:
                    notion_names.append(new_name)
        else:
            new_name = re.sub(pattern, replacement, jira_name)
            if new_name != jira_name and new_name not in notion_names:
                notion_names.append(new_name)
    
    # 特殊映射规则
    special_mappings = {
        'Controller v6.0': ['Controller 6.0', 'Controller 6.1 ePOS'],
        'Controller v6.1': ['Controller 6.1', 'Network 6.1'],  
        'Network v6.2': ['Network 6.2'],
        'Network v6.3': ['Network 6.3', 'network 6.3'],
        'Network v6.4': ['Network 6.4'],
        'Network v6.5': ['Network 6.5'],
        'AP v6.0': ['AP 6.0'],
        'AP v6.1': ['AP 6.1'],
        'AP v6.3': ['AP 6.3'],
        'Cloud Portal v5.1': ['Cloud Portal 5.1'],
        'Cloud Portal v5.2': ['Cloud Portal 5.2'],
        'Cloud Portal v5.3': ['Cloud Portal 5.3'],
        'Cloud Portal v5.4': ['Cloud Portal 5.4'],
        'Cloud Portal v5.5': ['Cloud Portal 5.5'],
        'Cloud Portal v5.6': ['Cloud Portal 5.6'],
        'Gateway v6.2': ['Gateway 6.2'],
        'Gateway v6.3': ['Gateway 6.3'], 
        'Gateway v6.4': ['Gateway 6.4'],
        'Switch v6.1': ['Switch 6.1'],
        'Switch v6.3': ['Switch 6.3'],
        'ODC v1.1': ['Design Center 1.1'],
        'Design Hub 1.2': ['Design Center 1.2'],
        'Design Hub 1.3': ['Design Center 1.3'],
        'ODC v2.0': ['Design Center 2.0'],
        'Navi v2.0': ['Navi APP 2.0'],
        'Controller v5.15.24': ['Controller 5.15.24'],
        'Omada CBC v5.15.24': ['Controller 5.15.24'],
        'Omada Pro v1.10.20': [],  # 没有对应的Notion版本
        'Omada Central v2.1': [],  # 没有对应的Notion版本
        '待评估版本': ['待评估版本', '未分配', 'TBD', '待定 TBD'],
        'AIO 1.0-Network': ['AIO GW Controller'],  # 网安一体机
        '25H2': [],  # 新版本，暂无映射
        '25H2-Beta': [],  # Beta版本
        'SE工作': [],  # SE工作版本
        '无': [],
        '未发布': [],
        '未解决': [],
    }
    
    if jira_name in special_mappings:
        special_names = special_mappings[jira_name]
        for name in special_names:
            if name not in notion_names:
                notion_names.append(name)
        return list(set(notion_names))  # 去重
    
    return list(set(notion_names))  # 去重

def update_version_mapping():
    """更新版本映射配置文件"""
    config_file = Path(__file__).parent.parent / "config" / "version_mapping.json"
    
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return False
        
    try:
        # 读取现有配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        version_mappings = config.get('version_mappings', {})
        updated_count = 0
        
        print("🔄 开始智能版本映射...")
        print(f"📋 找到 {len(version_mappings)} 个JIRA版本")
        
        # 遍历所有版本并生成映射
        for version_id, version_info in version_mappings.items():
            jira_name = version_info.get('jira_name', '')
            current_notion_names = version_info.get('notion_names', [])
            
            # 如果已经有映射且不为空，跳过
            if current_notion_names:
                print(f"✅ {jira_name} (ID: {version_id}) - 已有映射: {current_notion_names}")
                continue
            
            # 生成新的映射
            new_notion_names = create_notion_names_from_jira_name(jira_name)
            
            if new_notion_names:
                version_info['notion_names'] = new_notion_names
                version_info['comment'] = f"自动生成的映射，基于JIRA名称: {jira_name}"
                updated_count += 1
                print(f"🆕 {jira_name} (ID: {version_id}) - 新增映射: {new_notion_names}")
            else:
                print(f"⚠️  {jira_name} (ID: {version_id}) - 无法生成映射")
        
        # 更新配置文件
        config['last_updated'] = "2025-09-08T10:40:00.000000"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ 版本映射更新完成!")
        print(f"📊 更新了 {updated_count} 个版本映射")
        print(f"💾 配置文件已保存: {config_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新版本映射失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 智能版本映射工具")
    print("=" * 50)
    
    success = update_version_mapping()
    
    if success:
        print("\n💡 建议:")
        print("1. 检查生成的映射是否准确")
        print("2. 根据实际Notion版本名称调整映射")
        print("3. 测试版本映射功能")
        print("4. 运行同步服务验证效果")
    else:
        print("\n❌ 版本映射更新失败，请检查错误信息")

if __name__ == "__main__":
    main()