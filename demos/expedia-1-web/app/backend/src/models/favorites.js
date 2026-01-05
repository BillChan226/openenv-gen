const db = require('../db');

async function ensureFavoritesTable() {
  await db.query(`
    CREATE TABLE IF NOT EXISTS favorites (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL,
      type TEXT NOT NULL,
      item_id TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (user_id, type, item_id)
    );
  `);
}

async function listFavoritesByUser(userId) {
  const { rows } = await db.query(
    `SELECT id, user_id AS "userId", type, item_id AS "itemId", created_at AS "createdAt"
     FROM favorites
     WHERE user_id = $1
     ORDER BY created_at DESC`,
    [userId]
  );
  return rows;
}

async function addFavorite({ userId, type, itemId }) {
  const { rows } = await db.query(
    `INSERT INTO favorites (user_id, type, item_id)
     VALUES ($1, $2, $3)
     ON CONFLICT (user_id, type, item_id)
     DO UPDATE SET user_id = EXCLUDED.user_id
     RETURNING id, user_id AS "userId", type, item_id AS "itemId", created_at AS "createdAt"`,
    [userId, type, itemId]
  );
  return rows[0];
}

async function deleteFavorite({ userId, id }) {
  const { rowCount } = await db.query(`DELETE FROM favorites WHERE id = $1 AND user_id = $2`, [id, userId]);
  return rowCount > 0;
}

module.exports = {
  ensureFavoritesTable,
  listFavoritesByUser,
  addFavorite,
  deleteFavorite,
};
