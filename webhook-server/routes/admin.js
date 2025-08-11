const express = require('express');
const logger = require('../config/logger');
const redisManager = require('../config/redis_manager');
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
    const redisStatus = redisManager.getAllStatus();
    
    // 获取所有数据库的队列长度
    const queueStats = {};
    for (const [dbName, dbStatus] of Object.entries(redisStatus.databases)) {
      if (dbStatus.connected) {
        try {
          const dbNumber = dbStatus.database;
          const queueLength = await redisManager.getQueueLengthByDatabase(
            Object.keys(redisStatus.mapping).find(key => 
              redisStatus.mapping[key] === dbNumber
            ) || null, 
            'sync_queue'
          );
          queueStats[`${dbName}_sync_queue`] = queueLength;
        } catch (error) {
          queueStats[`${dbName}_sync_queue`] = 'error';
        }
      } else {
        queueStats[`${dbName}_sync_queue`] = 'disconnected';
      }
    }
    
    const status = {
      service: 'webhook-server',
      version: '1.0.0',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      redis: redisStatus,
      queues: queueStats,
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
    const redisStatus = redisManager.getAllStatus();
    const queues = {};
    
    // 遍历所有数据库获取队列统计
    for (const [databaseId, redisDB] of Object.entries(redisStatus.mapping)) {
      try {
        const queueLength = await redisManager.getQueueLengthByDatabase(databaseId, 'sync_queue');
        const dbName = databaseId === '19a15375830d81cbb107f8131b2d4cc0' ? 'network' : 'security';
        queues[`${dbName}_db${redisDB}`] = {
          length: queueLength,
          name: 'sync_queue',
          database_id: databaseId,
          redis_db: redisDB
        };
      } catch (error) {
        const dbName = databaseId === '19a15375830d81cbb107f8131b2d4cc0' ? 'network' : 'security';
        queues[`${dbName}_db${redisDB}`] = {
          length: 'error',
          name: 'sync_queue',
          database_id: databaseId,
          redis_db: redisDB,
          error: error.message
        };
      }
    }
    
    const stats = {
      queues,
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

    // 获取清空前的总长度
    let lengthBefore = 0;
    const redisStatus = redisManager.getAllStatus();
    for (const databaseId of Object.keys(redisStatus.mapping)) {
      try {
        const queueLength = await redisManager.getQueueLengthByDatabase(databaseId, queueName);
        lengthBefore += queueLength;
      } catch (error) {
        logger.warn(`获取队列长度失败`, { databaseId, error: error.message });
      }
    }
    
    // 清空所有数据库中的队列
    for (const databaseId of Object.keys(redisStatus.mapping)) {
      try {
        const redisInstance = redisManager.getClientByDatabaseId(databaseId);
        await redisInstance.client.del(queueName);
      } catch (error) {
        logger.warn(`清空Redis DB中的队列失败`, { databaseId, error: error.message });
      }
    }
    
    const lengthAfter = 0; // 清空后长度为0

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

    // 推送到队列（使用默认数据库）
    const messageId = await redisManager.pushToQueueByDatabase(
      testEvent.database_id, 
      'sync_queue', 
      {
        type: 'notion_to_jira_test',
        source: 'admin_test',
        event_data: testEvent,
        created_at: new Date().toISOString(),
        priority: 'low'
      }
    );

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

    // 设置到默认数据库的缓存
    await redisManager.setCacheByDatabase(null, key, value, expireSeconds);

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
    const value = await redisManager.getCacheByDatabase(null, key);

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