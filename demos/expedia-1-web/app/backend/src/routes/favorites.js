const express = require('express');

const { requireAuth } = require('../middleware/auth');
const { okResponse } = require('../utils/responses');
const favoritesModel = require('../models/favorites');

const router = express.Router();

router.get('/', requireAuth, async (req, res, next) => {
  try {
    await favoritesModel.ensureFavoritesTable();
    const items = await favoritesModel.listFavoritesByUser(req.user.id);
    return okResponse(res, { items });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const { type, itemId } = req.body || {};

    if (!type || !itemId) {
      const e = new Error('type and itemId are required');
      e.status = 400;
      e.code = 'VALIDATION_ERROR';
      throw e;
    }

    await favoritesModel.ensureFavoritesTable();
    const item = await favoritesModel.addFavorite({ userId: req.user.id, type, itemId });
    return okResponse(res, { item });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    await favoritesModel.ensureFavoritesTable();
    const ok = await favoritesModel.deleteFavorite({ userId: req.user.id, id: req.params.id });
    return okResponse(res, { ok });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
