const express = require('express');
const logger = require('../config/logger');
const redisClient = require('../config/redis');
const { verifyApiKey } = require('../middleware/auth');

const router = express.Router();

// 所有管理接口都需要API Key验证
router.use(verifyApiKey);

/**
 * GET /admin/status
 * 获取系统状态信息
 */
router.get('/status', async (req, res) => {
  try {
    const redisStatus = redisClient.getStatus();
    const queueLength = await redisClient.getQueueLength('sync_queue');
    
    const status = {
      service: 'webhook-server',
      version: '1.0.0',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      redis: redisStatus,
      queue: {
        sync_queue_length: queueLength
      },
      timestamp: new Date().toISOString()
    };

    res.json({
      success: true,
      data: status
    });

  } catch (error) {
    logger.error('获取系统状态失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get system status',
      message: error.message
    });
  }
});

/**
 * GET /admin/queue/stats
 * 获取队列统计信息
 */
router.get('/queue/stats', async (req, res) => {
  try {
    const syncQueueLength = await redisClient.getQueueLength('sync_queue');
    
    const stats = {
      queues: {
        sync_queue: {
          length: syncQueueLength,
          name: 'sync_queue'
        }
      },
      timestamp: new Date().toISOString()
    };

    res.json({
      success: true,
      data: stats
    });

  } catch (error) {
    logger.error('获取队列统计失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get queue stats',
      message: error.message
    });
  }
});

/**
 * POST /admin/queue/clear
 * 清空指定队列
 */
router.post('/queue/clear', async (req, res) => {
  try {
    const { queueName } = req.body;
    
    if (!queueName) {
      return res.status(400).json({
        success: false,
        error: 'Queue name is required'
      });
    }

    // 安全检查：只允许清空特定队列
    const allowedQueues = ['sync_queue'];
    if (!allowedQueues.includes(queueName)) {
      return res.status(400).json({
        success: false,
        error: 'Queue not allowed to be cleared'
      });
    }

    const lengthBefore = await redisClient.getQueueLength(queueName);
    
    // 清空队列
    if (redisClient.client && redisClient.isConnected) {
      await redisClient.client.del(queueName);
    }
    
    const lengthAfter = await redisClient.getQueueLength(queueName);

    logger.info('队列已清空', {
      queueName,
      lengthBefore,
      lengthAfter,
      admin: req.ip
    });

    res.json({
      success: true,
      message: `Queue ${queueName} cleared successfully`,
      data: {
        queueName,
        lengthBefore,
        lengthAfter
      }
    });

  } catch (error) {
    logger.error('清空队列失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to clear queue',
      message: error.message
    });
  }
});

/**
 * POST /admin/test/webhook
 * 测试webhook处理（模拟Notion事件）
 */
router.post('/test/webhook', async (req, res) => {
  try {
    const { eventType = 'page.updated', pageId, properties } = req.body;
    
    if (!pageId) {
      return res.status(400).json({
        success: false,
        error: 'pageId is required for testing'
      });
    }

    // 构造测试事件
    const testEvent = {
      event_type: eventType,
      page_id: pageId,
      database_id: 'test-database-id',
      properties: properties || {
        title: 'Test Page',
        sync2jira: true,
        priority: 'Medium'
      },
      timestamp: new Date().toISOString()
    };

    // 推送到队列
    const messageId = await redisClient.pushToQueue('sync_queue', {
      type: 'notion_to_jira_test',
      source: 'admin_test',
      event_data: testEvent,
      created_at: new Date().toISOString(),
      priority: 'low'
    });

    logger.info('测试事件已创建', {
      messageId,
      eventType,
      pageId,
      admin: req.ip
    });

    res.json({
      success: true,
      message: 'Test webhook event created successfully',
      data: {
        messageId,
        testEvent
      }
    });

  } catch (error) {
    logger.error('创建测试事件失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create test event',
      message: error.message
    });
  }
});

/**
 * GET /admin/logs/recent
 * 获取最近的日志记录
 */
router.get('/logs/recent', async (req, res) => {
  try {
    const { level = 'info', limit = 50 } = req.query;
    
    // 这里简化实现，实际应该从日志文件或日志系统中读取
    // 由于winston默认不提供查询接口，这里返回模拟数据
    const recentLogs = [
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'Recent logs endpoint accessed',
        service: 'notion-webhook'
      }
    ];

    res.json({
      success: true,
      data: {
        logs: recentLogs,
        total: recentLogs.length,
        level,
        limit: parseInt(limit)
      }
    });

  } catch (error) {
    logger.error('获取日志失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get recent logs',
      message: error.message
    });
  }
});

/**
 * POST /admin/cache/set
 * 设置缓存（用于测试）
 */
router.post('/cache/set', async (req, res) => {
  try {
    const { key, value, expireSeconds = 3600 } = req.body;
    
    if (!key || value === undefined) {
      return res.status(400).json({
        success: false,
        error: 'Key and value are required'
      });
    }

    await redisClient.setCache(key, value, expireSeconds);

    logger.info('缓存已设置', {
      key,
      expireSeconds,
      admin: req.ip
    });

    res.json({
      success: true,
      message: 'Cache set successfully',
      data: { key, expireSeconds }
    });

  } catch (error) {
    logger.error('设置缓存失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to set cache',
      message: error.message
    });
  }
});

/**
 * GET /admin/cache/get/:key
 * 获取缓存值
 */
router.get('/cache/get/:key', async (req, res) => {
  try {
    const { key } = req.params;
    const value = await redisClient.getCache(key);

    res.json({
      success: true,
      data: {
        key,
        value,
        exists: value !== null
      }
    });

  } catch (error) {
    logger.error('获取缓存失败:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get cache',
      message: error.message
    });
  }
});

module.exports = router; 