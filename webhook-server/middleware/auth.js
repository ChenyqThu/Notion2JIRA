const crypto = require('crypto');
const logger = require('../config/logger');

/**
 * 原始请求体捕获中间件
 * 保存原始请求体用于日志记录
 */
function captureRawBody(req, res, next) {
  const chunks = [];
  
  req.on('data', (chunk) => {
    chunks.push(chunk);
  });
  
  req.on('end', () => {
    req.rawBody = Buffer.concat(chunks).toString('utf8');
    next();
  });
}

/**
 * 基础请求验证中间件
 * 验证请求来源和基本安全检查
 */
function verifyWebhookRequest(req, res, next) {
  try {
    const userAgent = req.get('User-Agent');
    const contentType = req.get('Content-Type');

    // 记录请求信息
    logger.info('接收到 Webhook 请求', {
      ip: req.ip,
      userAgent,
      contentType,
      method: req.method,
      path: req.path
    });

    // 基本的内容类型检查
    if (!contentType || !contentType.includes('application/json')) {
      logger.warn('Webhook请求内容类型不正确', {
        contentType,
        ip: req.ip
      });
      return res.status(400).json({
        error: 'Invalid content type, expected application/json'
      });
    }

    next();
  } catch (error) {
    logger.error('请求验证过程中发生错误:', error);
    return res.status(500).json({
      error: 'Request verification failed'
    });
  }
}

/**
 * API Key 验证中间件（用于管理接口）
 */
function verifyApiKey(req, res, next) {
  const apiKey = req.headers['x-api-key'];
  const validApiKey = process.env.ADMIN_API_KEY;

  if (!apiKey || !validApiKey || apiKey !== validApiKey) {
    logger.warn('API Key验证失败', {
      hasApiKey: !!apiKey,
      ip: req.ip
    });
    return res.status(401).json({
      error: 'Invalid API key'
    });
  }

  next();
}

module.exports = {
  verifyWebhookRequest,
  captureRawBody,
  verifyApiKey
}; 