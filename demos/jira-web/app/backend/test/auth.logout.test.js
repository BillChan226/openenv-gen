import test from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';

import app from '../src/app.js';

// These tests assume the DB is available and seeded.
// They validate that logout revokes the presented JWT.

test('auth: logout revokes token; /me rejects after logout', { skip: process.env.RUN_DB_TESTS !== 'true' }, async () => {
  const agent = request(app);

  // Login with seeded user
  const loginRes = await agent
    .post('/api/auth/login')
    .set('Content-Type', 'application/json')
    .send({ email: 'admin@example.com', password: 'password' });

  assert.equal(loginRes.status, 200);
  assert.ok(loginRes.body?.token);

  const token = loginRes.body.token;

  const meBefore = await agent.get('/api/auth/me').set('Authorization', `Bearer ${token}`);
  assert.equal(meBefore.status, 200);
  assert.ok(meBefore.body?.user?.id);

  const logoutRes = await agent.post('/api/auth/logout').set('Authorization', `Bearer ${token}`);
  assert.equal(logoutRes.status, 204);

  const meAfter = await agent.get('/api/auth/me').set('Authorization', `Bearer ${token}`);
  assert.ok([401, 403].includes(meAfter.status));
});

test('smoke: GET /health returns 200', async () => {
  const res = await request(app).get('/health');
  assert.equal(res.status, 200);
});

// Non-blocking smoke coverage for core resources (ensures routes are wired).
// Uses AUTH_TEST_MODE escape hatch to avoid needing cookie persistence.
// If AUTH_TEST_MODE is not enabled, these will be skipped.

test('smoke: projects/issues endpoints respond (AUTH_TEST_MODE)', async (t) => {
  if (process.env.AUTH_TEST_MODE !== 'true') {
    t.skip('AUTH_TEST_MODE not enabled');
    return;
  }

  const token = process.env.AUTH_TEST_TOKEN || 'test-token';
  const agent = request(app);

  const projectsRes = await agent.get('/api/projects').set('x-test-auth', token);
  assert.ok([200, 401, 403].includes(projectsRes.status));

  const issuesRes = await agent.get('/api/issues').set('x-test-auth', token);
  assert.ok([200, 401, 403].includes(issuesRes.status));
});
