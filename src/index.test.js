/**
 * Tests for Hello World API
 */

const request = require('supertest');
const app = require('./index');

describe('Hello World API', () => {
  describe('GET /', () => {
    it('should return hello world message', async () => {
      const res = await request(app).get('/');

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('message');
      expect(res.body.message).toContain('Hello World');
      expect(res.body).toHaveProperty('version');
      expect(res.body).toHaveProperty('timestamp');
    });

    it('should return JSON content type', async () => {
      const res = await request(app).get('/');

      expect(res.headers['content-type']).toMatch(/json/);
    });
  });

  describe('GET /health', () => {
    it('should return healthy status', async () => {
      const res = await request(app).get('/health');

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('status', 'ok');
      expect(res.body).toHaveProperty('uptime');
      expect(res.body).toHaveProperty('timestamp');
    });

    it('should return uptime as number', async () => {
      const res = await request(app).get('/health');

      expect(typeof res.body.uptime).toBe('number');
      expect(res.body.uptime).toBeGreaterThanOrEqual(0);
    });
  });

  describe('GET /api/info', () => {
    it('should return API information', async () => {
      const res = await request(app).get('/api/info');

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('name');
      expect(res.body).toHaveProperty('version');
      expect(res.body).toHaveProperty('description');
      expect(res.body).toHaveProperty('endpoints');
    });

    it('should list all available endpoints', async () => {
      const res = await request(app).get('/api/info');

      expect(res.body.endpoints).toHaveProperty('health');
      expect(res.body.endpoints).toHaveProperty('root');
      expect(res.body.endpoints).toHaveProperty('info');
    });
  });

  describe('GET /unknown-route', () => {
    it('should return 404 for unknown routes', async () => {
      const res = await request(app).get('/unknown-route');

      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error', 'Not Found');
    });
  });
});
