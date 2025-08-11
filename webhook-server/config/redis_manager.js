const redis = require('redis');
const logger = require('./logger');

class RedisManager {
  constructor() {
    this.clients = new Map(); // db_number -> redis_client_instance
    this.isInitialized = false;
    
    // 数据库映射配置
    this.databaseMapping = {
      '19a15375830d81cbb107f8131b2d4cc0': 0, // 网络需求池
      '1af15375830d804e9d13c24f3d0a3424': 1  // 安防需求池
    };
    
    this.defaultRedisDB = 0; // 默认Redis DB，用于未配置的database_id
    
    logger.info('RedisManager初始化', {
      databaseMapping: this.databaseMapping,
      defaultDB: this.defaultRedisDB
    });
  }

  /**
   * 初始化所有需要的Redis连接
   */
  async initialize() {
    try {
      // 获取所有需要连接的DB编号
      const dbNumbers = [...new Set([
        ...Object.values(this.databaseMapping),
        this.defaultRedisDB
      ])];

      logger.info('开始创建Redis连接', { databases: dbNumbers });

      // 并行创建所有Redis连接
      const connectionPromises = dbNumbers.map(dbNumber => this.createClient(dbNumber));
      await Promise.all(connectionPromises);

      this.isInitialized = true;
      logger.info('RedisManager初始化完成', {
        connectedDatabases: Array.from(this.clients.keys())
      });

    } catch (error) {
      logger.error('RedisManager初始化失败:', error);
      throw error;
    }
  }

  /**
   * 创建指定DB的Redis客户端
   */
  async createClient(dbNumber) {
    try {
      const client = redis.createClient({
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
        password: process.env.REDIS_PASSWORD || undefined,
        database: dbNumber,
        retry_strategy: (retries) => {
          if (retries > 10) {
            logger.error(`Redis DB ${dbNumber} 重试次数超过10次，停止重试`);
            return null;
          }
          return Math.min(retries * 100, 3000);
        }
      });

      // 设置事件监听器
      client.on('connect', () => {
        logger.info(`Redis DB ${dbNumber} 连接成功`);
      });

      client.on('error', (err) => {
        logger.error(`Redis DB ${dbNumber} 连接错误:`, err);
      });

      client.on('end', () => {
        logger.warn(`Redis DB ${dbNumber} 连接已断开`);
      });

      client.on('ready', () => {
        logger.info(`Redis DB ${dbNumber} 客户端就绪`);
      });

      await client.connect();
      
      // 存储客户端实例
      this.clients.set(dbNumber, {
        client: client,
        dbNumber: dbNumber,
        isConnected: true
      });

      logger.info(`Redis DB ${dbNumber} 连接建立完成`);
      return client;

    } catch (error) {
      logger.error(`创建Redis DB ${dbNumber} 连接失败:`, error);
      throw error;
    }
  }

  /**
   * 根据database_id获取对应的Redis客户端
   */
  getClientByDatabaseId(databaseId) {
    if (!this.isInitialized) {
      throw new Error('RedisManager尚未初始化');
    }

    // 查找对应的Redis DB编号
    let dbNumber = this.databaseMapping[databaseId];
    
    if (dbNumber === undefined) {
      logger.warn('未找到database_id对应的Redis DB配置，使用默认DB', {
        databaseId: databaseId,
        defaultDB: this.defaultRedisDB
      });
      dbNumber = this.defaultRedisDB;
    }

    const redisInstance = this.clients.get(dbNumber);
    
    if (!redisInstance || !redisInstance.isConnected) {
      throw new Error(`Redis DB ${dbNumber} 连接不可用`);
    }

    logger.debug('路由到Redis DB', {
      databaseId: databaseId,
      redisDB: dbNumber
    });

    return redisInstance;
  }

  /**
   * 获取默认Redis客户端（用于向后兼容）
   */
  getDefaultClient() {
    return this.getClientByDatabaseId(null); // 会使用defaultRedisDB
  }

