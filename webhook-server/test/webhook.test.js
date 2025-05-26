const request = require('supertest');
const app = require('../server');

describe('Webhook API Tests', () => {
  let server;

  beforeAll(async () => {
    // 设置测试环境变量
    process.env.NODE_ENV = 'test';
    process.env.ADMIN_API_KEY = 'test-admin-key';
  });

  afterAll(async () => {
    if (server) {
      await server.close();
    }
  });

  describe('GET /', () => {
    it('应该返回服务基本信息', async () => {
      const response = await request(app)
        .get('/')
        .expect(200);

      expect(response.body).toHaveProperty('service');
      expect(response.body).toHaveProperty('version');
      expect(response.body).toHaveProperty('endpoints');
    });
  });

  describe('GET /health', () => {
    it('应该返回健康检查信息', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toHaveProperty('status');
      expect(response.body).toHaveProperty('timestamp');
      expect(response.body).toHaveProperty('uptime');
    });
  });

  describe('GET /webhook/test', () => {
    it('应该返回webhook测试信息', async () => {
      const response = await request(app)
        .get('/webhook/test')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message');
    });
  });

  describe('POST /webhook/notion', () => {
    it('应该拒绝非JSON内容类型的请求', async () => {
      await request(app)
        .post('/webhook/notion')
        .set('Content-Type', 'text/plain')
        .send('invalid data')
        .expect(400);
    });

    it('应该拒绝缺少必填字段的请求', async () => {
      const testEvent = {
        // 缺少 event_type 和 page_id
        properties: { sync2jira: true }
      };

      await request(app)
        .post('/webhook/notion')
        .set('Content-Type', 'application/json')
        .send(testEvent)
        .expect(400);
    });

    it('应该接受有效的webhook请求', async () => {
      const testEvent = {
        event_type: 'page.updated',
        page_id: 'test-page-id',
        database_id: 'test-database-id',
        properties: { sync2jira: true }
      };

      const response = await request(app)
        .post('/webhook/notion')
        .set('Content-Type', 'application/json')
        .send(testEvent)
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('result');
    });

    it('应该处理不支持的事件类型', async () => {
      const testEvent = {
        event_type: 'unsupported.event',
        page_id: 'test-page-id',
        properties: { sync2jira: true }
      };

      const response = await request(app)
        .post('/webhook/notion')
        .set('Content-Type', 'application/json')
        .send(testEvent)
        .expect(500); // 因为不支持的事件类型会抛出异常

      expect(response.body).toHaveProperty('success', false);
    });
  });

  describe('Admin API Tests', () => {
    describe('GET /admin/status', () => {
      it('应该拒绝没有API Key的请求', async () => {
        await request(app)
          .get('/admin/status')
          .expect(401);
      });

      it('应该接受有效API Key的请求', async () => {
        const response = await request(app)
          .get('/admin/status')
          .set('X-API-Key', 'test-admin-key')
          .expect(200);

        expect(response.body).toHaveProperty('success', true);
        expect(response.body).toHaveProperty('data');
        expect(response.body.data).toHaveProperty('service');
      });
    });

    describe('POST /admin/test/webhook', () => {
      it('应该创建测试webhook事件', async () => {
        const testData = {
          pageId: 'test-page-123',
          eventType: 'page.updated',
          properties: {
            title: 'Test Page',
            sync2jira: true
          }
        };

        const response = await request(app)
          .post('/admin/test/webhook')
          .set('X-API-Key', 'test-admin-key')
          .send(testData)
          .expect(200);

        expect(response.body).toHaveProperty('success', true);
        expect(response.body).toHaveProperty('data');
        expect(response.body.data).toHaveProperty('messageId');
      });

      it('应该拒绝没有pageId的请求', async () => {
        const testData = {
          eventType: 'page.updated'
        };

        await request(app)
          .post('/admin/test/webhook')
          .set('X-API-Key', 'test-admin-key')
          .send(testData)
          .expect(400);
      });
    });
  });

  describe('Error Handling', () => {
    it('应该返回404对于不存在的路由', async () => {
      await request(app)
        .get('/non-existent-route')
        .expect(404);
    });

    it('应该处理限流', async () => {
      // 这个测试需要根据实际的限流配置调整
      // 由于测试环境可能有不同的限流设置，这里只是示例
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(request(app).get('/'));
      }
      
      const responses = await Promise.all(promises);
      // 所有请求都应该成功，因为限流阈值通常较高
      responses.forEach(response => {
        expect([200, 429]).toContain(response.status);
      });
    });
  });
}); 