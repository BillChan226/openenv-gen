import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
let morgan;
try {
  // Optional dependency: if morgan isn't installed, we still want the API to start.
  ({ default: morgan } = await import('morgan'));
} catch {
  morgan = null;
}

import { errorHandler, notFoundHandler } from './src/middleware/error.js';

import healthRoutes from './src/routes/health.js';
import authRoutes from './src/routes/auth.js';
import restaurantCategoriesRoutes from './src/routes/restaurantCategories.js';
import restaurantsRoutes from './src/routes/restaurants.js';
import searchRoutes from './src/routes/search.js';
import recentSearchesRoutes from './src/routes/recentSearches.js';
import profileAddressesRoutes from './src/routes/profileAddresses.js';
import profilePaymentMethodsRoutes from './src/routes/profilePaymentMethods.js';
import favoritesRoutes from './src/routes/favorites.js';
import promoCodesRoutes from './src/routes/promoCodes.js';
import cartRoutes from './src/routes/cart.js';
import ordersRoutes from './src/routes/orders.js';

dotenv.config();

const app = express();

// Helpful request logging to stdout (Docker captures this)
// Use LOG_FORMAT=combined for more detailed logs.
const logFormat = process.env.LOG_FORMAT || (process.env.NODE_ENV === 'production' ? 'combined' : 'dev');
if (morgan) {
  app.use(morgan(logFormat));
} else {
  console.warn('morgan not installed; request logging disabled');
}

app.use(
  cors({
    origin: process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN.split(',') : '*',
    credentials: true
  })
);
app.use(express.json({ limit: '1mb' }));

app.use('/api/health', healthRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/restaurant-categories', restaurantCategoriesRoutes);
app.use('/api/restaurants', restaurantsRoutes);
app.use('/api/search', searchRoutes);
app.use('/api/users/me/recent-searches', recentSearchesRoutes);
app.use('/api/profile/addresses', profileAddressesRoutes);
app.use('/api/profile/payment-methods', profilePaymentMethodsRoutes);
app.use('/api/favorites', favoritesRoutes);
app.use('/api/promo-codes', promoCodesRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/orders', ordersRoutes);

app.use(notFoundHandler);
app.use(errorHandler);

// Ensure runtime errors show up in container logs
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled promise rejection:', reason);
});
process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
});

const PORT = Number(process.env.PORT || 3000);
app.listen(PORT, () => {
  console.log(`FoodHub API listening on :${PORT}`);
});
