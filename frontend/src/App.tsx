import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';

const ShopPage = lazy(() => import('./pages/ShopPage'));
const ConnectCompanionPage = lazy(() => import('./pages/ConnectCompanionPage'));

function PageLoader() {
  return <div className="route-loader" role="status" aria-live="polite"><span aria-hidden="true" />Opening VALSHOP</div>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<LoginPage />} />
              <Route path="/connect-companion" element={<ProtectedRoute><ConnectCompanionPage /></ProtectedRoute>} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <ShopPage />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  );
}
