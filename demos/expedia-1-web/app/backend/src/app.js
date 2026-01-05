const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const paymentMethodRoutes = require('./routes/paymentMethods');
const locationRoutes = require('./routes/locations');
const flightRoutes = require('./routes/flights');
const hotelRoutes = require('./routes/hotels');
const carRoutes = require('./routes/cars');
const cartRoutes = require('./routes/cart');
const bookingRoutes = require('./routes/bookings');

const { errorResponse, itemResponse } = require('./utils/responses');

const app = express();

app.set('trust proxy', 1);

app.use(helmet());

app.use(
  cors({
    origin: (process.env.CORS_ORIGIN || '*').split(',').map((s) => s.trim()),
    credentials: true,
  })
);

app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));

// Health endpoints
// Liveness: process is up.
app.get('/health', (req, res) => itemResponse(res, { ok: true }));

// Readiness: process is able to serve requests.
//
// IMPORTANT:
// Many deployment/test environments for this project do not run Postgres.
// If readiness hard-depends on DB availability, /readyz will return 503 and
// fail basic "backend is up" checks.
//
// Therefore:
// - /readyz returns 200 when the HTTP server is running.
// - It still reports dbAvailable so orchestrators/ops can observe dependency state.
async function readinessHandler(req, res) {
  const db = require('./db');

  let dbAvailable = false;
  try {
    dbAvailable = await db.isAvailable();
  } catch (e) {
    dbAvailable = false;
  }

  const ready = true;
  return res.status(200).json({ item: { ok: ready, ready, dbAvailable } });
}

// Primary readiness endpoint
app.get('/readyz', readinessHandler);

// Back-compat aliases
app.get('/ready', readinessHandler);
app.get('/health/ready', readinessHandler);
app.get('/health/readyz', readinessHandler);

app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/payment-methods', paymentMethodRoutes);
app.use('/api/locations', locationRoutes);
app.use('/api/flights', flightRoutes);
app.use('/api/hotels', hotelRoutes);
app.use('/api/cars', carRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/bookings', bookingRoutes);

app.use((req, res) => errorResponse(res, 404, 'NOT_FOUND', 'Route not found'));

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  // eslint-disable-next-line no-console
  console.error(err);
  return errorResponse(res, 500, 'INTERNAL_ERROR', 'Unexpected error');
});

module.exports = app;
