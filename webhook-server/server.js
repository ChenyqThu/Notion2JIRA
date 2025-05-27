#!/usr/bin/env node

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const logger = require('./config/logger');
const redisClient = require('./config/redis');
const webhookRoutes = require('./routes/webhook');
const adminRoutes = require('./routes/admin');

const app = express();
const PORT = process.env.PORT || 7654;

// 创建日志目录
const fs = require('fs');
const path = require('path');
const logDir = path.join(__dirname, 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// 安全中间件
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// CORS配置
const corsEnabled = process.env.CORS_ENABLED !== 'false'; // 默认启用，设置为 'false' 时禁用
const allowedOrigins = process.env.ALLOWED_ORIGINS 
  ? process.env.ALLOWED_ORIGINS.split(',')
  : ['https://api.notion.com', 'https://www.notion.so'];

if (corsEnabled) {
  app.use(cors({
    origin: function (origin, callback) {
      // 开发环境允许所有来源（方便本地调试）
      if (process.env.NODE_ENV === 'development') {
        return callback(null, true);
      }
      
      // 允许没有origin的请求（如移动应用或Postman）
      if (!origin) return callback(null, true);
      
      if (allowedOrigins.indexOf(origin) !== -1) {
        callback(null, true);
      } else {
        logger.warn('CORS阻止的请求', { origin });
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key', 'Notion-Webhook-Signature', 'Notion-Webhook-Timestamp']
  }));
  logger.info('CORS已启用', { allowedOrigins, isDevelopment: process.env.NODE_ENV === 'development' });
} else {
  logger.info('CORS已禁用');
}

// 限流配置
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15分钟
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100, // 限制每个IP最多100请求
  message: {
    error: 'Too many requests from this IP, please try again later.',
    retryAfter: '15 minutes'
  },
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    logger.warn('限流触发', {
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      path: req.path
    });
    res.status(429).json({
      error: 'Too many requests',
      message: 'Rate limit exceeded, please try again later'
    });
  }
});

app.use(limiter);

// 请求日志
app.use(morgan('combined', {
  stream: {
    write: (message) => {
      logger.info(message.trim());
    }
  }
}));

// 信任代理（如果在负载均衡器后面）
app.set('trust proxy', 1);

// 健康检查端点（在其他中间件之前）
app.get(process.env.HEALTH_CHECK_PATH || '/health', (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    redis: redisClient.getStatus(),
    memory: process.memoryUsage(),
    version: '1.0.0'
  };

  const statusCode = health.redis.connected ? 200 : 503;
  res.status(statusCode).json(health);
});

// 基础信息端点
app.get('/', (req, res) => {
  res.json({
    service: 'Notion Webhook Server',
    version: '1.0.0',
    description: 'Webhook receiver for Notion-JIRA sync system',
    endpoints: {
      webhook: '/webhook/notion',
      health: '/health',
      admin: '/admin/*'
    },
    timestamp: new Date().toISOString()
  });
});

// 路由配置
app.use('/webhook', webhookRoutes);
app.use('/admin', adminRoutes);

// 404处理
app.use('*', (req, res) => {
  logger.warn('404请求', {
    method: req.method,
    url: req.originalUrl,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });
  
  res.status(404).json({
    error: 'Not Found',
    message: 'The requested endpoint does not exist',
    timestamp: new Date().toISOString()
  });
});

// 全局错误处理
app.use((err, req, res, next) => {
  logger.error('未处理的错误:', {
    error: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip
  });

  // 不要在生产环境中暴露错误堆栈
  const isDevelopment = process.env.NODE_ENV !== 'production';
  
  res.status(err.status || 500).json({
    error: 'Internal Server Error',
    message: isDevelopment ? err.message : 'Something went wrong',
    ...(isDevelopment && { stack: err.stack }),
    timestamp: new Date().toISOString()
  });
});

// 优雅关闭处理
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

async function gracefulShutdown(signal) {
  logger.info(`收到 ${signal} 信号，开始优雅关闭...`);
  
  // 停止接受新连接
  server.close(async () => {
    logger.info('HTTP服务器已关闭');
    
    try {
      // 关闭Redis连接
      await redisClient.disconnect();
      logger.info('Redis连接已关闭');
      
      logger.info('优雅关闭完成');
      process.exit(0);
    } catch (error) {
      logger.error('优雅关闭过程中发生错误:', error);
      process.exit(1);
    }
  });

  // 强制关闭超时
  setTimeout(() => {
    logger.error('强制关闭超时，立即退出');
    process.exit(1);
  }, 10000);
}

// 未捕获异常处理
process.on('uncaughtException', (err) => {
  logger.error('未捕获的异常:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('未处理的Promise拒绝:', { reason, promise });
  process.exit(1);
});

// 启动服务器
async function startServer() {
  try {
    // 连接Redis
    await redisClient.connect();
    logger.info('Redis连接成功');

    // 启动HTTP服务器
    const server = app.listen(PORT, () => {
      logger.info(`Webhook服务器启动成功`, {
        port: PORT,
        env: process.env.NODE_ENV || 'development',
        pid: process.pid
      });
    });

    // 保存server实例用于优雅关闭
    global.server = server;

    return server;
  } catch (error) {
    logger.error('服务器启动失败:', error);
    process.exit(1);
  }
}

// 如果直接运行此文件，则启动服务器
if (require.main === module) {
  startServer();
}

module.exports = app; 