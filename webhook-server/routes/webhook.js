const express = require('express');
const { body, validationResult } = require('express-validator');
const logger = require('../config/logger');
const redisClient = require('../config/redis');
const { verifyWebhookRequest } = require('../middleware/auth');

const router = express.Router();

/**
 * Notion Webhook 事件处理器
 */
class NotionWebhookHandler {
  constructor() {
    this.supportedEvents = [
      'page.created',
      'page.updated', 
      'page.deleted',
      'database.created',
      'database.updated',
      'database.deleted'
    ];
  }

  /**
   * 解析 Notion Webhook 数据
   */
  parseNotionWebhookData(webhookData) {
    const { source, data } = webhookData;
    
    // 从 source 推断事件类型，如果没有则默认为 page.updated
    let eventType = 'page.updated';
    if (source && source.type === 'automation') {
      // 可以根据需要进一步细化事件类型判断逻辑
      eventType = 'page.updated';
    }

    // 提取页面基本信息
    const pageId = data.id;
    const databaseId = data.parent?.database_id;
    const lastEditedTime = data.last_edited_time;
    const createdTime = data.created_time;
    const archived = data.archived;
    const inTrash = data.in_trash;

    // 解析属性
    const propertiesData = this.parseNotionProperties(data.properties);

    // 检查是否需要同步到 JIRA（移除 Formula 字段依赖）
    const sync2jira = this.checkSync2JiraFlag(propertiesData.parsed);

    return {
      event_type: eventType,
      page_id: pageId,
      database_id: databaseId,
      last_edited_time: lastEditedTime,
      created_time: createdTime,
      archived,
      in_trash: inTrash,
      properties: propertiesData.parsed,
      raw_properties: propertiesData.raw,
      sync2jira,
      raw_data: data,
      source_info: source
    };
  }

  /**
   * 解析 Notion 属性
   * 采用通用解析策略，存储尽可能多的字段信息，便于未来扩展
   */
  parseNotionProperties(notionProperties) {
    const parsed = {};
    const rawProperties = {}; // 保存原始数据
    
    for (const [key, value] of Object.entries(notionProperties)) {
      try {
        // 保存原始属性数据
        rawProperties[key] = value;
        
        // 根据类型解析为易用格式
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
          case 'email':
            parsed[key] = {
              type: 'email',
              value: value.email || null,
              raw: value.email
            };
            break;
          case 'phone_number':
            parsed[key] = {
              type: 'phone_number',
              value: value.phone_number || null,
              raw: value.phone_number
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
          case 'files':
            parsed[key] = {
              type: 'files',
              value: value.files?.map(file => ({
                name: file.name,
                url: file.file?.url || file.external?.url,
                type: file.type
              })) || [],
              raw: value.files || []
            };
            break;
          case 'created_time':
          case 'last_edited_time':
            parsed[key] = {
              type: value.type,
              value: value[value.type],
              raw: value[value.type]
            };
            break;
          case 'created_by':
          case 'last_edited_by':
            parsed[key] = {
              type: value.type,
              value: {
                id: value[value.type]?.id,
                name: value[value.type]?.name,
                email: value[value.type]?.person?.email
              },
              raw: value[value.type]
            };
            break;
          case 'relation':
            parsed[key] = {
              type: 'relation',
              value: value.relation?.map(rel => rel.id) || [],
              raw: value.relation || []
            };
            break;
          case 'rollup':
            parsed[key] = {
              type: 'rollup',
              value: value.rollup?.array || value.rollup?.number || value.rollup?.date || null,
              raw: value.rollup
            };
            break;
          case 'button':
            // Button 字段通常不包含具体值，但其存在表示可以触发操作
            parsed[key] = {
              type: 'button',
              value: true, // 表示按钮存在
              raw: value.button || {}
            };
            break;
          case 'unique_id':
            parsed[key] = {
              type: 'unique_id',
              value: value.unique_id?.number || null,
              prefix: value.unique_id?.prefix || null,
              raw: value.unique_id
            };
            break;
          case 'verification':
            parsed[key] = {
              type: 'verification',
              value: value.verification?.state || null,
              verified_by: value.verification?.verified_by,
              date: value.verification?.date,
              raw: value.verification
            };
            break;
          case 'formula':
            // Formula 字段处理 - 根据实际返回的数据类型解析
            let formulaValue = null;
            if (value.formula) {
              // Formula 可能返回不同类型的值
              if (value.formula.string !== undefined) {
                formulaValue = value.formula.string;
              } else if (value.formula.number !== undefined) {
                formulaValue = value.formula.number;
              } else if (value.formula.boolean !== undefined) {
                formulaValue = value.formula.boolean;
              } else if (value.formula.date) {
                formulaValue = value.formula.date.start;
              } else {
                // 其他类型或null值
                formulaValue = value.formula;
              }
            }
            parsed[key] = {
              type: 'formula',
              value: formulaValue,
              raw: value.formula
            };
            break;
          default:
            // 对于未知类型，保存完整的原始数据
            parsed[key] = {
              type: value.type || 'unknown',
              value: value,
              raw: value
            };
            logger.info(`发现新的属性类型: ${value.type}`, { key, type: value.type });
        }
      } catch (error) {
        logger.warn(`解析属性 ${key} 失败:`, error);
        // 解析失败时保存原始数据
        parsed[key] = {
          type: 'error',
          value: null,
          raw: value,
          error: error.message
        };
      }
    }
    
    // 返回解析后的数据和原始数据
    return {
      parsed,
      raw: rawProperties
    };
  }

