const redis = require('redis');
const logger = require('./logger');

class RedisClient {
  constructor() {
    this.client = null;
    this.isConnected = false;
  }

  async connect() {
    try {
      this.client = redis.createClient({
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
        password: process.env.REDIS_PASSWORD || undefined,
        database: process.env.REDIS_DB || 0,
        retry_strategy: (retries) => {
          if (retries > 10) {
            logger.error('Redis重试次数超过10次，停止重试');
            return null;
          }
          // 指数退避重试
          return Math.min(retries * 100, 3000);
        }
      });

      this.client.on('connect', () => {
        logger.info('Redis客户端连接成功');
        this.isConnected = true;
      });

      this.client.on('error', (err) => {
        logger.error('Redis连接错误:', err);
        this.isConnected = false;
      });

      this.client.on('end', () => {
        logger.warn('Redis连接已断开');
        this.isConnected = false;
      });

      this.client.on('ready', () => {
        logger.info('Redis客户端就绪');
        this.isConnected = true;
      });

      await this.client.connect();
      logger.info('Redis连接初始化完成');
      
    } catch (error) {
      logger.error('Redis连接失败:', error);
      throw error;
    }
  }

  async disconnect() {
    if (this.client) {
      await this.client.quit();
      logger.info('Redis连接已关闭');
    }
  }

  async pushToQueue(queueName, data) {
    try {
      if (!this.isConnected) {
        throw new Error('Redis未连接');
      }

      const message = {
        id: this.generateId(),
        timestamp: Date.now(),
        data: data,
        retry_count: 0
      };

      await this.client.lPush(queueName, JSON.stringify(message));
      logger.info(`消息已推送到队列 ${queueName}:`, { messageId: message.id });
      
      return message.id;
    } catch (error) {
      logger.error('推送消息到队列失败:', error);
      throw error;
    }
  }

  async getQueueLength(queueName) {
    try {
      if (!this.isConnected) {
        return 0;
      }
      return await this.client.lLen(queueName);
    } catch (error) {
      logger.error('获取队列长度失败:', error);
      return 0;
    }
  }

  async setCache(key, value, expireSeconds = 3600) {
    try {
      if (!this.isConnected) {
        throw new Error('Redis未连接');
      }
      
      await this.client.setEx(key, expireSeconds, JSON.stringify(value));
      logger.debug(`缓存已设置: ${key}`);
    } catch (error) {
      logger.error('设置缓存失败:', error);
      throw error;
    }
  }

  async getCache(key) {
    try {
      if (!this.isConnected) {
        return null;
      }
      
      const value = await this.client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('获取缓存失败:', error);
      return null;
    }
  }

  generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  getStatus() {
    return {
      connected: this.isConnected,
      ready: this.client?.isReady || false
    };
  }
}

module.exports = new RedisClient(); 