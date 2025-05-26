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
   * 处理页面创建事件
   */
  async handlePageCreated(event) {
    logger.info('处理页面创建事件', {
      pageId: event.page_id,
      databaseId: event.database_id
    });

    // 检查是否需要同步到JIRA
    const properties = event.properties || {};
    if (properties.sync2jira === true) {
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
      databaseId: event.database_id
    });

    const properties = event.properties || {};
    
    // 检查是否是同步相关的更新
    if (properties.sync2jira === true) {
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
    const required = ['event_type', 'page_id'];
    const missing = required.filter(field => !event[field]);
    
    if (missing.length > 0) {
      throw new Error(`缺少必填字段: ${missing.join(', ')}`);
    }

    if (!this.supportedEvents.includes(event.event_type)) {
      throw new Error(`不支持的事件类型: ${event.event_type}`);
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
    body('event_type').notEmpty().withMessage('event_type 是必填项'),
    body('page_id').notEmpty().withMessage('page_id 是必填项'),
    body('database_id').optional().isString(),
    body('properties').optional().isObject()
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

      const event = req.body;
      
      // 记录接收到的事件
      logger.info('接收到Notion Webhook事件', {
        eventType: event.event_type,
        pageId: event.page_id,
        databaseId: event.database_id,
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