  /**
   * 检查是否需要同步到 JIRA
   * 注意：同步是通过 Notion database 的 button property 点击触发的
   * 如果收到 webhook，说明用户已经点击了同步按钮，因此默认需要同步
   */
  checkSync2JiraFlag(parsedProperties) {
    // 由于 webhook 是通过点击 button property 触发的
    // 收到 webhook 就意味着用户想要同步到 JIRA
    // 但我们仍然可以检查一些条件来确认
    
    // 检查是否有明确的禁用同步标志（checkbox 字段）
    const sync2jiraField = parsedProperties['sync2jira'] || parsedProperties['同步到JIRA'] || parsedProperties['Sync to JIRA'];
    if (sync2jiraField?.type === 'checkbox' && sync2jiraField.value === false) {
      return false; // 明确设置为不同步
    }

    // 检查页面是否被归档或删除
    // 这些检查在上层已经处理，这里主要关注业务逻辑
    
    // 检查是否有同步按钮字段存在
    const buttonFields = Object.values(parsedProperties).filter(prop => prop.type === 'button');
    if (buttonFields.length > 0) {
      // 有按钮字段存在，说明支持同步功能
      return true;
    }

    // 默认情况下，收到 webhook 就认为需要同步
    // 这是因为 webhook 通常是由用户主动触发的操作产生的
    return true;
  }

  /**
   * 处理页面创建事件
   */
  async handlePageCreated(event) {
    const title = this.extractTitle(event.properties);
    
    logger.info('处理页面创建事件', {
      pageId: event.page_id,
      databaseId: event.database_id,
      title: title
    });

    // 检查是否需要同步到JIRA
    // 由于 webhook 是通过点击同步按钮触发的，默认都需要同步
    if (event.sync2jira === true) {
      await this.queueSyncEvent('notion_to_jira_create', event);
    }

    return { processed: true, action: 'page_created' };
  }

  /**
   * 处理页面更新事件
   */
  async handlePageUpdated(event) {
    const title = this.extractTitle(event.properties);
    
    logger.info('处理页面更新事件', {
      pageId: event.page_id,
      databaseId: event.database_id,
      title: title,
      sync2jira: event.sync2jira
    });
    
    // 检查是否是同步相关的更新
    // 由于 webhook 是通过点击同步按钮触发的，默认都需要同步
    if (event.sync2jira === true) {
      // 检查是否已存在JIRA关联
      const existingMapping = await this.checkExistingMapping(event.page_id);
      
      if (existingMapping) {
        await this.queueSyncEvent('notion_to_jira_update', event);
      } else {
        await this.queueSyncEvent('notion_to_jira_create', event);
      }
    }

    return { processed: true, action: 'page_updated' };
  }

  /**
   * 处理页面删除事件
   */
  async handlePageDeleted(event) {
    logger.info('处理页面删除事件', {
      pageId: event.page_id
    });

    // 检查是否有JIRA关联需要处理
    const existingMapping = await this.checkExistingMapping(event.page_id);
    if (existingMapping) {
      await this.queueSyncEvent('notion_to_jira_delete', event);
    }

    return { processed: true, action: 'page_deleted' };
  }

