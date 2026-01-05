import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import AppShell from './components/layout/AppShell.jsx';
import HomePage from './pages/HomePage.jsx';
import RestaurantPage from './pages/RestaurantPage.jsx';
import PharmacyPage from './pages/PharmacyPage.jsx';
import FavoritesPage from './pages/FavoritesPage.jsx';
import CheckoutPage from './pages/CheckoutPage.jsx';
import OrderDetailPage from './pages/OrderDetailPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';

// Existing pages (kept for backwards compatibility / internal reuse)
import Home from './pages/Home.jsx';
import Store from './pages/Store.jsx';
import Goods from './pages/Goods.jsx';
import Grocery from './pages/Grocery.jsx';
import Retail from './pages/Retail.jsx';
import Orders from './pages/Orders.jsx';
import Account from './pages/Account.jsx';
import Login from './pages/Login.jsx';
import NotFound from './pages/NotFound.jsx';

import { AuthProvider, useAuth } from './contexts/AuthContext.jsx';
import { CartProvider } from './contexts/CartContext.jsx';

function RequireAuth({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 px-6 py-4 text-zinc-700">
          Loading…
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
        <Routes>
          <Route element={<AppShell />}>
            {/* Spec routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/grocery" element={<Grocery />} />
            <Route path="/retail" element={<Retail />} />
            <Route path="/pharmacy" element={<PharmacyPage />} />
            <Route path="/restaurants/:restaurantId" element={<RestaurantPage />} />

            <Route
              path="/orders"
              element={
                <RequireAuth>
                  <Orders />
                </RequireAuth>
              }
            />
            <Route
              path="/orders/:orderId"
              element={
                <RequireAuth>
                  <OrderDetailPage />
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
              path="/checkout"
              element={
                <RequireAuth>
                  <CheckoutPage />
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

            {/* Backwards compatible routes */}
            <Route path="/goods" element={<Goods />} />
            <Route path="/store/:storeId" element={<Store />} />
            <Route
              path="/account"
              element={
                <RequireAuth>
                  <Account />
                </RequireAuth>
              }
            />
            <Route path="/restaurants" element={<Navigate to="/" replace />} />
          </Route>

          {/* Minimal layout routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;
