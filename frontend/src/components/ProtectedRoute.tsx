import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === 'idle') {
    // Still checking session
    return null;
  }

  if (!state.sessionValid) {
    if (location.pathname !== '/') sessionStorage.setItem('post_login_path', `${location.pathname}${location.search}`);
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
