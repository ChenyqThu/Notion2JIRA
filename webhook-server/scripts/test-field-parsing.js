#!/usr/bin/env node

/**
 * 测试字段解析逻辑
 * 用于验证新的字段存储策略是否正常工作
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// 模拟 Notion Webhook 数据
const mockNotionData = {
  "source": {
    "type": "automation",
    "automation_id": "test-automation",
    "user_id": "test-user"
  },
  "data": {
    "object": "page",
    "id": "test-page-123",
    "created_time": "2024-01-15T10:30:00.000Z",
    "last_edited_time": "2024-01-15T11:00:00.000Z",
    "parent": {
      "type": "database_id",
      "database_id": "test-database"
    },
    "archived": false,
    "in_trash": false,
    "properties": {
      "功能 Name": {
        "id": "title",
        "type": "title",
        "title": [
          {
            "type": "text",
            "text": {
              "content": "测试功能页面"
            },
            "plain_text": "测试功能页面"
          }
        ]
      },
      "Status": {
        "id": "status",
        "type": "status",
        "status": {
          "id": "status-1",
          "name": "进行中",
          "color": "blue"
        }
      },
      "优先级 P": {
        "id": "priority",
        "type": "select",
        "select": {
          "id": "high",
          "name": "高 High",
          "color": "red"
        }
      },
      "类型 Type": {
        "id": "type",
        "type": "multi_select",
        "multi_select": [
          {
            "id": "app",
            "name": "APP",
            "color": "green"
          },
          {
            "id": "web",
            "name": "Web",
            "color": "blue"
          }
        ]
      },
      "JIRA Card": {
        "id": "jira",
        "type": "url",
        "url": "https://jira.example.com/browse/PROJ-123"
      },
      "需求录入": {
        "id": "people",
        "type": "people",
        "people": [
          {
            "id": "user-1",
            "name": "张三",
            "avatar_url": "https://example.com/avatar1.jpg",
            "person": {
              "email": "zhangsan@example.com"
            }
          }
        ]
      },
      "截止日期": {
        "id": "date",
        "type": "date",
        "date": {
          "start": "2024-02-01",
          "end": null
        }
      },
      "预估工时": {
        "id": "number",
        "type": "number",
        "number": 8.5
      },
      "是否紧急": {
        "id": "urgent",
        "type": "checkbox",
        "checkbox": true
      },
      "同步到JIRA": {
        "id": "sync",
        "type": "checkbox",
        "checkbox": true
      },
      "同步按钮": {
        "id": "button",
        "type": "button",
        "button": {}
      },
      "功能说明 Desc": {
        "id": "desc",
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": "这是一个测试功能的详细说明"
            },
            "plain_text": "这是一个测试功能的详细说明"
          }
        ]
      },
      "未知字段": {
        "id": "unknown",
        "type": "new_field_type",
        "new_field_type": {
          "some_property": "some_value"
        }
      }
    }
  }
};

// 简化版的 NotionWebhookHandler 用于测试
class TestNotionWebhookHandler {
  parseNotionProperties(notionProperties) {
    const parsed = {};
    const rawProperties = {};
    
    for (const [key, value] of Object.entries(notionProperties)) {
      try {
        rawProperties[key] = value;
        
        switch (value.type) {
          case 'title':
            parsed[key] = {
              type: 'title',
              value: value.title?.[0]?.plain_text || '',
              raw: value.title || []
            };
            break;
          case 'rich_text':
            parsed[key] = {
              type: 'rich_text',
              value: value.rich_text?.[0]?.plain_text || '',
              raw: value.rich_text || []
            };
            break;
          case 'select':
            parsed[key] = {
              type: 'select',
              value: value.select?.name || null,
              raw: value.select
            };
            break;
          case 'multi_select':
            parsed[key] = {
              type: 'multi_select',
              value: value.multi_select?.map(item => item.name) || [],
              raw: value.multi_select || []
            };
            break;
          case 'status':
            parsed[key] = {
              type: 'status',
              value: value.status?.name || null,
              raw: value.status
            };
            break;
          case 'checkbox':
            parsed[key] = {
              type: 'checkbox',
              value: value.checkbox || false,
              raw: value.checkbox
            };
            break;
          case 'url':
            parsed[key] = {
              type: 'url',
              value: value.url || null,
              raw: value.url
            };
            break;
          case 'number':
            parsed[key] = {
              type: 'number',
              value: value.number || null,
              raw: value.number
            };
            break;
          case 'date':
            parsed[key] = {
              type: 'date',
              value: value.date?.start || null,
              end: value.date?.end || null,
              raw: value.date
            };
            break;
          case 'people':
            parsed[key] = {
              type: 'people',
              value: value.people?.map(person => ({
                id: person.id,
                name: person.name,
                email: person.person?.email,
                avatar_url: person.avatar_url
              })) || [],
              raw: value.people || []
            };
            break;
          case 'button':
            parsed[key] = {
              type: 'button',
              value: true,
              raw: value.button || {}
            };
            break;
          default:
            parsed[key] = {
              type: value.type || 'unknown',
              value: value,
              raw: value
            };
            console.log(`发现新的属性类型: ${value.type}`, { key, type: value.type });
        }
      } catch (error) {
        console.warn(`解析属性 ${key} 失败:`, error);
        parsed[key] = {
          type: 'error',
          value: null,
          raw: value,
          error: error.message
        };
      }
    }
    
    return {
      parsed,
      raw: rawProperties
    };
  }

  extractTitle(properties) {
    const titleFields = ['功能 Name', 'title', 'Title', 'Name', 'name', '标题'];
    
    for (const fieldName of titleFields) {
      const field = properties[fieldName];
      if (field && (field.type === 'title' || field.type === 'rich_text') && field.value) {
        return field.value;
      }
    }
    
    for (const [key, field] of Object.entries(properties)) {
      if ((field.type === 'title' || field.type === 'rich_text') && field.value) {
        return field.value;
      }
    }
    
    return '未命名页面';
  }

  checkSync2JiraFlag(parsedProperties) {
    const sync2jiraField = parsedProperties['sync2jira'] || parsedProperties['同步到JIRA'] || parsedProperties['Sync to JIRA'];
    if (sync2jiraField?.type === 'checkbox' && sync2jiraField.value === false) {
      return false;
    }

    const buttonFields = Object.values(parsedProperties).filter(prop => prop.type === 'button');
    if (buttonFields.length > 0) {
      return true;
    }

    return true;
  }
}

// 运行测试
function runTest() {
  console.log('🧪 开始测试字段解析逻辑...\n');
  
  const handler = new TestNotionWebhookHandler();
  const propertiesData = handler.parseNotionProperties(mockNotionData.data.properties);
  
  console.log('📊 解析结果统计:');
  console.log(`- 总字段数: ${Object.keys(propertiesData.parsed).length}`);
  console.log(`- 原始数据字段数: ${Object.keys(propertiesData.raw).length}`);
  
  console.log('\n📝 解析后的字段:');
  for (const [key, field] of Object.entries(propertiesData.parsed)) {
    console.log(`- ${key}: ${field.type} = ${JSON.stringify(field.value)}`);
  }
  
  console.log('\n🎯 标题提取测试:');
  const title = handler.extractTitle(propertiesData.parsed);
  console.log(`提取的标题: "${title}"`);
  
  console.log('\n🔄 同步标志检查:');
  const shouldSync = handler.checkSync2JiraFlag(propertiesData.parsed);
  console.log(`是否需要同步: ${shouldSync}`);
  
  console.log('\n✅ 测试完成!');
  
  // 输出完整的解析结果（用于调试）
  if (process.argv.includes('--verbose')) {
    console.log('\n🔍 详细解析结果:');
    console.log(JSON.stringify(propertiesData, null, 2));
  }
}

// 运行测试
if (require.main === module) {
  runTest();
}

module.exports = { TestNotionWebhookHandler, mockNotionData }; 