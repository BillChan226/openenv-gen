import assert from 'node:assert/strict';
import test from 'node:test';

import searchRouter from './search.js';
import pool from '../db/pool.js';

function createMockRes() {
  const res = {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
  return res;
}

async function invokeSearchHandler(req, res) {
  // Express Router stores layers in stack; find GET '/' handler
  const layer = searchRouter.stack.find((l) => l?.route?.path === '/' && l?.route?.methods?.get);
  assert.ok(layer, 'expected GET / handler layer to exist');

  // Route stack: [authRequired, handler]
  const handler = layer.route.stack[layer.route.stack.length - 1].handle;

  let nextErr;
  await handler(req, res, (err) => {
    nextErr = err;
  });

  return { nextErr };
}

test('GET /api/search: missing q -> ApiError with standard shape via next()', async () => {
  const req = { query: {}, headers: {}, user: { id: 'u1' } };
  const res = createMockRes();

  const { nextErr } = await invokeSearchHandler(req, res);

  assert.ok(nextErr, 'expected next(err) to be called');
  assert.equal(nextErr.status, 400);
  assert.equal(nextErr.code, 'validation_error');
  assert.match(nextErr.message, /q is required/i);
  assert.deepEqual(nextErr.details, { field: 'q' });
});

test('GET /api/search: applies filters and returns issues with project context', async () => {
  const originalQuery = pool.query;

  try {
    // Mock DB response
    pool.query = async (_sql, params) => {
      // params: [q, %q%, projectId?, status?, assigneeId?, limit, offset]
      assert.equal(params[0], 'test');
      assert.equal(params[1], '%test%');

      return {
        rows: [
          {
            id: 'i1',
            key: 'ACME-1',
            title: 'Test issue',
            description: 'test description',
            status: 'TODO',
            priority: 'MEDIUM',
            assignee_user_id: 'u2',
            reporter_user_id: 'u1',
            project_id: 'p1',
            project_key: 'ACME',
            project_name: 'Acme Project',
            created_at: new Date('2024-01-01T00:00:00.000Z'),
            updated_at: new Date('2024-01-02T00:00:00.000Z'),
          },
        ],
      };
    };

    const req = {
      query: {
        q: 'test',
        projectId: 'p1',
        status: 'TODO',
        assigneeId: 'u2',
        limit: '10',
        offset: '0',
      },
      headers: {},
      user: { id: 'u1' },
    };

    const res = createMockRes();

    const { nextErr } = await invokeSearchHandler(req, res);

    assert.equal(nextErr, undefined);
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.query, 'test');
    assert.ok(Array.isArray(res.body.issues));
    assert.equal(res.body.issues.length, 1);

    const issue = res.body.issues[0];
    assert.equal(issue.key, 'ACME-1');
    assert.ok(issue.project);
    assert.equal(issue.project.key, 'ACME');
    assert.equal(issue.project.name, 'Acme Project');
  } finally {
    pool.query = originalQuery;
  }
});
