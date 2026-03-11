import { Navigate, useLocation } from 'react-router-dom';
import { useAuthContext } from '../context/AuthContext';

type Role = 'admin' | 'teacher' | 'student';

export function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: Role[];
}) {
  const { isAuthenticated, user } = useAuthContext();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && user && !roles.includes(user.role as Role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
