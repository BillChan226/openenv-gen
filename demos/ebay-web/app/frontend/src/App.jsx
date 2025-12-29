import { Navigate, Route, Routes } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { Spinner } from './components/ui/Spinner.jsx';
import { AppLayout } from './components/layout/AppLayout.jsx';
import { ProtectedRoute } from './components/routing/ProtectedRoute.jsx';

const HomePage = lazy(() => import('./pages/HomePage.jsx'));
const CategoryPage = lazy(() => import('./pages/CategoryPage.jsx'));
const AdvancedSearchPage = lazy(() => import('./pages/AdvancedSearchPage.jsx'));
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'));
const AccountPage = lazy(() => import('./pages/AccountPage.jsx'));
const WishlistPage = lazy(() => import('./pages/WishlistPage.jsx'));
const CartPage = lazy(() => import('./pages/CartPage.jsx'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'));

export default function App() {
  return (
    <AppLayout>
      <Suspense
        fallback={
          <div className="container-page py-10">
            <div className="flex items-center justify-center py-16">
              <Spinner />
            </div>
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/category/:slug" element={<CategoryPage />} />
          <Route path="/advanced-search" element={<AdvancedSearchPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AccountPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/account/wishlist"
            element={
              <ProtectedRoute>
                <WishlistPage />
              </ProtectedRoute>
            }
          />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}
