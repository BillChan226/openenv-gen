import React from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import { ToastProvider } from './components/ui/Toast';
import { useAuth } from './contexts/AuthContext';

import Home from './pages/Home';
import FlightsResults from './pages/FlightsResults';
import FlightDetail from './pages/FlightDetail';
import StaysResults from './pages/StaysResults';
import HotelDetail from './pages/HotelDetail';

import CarsResultsPage from './pages/CarsResultsPage';
import CarDetailsPage from './pages/CarDetailsPage';
import PackagesPage from './pages/PackagesPage';
import FavoritesPage from './pages/FavoritesPage';
import CartPage from './pages/CartPage';
import CheckoutPage from './pages/CheckoutPage';
import TripsPage from './pages/TripsPage';
import ProfilePage from './pages/ProfilePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

import NotFound from './pages/NotFound';

function RequireAuth({ children }) {
  const { isAuthed, loading } = useAuth();
  const location = useLocation();
  if (loading) return children;
  if (!isAuthed) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return children;
}

export default function App() {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <Header />
        <main className="min-h-[70vh]">
          <Routes>
            <Route path="/" element={<Home />} />

            <Route path="/flights" element={<FlightsResults />} />
            <Route path="/flights/:flightId" element={<FlightDetail />} />

            <Route path="/hotels" element={<StaysResults />} />
            <Route path="/hotels/:hotelId" element={<HotelDetail />} />

            <Route path="/cars" element={<CarsResultsPage />} />
            <Route path="/cars/:carId" element={<CarDetailsPage />} />

            <Route path="/packages" element={<PackagesPage />} />

            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route
              path="/cart"
              element={
                <RequireAuth>
                  <CartPage />
                </RequireAuth>
              }
            />
            <Route
              path="/checkout"
              element={
                <RequireAuth>
                  <CheckoutPage />
                </RequireAuth>
              }
            />

            <Route
              path="/trips"
              element={
                <RequireAuth>
                  <TripsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/favorites"
              element={
                <RequireAuth>
                  <FavoritesPage />
                </RequireAuth>
              }
            />

            <Route
              path="/profile"
              element={
                <RequireAuth>
                  <ProfilePage />
                </RequireAuth>
              }
            />

            <Route path="/404" element={<NotFound />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </ToastProvider>
  );
}
