/**
 * Hello World API
 * Simple Express server for testing the GitLab CI/CD pipeline
 */

const express = require('express');
const app = express();

const PORT = process.env.PORT || 3000;
const VERSION = require('../package.json').version;

// Middleware
app.use(express.json());

// Health check endpoint (required for Docker health checks)
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

// Hello World endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Hello World from GitLab CI/CD Template! 🚀',
    version: VERSION,
    environment: process.env.NODE_ENV || 'development',
    timestamp: new Date().toISOString(),
  });
});

// API info endpoint
app.get('/api/info', (req, res) => {
  res.json({
    name: 'GitLab CI/CD Template API',
    version: VERSION,
    description: 'Simple Hello World API to test the complete CI/CD pipeline',
    endpoints: {
      health: '/health',
      root: '/',
      info: '/api/info',
    },
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.url} not found`,
  });
});

// Error handler
app.use((err, req, res, _next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message,
  });
});

// Start server only if not in test mode
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`📦 Version: ${VERSION}`);
    console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log('\n📍 Endpoints:');
    console.log(`   - http://localhost:${PORT}/`);
    console.log(`   - http://localhost:${PORT}/health`);
    console.log(`   - http://localhost:${PORT}/api/info`);
  });
}

// Export for testing
module.exports = app;