  /**
   * 将同步事件推送到队列
   */
  async queueSyncEvent(eventType, eventData) {
    try {
      const queueData = {
        type: eventType,
        source: 'notion',
        event_data: eventData,
        created_at: new Date().toISOString(),
        priority: this.getEventPriority(eventType)
      };

      const messageId = await redisClient.pushToQueue('sync_queue', queueData);
      
      logger.info('同步事件已加入队列', {
        messageId,
        eventType,
        pageId: eventData.page_id
      });

      return messageId;
    } catch (error) {
      logger.error('推送同步事件到队列失败:', error);
      throw error;
    }
  }

  /**
   * 检查是否存在JIRA映射关系
   */
  async checkExistingMapping(pageId) {
    try {
      // 从缓存中检查映射关系
      const mapping = await redisClient.getCache(`mapping:${pageId}`);
      return mapping;
    } catch (error) {
      logger.error('检查映射关系失败:', error);
      return null;
    }
  }

  /**
   * 获取事件优先级
   */
  getEventPriority(eventType) {
    const priorities = {
      'notion_to_jira_create': 'high',
      'notion_to_jira_update': 'medium',
      'notion_to_jira_delete': 'high'
    };
    return priorities[eventType] || 'low';
  }

  /**
   * 验证事件数据格式
   */
  validateEventData(event) {
    const required = ['page_id'];
    const missing = required.filter(field => !event[field]);
    
    if (missing.length > 0) {
      throw new Error(`缺少必填字段: ${missing.join(', ')}`);
    }

    return true;
  }

  /**
   * 从属性中提取标题
   */
  extractTitle(properties) {
    // 尝试多种可能的标题字段名
    const titleFields = ['功能 Name', 'title', 'Title', 'Name', 'name', '标题'];
    
    for (const fieldName of titleFields) {
      const field = properties[fieldName];
      if (field && (field.type === 'title' || field.type === 'rich_text') && field.value) {
        return field.value;
      }
    }
    
    // 如果没有找到标题字段，返回第一个有值的文本字段
    for (const [key, field] of Object.entries(properties)) {
      if ((field.type === 'title' || field.type === 'rich_text') && field.value) {
        return field.value;
      }
    }
    
    return '未命名页面';
  }
}

const webhookHandler = new NotionWebhookHandler();

/**
 * POST /webhook/notion
 * 接收 Notion Webhook 事件
 */
router.post('/notion', 
  express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf.toString('utf8');
    }
  }),
  verifyWebhookRequest,
  [
    body('source').optional().isObject(),
    body('data').notEmpty().withMessage('data 是必填项'),
    body('data.id').notEmpty().withMessage('data.id 是必填项'),
    body('data.object').equals('page').withMessage('只支持页面对象'),
    body('data.properties').optional().isObject()
  ],
  async (req, res) => {
    try {
      // 验证请求数据
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        logger.warn('Webhook请求数据验证失败', {
          errors: errors.array(),
          body: req.body
        });
        return res.status(400).json({
          error: 'Invalid request data',
          details: errors.array()
        });
      }

      // 解析 Notion Webhook 数据
      const event = webhookHandler.parseNotionWebhookData(req.body);
      
      // 记录接收到的事件
      const title = webhookHandler.extractTitle(event.properties);
      logger.info('接收到Notion Webhook事件', {
        eventType: event.event_type,
        pageId: event.page_id,
        databaseId: event.database_id,
        title: title,
        sync2jira: event.sync2jira,
        propertyCount: Object.keys(event.properties).length,
        timestamp: new Date().toISOString(),
        ip: req.ip
      });

      // 验证事件数据
      webhookHandler.validateEventData(event);

      // 根据事件类型处理
      let result;
      switch (event.event_type) {
        case 'page.created':
          result = await webhookHandler.handlePageCreated(event);
          break;
        case 'page.updated':
          result = await webhookHandler.handlePageUpdated(event);
          break;
        case 'page.deleted':
          result = await webhookHandler.handlePageDeleted(event);
          break;
        default:
          logger.info('忽略不支持的事件类型', {
            eventType: event.event_type,
            pageId: event.page_id
          });
          result = { processed: false, reason: 'unsupported_event_type' };
      }

      // 返回成功响应
      res.status(200).json({
        success: true,
        message: 'Webhook processed successfully',
        result: result,
        timestamp: new Date().toISOString()
      });

    } catch (error) {
      logger.error('处理Webhook事件失败:', error);
      
      res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * GET /webhook/test
 * 测试端点，用于验证服务是否正常
 */
router.get('/test', (req, res) => {
  res.json({
    success: true,
    message: 'Webhook service is running',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

module.exports = router; 