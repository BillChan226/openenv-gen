import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import { env } from './src/config/env.js';
import { notFound, errorHandler } from './src/middleware/error.js';

import healthRoutes from './src/routes/health.js';
import authRoutes from './src/routes/auth.js';
import usersRoutes from './src/routes/users.js';
import locationsRoutes from './src/routes/locations.js';
import flightsRoutes from './src/routes/flights.js';
import hotelsRoutes from './src/routes/hotels.js';
import carsRoutes from './src/routes/cars.js';
import packagesRoutes from './src/routes/packages.js';
import favoritesRoutes from './src/routes/favorites.js';
import cartRoutes from './src/routes/cart.js';
import checkoutRoutes from './src/routes/checkout.js';
import tripsRoutes from './src/routes/trips.js';

const app = express();

app.use(helmet());
app.use(
  cors({
    origin: env.CORS_ORIGIN === '*' ? true : env.CORS_ORIGIN,
    credentials: true
  })
);
app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));

// No /api prefix per spec
app.use(healthRoutes);
app.use(authRoutes);
app.use(usersRoutes);
app.use(locationsRoutes);
app.use(flightsRoutes);
app.use(hotelsRoutes);
app.use(carsRoutes);
app.use(packagesRoutes);
app.use(favoritesRoutes);
app.use(cartRoutes);
app.use(checkoutRoutes);
app.use(tripsRoutes);

app.use(notFound);
app.use(errorHandler);

app.listen(env.PORT, () => {
  // eslint-disable-next-line no-undef
  console.log(`Backend listening on http://localhost:${env.PORT}`);
});