  /**
   * 推送消息到指定database对应的队列
   */
  async pushToQueueByDatabase(databaseId, queueName, data) {
    try {
      const redisInstance = this.getClientByDatabaseId(databaseId);
      const client = redisInstance.client;

      const message = {
        id: this.generateId(),
        timestamp: Date.now(),
        data: data,
        retry_count: 0,
        database_id: databaseId,
        redis_db: redisInstance.dbNumber
      };

      await client.lPush(queueName, JSON.stringify(message));
      
      logger.info(`消息已推送到队列`, {
        messageId: message.id,
        queueName: queueName,
        databaseId: databaseId,
        redisDB: redisInstance.dbNumber
      });
      
      return message.id;
      
    } catch (error) {
      logger.error('推送消息到队列失败:', error);
      throw error;
    }
  }

  /**
   * 获取指定database对应队列的长度
   */
  async getQueueLengthByDatabase(databaseId, queueName) {
    try {
      const redisInstance = this.getClientByDatabaseId(databaseId);
      const client = redisInstance.client;
      
      return await client.lLen(queueName);
    } catch (error) {
      logger.error('获取队列长度失败:', error);
      return 0;
    }
  }

  /**
   * 在指定database对应的Redis中设置缓存
   */
  async setCacheByDatabase(databaseId, key, value, expireSeconds = 3600) {
    try {
      const redisInstance = this.getClientByDatabaseId(databaseId);
      const client = redisInstance.client;
      
      await client.setEx(key, expireSeconds, JSON.stringify(value));
      logger.debug(`缓存已设置在Redis DB ${redisInstance.dbNumber}: ${key}`);
    } catch (error) {
      logger.error('设置缓存失败:', error);
      throw error;
    }
  }

  /**
   * 从指定database对应的Redis中获取缓存
   */
  async getCacheByDatabase(databaseId, key) {
    try {
      const redisInstance = this.getClientByDatabaseId(databaseId);
      const client = redisInstance.client;
      
      const value = await client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('获取缓存失败:', error);
      return null;
    }
  }

  /**
   * 获取所有Redis连接的状态
   */
  getAllStatus() {
    const statuses = {};
    
    for (const [dbNumber, redisInstance] of this.clients.entries()) {
      statuses[`db_${dbNumber}`] = {
        connected: redisInstance.isConnected,
        ready: redisInstance.client?.isReady || false,
        database: dbNumber
      };
    }

    return {
      initialized: this.isInitialized,
      databases: statuses,
      mapping: this.databaseMapping
    };
  }

  /**
   * 关闭所有Redis连接
   */
  async disconnect() {
    logger.info('开始关闭所有Redis连接');
    
    const disconnectPromises = [];
    
    for (const [dbNumber, redisInstance] of this.clients.entries()) {
      if (redisInstance.client) {
        disconnectPromises.push(
          redisInstance.client.quit().then(() => {
            logger.info(`Redis DB ${dbNumber} 连接已关闭`);
            redisInstance.isConnected = false;
          }).catch(error => {
            logger.error(`关闭Redis DB ${dbNumber} 连接失败:`, error);
          })
        );
      }
    }
    
    await Promise.all(disconnectPromises);
    this.clients.clear();
    this.isInitialized = false;
    
    logger.info('所有Redis连接已关闭');
  }

  /**
   * 生成唯一ID
   */
  generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 添加新的database映射（运行时动态添加）
   */
  async addDatabaseMapping(databaseId, redisDB) {
    try {
      // 检查Redis DB是否已存在连接
      if (!this.clients.has(redisDB)) {
        await this.createClient(redisDB);
      }
      
      // 添加映射关系
      this.databaseMapping[databaseId] = redisDB;
      
      logger.info('添加数据库映射', {
        databaseId: databaseId,
        redisDB: redisDB
      });
      
    } catch (error) {
      logger.error('添加数据库映射失败:', error);
      throw error;
    }
  }
}

module.exports = new RedisManager();