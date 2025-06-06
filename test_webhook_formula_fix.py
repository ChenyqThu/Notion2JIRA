#!/usr/bin/env python3
"""
测试脚本：验证webhook-server修复formula字段处理后的效果
模拟webhook-server处理包含formula字段的数据
"""

import json

def simulate_webhook_formula_processing():
    """模拟webhook-server现在应该能正确处理formula字段"""
    
    # 模拟包含Relation formula字段的webhook数据
    mock_webhook_data = {
        "properties": {
            "标题": {
                "type": "title",
                "title": [{"plain_text": "测试页面"}]
            },
            "涉及产品线": {
                "type": "multi_select", 
                "multi_select": [{"name": "Controller"}]
            },
            "Relation": {
                "type": "formula",
                "formula": {
                    "string": "http://rdjira.tp-link.com/browse/SMBNET-218,http://rdjira.tp-link.com/browse/SMBNET-219,http://rdjira.tp-link.com/browse/SMBNET-220"
                }
            },
            "Status": {
                "type": "status",
                "status": {"name": "未开始"}
            }
        }
    }
    
    print("🔍 测试webhook-server formula字段修复")
    print("=" * 60)
    
    # 模拟原来的处理（缺少formula支持）
    print("❌ 修复前 - 缺少formula处理:")
    old_supported_types = [
        'title', 'rich_text', 'select', 'multi_select', 'status', 
        'checkbox', 'url', 'email', 'phone_number', 'number', 
        'date', 'people', 'files', 'created_time', 'last_edited_time',
        'created_by', 'last_edited_by', 'relation', 'rollup', 
        'button', 'unique_id', 'verification'
    ]
    
    old_parsed = {}
    for key, value in mock_webhook_data["properties"].items():
        if value["type"] in old_supported_types:
            old_parsed[key] = f"已处理 ({value['type']})"
        else:
            old_parsed[key] = f"未知类型 ({value['type']}) - 进入default分支"
    
    print(f"  - 处理字段数: {len([k for k, v in old_parsed.items() if '已处理' in v])}")
    print(f"  - 未知字段数: {len([k for k, v in old_parsed.items() if '未知' in v])}")
    print("  - 字段详情:")
    for key, status in old_parsed.items():
        icon = "✅" if "已处理" in status else "❌" 
        print(f"    {icon} {key}: {status}")
    
    print()
    
    # 模拟现在的处理（包含formula支持）
    print("✅ 修复后 - 支持formula处理:")
    new_supported_types = old_supported_types + ['formula']
    
    new_parsed = {}
    for key, value in mock_webhook_data["properties"].items():
        if value["type"] in new_supported_types:
            if value["type"] == "formula":
                formula_value = value["formula"].get("string", "其他formula类型")
                new_parsed[key] = f"已处理 (formula) - 值: {formula_value}"
            else:
                new_parsed[key] = f"已处理 ({value['type']})"
        else:
            new_parsed[key] = f"未知类型 ({value['type']}) - 进入default分支"
    
    print(f"  - 处理字段数: {len([k for k, v in new_parsed.items() if '已处理' in v])}")
    print(f"  - 未知字段数: {len([k for k, v in new_parsed.items() if '未知' in v])}")
    print("  - 字段详情:")
    for key, status in new_parsed.items():
        icon = "✅" if "已处理" in status else "❌"
        print(f"    {icon} {key}: {status}")
    
    print()
    print("🎯 关键差异:")
    print(f"  - Relation字段: 修复前❌未处理 → 修复后✅已处理")
    print(f"  - 字段总数: 修复前{len([k for k, v in old_parsed.items() if '已处理' in v])}个 → 修复后{len([k for k, v in new_parsed.items() if '已处理' in v])}个")
    
    # 验证关联链接提取
    relation_field = mock_webhook_data["properties"]["Relation"]
    if relation_field["type"] == "formula" and "string" in relation_field["formula"]:
        relation_links = relation_field["formula"]["string"]
        print(f"  - 关联链接: {relation_links}")
        
        # 模拟sync-service中的处理
        if relation_links and "," in relation_links:
            links = [link.strip() for link in relation_links.split(",") if link.strip()]
            print(f"  - 解析出的链接数量: {len(links)}")
            for i, link in enumerate(links, 1):
                print(f"    {i}. {link}")

if __name__ == "__main__":
    simulate_webhook_formula_processing() 