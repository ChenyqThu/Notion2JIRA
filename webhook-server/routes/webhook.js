const express = require('express');
const { body, validationResult } = require('express-validator');
const logger = require('../config/logger');
const redisClient = require('../config/redis');
const { verifyWebhookRequest, captureRawBody } = require('../middleware/auth');

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
    const properties = this.parseNotionProperties(data.properties);

    // 检查是否需要同步到 JIRA
    const sync2jira = this.checkSync2JiraFlag(data.properties);

    return {
      event_type: eventType,
      page_id: pageId,
      database_id: databaseId,
      last_edited_time: lastEditedTime,
      created_time: createdTime,
      archived,
      in_trash: inTrash,
      properties,
      sync2jira,
      raw_data: data,
      source_info: source
    };
  }

  /**
   * 解析 Notion 属性
   */
  parseNotionProperties(notionProperties) {
    const parsed = {};
    
    for (const [key, value] of Object.entries(notionProperties)) {
      try {
        switch (value.type) {
          case 'title':
            parsed[key] = value.title?.[0]?.plain_text || '';
            break;
          case 'rich_text':
            parsed[key] = value.rich_text?.[0]?.plain_text || '';
            break;
          case 'select':
            parsed[key] = value.select?.name || null;
            break;
          case 'multi_select':
            parsed[key] = value.multi_select?.map(item => item.name) || [];
            break;
          case 'status':
            parsed[key] = value.status?.name || null;
            break;
          case 'checkbox':
            parsed[key] = value.checkbox || false;
            break;
          case 'url':
            parsed[key] = value.url || null;
            break;
          case 'people':
            parsed[key] = value.people?.map(person => ({
              id: person.id,
              name: person.name,
              email: person.person?.email
            })) || [];
            break;
          case 'formula':
            parsed[key] = value.formula?.string || value.formula?.number || null;
            break;
          case 'created_time':
          case 'last_edited_time':
            parsed[key] = value[value.type];
            break;
          case 'relation':
            parsed[key] = value.relation || [];
            break;
          case 'rollup':
            parsed[key] = value.rollup;
            break;
          case 'button':
            // Button 字段通常不包含具体值，但其存在表示可以触发操作
            parsed[key] = value.button || {};
            break;
          default:
            parsed[key] = value;
        }
      } catch (error) {
        logger.warn(`解析属性 ${key} 失败:`, error);
        parsed[key] = value;
      }
    }
    
    return parsed;
  }

  /**
   * 检查是否需要同步到 JIRA
   * 注意：同步是通过 Notion database 的 button property 点击触发的
   * 如果收到 webhook，说明用户已经点击了同步按钮，因此默认需要同步
   */
  checkSync2JiraFlag(notionProperties) {
    // 由于 webhook 是通过点击 button property 触发的
    // 收到 webhook 就意味着用户想要同步到 JIRA
    // 但我们仍然可以检查一些条件来确认
    
    // 检查是否有 sync2jira 相关的 checkbox 字段
    const sync2jiraField = notionProperties.sync2jira;
    if (sync2jiraField?.checkbox === false) {
      return false; // 明确设置为不同步
    }

    // 检查是否有同步按钮字段（button 类型在 webhook 中可能不会显示具体值）
    // 默认情况下，收到 webhook 就认为需要同步
    return true;
  }

  /**
   * 处理页面创建事件
   */
  async handlePageCreated(event) {
    logger.info('处理页面创建事件', {
      pageId: event.page_id,
      databaseId: event.database_id,
      title: event.properties['功能 Name'] || event.properties.title
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
    logger.info('处理页面更新事件', {
      pageId: event.page_id,
      databaseId: event.database_id,
      title: event.properties['功能 Name'] || event.properties.title,
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
}

const webhookHandler = new NotionWebhookHandler();

/**
 * POST /webhook/notion
 * 接收 Notion Webhook 事件
 */
router.post('/notion', 
  captureRawBody,
  express.json(),
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
      logger.info('接收到Notion Webhook事件', {
        eventType: event.event_type,
        pageId: event.page_id,
        databaseId: event.database_id,
        title: event.properties['功能 Name'] || event.properties.title,
        sync2jira: event.sync2jira,
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